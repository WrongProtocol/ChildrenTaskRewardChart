from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import child, kiosk, parent
from app.config import DEFAULT_CATEGORIES, DEFAULT_CHILDREN, DEFAULT_PARENT_PIN
from app.data.models import Base, Child, Goal, Settings, Wallet
from app.data.session import SessionLocal, engine
from app.security.pin import hash_pin

app = FastAPI(title="Home Rewards Kiosk")

app.include_router(kiosk.router)
app.include_router(child.router)
app.include_router(parent.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        if not session.query(Settings).first():
            salt, pin_hash = hash_pin(DEFAULT_PARENT_PIN)
            session.add(Settings(pin_salt=salt, pin_hash=pin_hash))

        if session.query(Child).count() == 0:
            for child in DEFAULT_CHILDREN:
                record = Child(**child)
                session.add(record)
                session.flush()
                session.add(Wallet(child_id=record.id, minutes_balance=0, money_balance_cents=0))
                for category in DEFAULT_CATEGORIES:
                    session.add(
                        Goal(
                            child_id=record.id,
                            category=category,
                            title=f"{category} starter",
                            reward_minutes=10,
                        )
                    )
        session.commit()
    finally:
        session.close()
