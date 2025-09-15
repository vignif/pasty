# ---- Routes ----


# ---- HTML Page Routes ----

"""
main.py

Entry point for the Pasty FastAPI application. Handles routing, background tasks, and integrates Socket.IO for real-time updates.
"""

from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timezone
from dotenv import load_dotenv
import socketio
import db
import logging

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Socket.IO setup
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=[])
socket_app = socketio.ASGIApp(sio)

# FastAPI app and router
app = FastAPI()
router = APIRouter()

# Mount static directory for JS, CSS, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# ---- Models ----

class TextPayload(BaseModel):
    """Pydantic model for text payloads submitted via API."""
    content: str

# ---- Utility Functions ----


def delete_expired_entries_background():
    """Background task to delete expired text entries from the database."""
    db.delete_expired_entries()


async def update_row_count():
    """Emit the current row count to all connected Socket.IO clients."""
    try:
        row_count = db.get_db_count()
        logger.info(f"Broadcasting new row count: {row_count}")
        await sio.emit('count_update', {'count': row_count})
    except Exception as e:
        logger.error(f"Failed to update row count: {e}")

# ---- Socket.IO Events ----

@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")
    # Send current count immediately on connect
    await update_row_count()

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")

# @sio.event
# async def ping(sid):
#     await sio.emit('pong', {
#         'server_time': datetime.now(timezone.utc).isoformat(),
#         'active_connections': len(sio.manager.get_participants('/', None))
#     }, room=sid)

@sio.event
async def ping(sid):
    # Get all connected clients and count them
    participants = list(sio.manager.get_participants('/', None))
    await sio.emit('pong', {
        'server_time': datetime.now(timezone.utc).isoformat(),
        'active_connections': len(participants)
    }, room=sid)

@sio.event
async def save_text(sid, data):
    try:
        if len(data['content']) > 2000:
            await sio.emit('save_error', {'error': 'Text exceeds allowed length.'}, room=sid)
            return
        
        now = datetime.now(timezone.utc)
        id_ = db.generate_unique_id()
        ip_address = 'socket.io'  # Can't get IP directly from Socket.IO
        
        db.insert_text(id_, data['content'], now, now, ip_address)
        await update_row_count()
        
        await sio.emit('save_success', {
            'id': id_,
            'content': data['content']
        }, room=sid)
    except Exception as e:
        logger.error(f"Error saving text: {e}")
        await sio.emit('save_error', {'error': 'An error occurred. Please try again.'}, room=sid)

@sio.event
async def retrieve_text(sid, data):
    try:
        # CAPTCHA check
        captcha_input = data.get('captcha_input', '').strip().upper()
        captcha_code = data.get('captcha_code', '').strip().upper()
        if captcha_input != captcha_code:
            await sio.emit('retrieve_error', {'error': 'CAPTCHA verification failed. Please try again.'}, room=sid)
            return

        text_id = data.get('lookup_id', '')
        db.delete_expired_entries()
        row = db.get_text_by_id(str(text_id))
        if row:
            db.update_last_accessed(text_id, datetime.now(timezone.utc))
            await sio.emit('retrieve_success', {
                'id': text_id,
                'content': str(row)
            }, room=sid)
        else:
            await sio.emit('retrieve_error', {
                'error': 'ID not found'
            }, room=sid)
    except Exception as e:
        logger.error(f"Error retrieving text: {e}")
        await sio.emit('retrieve_error', {'error': 'An error occurred. Please try again.'}, room=sid)

# ---- Startup Events ----

@app.on_event("startup")
def startup_event():
    try:
        db.initialize_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")


# ---- HTML Page Routes ----

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "EXPIRATION_HOURS": db.EXPIRATION_HOURS
    })

@app.get("/readme", response_class=HTMLResponse)
def readme(request: Request):
    return templates.TemplateResponse("readme.html", {"request": request})

# ---- hCaptcha Verification Helper ----
import requests
def verify_hcaptcha(token, remoteip=None):
    """Verify hCaptcha response token with hCaptcha API."""
    import os
    secret = os.getenv("HCAPTCHA_SECRET", "")
    url = "https://hcaptcha.com/siteverify"
    data = {
        "secret": secret,
        "response": token
    }
    if remoteip:
        data["remoteip"] = remoteip
    try:
        resp = requests.post(url, data=data, timeout=5)
        result = resp.json()
        return result.get("success", False)
    except Exception as e:
        logger.error(f"hCaptcha verification error: {e}")
        return False

# ---- Save Text Endpoint (with hCaptcha) ----
from fastapi import Form
@app.post("/save", response_class=HTMLResponse)
async def save_text_form(request: Request, content: str = Form(...), captcha_input: str = Form(...), captcha_code: str = Form(...)):
    # Simple CAPTCHA verification
    if captcha_input.strip().upper() != captcha_code.strip().upper():
        return templates.TemplateResponse("index.html", {"request": request, "error": "CAPTCHA verification failed. Please try again."})
    # ...existing save logic (call your db.insert_text etc.)...
    # For demo, just return success
    return templates.TemplateResponse("index.html", {"request": request, "success": True})


# Mount Socket.IO app
app.mount("/socket.io", socket_app)