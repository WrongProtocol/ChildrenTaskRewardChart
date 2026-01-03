from sqlalchemy.orm import Session

from app.data.models import Wallet
from app.data.repos import wallets_repo


def get_or_create_wallet(session: Session, child_id: int) -> Wallet:
    wallet = wallets_repo.get_wallet(session, child_id)
    if wallet:
        return wallet
    wallet = Wallet(child_id=child_id, minutes_balance=0, money_balance_cents=0)
    return wallets_repo.upsert_wallet(session, wallet)


def add_minutes(session: Session, child_id: int, minutes: int) -> Wallet:
    wallet = get_or_create_wallet(session, child_id)
    wallet.minutes_balance += minutes
    return wallets_repo.upsert_wallet(session, wallet)


def spend_minutes(session: Session, child_id: int, minutes: int) -> Wallet:
    wallet = get_or_create_wallet(session, child_id)
    wallet.minutes_balance = max(wallet.minutes_balance - minutes, 0)
    return wallets_repo.upsert_wallet(session, wallet)


def add_money(session: Session, child_id: int, cents: int) -> Wallet:
    wallet = get_or_create_wallet(session, child_id)
    wallet.money_balance_cents += cents
    return wallets_repo.upsert_wallet(session, wallet)
