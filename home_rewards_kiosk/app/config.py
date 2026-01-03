from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "kiosk.sqlite3"

DEFAULT_CHILDREN = [
    {"name": "Alex", "avatar_color": "#4F46E5"},
    {"name": "Jordan", "avatar_color": "#EC4899"},
    {"name": "Riley", "avatar_color": "#22C55E"},
]

DEFAULT_CATEGORIES = ["Schoolwork", "Hygiene", "Family Help"]
DEFAULT_DAILY_MINUTE_CAP = 120
DEFAULT_EXCHANGE_RATE_CENTS = 25
DEFAULT_PARENT_PIN = "1234"
