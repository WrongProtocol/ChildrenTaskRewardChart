import datetime
import os

import jwt

SECRET_KEY = os.environ.get("KIOSK_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30


def create_token() -> str:
    now = datetime.datetime.utcnow()
    payload = {
        "sub": "parent",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> bool:
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except jwt.PyJWTError:
        return False
