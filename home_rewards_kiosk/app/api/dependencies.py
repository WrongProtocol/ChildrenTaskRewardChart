from app.data.session import SessionLocal


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
