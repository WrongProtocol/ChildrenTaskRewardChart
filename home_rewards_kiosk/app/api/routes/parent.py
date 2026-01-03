from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.api.schemas import (
    ApprovalRequest,
    GoalCreateRequest,
    GoalUpdateRequest,
    SettingsOut,
    SettingsUpdateRequest,
    UnlockRequest,
    GoalOut,
)
from app.data.models import Goal, GoalInstance, Settings
from app.data.repos import goals_repo
from app.domain.services import approval_service, wallet_service
from app.security.pin import hash_pin, verify_pin

router = APIRouter(prefix="/parent")


def require_pin(session: Session, pin: str) -> Settings:
    settings = session.query(Settings).first()
    if not settings:
        raise HTTPException(status_code=500, detail="Settings not initialized")
    if not verify_pin(pin, settings.pin_salt, settings.pin_hash):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return settings


@router.post("/unlock")
def unlock(payload: UnlockRequest, session: Session = Depends(get_session)):
    require_pin(session, payload.pin)
    return {"unlocked": True}


@router.post("/approve")
def approve(payload: ApprovalRequest, pin: str, session: Session = Depends(get_session)):
    require_pin(session, pin)
    instance = session.get(GoalInstance, payload.instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    updated = approval_service.approve_instance(session, instance, payload.approve)
    if payload.approve:
        goal = session.get(Goal, updated.goal_id)
        if goal:
            wallet_service.add_minutes(session, updated.child_id, goal.reward_minutes)
    return {"status": updated.status}


@router.get("/goals", response_model=list[GoalOut])
def list_goals(pin: str, session: Session = Depends(get_session)):
    require_pin(session, pin)
    return goals_repo.list_goals(session)


@router.post("/goals", response_model=GoalOut)
def create_goal(payload: GoalCreateRequest, pin: str, session: Session = Depends(get_session)):
    require_pin(session, pin)
    goal = Goal(**payload.dict())
    return goals_repo.create_goal(session, goal)


@router.put("/goals/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, payload: GoalUpdateRequest, pin: str, session: Session = Depends(get_session)):
    require_pin(session, pin)
    goal = goals_repo.get_goal(session, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    updates = payload.dict(exclude_unset=True)
    for key, value in updates.items():
        setattr(goal, key, value)
    return goals_repo.update_goal(session, goal)


@router.delete("/goals/{goal_id}")
def delete_goal(goal_id: int, pin: str, session: Session = Depends(get_session)):
    require_pin(session, pin)
    goal = goals_repo.get_goal(session, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    goals_repo.delete_goal(session, goal)
    return {"deleted": True}


@router.get("/settings", response_model=SettingsOut)
def get_settings(pin: str, session: Session = Depends(get_session)):
    settings = require_pin(session, pin)
    return settings


@router.put("/settings", response_model=SettingsOut)
def update_settings(payload: SettingsUpdateRequest, pin: str, session: Session = Depends(get_session)):
    settings = require_pin(session, pin)
    updates = payload.dict(exclude_unset=True)
    if "pin" in updates:
        salt, pin_hash = hash_pin(updates.pop("pin"))
        settings.pin_salt = salt
        settings.pin_hash = pin_hash
    for key, value in updates.items():
        setattr(settings, key, value)
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings
