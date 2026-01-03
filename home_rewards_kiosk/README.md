# Home Rewards Kiosk

Local-only FastAPI kiosk for a wall-mounted family rewards display.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` for the kiosk screen.
