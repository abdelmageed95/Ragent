# Session Types Implementation - Agentic AI vs Agentic RAG

## ✅ What's Been Done

### 1. Dashboard - Session Creation (COMPLETED)
- Added visual session type selector with two options:
  - **🤖 Agentic AI** - General chat with tools
  - **📚 Agentic RAG** - Document Q&A with file uploads
- Updated JavaScript to send `session_type` parameter
- Added beautiful CSS styling for the selector

### 2. Chat Interface - File Upload Button (COMPLETED)
- Added "Add file to KB" button for RAG sessions
- Added file upload modal with drag & drop
- Button is hidden by default (will show only in RAG mode)

## 🔨 What Still Needs to Be Done

### 1. Add CSS for File Upload Elements

Add this CSS to `chat.html` in the `<style>` section:

```css
/* RAG Controls */
.rag-controls {
    margin-bottom: 12px;
    display: flex;
    justify-content: flex-end;
}

.add-file-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
}

.add-file-btn:hover {
    background: var(--primary);
    transform: translateY(-2px);
}

/* File Drop Zone */
.file-drop-zone {
    border: 2px dashed var(--border);
    border-radius: 12px;
    padding: 40px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-bottom: 16px;
}

.file-drop-zone:hover {
    border-color: var(--primary);
    background: rgba(49, 130, 206, 0.05);
}

.file-drop-zone i {
    font-size: 48px;
    margin-bottom: 12px;
    display: block;
}

.file-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    background: var(--secondary);
    border-radius: 8px;
    margin-bottom: 16px;
}

.remove-file {
    background: var(--error);
    color: white;
    border: none;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    cursor: pointer;
}
```

### 2. Add JavaScript for File Upload Handling

Add this JavaScript to `chat.html` in the `<script>` section:

```javascript
// Session type detection
let sessionType = 'ai';  // Default to AI mode

// Check session type from URL or metadata
function detectSessionType() {
    // Try to get from session data (you'll need to pass this from backend)
    const sessionData = document.getElementById('session-data');
    if (sessionData) {
        sessionType = sessionData.dataset.sessionType || 'ai';
    }

    // Show/hide controls based on session type
    if (sessionType === 'rag') {
        document.getElementById('rag-controls').style.display = 'flex';
        document.getElementById('mode-toggle').style.display = 'none';
        // Auto-select RAG mode
        document.getElementById('rag-mode').checked = true;
    } else {
        document.getElementById('rag-controls').style.display = 'none';
        document.getElementById('mode-toggle').style.display = 'flex';
    }
}

// File upload modal handlers
document.getElementById('add-file-btn').addEventListener('click', function() {
    document.getElementById('file-upload-modal').style.display = 'flex';
});

function closeFileUploadModal() {
    document.getElementById('file-upload-modal').style.display = 'none';
    document.getElementById('file-upload-form').reset();
    document.getElementById('file-info').style.display = 'none';
}

// File drop zone
const dropZone = document.getElementById('file-drop-zone');
const fileInput = document.getElementById('file-input');

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--primary)';
});

dropZone.addEventListener('dragleave', () => {
    dropZone.style.borderColor = 'var(--border)';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--border)';
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

function handleFile(file) {
    document.getElementById('file-name').textContent = file.name;
    document.getElementById('file-info').style.display = 'flex';
    document.getElementById('upload-btn').disabled = false;
}

function removeFile() {
    fileInput.value = '';
    document.getElementById('file-info').style.display = 'none';
    document.getElementById('upload-btn').disabled = true;
}

// File upload form submission
document.getElementById('file-upload-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/knowledge-base/upload', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            alert('File uploaded successfully!');
            closeFileUploadModal();
        } else {
            alert('Upload failed. Please try again.');
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('Upload failed. Please try again.');
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', detectSessionType);
```

### 3. Update Backend - Sessions API

Update `core/api/sessions.py` to handle `session_type`:

```python
@router.post("/sessions")
async def create_session(
    name: str = Body(...),
    description: Optional[str] = Body(None),
    session_type: str = Body("ai"),  # Add this
    current_user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(lambda: app.state.db)
):
    user_id = current_user["_id"]
    session_data = {
        "name": name,
        "description": description,
        "session_type": session_type,  # Store session type
        "created_at": datetime.utcnow().isoformat(),
        "user_id": user_id
    }

    session_id = await db.create_session(session_data)
    # ... rest of the code
```

### 4. Update Chat Page to Pass Session Type

In `main.py` or wherever you render the chat template, pass the session type:

```python
@app.get("/chat/{session_id}")
async def chat_page(
    request: Request,
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Get session from database
    session = await db.get_session(session_id)

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "session_id": session_id,
        "session_type": session.get("session_type", "ai"),  # Pass this
        "current_user": current_user
    })
```

And in `chat.html`, add this hidden element at the top:

```html
<div id="session-data"
     data-session-type="{{ session_type }}"
     style="display: none;"></div>
```

### 5. Update Chat Mode Routing

In `graph/supervisor.py`, update to handle session types:

```python
async def supervisor_node(state: Dict) -> Dict:
    session_type = state.get("session_type", "ai")

    # If session is RAG type, always route to RAG agent
    if session_type == "rag":
        selected_agent = "rag_agent"
        reason = "RAG session type"
    # Otherwise use existing logic
    elif chat_mode == 'rag' or chat_mode == 'my_resources':
        selected_agent = "rag_agent"
        # ... existing code
```

## 🎯 Expected Behavior

### Agentic AI Sessions (session_type='ai')
1. Shows mode toggle (General / My Resources)
2. No "Add file to KB" button
3. Routes to chatbot by default
4. Can switch to RAG mode via toggle

### Agentic RAG Sessions (session_type='rag')
1. Shows "Add file to KB" button
2. No mode toggle (always in RAG mode)
3. Always routes to RAG agent
4. Can upload files anytime during chat

## 📝 Testing Steps

1. Create new "Agentic AI" session → Should see mode toggle
2. Create new "Agentic RAG" session → Should see "Add file to KB" button
3. In RAG session, click "Add file to KB" → Modal opens
4. Upload a PDF file → File added to KB
5. Ask a question about the file → RAG retrieves info
6. In AI session, test calendar, calculator, web search

## 🐛 Known Issues to Fix

1. Need to update database schema to store `session_type`
2. Need to add session type indicator in session cards on dashboard
3. File upload endpoint needs to associate files with user/session
4. Consider adding file list view in RAG sessions

## 📚 Files Modified

1. `templates/dashboard.html` - Session creation UI ✅
2. `templates/chat.html` - File upload button and modal ✅
3. `core/api/sessions.py` - Session creation backend (TODO)
4. `graph/supervisor.py` - Routing logic (TODO)
5. `main.py` - Chat page rendering (TODO)

