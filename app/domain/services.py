"""
Core business logic for the rewards system.
Handles state building, task management, template management, and approval workflows.
"""
import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.data.models import Child, DailyTaskInstance, Settings, TaskTemplateItem
from app.security.pin import hash_pin
from app.domain.seed import seed_data

# Task categories - used throughout the system
CATEGORIES = ["SCHOOLWORK", "HYGIENE", "HELPFUL"]
MAX_CHILDREN = 5
MIN_CHILDREN = 1


def today_str() -> str:
    """Get today's date as ISO format string (YYYY-MM-DD)."""
    return datetime.date.today().isoformat()


def get_settings(session: Session) -> Settings:
    """
    Get or create singleton Settings record.
    If no settings exist, creates default settings with PIN '1234'.
    
    Returns:
        Settings: The singleton settings record
    """
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
    """
    Create today's task instances from templates if not already done.
    Runs once per day when system first starts or when date changes.
    
    Process:
    1. Ensure seed data exists (children and templates)
    2. Check if today's tasks already created (via last_reset_date)
    3. Determine template type (WEEKDAY vs WEEKEND)
    4. For each child, create task instances from matching templates
    5. Update last_reset_date to prevent duplication
    """
    seed_data(session)
    settings = get_settings(session)
    current_date = today_str()
    
    # Exit early if today's tasks already initialized
    if settings.last_reset_date == current_date:
        return

    # Determine if today is weekday (0-4) or weekend (5-6)
    template_type = "WEEKEND" if datetime.date.today().weekday() >= 5 else "WEEKDAY"
    
    # Get all children in display order
    children = session.execute(select(Child).order_by(Child.display_order)).scalars().all()
    
    # Get all template items for today's day type
    template_items = (
        session.execute(
            select(TaskTemplateItem)
            .where(TaskTemplateItem.template_type == template_type)
            .order_by(TaskTemplateItem.sort_order)
        )
        .scalars()
        .all()
    )

    # Create task instance for each child-template combination
    for child in children:
        for item in template_items:
            # Skip if template is assigned to specific child and it's not this child
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

    # Mark that today's tasks have been initialized
    settings.last_reset_date = current_date
    session.commit()




# ============================================
# CHILD MANAGEMENT
# ============================================

def list_children(session: Session) -> List[Dict]:
    children = session.execute(select(Child).order_by(Child.display_order)).scalars().all()
    return [
        {
            "id": child.id,
            "name": child.name,
            "display_order": child.display_order,
        }
        for child in children
    ]


def create_child(session: Session, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    ensure_today_initialized(session)
    children = session.execute(select(Child).order_by(Child.display_order)).scalars().all()
    if len(children) >= MAX_CHILDREN:
        return None, f"Maximum of {MAX_CHILDREN} children allowed"

    requested_order = data.get("display_order")
    if requested_order is None:
        requested_order = len(children)
    if requested_order < 0 or requested_order > len(children):
        return None, f"display_order must be between 0 and {len(children)}"

    for child in children:
        if child.display_order >= requested_order:
            child.display_order += 1

    new_child = Child(name=data["name"], display_order=requested_order)
    session.add(new_child)
    session.commit()

    current_date = today_str()
    template_type = "WEEKEND" if datetime.date.today().weekday() >= 5 else "WEEKDAY"
    template_items = (
        session.execute(
            select(TaskTemplateItem)
            .where(TaskTemplateItem.template_type == template_type)
            .order_by(TaskTemplateItem.sort_order)
        )
        .scalars()
        .all()
    )

    for item in template_items:
        if item.child_id is not None and item.child_id != new_child.id:
            continue
        session.add(
            DailyTaskInstance(
                date=current_date,
                child_id=new_child.id,
                category=item.category,
                title=item.title,
                required=item.required,
                reward_text=item.reward_text,
                sort_order=item.sort_order,
                state="OPEN",
            )
        )
    session.commit()
    return {
        "id": new_child.id,
        "name": new_child.name,
        "display_order": new_child.display_order,
    }, None


def update_child(session: Session, child_id: int, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    child = session.get(Child, child_id)
    if not child:
        return None, "Child not found"

    children = session.execute(select(Child).order_by(Child.display_order)).scalars().all()
    if "name" in data and data["name"] is not None:
        child.name = data["name"]

    if "display_order" in data and data["display_order"] is not None:
        new_order = data["display_order"]
        if new_order < 0 or new_order >= len(children):
            return None, f"display_order must be between 0 and {len(children) - 1}"

        ordered = [item for item in children if item.id != child.id]
        ordered.insert(new_order, child)
        for index, item in enumerate(ordered):
            item.display_order = index

    if "color" in data and data["color"] is not None:
        color_value = data["color"]
        # Validate hex color format (e.g., #FF5733)
        if isinstance(color_value, str) and len(color_value) == 7 and color_value.startswith("#"):
            child.color = color_value
        elif isinstance(color_value, str) and color_value == "":
            child.color = None
        # else: invalid color format, skip setting it

    session.commit()
    return {
        "id": child.id,
        "name": child.name,
        "display_order": child.display_order,
        "color": child.color,
    }, None


def delete_child(session: Session, child_id: int) -> Optional[str]:
    child = session.get(Child, child_id)
    if not child:
        return "Child not found"

    total_children = session.execute(select(Child)).scalars().all()
    if len(total_children) <= MIN_CHILDREN:
        return "At least one child must remain"

    session.execute(delete(DailyTaskInstance).where(DailyTaskInstance.child_id == child_id))
    session.execute(delete(TaskTemplateItem).where(TaskTemplateItem.child_id == child_id))
    session.delete(child)

    remaining = session.execute(select(Child).order_by(Child.display_order)).scalars().all()
    for index, item in enumerate(remaining):
        item.display_order = index

    session.commit()
    return None


# ============================================
# TASK STATE TRANSITIONS
# ============================================

def claim_task(session: Session, child_id: int, task_id: int) -> Optional[str]:
    """
    Child claims a task, moving it from OPEN to PENDING.
    Task awaits parent approval to be considered complete.
    
    Args:
        session: Database session
        child_id: ID of child claiming task (validation)
        task_id: ID of task to claim
    
    Returns:
        None if successful, error message if failed
    """
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
    """
    Child unclaims a task, returning it from PENDING to OPEN.
    Allows child to abandon a task they don't want to complete.
    
    Args:
        session: Database session
        child_id: ID of child unclaiming task (validation)
        task_id: ID of task to unclaim
    
    Returns:
        None if successful, error message if failed
    """
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
    """
    Parent approves a pending task, moving it to APPROVED.
    Task is considered complete; child gets the reward.
    
    Args:
        session: Database session
        task_id: ID of task to approve
    
    Returns:
        None if successful, error message if failed
    """
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
    """
    Parent rejects a pending task, returning it to OPEN.
    Child must redo the task and resubmit for approval.
    
    Args:
        session: Database session
        task_id: ID of task to reject
    
    Returns:
        None if successful, error message if failed
    """
    task = session.get(DailyTaskInstance, task_id)
    if not task:
        return "Task not found"
    task.state = "OPEN"
    task.claimed_at = None
    task.approved_at = None
    session.commit()
    return None


def revoke_task(session: Session, task_id: int) -> Optional[str]:
    """
    Parent revokes an approved task, returning it to OPEN.
    Used to undo previous approval and have child redo work.
    
    Args:
        session: Database session
        task_id: ID of task to revoke
    
    Returns:
        None if successful, error message if failed
    """
    task = session.get(DailyTaskInstance, task_id)
    if not task:
        return "Task not found"
    task.state = "OPEN"
    task.claimed_at = None
    task.approved_at = None
    session.commit()
    return None


# ============================================
# TASK LISTING ENDPOINTS
# ============================================

def list_pending_tasks(session: Session) -> List[Dict]:
    """
    Get all pending tasks (claimed by children, waiting for parent approval).
    Organized by child and category for parent review.
    
    Returns:
        List of pending tasks with child info, title, and category
    """
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
    """
    Get all completed tasks (approved by parent today).
    Organized by child and category for parent review.
    
    Returns:
        List of approved tasks with child info, title, and category
    """
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


# ============================================
# TODAY'S TASKS CRUD (One-time tasks)
# ============================================

def create_today_task(session: Session, data: Dict) -> List[int]:
    """
    Create a one-time task for today.
    If child_id is null, creates for all children.
    
    Args:
        session: Database session
        data: Task data (category, title, required, reward_text, sort_order, child_id)
    
    Returns:
        List of created task IDs (one per affected child)
    """
    current_date = today_str()
    child_id = data.get("child_id")
    
    # Get target children (specific child or all children)
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
    """
    Update an existing today's task.
    Can modify title, category, required status, reward text, or sort order.
    
    Args:
        session: Database session
        task_id: ID of task to update
        data: Fields to update
    
    Returns:
        None if successful, error message if failed
    """
    task = session.get(DailyTaskInstance, task_id)
    if not task:
        return "Task not found"
    for field in ["category", "title", "required", "reward_text", "sort_order"]:
        if field in data and data[field] is not None:
            setattr(task, field, data[field])
    session.commit()
    return None


def delete_today_task(session: Session, task_id: int) -> Optional[str]:
    """
    Delete a one-time task from today.
    
    Args:
        session: Database session
        task_id: ID of task to delete
    
    Returns:
        None if successful, error message if failed
    """
    task = session.get(DailyTaskInstance, task_id)
    if not task:
        return "Task not found"
    session.delete(task)
    session.commit()
    return None


# ============================================
# TEMPLATE CRUD (Recurring tasks)
# ============================================

def list_templates(session: Session) -> List[Dict]:
    """
    Get all recurring task templates (weekday and weekend).
    
    Returns:
        List of template tasks with their configuration
    """
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
    """
    Create a new recurring task template (WEEKDAY or WEEKEND).
    This task will appear every matching day until deleted.
    
    Args:
        session: Database session
        data: Template data (template_type, category, title, required, reward_text, sort_order, child_id)
    
    Returns:
        ID of created template task
    """
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
    """
    Update an existing template task.
    Changes apply to future days only (today's tasks not retroactively changed).
    
    Args:
        session: Database session
        task_id: ID of template task to update
        data: Fields to update
    
    Returns:
        None if successful, error message if failed
    """
    item = session.get(TaskTemplateItem, task_id)
    if not item:
        return "Task not found"
    for field in ["template_type", "category", "title", "required", "reward_text", "sort_order", "child_id"]:
        if field in data and data[field] is not None:
            setattr(item, field, data[field])
    session.commit()
    return None


def delete_template_task(session: Session, task_id: int) -> Optional[str]:
    """
    Delete a template task.
    This task will no longer appear on future days (today's tasks unaffected).
    
    Args:
        session: Database session
        task_id: ID of template task to delete
    
    Returns:
        None if successful, error message if failed
    """
    item = session.get(TaskTemplateItem, task_id)
    if not item:
        return "Task not found"
    session.delete(item)
    session.commit()
    return None


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
        # Calculate percent_complete based only on REQUIRED tasks
        percent_complete = int((required_approved / required_total) * 100) if required_total else 0
        unlocked = required_total == required_approved
        pending_count = len([t for t in child_tasks if t.state == "PENDING"])
        child_states.append(
            {
                "id": child.id,
                "name": child.name,
                "display_order": child.display_order,
                "color": child.color,
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
