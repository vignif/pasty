from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timezone
from dotenv import load_dotenv
import db

load_dotenv()

app = FastAPI()
router = APIRouter()

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load Jinja2 templates
templates = Jinja2Templates(directory="templates")


# Background task to delete expired entries
def delete_expired_entries_background():
    db.delete_expired_entries()


# Startup event
@app.on_event("startup")
def startup_event():
    try:
        db.initialize_db()
        print("Database initialized")
    except Exception as e:
        print(f"Error initializing database: {e}")


# Models
class TextPayload(BaseModel):
    content: str


# API ROUTES

@router.get("/api/count")
async def get_count():
    count = db.get_db_count()
    return JSONResponse(content={"count": count})


@router.post("/save")
def api_save(payload: TextPayload, background_tasks: BackgroundTasks, request: Request):
    background_tasks.add_task(delete_expired_entries_background)
    now = datetime.now(timezone.utc)
    id_ = db.generate_unique_id()
    ip_address = request.client.host
    db.insert_text(id_, payload.content, now, now, ip_address)
    return {"id": id_}


@router.get("/get/{text_id}")
def api_get(text_id: str):
    db.delete_expired_entries()
    row = db.get_text_by_id(text_id)

    if row:
        db.update_last_accessed(text_id, datetime.now(timezone.utc))
        return {"content": row[0]}
    else:
        raise HTTPException(status_code=404, detail="ID not found")


# HTML ROUTES

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/submit", response_class=HTMLResponse)
def submit_form(request: Request, background_tasks: BackgroundTasks, content: str = Form(...)):
    if len(content) > 2000:
        raise HTTPException(status_code=400, detail="Text exceeds maximum allowed length.")

    background_tasks.add_task(delete_expired_entries_background)
    now = datetime.now(timezone.utc)
    id_ = db.generate_unique_id()
    ip_address = request.client.host
    db.insert_text(id_, content, now, now, ip_address)

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
        db.update_last_accessed(lookup_id, datetime.now(timezone.utc))
        return templates.TemplateResponse("index.html", {
            "request": request,
            "retrieved_content": row,
            "activate_retrieve": True,
            "lookup_id": lookup_id
        })
    else:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "ID not found",
            "activate_retrieve": True,
            "lookup_id": lookup_id
        })


# Include the router
app.include_router(router)
