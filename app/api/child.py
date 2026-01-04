"""
Child-facing API endpoints.
Allows children to claim and unclaim tasks for parent approval.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain import services

router = APIRouter()


@router.post("/api/child/{child_id}/tasks/{task_id}/claim")
def claim_task(child_id: int, task_id: int, db: Session = Depends(get_db)):
    """
    Child claims a task, moving it from OPEN to PENDING state.
    Requires parent approval before task is considered complete.
    
    Args:
        child_id: ID of the child claiming the task
        task_id: ID of the task to claim
        db: Database session (auto-injected)
    
    Returns:
        Status confirmation if successful, or error details if failed
    """
    error = services.claim_task(db, child_id, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.post("/api/child/{child_id}/tasks/{task_id}/unclaim")
def unclaim_task(child_id: int, task_id: int, db: Session = Depends(get_db)):
    """
    Child unclaims a task, moving it back from PENDING to OPEN state.
    Allows children to abandon a task they've claimed but don't want to complete.
    
    Args:
        child_id: ID of the child unclaiming the task
        task_id: ID of the task to unclaim
        db: Database session (auto-injected)
    
    Returns:
        Status confirmation if successful, or error details if failed
    """
    error = services.unclaim_task(db, child_id, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}
