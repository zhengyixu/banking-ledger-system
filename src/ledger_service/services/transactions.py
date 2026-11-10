"""Reading an account's transaction history (newest first, keyset pagination)."""

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ledger_service.models import Transaction
from ledger_service.pagination import Cursor
from ledger_service.services.accounts import get_account


def list_transactions(
    session: Session,
    account_id: int,
    limit: int,
    after: Cursor | None = None,
) -> tuple[list[Transaction], bool]:
    """Return (up to `limit` transactions, has_more), newest first."""
    get_account(session, account_id)

    stmt = select(Transaction).where(Transaction.account_id == account_id)
    if after is not None:
        created_at, tx_id = after
        stmt = stmt.where(
            or_(
                Transaction.created_at < created_at,
                and_(Transaction.created_at == created_at, Transaction.id < tx_id),
            )
        )

    """Sort by (created_at DESC, id DESC). `created_at` alone is NOT unique: the rows of
       one transaction share the same now(), so `id` is the tie-breaker. Without it, rows
       with the same timestamp can be skipped or repeated across pages."""
    stmt = stmt.order_by(Transaction.created_at.desc(), Transaction.id.desc()).limit(limit + 1)

    rows = list(session.scalars(stmt))
    has_more = len(rows) > limit

    transactions = rows[:limit]

    return transactions, has_more
