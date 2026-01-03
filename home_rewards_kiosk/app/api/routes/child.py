from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.api.schemas import CashoutRequest, ClaimRequest, PlayRequest
from app.data.models import Goal
from app.data.repos import goals_repo
from app.domain.services import cashout_service, goal_service, wallet_service

router = APIRouter(prefix="/child")


@router.post("/{child_id}/claim")
def claim_goal(child_id: int, payload: ClaimRequest, session: Session = Depends(get_session)):
    goal = goals_repo.get_goal(session, payload.goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    instance = goal_service.claim_goal(session, goal, child_id)
    if instance.status == "approved":
        wallet_service.add_minutes(session, child_id, goal.reward_minutes)
    return {"instance_id": instance.id, "status": instance.status}


@router.post("/{child_id}/play/start")
def start_play(child_id: int, payload: PlayRequest, session: Session = Depends(get_session)):
    wallet = wallet_service.spend_minutes(session, child_id, payload.minutes)
    return {"minutes_balance": wallet.minutes_balance}


@router.post("/{child_id}/play/stop")
def stop_play(child_id: int, payload: PlayRequest, session: Session = Depends(get_session)):
    wallet = wallet_service.spend_minutes(session, child_id, payload.minutes)
    return {"minutes_balance": wallet.minutes_balance}


@router.post("/{child_id}/cashout/request")
def request_cashout(child_id: int, payload: CashoutRequest, session: Session = Depends(get_session)):
    transaction = cashout_service.request_cashout(session, child_id, payload.minutes)
    return {"transaction_id": transaction.id, "status": transaction.status}
