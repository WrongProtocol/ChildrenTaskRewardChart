"""
Public state API endpoint.
Returns complete kiosk state including all children, their tasks, and progress.
This endpoint requires no authentication (used by kiosk display).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain.services import build_state
from app.schemas.state import StateResponse

router = APIRouter()


@router.get("/api/state", response_model=StateResponse)
def get_state(db: Session = Depends(get_db)):
    """
    Get complete kiosk state for display.
    Includes all children, their tasks organized by category and status,
    progress percentages, and today's date.
    
    Returns:
        StateResponse with children array, tasks, completion stats, and date
    """
    return build_state(db)
