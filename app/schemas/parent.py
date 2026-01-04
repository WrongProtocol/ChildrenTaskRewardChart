from typing import Optional

from pydantic import BaseModel


class PinRequest(BaseModel):
    pin: str


class TokenResponse(BaseModel):
    token: str


class TaskCreate(BaseModel):
    child_id: Optional[int] = None
    category: str
    title: str
    required: bool
    reward_text: Optional[str] = None
    sort_order: int


class TaskUpdate(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    required: Optional[bool] = None
    reward_text: Optional[str] = None
    sort_order: Optional[int] = None


class SettingsUpdate(BaseModel):
    daily_reward_text: Optional[str] = None
    old_pin: Optional[str] = None
    new_pin: Optional[str] = None
