"""
FastAPI application entry point for the Home Rewards Kiosk.
Sets up routes, database initialization, and serves static frontend files.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import child, parent, state
from app.data.database import Base, engine, SessionLocal
from app.domain.seed import seed_data
from app.domain.services import ensure_today_initialized

# Create FastAPI application instance
app = FastAPI(title="Home Rewards Kiosk")

# Include all API route routers (child, parent, and public state endpoints)
app.include_router(state.router)
app.include_router(child.router)
app.include_router(parent.router)

# Mount static files (HTML, CSS, JavaScript) from the static directory
static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def on_startup() -> None:
    """
    Application startup handler.
    - Creates all database tables if they don't exist
    - Seeds initial data (children, task templates)
    - Initializes today's task instances from templates
    """
    # Create all database tables defined in ORM models
    Base.metadata.create_all(bind=engine)
    
    # Get a database session
    db = SessionLocal()
    try:
        # Populate database with default children and task templates
        seed_data(db)
        # Create today's task instances from templates (weekday or weekend)
        ensure_today_initialized(db)
    finally:
        # Always close the database session
        db.close()


@app.get("/")
def root():
    """Serve the main HTML interface when user accesses the root path."""
    return FileResponse(static_dir / "index.html")
