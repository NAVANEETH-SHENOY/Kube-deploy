from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

# Setup templates directory
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

@router.get("/", response_class=HTMLResponse)
@router.get("/index.html", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/events", response_class=HTMLResponse)
async def events_page(request: Request):
    return templates.TemplateResponse("events.html", {"request": request})

@router.get("/event/{event_id}", response_class=HTMLResponse)
async def event_detail_page(request: Request, event_id: str):
    return templates.TemplateResponse("event_detail.html", {"request": request})

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@router.get("/admin/events/new", response_class=HTMLResponse)
async def admin_new_event(request: Request):
    return templates.TemplateResponse("admin_form.html", {"request": request})

@router.get("/admin/events/edit/{event_id}", response_class=HTMLResponse)
async def admin_edit_event(request: Request, event_id: str):
    return templates.TemplateResponse("admin_form.html", {"request": request})

@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@router.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    return templates.TemplateResponse("status.html", {"request": request})