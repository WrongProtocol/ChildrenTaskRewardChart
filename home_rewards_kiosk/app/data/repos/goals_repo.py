from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.data.models import Goal, GoalInstance


def list_goals(session: Session) -> list[Goal]:
    return session.query(Goal).all()


def get_goal(session: Session, goal_id: int) -> Optional[Goal]:
    return session.get(Goal, goal_id)


def create_goal(session: Session, goal: Goal) -> Goal:
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


def update_goal(session: Session, goal: Goal) -> Goal:
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


def delete_goal(session: Session, goal: Goal) -> None:
    session.delete(goal)
    session.commit()


def find_goal_instance(session: Session, goal_id: int, child_id: int, on_date: date) -> Optional[GoalInstance]:
    return (
        session.query(GoalInstance)
        .filter(GoalInstance.goal_id == goal_id, GoalInstance.child_id == child_id, GoalInstance.date == on_date)
        .one_or_none()
    )


def create_goal_instance(session: Session, instance: GoalInstance) -> GoalInstance:
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


def list_pending_instances(session: Session) -> list[GoalInstance]:
    return session.query(GoalInstance).filter(GoalInstance.status == "pending").all()


def get_goal_instance(session: Session, instance_id: int) -> Optional[GoalInstance]:
    return session.get(GoalInstance, instance_id)
