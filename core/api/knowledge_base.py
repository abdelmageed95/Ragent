"""
Knowledge Base API endpoints for PDF upload and embedding creation
"""
import os
import uuid
import shutil
import asyncio
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.auth.dependencies import get_current_user
from rag_agent.build_kb import build_and_save_indices

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

async def build_knowledge_base_task(task_id: str, pdf_files: List[str], user_id: str):
    """Background task to build knowledge base"""
    try:
        update_task_status(task_id, "processing", "Starting knowledge base creation...", 10, 0, len(pdf_files))
        
        # Update progress to 30%
        update_task_status(task_id, "processing", "Analyzing PDF pages...", 30, 0, len(pdf_files))
        
        # Run the build process
        build_and_save_indices(pdf_files)
        
        # Update progress to 90%
        update_task_status(task_id, "processing", "Finalizing indices...", 90, len(pdf_files), len(pdf_files))
        
        # Complete
        update_task_status(task_id, "completed", "Knowledge base created successfully!", 100, len(pdf_files), len(pdf_files))
        
    except Exception as e:
        update_task_status(task_id, "error", f"Error building knowledge base: {str(e)}", 0, 0, len(pdf_files))

@router.post("/upload", response_model=KBBuildResponse)
async def upload_pdfs_and_build_kb(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_user)
):
    """
    Upload PDF files and start knowledge base building process
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
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
        update_task_status(task_id, "uploading", "Files uploaded successfully", 5, 0, len(files))
        
        # Start background task
        background_tasks.add_task(build_knowledge_base_task, task_id, pdf_files, user_id)
        
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
    Get information about the current knowledge base
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    data_dir = "data"
    text_index_path = os.path.join(data_dir, "faiss_text.index")
    image_index_path = os.path.join(data_dir, "faiss_image.index")
    text_meta_path = os.path.join(data_dir, "text_docs_info.pkl")
    image_meta_path = os.path.join(data_dir, "image_docs_info.pkl")
    
    has_text_index = os.path.exists(text_index_path)
    has_image_index = os.path.exists(image_index_path)
    has_text_meta = os.path.exists(text_meta_path)
    has_image_meta = os.path.exists(image_meta_path)
    
    return {
        "has_knowledge_base": has_text_index or has_image_index,
        "text_index_exists": has_text_index,
        "image_index_exists": has_image_index,
        "text_meta_exists": has_text_meta,
        "image_meta_exists": has_image_meta,
        "index_files": {
            "text_index_size": os.path.getsize(text_index_path) if has_text_index else 0,
            "image_index_size": os.path.getsize(image_index_path) if has_image_index else 0,
        }
    }

@router.delete("/clear")
async def clear_knowledge_base(current_user = Depends(get_current_user)):
    """
    Clear the current knowledge base (delete indices and metadata)
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    data_dir = "data"
    files_to_remove = [
        os.path.join(data_dir, "faiss_text.index"),
        os.path.join(data_dir, "faiss_image.index"),
        os.path.join(data_dir, "text_docs_info.pkl"),
        os.path.join(data_dir, "image_docs_info.pkl")
    ]
    
    removed_count = 0
    for file_path in files_to_remove:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                removed_count += 1
        except Exception as e:
            print(f"Error removing {file_path}: {e}")
    
    # Also clear image preview files
    try:
        for file in os.listdir(data_dir):
            if file.endswith('.png') and '_img_' in file:
                os.remove(os.path.join(data_dir, file))
                removed_count += 1
    except Exception as e:
        print(f"Error clearing preview images: {e}")
    
    return {
        "message": f"Knowledge base cleared successfully ({removed_count} files removed)",
        "cleared": True
    }