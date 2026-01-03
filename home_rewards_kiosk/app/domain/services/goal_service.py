from datetime import date, datetime

from sqlalchemy.orm import Session

from app.data.models import Goal, GoalInstance
from app.data.repos import goals_repo


def claim_goal(session: Session, goal: Goal, child_id: int) -> GoalInstance:
    today = date.today()
    existing = goals_repo.find_goal_instance(session, goal.id, child_id, today)
    if existing and existing.status == "approved":
        return existing

    instance = existing or GoalInstance(goal_id=goal.id, child_id=child_id, date=today)
    instance.status = "pending"
    instance.claimed_at = datetime.utcnow()

    if goal.auto_approve:
        instance.status = "approved"
        instance.approved_at = datetime.utcnow()

    if existing:
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance

    return goals_repo.create_goal_instance(session, instance)
