from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.api.schemas import KioskStateOut
from app.data.models import Child, Goal, GoalInstance, Settings, Wallet

router = APIRouter()


@router.get("/kiosk/state", response_model=KioskStateOut)
def kiosk_state(session: Session = Depends(get_session)):
    return {
        "children": session.query(Child).all(),
        "goals": session.query(Goal).all(),
        "instances": session.query(GoalInstance).all(),
        "wallets": session.query(Wallet).all(),
        "settings": session.query(Settings).first(),
    }
