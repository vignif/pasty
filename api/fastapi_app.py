from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timezone
from dotenv import load_dotenv
from mangum import Mangum
import db  # your own database module

load_dotenv()

# Create FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def startup_event():
    try:
        db.initialize_db()
        print("Database initialized")
    except Exception as e:
        print(f"Error initializing database: {e}")
    

# Background task to delete expired entries
def delete_expired_entries_background():
    db.delete_expired_entries()


# Pydantic model for API input (JSON body)
class TextPayload(BaseModel):
    content: str


# Web Routes
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/submit", response_class=HTMLResponse)
def submit_form(
    request: Request,
    background_tasks: BackgroundTasks,
    content: str = Form(...)
):
    # Add background task to delete expired entries
    background_tasks.add_task(delete_expired_entries_background)
    # Get current timestamp and generate unique ID
    now = datetime.now(timezone.utc).isoformat()
    id_ = db.generate_unique_id()
    # Insert text into DB
    db.insert_text(id_, content, now, now)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "id": id_,
        "content": content
    })


@app.get("/retrieve", response_class=HTMLResponse)
def retrieve_form(request: Request, lookup_id: str = ""):
    db.delete_expired_entries()
    row = db.get_text_by_id(lookup_id)
    if row:
        # Update last accessed time when retrieving content
        now = datetime.now(timezone.utc).isoformat()
        db.update_last_accessed(lookup_id, now)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "retrieved_content": row[0],
            "activate_retrieve": True
        })
    else:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "ID not found",
            "activate_retrieve": True
        })


# API Endpoints (JSON-based)
@app.post("/save")
def api_save(payload: TextPayload, background_tasks: BackgroundTasks):
    background_tasks.add_task(delete_expired_entries_background)
    now = datetime.now(timezone.utc).isoformat()
    id_ = db.generate_unique_id()
    db.insert_text(id_, payload.content, now, now)
    return {"id": id_}


@app.get("/get/{text_id}")
def api_get(text_id: str):
    db.delete_expired_entries()
    row = db.get_text_by_id(text_id)
    if row:
        db.update_last_accessed(text_id, datetime.now(timezone.utc).isoformat())
        return {"content": row[0]}
    else:
        raise HTTPException(status_code=404, detail="ID not found")

# Lambda handler for serverless execution using Mangum
handler = Mangum(app)
