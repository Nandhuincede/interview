import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.db.database import engine, Base
from app.api import candidate, speech, interview
from typing import Union

# Initialize database tables on server startup (SQLite auto-creation)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-Ready AI-Powered Voice Interview System Backend with LangGraph Multi-Agent workflows.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration to allow local access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(candidate.router, prefix=settings.API_V1_STR)
app.include_router(speech.router, prefix=settings.API_V1_STR)
app.include_router(interview.router, prefix=settings.API_V1_STR)

# Ensure static folder exists
os.makedirs("app/static", exist_ok=True)

# Mount Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_model=None)
def serve_frontend():
    """
    Serves the premium, self-contained AI interview dashboard.
    """
    index_path = "app/static/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "message": "Frontend files not found. Please write index.html to app/static.",
        "docs": "/docs"
    }
