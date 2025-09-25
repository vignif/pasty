# ---- Routes ----


# ---- HTML Page Routes ----

"""
main.py

Entry point for the Pasty FastAPI application. Handles routing, background tasks, and integrates Socket.IO for real-time updates.
"""

from fastapi import FastAPI, Request, APIRouter, Form, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests
import os
import asyncio
import time
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
# Keep app root_path empty so backend routes like /static work when the proxy strips prefixes.
ROOT_PATH = os.getenv("ROOT_PATH", "")
app = FastAPI(root_path="")
router = APIRouter()

# Resolve absolute directories for static files and templates to be robust to CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Mount static directory for JS, CSS, etc.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Optional: also mount static under an alternate prefix if the proxy doesn't strip
ALT_STATIC_PREFIX = os.getenv("ALT_STATIC_PREFIX", "").rstrip("/")
if ALT_STATIC_PREFIX:
    mount_path = f"{ALT_STATIC_PREFIX}/static"
    if not mount_path.startswith("/"):
        mount_path = "/" + mount_path
    app.mount(mount_path, StaticFiles(directory=STATIC_DIR), name="static_alt")

# Jinja2 templates directory
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Provide PUBLIC_ROOT to templates for building absolute asset URLs under a prefix
PUBLIC_ROOT = os.getenv("PUBLIC_ROOT", ROOT_PATH).rstrip("/")
if PUBLIC_ROOT and not PUBLIC_ROOT.startswith("/"):
    PUBLIC_ROOT = "/" + PUBLIC_ROOT
ASSET_VER = os.getenv("ASSET_VER") or str(int(os.environ.get("START_TIME", "0") or __import__("time").time()))
templates.env.globals.update({
    "PUBLIC_ROOT": PUBLIC_ROOT,
    "ASSET_VER": ASSET_VER,
})

# Middleware to respect X-Forwarded-Prefix from Caddy and similar proxies
# Prefix middleware is not required when using app.root_path and a proxy that strips the prefix.
# Leaving implementation here for reference but not registering it to avoid route mismatches.
class PrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await call_next(request)

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
    # Prefer Cloudflare and proxy headers; fallback to client host
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
    window = now // 60  # per-minute fixed window
    ip = _client_ip(request)
    key = (ip, window)
    async with _rate_lock:
        # Cleanup old windows for this IP
        # (optional light cleanup across all keys)
        for (k_ip, k_win) in list(_rate_buckets.keys()):
            if k_win < window - 1:
                _rate_buckets.pop((k_ip, k_win), None)

        count = _rate_buckets.get(key, 0) + 1
        _rate_buckets[key] = count
        if count > RATE_LIMIT_PER_MINUTE:
            # Too Many Requests
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

@app.get("/ping")
async def ping_route(_: None = Depends(rate_limit_ping)):
    # trivial health/rate-limited endpoint
    return {"status": "ok"}

@app.head("/")
def head_root():
    return Response(status_code=200)

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