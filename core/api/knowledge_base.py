"""
Knowledge Base API endpoints for PDF upload and embedding creation
"""
import os
import uuid
import shutil
import asyncio
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Request, Form
from pydantic import BaseModel

from core.auth.dependencies import get_current_user
from rag_agent.build_kb_simple import build_text_index

router = APIRouter(prefix="/api/kb", tags=["knowledge_base"])

class KBStatus(BaseModel):
    status: str
    message: str
    progress: int = 0
    files_processed: int = 0
    total_files: int = 0

class KBBuildResponse(BaseModel):
    task_id: str
    status: str
    message: str

# In-memory task storage (in production, use Redis or database)
kb_build_tasks = {}

def update_task_status(task_id: str, status: str, message: str, progress: int = 0, 
                      files_processed: int = 0, total_files: int = 0):
    """Update task status in memory"""
    kb_build_tasks[task_id] = {
        "status": status,
        "message": message,
        "progress": progress,
        "files_processed": files_processed,
        "total_files": total_files,
        "timestamp": asyncio.get_event_loop().time()
    }

async def build_knowledge_base_task(task_id: str, pdf_files: List[str], user_id: str, collection_name: str = "documents"):
    """Background task to build knowledge base"""
    try:
        update_task_status(task_id, "processing", "Starting knowledge base creation...", 10, 0, len(pdf_files))

        # Update progress to 30%
        update_task_status(
            task_id, "processing", "Extracting text from PDFs...", 30, 0, len(pdf_files)
        )

        # Run the build process using ChromaDB
        result = build_text_index(
            pdf_paths=pdf_files,
            collection_name=collection_name,  # Use dynamic collection name
            chunk_size=500,
            chunk_overlap=50,
            reset_collection=False,  # Append to existing collection
        )

        # Update progress to 90%
        update_task_status(
            task_id,
            "processing",
            "Finalizing ChromaDB collection...",
            90,
            len(pdf_files),
            len(pdf_files),
        )

        # Create completion message with duplicate information
        if result['duplicates_skipped'] > 0 and result['new_documents'] == 0:
            # All files were duplicates
            completion_msg = f"All {result['duplicates_skipped']} file(s) already exist in knowledge base. No new documents added."
        elif result['duplicates_skipped'] > 0:
            # Mixed: some new, some duplicates
            completion_msg = f"Knowledge base updated! Added {result['new_documents']} new document(s), {result['duplicates_skipped']} duplicate(s) skipped."
        else:
            # All new files
            completion_msg = f"Knowledge base updated! Added {result['new_documents']} new document(s)."

        # Complete
        update_task_status(task_id, "completed", completion_msg, 100, len(pdf_files), len(pdf_files))

    except Exception as e:
        update_task_status(task_id, "error", f"Error building knowledge base: {str(e)}", 0, 0, len(pdf_files))

@router.post("/upload", response_model=KBBuildResponse)
async def upload_pdfs_and_build_kb(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    session_id: str = Form(None),
    current_user = Depends(get_current_user)
):
    """
    Upload PDF files and start knowledge base building process
    Supports both session-specific and unified knowledge bases
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Get user ID
    user_id = str(current_user["_id"])

    # Determine collection name based on session
    collection_name = "documents"  # Default to unified KB
    rag_mode = "unified_kb"

    if session_id:
        # Get session from database to check rag_mode
        db = request.app.state.db
        session = await db.get_session_by_id(session_id, user_id)

        if session:
            rag_mode = session.get("rag_mode", "unified_kb")

            if rag_mode == "specific_files":
                # Use session-specific collection
                collection_name = f"session_{session_id}"
                print(f"📁 Using session-specific collection: {collection_name}")
            else:
                print(f"🗄️ Using unified KB collection: {collection_name}")

    # Validate files
    pdf_files = []
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")
        if file.size > 50 * 1024 * 1024:  # 50MB limit per file
            raise HTTPException(status_code=400, detail=f"File {file.filename} is too large (max 50MB)")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 10:  # Maximum 10 files at once
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed at once")
    
    # Create user-specific upload directory
    user_id = str(current_user["_id"])
    upload_dir = os.path.join("data", "uploads", user_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Create task ID
    task_id = str(uuid.uuid4())
    
    try:
        # Save uploaded files
        saved_files = []
        for file in files:
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(file_path)
            pdf_files.append(file_path)
        
        # Initialize task status
        mode_info = f"({rag_mode}: {collection_name})"
        update_task_status(task_id, "uploading", f"Files uploaded successfully {mode_info}", 5, 0, len(files))

        # Start background task with collection name
        background_tasks.add_task(build_knowledge_base_task, task_id, pdf_files, user_id, collection_name)
        
        return KBBuildResponse(
            task_id=task_id,
            status="started",
            message=f"Knowledge base building started for {len(files)} files"
        )
        
    except Exception as e:
        # Clean up uploaded files on error
        for file_path in saved_files:
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

@router.get("/status/{task_id}", response_model=KBStatus)
async def get_kb_build_status(task_id: str, current_user = Depends(get_current_user)):
    """
    Get the status of a knowledge base building task
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if task_id not in kb_build_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = kb_build_tasks[task_id]
    
    return KBStatus(
        status=task["status"],
        message=task["message"],
        progress=task["progress"],
        files_processed=task["files_processed"],
        total_files=task["total_files"]
    )

@router.get("/info")
async def get_kb_info(current_user = Depends(get_current_user)):
    """
    Get information about the current knowledge base (ChromaDB)
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    import chromadb
    from chromadb.config import Settings

    data_dir = "data"
    chroma_db_dir = os.path.join(data_dir, "chroma_db")

    has_chromadb = os.path.exists(chroma_db_dir)
    collection_info = {}

    if has_chromadb:
        try:
            client = chromadb.PersistentClient(
                path=chroma_db_dir, settings=Settings(anonymized_telemetry=False)
            )
            # Try to get the documents collection
            try:
                collection = client.get_collection(name="documents")
                collection_info = {"name": "documents", "count": collection.count(), "exists": True}
            except:
                collection_info = {"name": "documents", "count": 0, "exists": False}
        except Exception as e:
            collection_info = {"error": str(e)}

    # Calculate ChromaDB directory size
    chroma_size = 0
    if has_chromadb:
        for dirpath, dirnames, filenames in os.walk(chroma_db_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                chroma_size += os.path.getsize(filepath)

    return {
        "has_knowledge_base": has_chromadb and collection_info.get("exists", False),
        "storage_type": "chromadb",
        "chromadb_exists": has_chromadb,
        "collection": collection_info,
        "storage_size_bytes": chroma_size,
        "storage_size_mb": round(chroma_size / (1024 * 1024), 2),
    }

@router.delete("/clear")
async def clear_knowledge_base(current_user = Depends(get_current_user)):
    """
    Clear the current knowledge base (delete ChromaDB collection)
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    import chromadb
    from chromadb.config import Settings

    data_dir = "data"
    chroma_db_dir = os.path.join(data_dir, "chroma_db")

    removed_count = 0

    # Try to delete the documents collection from ChromaDB
    if os.path.exists(chroma_db_dir):
        try:
            client = chromadb.PersistentClient(
                path=chroma_db_dir, settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            try:
                client.delete_collection(name="documents")
                removed_count += 1
            except:
                pass  # Collection might not exist
        except Exception as e:
            print(f"Error clearing ChromaDB: {e}")

    return {
        "message": f"Knowledge base cleared successfully ({removed_count} collections removed)",
        "cleared": True,
        "storage_type": "chromadb",
    }
