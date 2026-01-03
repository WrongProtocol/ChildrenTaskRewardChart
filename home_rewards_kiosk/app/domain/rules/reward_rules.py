from app.config import DEFAULT_DAILY_MINUTE_CAP


def within_daily_cap(current_minutes: int, add_minutes: int, cap: int | None = None) -> bool:
    limit = cap if cap is not None else DEFAULT_DAILY_MINUTE_CAP
    return current_minutes + add_minutes <= limit
