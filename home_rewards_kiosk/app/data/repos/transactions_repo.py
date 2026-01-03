from typing import Optional

from sqlalchemy.orm import Session

from app.data.models import Transaction


def create_transaction(session: Session, transaction: Transaction) -> Transaction:
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def list_transactions(session: Session, child_id: Optional[int] = None) -> list[Transaction]:
    query = session.query(Transaction)
    if child_id is not None:
        query = query.filter(Transaction.child_id == child_id)
    return query.all()
