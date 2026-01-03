from datetime import datetime

from sqlalchemy.orm import Session

from app.data.models import GoalInstance


def approve_instance(session: Session, instance: GoalInstance, approve: bool) -> GoalInstance:
    instance.status = "approved" if approve else "open"
    instance.approved_at = datetime.utcnow() if approve else None
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance
