from typing import Dict, List, Optional

from pydantic import BaseModel


class TaskOut(BaseModel):
    id: int
    title: str
    required: bool
    reward_text: Optional[str]
    state: str
    category: str
    sort_order: int


class CategoryProgress(BaseModel):
    approved: int
    total: int


class ChildState(BaseModel):
    id: int
    name: str
    display_order: int
    color: Optional[str] = None
    percent_complete: int
    unlocked: bool
    pending_count: int
    categories: Dict[str, List[TaskOut]]
    category_progress: Dict[str, CategoryProgress]


class StateResponse(BaseModel):
    date: str
    children: List[ChildState]
    daily_reward_text: str
