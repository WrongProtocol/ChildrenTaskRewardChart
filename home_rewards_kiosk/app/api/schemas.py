from datetime import date, datetime
from pydantic import BaseModel


class ChildOut(BaseModel):
    id: int
    name: str
    avatar_color: str

    class Config:
        from_attributes = True


class GoalOut(BaseModel):
    id: int
    child_id: int | None
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
    claimed_at: datetime | None
    approved_at: datetime | None

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
    settings: SettingsOut | None


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
    child_id: int | None = None
    category: str
    title: str
    reward_minutes: int
    repeat_rule: str = "daily"
    proof_required: bool = False
    auto_approve: bool = False


class GoalUpdateRequest(BaseModel):
    category: str | None = None
    title: str | None = None
    reward_minutes: int | None = None
    repeat_rule: str | None = None
    proof_required: bool | None = None
    auto_approve: bool | None = None


class SettingsUpdateRequest(BaseModel):
    daily_minute_cap: int | None = None
    exchange_rate_cents: int | None = None
    pin: str | None = None
