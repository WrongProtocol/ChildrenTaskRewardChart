# Home Rewards Kiosk

A local-only, wall-mounted kiosk checklist for three children. It runs on a LAN and is designed for a fixed 1920×1080 display with **no scrolling**.

## Features

- Exactly 3 child columns with Schoolwork, Hygiene, and Helpful categories.
- Child taps mark tasks as **Pending** until a parent approves or rejects.
- Parent-only approvals and editing behind a PIN.
- Weekday/Weekend templates with automatic midnight reset.
- Bonus tasks show reward text but never block unlock.

## Run Locally

1. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start the server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. Open the kiosk view in a browser on the LAN:

```
http://<your-lan-ip>:8000/
```

## Parent PIN

The default Parent PIN is `1234`. To change it:

1. Click **Parent 🔒** in the kiosk UI.
2. Enter the current PIN.
3. Open the **Settings** tab and set a new PIN.

> You can also set a secret for tokens with the `KIOSK_SECRET_KEY` environment variable.

## Layout / No Scrolling

The UI is designed for **1920×1080** and enforces `overflow: hidden` on the page.
Keep task lists short (around 10–12 items per child) to maintain the no-scroll layout.
