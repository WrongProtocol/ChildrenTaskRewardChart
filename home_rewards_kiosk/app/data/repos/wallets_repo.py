from sqlalchemy.orm import Session

from app.data.models import Wallet


def get_wallet(session: Session, child_id: int) -> Wallet | None:
    return session.query(Wallet).filter(Wallet.child_id == child_id).one_or_none()


def upsert_wallet(session: Session, wallet: Wallet) -> Wallet:
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet
