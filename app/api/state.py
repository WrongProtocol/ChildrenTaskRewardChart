from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain.services import build_state
from app.schemas.state import StateResponse

router = APIRouter()


@router.get("/api/state", response_model=StateResponse)
def get_state(db: Session = Depends(get_db)):
    return build_state(db)
