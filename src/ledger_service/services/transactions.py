"""Reading an account's transaction history (newest first, keyset pagination)."""

from sqlalchemy.orm import Session

from ledger_service.models import Transaction
from ledger_service.pagination import Cursor


def list_transactions(
    session: Session,
    account_id: int,
    limit: int,
    after: Cursor | None = None,
) -> tuple[list[Transaction], bool]:
    """Return (up to `limit` transactions, has_more), newest first.

    TODO(you): implement. Hints:

    1. Unknown account -> AccountNotFound (reuse accounts.get_account).
    2. Sort by (created_at DESC, id DESC). `created_at` alone is NOT unique: the rows of
       one transaction share the same now(), so `id` is the tie-breaker. Without it, rows
       with the same timestamp can be skipped or repeated across pages.
    3. Keyset condition when `after` is given: rows strictly OLDER than the cursor,
       i.e. (created_at, id) < (after_created_at, after_id). SQLAlchemy has
       `sqlalchemy.tuple_(Transaction.created_at, Transaction.id) < (c, i)`; the
       equivalent long form is  created_at < c OR (created_at = c AND id < i).
    4. Fetch `limit + 1` rows. If you got more than `limit`, has_more is True and you
       drop the extra one. This answers "is there a next page?" without a COUNT(*).
    5. Do NOT use OFFSET: its cost grows with the page number and rows shift when new
       transactions arrive between requests (the keyset tests below check that).
    6. Read-only: no `session.begin()` needed.
    """
    raise NotImplementedError("TODO(you): implement list_transactions")
