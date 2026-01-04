import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.models import Child, DailyTaskInstance, Settings, TaskTemplateItem
from app.security.pin import hash_pin
from app.domain.seed import seed_data

CATEGORIES = ["SCHOOLWORK", "HYGIENE", "HELPFUL"]


def today_str() -> str:
    return datetime.date.today().isoformat()


def get_settings(session: Session) -> Settings:
    settings = session.execute(select(Settings)).scalar_one_or_none()
    if not settings:
        settings = Settings(
            parent_pin_hash=hash_pin("1234"),
            daily_reward_text="Playtime is unlocked!",
            last_reset_date=None,
        )
        session.add(settings)
        session.commit()
    return settings


def ensure_today_initialized(session: Session) -> None:
    seed_data(session)
    settings = get_settings(session)
    current_date = today_str()
    if settings.last_reset_date == current_date:
        return

    template_type = "WEEKEND" if datetime.date.today().weekday() >= 5 else "WEEKDAY"
    children = session.execute(select(Child).order_by(Child.display_order)).scalars().all()
    template_items = (
        session.execute(
            select(TaskTemplateItem)
            .where(TaskTemplateItem.template_type == template_type)
            .order_by(TaskTemplateItem.sort_order)
        )
        .scalars()
        .all()
    )

    for child in children:
        for item in template_items:
            if item.child_id is not None and item.child_id != child.id:
                continue
            session.add(
                DailyTaskInstance(
                    date=current_date,
                    child_id=child.id,
                    category=item.category,
                    title=item.title,
                    required=item.required,
                    reward_text=item.reward_text,
                    sort_order=item.sort_order,
                    state="OPEN",
                )
            )

    settings.last_reset_date = current_date
    session.commit()


def build_state(session: Session) -> Dict:
    ensure_today_initialized(session)
    current_date = today_str()
    settings = get_settings(session)
    children = session.execute(select(Child).order_by(Child.display_order)).scalars().all()
    tasks = (
        session.execute(select(DailyTaskInstance).where(DailyTaskInstance.date == current_date))
        .scalars()
        .all()
    )

    tasks_by_child: Dict[int, List[DailyTaskInstance]] = {}
    for task in tasks:
        tasks_by_child.setdefault(task.child_id, []).append(task)

    child_states = []
    for child in children:
        child_tasks = sorted(tasks_by_child.get(child.id, []), key=lambda t: (t.category, t.sort_order))
        categories = {category: [] for category in CATEGORIES}
        category_progress = {category: {"approved": 0, "total": 0} for category in CATEGORIES}
        approved_count = 0
        required_total = 0
        required_approved = 0
        for task in child_tasks:
            categories[task.category].append(
                {
                    "id": task.id,
                    "title": task.title,
                    "required": task.required,
                    "reward_text": task.reward_text,
                    "state": task.state,
                    "category": task.category,
                    "sort_order": task.sort_order,
                }
            )
            category_progress[task.category]["total"] += 1
            if task.state == "APPROVED":
                approved_count += 1
                category_progress[task.category]["approved"] += 1
            if task.required:
                required_total += 1
                if task.state == "APPROVED":
                    required_approved += 1

        total_count = len(child_tasks)
        percent_complete = int((approved_count / total_count) * 100) if total_count else 0
        unlocked = required_total == required_approved
        pending_count = len([t for t in child_tasks if t.state == "PENDING"])
        child_states.append(
            {
                "id": child.id,
                "name": child.name,
                "display_order": child.display_order,
                "percent_complete": percent_complete,
                "unlocked": unlocked,
                "pending_count": pending_count,
                "categories": categories,
                "category_progress": category_progress,
            }
        )

    return {
        "date": current_date,
        "children": child_states,
        "daily_reward_text": settings.daily_reward_text,
    }


def claim_task(session: Session, child_id: int, task_id: int) -> Optional[str]:
    task = session.get(DailyTaskInstance, task_id)
    if not task or task.child_id != child_id:
        return "Task not found"
    if task.state == "APPROVED":
        return "Task already approved"
    if task.state == "OPEN":
        task.state = "PENDING"
        task.claimed_at = datetime.datetime.utcnow()
        task.approved_at = None
    session.commit()
    return None


def unclaim_task(session: Session, child_id: int, task_id: int) -> Optional[str]:
    task = session.get(DailyTaskInstance, task_id)
    if not task or task.child_id != child_id:
        return "Task not found"
    if task.state == "PENDING":
        task.state = "OPEN"
        task.claimed_at = None
        task.approved_at = None
        session.commit()
    return None


def approve_task(session: Session, task_id: int) -> Optional[str]:
    task = session.get(DailyTaskInstance, task_id)
    if not task:
        return "Task not found"
    task.state = "APPROVED"
    if not task.claimed_at:
        task.claimed_at = datetime.datetime.utcnow()
    task.approved_at = datetime.datetime.utcnow()
    session.commit()
    return None


def reject_task(session: Session, task_id: int) -> Optional[str]:
    task = session.get(DailyTaskInstance, task_id)
    if not task:
        return "Task not found"
    task.state = "OPEN"
    task.claimed_at = None
    task.approved_at = None
    session.commit()
    return None


def revoke_task(session: Session, task_id: int) -> Optional[str]:
    task = session.get(DailyTaskInstance, task_id)
    if not task:
        return "Task not found"
    task.state = "OPEN"
    task.claimed_at = None
    task.approved_at = None
    session.commit()
    return None


def list_pending_tasks(session: Session) -> List[Dict]:
    current_date = today_str()
    pending_tasks = (
        session.execute(
            select(DailyTaskInstance, Child)
            .join(Child, DailyTaskInstance.child_id == Child.id)
            .where(DailyTaskInstance.date == current_date, DailyTaskInstance.state == "PENDING")
            .order_by(Child.display_order, DailyTaskInstance.category, DailyTaskInstance.sort_order)
        )
        .all()
    )
    result = []
    for task, child in pending_tasks:
        result.append(
            {
                "id": task.id,
                "child_id": child.id,
                "child_name": child.name,
                "title": task.title,
                "category": task.category,
            }
        )
    return result


def list_completed_tasks(session: Session) -> List[Dict]:
    current_date = today_str()
    completed_tasks = (
        session.execute(
            select(DailyTaskInstance, Child)
            .join(Child, DailyTaskInstance.child_id == Child.id)
            .where(DailyTaskInstance.date == current_date, DailyTaskInstance.state == "APPROVED")
            .order_by(Child.display_order, DailyTaskInstance.category, DailyTaskInstance.sort_order)
        )
        .all()
    )
    result = []
    for task, child in completed_tasks:
        result.append(
            {
                "id": task.id,
                "child_id": child.id,
                "child_name": child.name,
                "title": task.title,
                "category": task.category,
            }
        )
    return result


def create_today_task(session: Session, data: Dict) -> List[int]:
    current_date = today_str()
    child_id = data.get("child_id")
    children = (
        [session.get(Child, child_id)]
        if child_id
        else session.execute(select(Child).order_by(Child.display_order)).scalars().all()
    )
    created_ids = []
    for child in children:
        if not child:
            continue
        task = DailyTaskInstance(
            date=current_date,
            child_id=child.id,
            category=data["category"],
            title=data["title"],
            required=data["required"],
            reward_text=data.get("reward_text"),
            sort_order=data["sort_order"],
            state="OPEN",
        )
        session.add(task)
        session.flush()
        created_ids.append(task.id)
    session.commit()
    return created_ids


def update_today_task(session: Session, task_id: int, data: Dict) -> Optional[str]:
    task = session.get(DailyTaskInstance, task_id)
    if not task:
        return "Task not found"
    for field in ["category", "title", "required", "reward_text", "sort_order"]:
        if field in data and data[field] is not None:
            setattr(task, field, data[field])
    session.commit()
    return None


def delete_today_task(session: Session, task_id: int) -> Optional[str]:
    task = session.get(DailyTaskInstance, task_id)
    if not task:
        return "Task not found"
    session.delete(task)
    session.commit()
    return None


def list_templates(session: Session) -> List[Dict]:
    items = (
        session.execute(select(TaskTemplateItem).order_by(TaskTemplateItem.template_type, TaskTemplateItem.sort_order))
        .scalars()
        .all()
    )
    return [
        {
            "id": item.id,
            "template_type": item.template_type,
            "category": item.category,
            "title": item.title,
            "required": item.required,
            "reward_text": item.reward_text,
            "sort_order": item.sort_order,
            "child_id": item.child_id,
        }
        for item in items
    ]


def create_template_task(session: Session, data: Dict) -> int:
    item = TaskTemplateItem(
        template_type=data["template_type"],
        category=data["category"],
        title=data["title"],
        required=data["required"],
        reward_text=data.get("reward_text"),
        sort_order=data["sort_order"],
        child_id=data.get("child_id"),
    )
    session.add(item)
    session.commit()
    return item.id


def update_template_task(session: Session, task_id: int, data: Dict) -> Optional[str]:
    item = session.get(TaskTemplateItem, task_id)
    if not item:
        return "Task not found"
    for field in ["template_type", "category", "title", "required", "reward_text", "sort_order", "child_id"]:
        if field in data and data[field] is not None:
            setattr(item, field, data[field])
    session.commit()
    return None


def delete_template_task(session: Session, task_id: int) -> Optional[str]:
    item = session.get(TaskTemplateItem, task_id)
    if not item:
        return "Task not found"
    session.delete(item)
    session.commit()
    return None
