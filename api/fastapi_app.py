from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timezone
from dotenv import load_dotenv
import json
import db
import logging

# Import WebSocket logic
from websocket import notify_clients, manager

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        await notify_clients(row_count)
    except Exception as e:
        logger.error(f"Failed to update row count: {e}")

# ---- Startup Events ----

@app.on_event("startup")
def startup_event():
    try:
        db.initialize_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# ---- WebSocket Endpoint ----
@app.websocket("/ws/row-count")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Wait for any message (text or bytes)
            data = await websocket.receive()
            
            # Handle ping messages
            if isinstance(data, str):
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass  # Ignore non-JSON messages
                    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(websocket)

# ---- API Routes ----

@router.get("/api/count")
async def api_get_count():
    count = db.get_db_count()
    return JSONResponse(content={"count": count})

@router.post("/save")
async def api_save(payload: TextPayload, background_tasks: BackgroundTasks, request: Request):
    background_tasks.add_task(delete_expired_entries_background)
    now = datetime.now(timezone.utc)
    id_ = db.generate_unique_id()
    ip_address = request.client.host
    db.insert_text(id_, payload.content, now, now, ip_address)
    await update_row_count()
    return {"id": id_}

@router.get("/get/{text_id}")
def api_get(text_id: str):
    db.delete_expired_entries()
    row = db.get_text_by_id(text_id)
    if row:
        db.update_last_accessed(text_id, datetime.now(timezone.utc))
        return {"content": row[0]}
    raise HTTPException(status_code=404, detail="ID not found")

# ---- HTML Page Routes ----

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit", response_class=HTMLResponse)
async def submit_form(
    request: Request, 
    background_tasks: BackgroundTasks, 
    content: str = Form(...)
):
    if len(content) > 2000:
        raise HTTPException(status_code=400, detail="Text exceeds allowed length.")

    background_tasks.add_task(delete_expired_entries_background)
    now = datetime.now(timezone.utc)
    id_ = db.generate_unique_id()
    ip_address = request.client.host
    db.insert_text(id_, content, now, now, ip_address)
    await update_row_count()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "id": id_,
        "content": content
    })

@app.get("/retrieve", response_class=HTMLResponse)
def retrieve_form(request: Request, lookup_id: str = ""):
    db.delete_expired_entries()
    row = db.get_text_by_id(lookup_id)

    context = {
        "request": request,
        "activate_retrieve": True,
        "lookup_id": lookup_id
    }

    if row:
        db.update_last_accessed(lookup_id, datetime.now(timezone.utc))
        context["retrieved_content"] = row
    else:
        context["error"] = "ID not found"

    return templates.TemplateResponse("index.html", context)

# ---- Include the API Router ----
app.include_router(router)
