from sqlalchemy.orm import Session

from app.data.models import Settings, Transaction
from app.data.repos import transactions_repo
from app.domain.services import wallet_service


def request_cashout(session: Session, child_id: int, minutes: int) -> Transaction:
    settings = session.query(Settings).first()
    if not settings:
        raise ValueError("Settings not initialized")

    cents = minutes * settings.exchange_rate_cents
    wallet_service.spend_minutes(session, child_id, minutes)
    wallet_service.add_money(session, child_id, cents)

    transaction = Transaction(
        child_id=child_id,
        type="cashout",
        minutes_delta=-minutes,
        cents_delta=cents,
        status="pending",
    )
    return transactions_repo.create_transaction(session, transaction)
