from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain import services

router = APIRouter()


@router.post("/api/child/{child_id}/tasks/{task_id}/claim")
def claim_task(child_id: int, task_id: int, db: Session = Depends(get_db)):
    error = services.claim_task(db, child_id, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.post("/api/child/{child_id}/tasks/{task_id}/unclaim")
def unclaim_task(child_id: int, task_id: int, db: Session = Depends(get_db)):
    error = services.unclaim_task(db, child_id, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}
