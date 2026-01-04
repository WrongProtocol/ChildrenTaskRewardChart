from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import child, parent, state
from app.data.database import Base, engine, SessionLocal
from app.domain.seed import seed_data
from app.domain.services import ensure_today_initialized

app = FastAPI(title="Home Rewards Kiosk")

app.include_router(state.router)
app.include_router(child.router)
app.include_router(parent.router)

static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data(db)
        ensure_today_initialized(db)
    finally:
        db.close()


@app.get("/")
def root():
    return FileResponse(static_dir / "index.html")
