from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timezone
from dotenv import load_dotenv
import socketio
import json
import db
import logging
import asyncio

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
    content: str

# ---- Utility Functions ----

def delete_expired_entries_background():
    db.delete_expired_entries()

async def update_row_count():
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
        await sio.emit('save_error', {'error': str(e)}, room=sid)

@sio.event
async def retrieve_text(sid, text_id):
    try:
        db.delete_expired_entries()
        row = db.get_text_by_id(text_id)
        
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
        await sio.emit('retrieve_error', {'error': str(e)}, room=sid)

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

# Mount Socket.IO app
app.mount("/socket.io", socket_app)