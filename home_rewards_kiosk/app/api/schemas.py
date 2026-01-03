from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ChildOut(BaseModel):
    id: int
    name: str
    avatar_color: str

    class Config:
        from_attributes = True


class GoalOut(BaseModel):
    id: int
    child_id: Optional[int]
    category: str
    title: str
    reward_minutes: int
    repeat_rule: str
    proof_required: bool
    auto_approve: bool

    class Config:
        from_attributes = True


class GoalInstanceOut(BaseModel):
    id: int
    goal_id: int
    child_id: int
    date: date
    status: str
    claimed_at: Optional[datetime]
    approved_at: Optional[datetime]

    class Config:
        from_attributes = True


class WalletOut(BaseModel):
    id: int
    child_id: int
    minutes_balance: int
    money_balance_cents: int

    class Config:
        from_attributes = True


class SettingsOut(BaseModel):
    id: int
    daily_minute_cap: int
    exchange_rate_cents: int

    class Config:
        from_attributes = True


class KioskStateOut(BaseModel):
    children: list[ChildOut]
    goals: list[GoalOut]
    instances: list[GoalInstanceOut]
    wallets: list[WalletOut]
    settings: Optional[SettingsOut]


class ClaimRequest(BaseModel):
    goal_id: int


class PlayRequest(BaseModel):
    minutes: int


class CashoutRequest(BaseModel):
    minutes: int


class UnlockRequest(BaseModel):
    pin: str


class ApprovalRequest(BaseModel):
    instance_id: int
    approve: bool


class GoalCreateRequest(BaseModel):
    child_id: Optional[int] = None
    category: str
    title: str
    reward_minutes: int
    repeat_rule: str = "daily"
    proof_required: bool = False
    auto_approve: bool = False


class GoalUpdateRequest(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    reward_minutes: Optional[int] = None
    repeat_rule: Optional[str] = None
    proof_required: Optional[bool] = None
    auto_approve: Optional[bool] = None


class SettingsUpdateRequest(BaseModel):
    daily_minute_cap: Optional[int] = None
    exchange_rate_cents: Optional[int] = None
    pin: Optional[str] = None
