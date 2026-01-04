from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain import services
from app.schemas.parent import PinRequest, SettingsUpdate, TaskCreate, TaskUpdate, TokenResponse
from app.security.pin import verify_pin, hash_pin
from app.security.token import create_token, verify_token

router = APIRouter()


def require_token(authorization: str = Header(default="")) -> None:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/api/parent/unlock", response_model=TokenResponse)
def unlock_parent(request: PinRequest, db: Session = Depends(get_db)):
    settings = services.get_settings(db)
    if not verify_pin(request.pin, settings.parent_pin_hash):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return {"token": create_token()}


@router.post("/api/parent/tasks/{task_id}/approve")
def approve_task(task_id: int, db: Session = Depends(get_db), _: None = Depends(require_token)):
    error = services.approve_task(db, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.post("/api/parent/tasks/{task_id}/reject")
def reject_task(task_id: int, db: Session = Depends(get_db), _: None = Depends(require_token)):
    error = services.reject_task(db, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.get("/api/parent/pending")
def list_pending(db: Session = Depends(get_db), _: None = Depends(require_token)):
    return {"pending": services.list_pending_tasks(db)}


@router.post("/api/parent/today/tasks")
def create_today_task(request: TaskCreate, db: Session = Depends(get_db), _: None = Depends(require_token)):
    ids = services.create_today_task(db, request.model_dump())
    return {"ids": ids}


@router.put("/api/parent/today/tasks/{task_id}")
def update_today_task(task_id: int, request: TaskUpdate, db: Session = Depends(get_db), _: None = Depends(require_token)):
    error = services.update_today_task(db, task_id, request.model_dump(exclude_unset=True))
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.delete("/api/parent/today/tasks/{task_id}")
def delete_today_task(task_id: int, db: Session = Depends(get_db), _: None = Depends(require_token)):
    error = services.delete_today_task(db, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.get("/api/parent/templates")
def get_templates(db: Session = Depends(get_db), _: None = Depends(require_token)):
    return {"templates": services.list_templates(db)}


@router.post("/api/parent/templates/tasks")
def create_template_task(request: dict, db: Session = Depends(get_db), _: None = Depends(require_token)):
    task_id = services.create_template_task(db, request)
    return {"id": task_id}


@router.put("/api/parent/templates/tasks/{task_id}")
def update_template_task(task_id: int, request: dict, db: Session = Depends(get_db), _: None = Depends(require_token)):
    error = services.update_template_task(db, task_id, request)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.delete("/api/parent/templates/tasks/{task_id}")
def delete_template_task(task_id: int, db: Session = Depends(get_db), _: None = Depends(require_token)):
    error = services.delete_template_task(db, task_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"status": "ok"}


@router.get("/api/parent/settings")
def get_settings(db: Session = Depends(get_db), _: None = Depends(require_token)):
    settings = services.get_settings(db)
    return {
        "daily_reward_text": settings.daily_reward_text,
    }


@router.put("/api/parent/settings")
def update_settings(request: SettingsUpdate, db: Session = Depends(get_db), _: None = Depends(require_token)):
    settings = services.get_settings(db)
    if request.daily_reward_text is not None:
        settings.daily_reward_text = request.daily_reward_text
    if request.new_pin:
        if not request.old_pin or not verify_pin(request.old_pin, settings.parent_pin_hash):
            raise HTTPException(status_code=400, detail="Invalid old PIN")
        settings.parent_pin_hash = hash_pin(request.new_pin)
    db.commit()
    return {"status": "ok"}
