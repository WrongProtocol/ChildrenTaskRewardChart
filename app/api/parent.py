"""
Parent admin API endpoints.
Provides task approval/rejection, template management, and kiosk configuration.
All endpoints except /unlock require Bearer token authentication.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain import services
from app.schemas.parent import (
    ChildCreate,
    ChildListResponse,
    ChildResponse,
    ChildUpdate,
    PinRequest,
    SettingsUpdate,
    TaskCreate,
    TaskUpdate,
    TokenResponse,
)
from app.security.pin import verify_pin, hash_pin
from app.security.token import create_token, verify_token

router = APIRouter()


def require_token(authorization: str = Header(default="")) -> None:
    """
    Dependency to verify parent authentication token.
    Extracts Bearer token from Authorization header and validates it.
    
    Raises:
        HTTPException 401: If token is missing or invalid
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/api/parent/unlock", response_model=TokenResponse)
def unlock_parent(request: PinRequest, db: Session = Depends(get_db)):
    """
    Authenticate parent with PIN and return authentication token.
    Token is used for subsequent admin API requests (CORS-friendly via Bearer header).
    
    Args:
        request: PinRequest containing the parent PIN
        db: Database session (auto-injected)
    
    Returns:
        TokenResponse with authentication token if PIN is correct
    
    Raises:
        HTTPException 401: If PIN is invalid
    """
    settings = services.get_settings(db)
    if not verify_pin(request.pin, settings.parent_pin_hash):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return {"token": create_token()}


# ============================================
# CHILD MANAGEMENT ENDPOINTS
# ============================================

@router.get("/api/parent/children", response_model=ChildListResponse)
def list_children(db: Session = Depends(get_db), _: None = Depends(require_token)):
    """Get all children in display order."""
    return {"children": services.list_children(db)}


@router.post("/api/parent/children", response_model=ChildResponse)
def create_child(request: ChildCreate, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Create a new child profile.
    Display order is optional; defaults to the end of the list.
    """
    child, error = services.create_child(db, request.model_dump())
    if error:
        raise HTTPException(status_code=400, detail=error)
    return child


@router.put("/api/parent/children/{child_id}", response_model=ChildResponse)
def update_child(child_id: int, request: ChildUpdate, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """Update a child's name and/or display order."""
    child, error = services.update_child(db, child_id, request.model_dump(exclude_unset=True))
    if error:
        raise HTTPException(status_code=400, detail=error)
    return child


@router.delete("/api/parent/children/{child_id}")
def delete_child(child_id: int, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """Delete a child and associated tasks/templates."""
    error = services.delete_child(db, child_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


# ============================================
# TASK APPROVAL ENDPOINTS
# ============================================

@router.post("/api/parent/tasks/{task_id}/approve")
def approve_task(task_id: int, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Parent approves a pending task, marking it as APPROVED.
    Parent receives the reward specified in task definition (if auto_approve=true).
    
    Args:
        task_id: ID of the pending task to approve
        db: Database session (auto-injected)
    
    Returns:
        Status confirmation if successful
    """
    error = services.approve_task(db, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.post("/api/parent/tasks/{task_id}/reject")
def reject_task(task_id: int, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Parent rejects a pending task, returning it to OPEN state.
    Child must complete the task again and resubmit for approval.
    
    Args:
        task_id: ID of the pending task to reject
        db: Database session (auto-injected)
    
    Returns:
        Status confirmation if successful
    """
    error = services.reject_task(db, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.post("/api/parent/tasks/{task_id}/revoke")
def revoke_task(task_id: int, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Parent revokes an approved task, returning it to OPEN state.
    Used to undo approvals and have child redo work.
    
    Args:
        task_id: ID of the approved task to revoke
        db: Database session (auto-injected)
    
    Returns:
        Status confirmation if successful
    """
    error = services.revoke_task(db, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


# ============================================
# TASK LISTING ENDPOINTS
# ============================================

@router.get("/api/parent/pending")
def list_pending(db: Session = Depends(get_db), _: None = Depends(require_token)):
    """Get all tasks awaiting parent approval (state=PENDING)."""
    return {"pending": services.list_pending_tasks(db)}


@router.get("/api/parent/completed")
def list_completed(db: Session = Depends(get_db), _: None = Depends(require_token)):
    """Get all tasks that have been approved by parent (state=APPROVED)."""
    return {"completed": services.list_completed_tasks(db)}


# ============================================
# TODAY'S TASKS ENDPOINTS (One-time tasks for today)
# ============================================

@router.post("/api/parent/today/tasks")
def create_today_task(request: TaskCreate, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Create a one-time task for today.
    If child_id is null, task is assigned to all children.
    
    Args:
        request: TaskCreate with task details (category, title, required, etc.)
        db: Database session (auto-injected)
    
    Returns:
        List of created task IDs (one per child if assigned to all)
    """
    ids = services.create_today_task(db, request.model_dump())
    return {"ids": ids}


@router.put("/api/parent/today/tasks/{task_id}")
def update_today_task(task_id: int, request: TaskUpdate, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Update an existing today's task (title, category, required status, etc.).
    
    Args:
        task_id: ID of the task to update
        request: TaskUpdate with fields to modify
        db: Database session (auto-injected)
    
    Returns:
        Status confirmation if successful
    """
    error = services.update_today_task(db, task_id, request.model_dump(exclude_unset=True))
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.delete("/api/parent/today/tasks/{task_id}")
def delete_today_task(task_id: int, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Delete a one-time task from today's list.
    
    Args:
        task_id: ID of the task to delete
        db: Database session (auto-injected)
    
    Returns:
        Status confirmation if successful
    """
    error = services.delete_today_task(db, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


# ============================================
# TEMPLATE ENDPOINTS (Recurring tasks)
# ============================================

@router.get("/api/parent/templates")
def get_templates(db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Get all recurring task templates (weekday and weekend).
    Templates define which tasks appear each day based on day of week.
    """
    return {"templates": services.list_templates(db)}


@router.post("/api/parent/templates/tasks")
def create_template_task(request: dict, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Create a new recurring task template (WEEKDAY or WEEKEND).
    This task will appear every weekday/weekend until deleted.
    
    Args:
        request: Template task details (template_type, category, title, etc.)
        db: Database session (auto-injected)
    
    Returns:
        ID of the created template task
    """
    task_id = services.create_template_task(db, request)
    return {"id": task_id}


@router.put("/api/parent/templates/tasks/{task_id}")
def update_template_task(task_id: int, request: dict, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Update an existing template task.
    Changes apply to future days (today's tasks not retroactively affected).
    
    Args:
        task_id: ID of the template task to update
        request: Updated template task details
        db: Database session (auto-injected)
    
    Returns:
        Status confirmation if successful
    """
    error = services.update_template_task(db, task_id, request)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.delete("/api/parent/templates/tasks/{task_id}")
def delete_template_task(task_id: int, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Delete a template task.
    This task will no longer appear on future days (today's tasks not affected).
    
    Args:
        task_id: ID of the template task to delete
        db: Database session (auto-injected)
    
    Returns:
        Status confirmation if successful
    """
    error = services.delete_template_task(db, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


# ============================================
# SETTINGS ENDPOINTS
# ============================================

@router.get("/api/parent/settings")
def get_settings(db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Get current kiosk settings.
    Returns the text shown when all daily tasks are completed.
    """
    settings = services.get_settings(db)
    return {
        "daily_reward_text": settings.daily_reward_text,
    }


@router.put("/api/parent/settings")
def update_settings(request: SettingsUpdate, db: Session = Depends(get_db), _: None = Depends(require_token)):
    """
    Update kiosk settings (daily reward text and/or parent PIN).
    PIN change requires verification of old PIN.
    
    Args:
        request: SettingsUpdate with fields to modify
        db: Database session (auto-injected)
    
    Returns:
        Status confirmation if successful
    
    Raises:
        HTTPException 400: If old PIN is invalid when changing PIN
    """
    settings = services.get_settings(db)
    if request.daily_reward_text is not None:
        settings.daily_reward_text = request.daily_reward_text
    if request.new_pin:
        if not request.old_pin or not verify_pin(request.old_pin, settings.parent_pin_hash):
            raise HTTPException(status_code=400, detail="Invalid old PIN")
        settings.parent_pin_hash = hash_pin(request.new_pin)
    db.commit()
    return {"status": "ok"}
