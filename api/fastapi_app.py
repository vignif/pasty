
"""
api/fastapi_app.py

FastAPI application for Pasty serverless deployment. Handles API endpoints, background tasks, and integrates Socket.IO for real-time updates.
"""

from fastapi import FastAPI, Request, APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
from dotenv import load_dotenv
import socketio
import db
import logging
import os
import asyncio
import time

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Socket.IO setup
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=[])
socket_app = socketio.ASGIApp(sio)

# FastAPI app and router
# Support deployment under a path prefix (e.g., /pasty) via ROOT_PATH env and/or proxy header
ROOT_PATH = os.getenv("ROOT_PATH", "")
app = FastAPI(root_path=ROOT_PATH)
router = APIRouter()

# Mount static directory for JS, CSS, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Optional: also mount static under an alternate prefix if the proxy doesn't strip
ALT_STATIC_PREFIX = os.getenv("ALT_STATIC_PREFIX", "").rstrip("/")
if ALT_STATIC_PREFIX:
    mount_path = f"{ALT_STATIC_PREFIX}/static"
    if not mount_path.startswith("/"):
        mount_path = "/" + mount_path
    app.mount(mount_path, StaticFiles(directory="static"), name="static_alt")

# Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Middleware to respect X-Forwarded-Prefix from Caddy and similar proxies
class PrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        prefix = request.headers.get('x-forwarded-prefix') or request.headers.get('X-Forwarded-Prefix')
        if prefix:
            request.scope['root_path'] = prefix.rstrip('/')
        response = await call_next(request)
        return response

app.add_middleware(PrefixMiddleware)

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

# ---- Simple Rate Limiter (30 per minute) ----
RATE_LIMIT_PER_MINUTE = 30
_rate_buckets = {}
_rate_lock = asyncio.Lock()

def _client_ip(request: Request) -> str:
    ip = request.headers.get('cf-connecting-ip')
    if not ip:
        xff = request.headers.get('x-forwarded-for')
        if xff:
            ip = xff.split(',')[0].strip()
    if not ip:
        ip = request.headers.get('x-real-ip')
    if not ip and request.client:
        ip = request.client.host
    return ip or 'unknown'

async def rate_limit_ping(request: Request):
    now = int(time.time())
    window = now // 60
    ip = _client_ip(request)
    key = (ip, window)
    async with _rate_lock:
        for (k_ip, k_win) in list(_rate_buckets.keys()):
            if k_win < window - 1:
                _rate_buckets.pop((k_ip, k_win), None)
        count = _rate_buckets.get(key, 0) + 1
        _rate_buckets[key] = count
        if count > RATE_LIMIT_PER_MINUTE:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

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

@app.get("/readme", response_class=HTMLResponse)
def read_me(request: Request):
    return templates.TemplateResponse("readme.html", {
        "request": request,
        "EXPIRATION_HOURS": db.EXPIRATION_HOURS
    })

@app.get("/ping")
async def ping_route(_: None = Depends(rate_limit_ping)):
    return {"status": "ok"}

# Mount Socket.IO app
app.mount("/socket.io", socket_app)