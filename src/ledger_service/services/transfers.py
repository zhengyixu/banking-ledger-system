"""Moving money between two accounts, atomically.

Pay attention to transactions, locking, deadlock avoidance and the ledger invariant.
"""

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from ledger_service.exceptions import CurrencyMismatch, InsufficientFunds, SameAccountTransfer
from ledger_service.models import Transaction
from ledger_service.services.accounts import get_account_for_update, require_positive


def transfer(
    session: Session,
    from_account_id: int,
    to_account_id: int,
    amount: Decimal,
    idempotency_key: str | None = None,
) -> tuple[Transaction, Transaction]:
    require_positive(amount)

    if from_account_id == to_account_id:
        raise SameAccountTransfer(from_account_id)

    with session.begin():
        # TODO(idempotency): when `idempotency_key` is not None, FIRST STATEMENT of this
        # transaction (before any account lock):
        #   1. Generate transfer_id here (uuid4) instead of further down.
        #   2. INSERT INTO idempotency_keys (key, request_hash, transfer_id)
        #      ON CONFLICT (key) DO NOTHING RETURNING key
        #      (SQLAlchemy: sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_nothing(
        #      index_elements=[...]).returning(...)). Run it with session.execute.
        #   3. If it returned no row, the key already exists (a concurrent insert makes us WAIT
        #      for the other transaction to finish, which is exactly what we want):
        #      SELECT the existing row; if its request_hash != ours, raise IdempotencyKeyReuse(key);
        #      otherwise load the two Transactions with that transfer_id (transfer_out first) and
        #      return them. Do not touch any balance.
        #   request_hash: hash of (from_account_id, to_account_id, amount). Use hashlib.sha256 over
        #   a canonical string, e.g. f"{from_account_id}|{to_account_id}|{amount}".
        #   Failures must NOT consume the key: they roll back the whole transaction, key row
        #   included, which is why the insert lives inside this `with` block.
        accounts_dictionary = {
            i: get_account_for_update(session, i) for i in sorted([from_account_id, to_account_id])
        }
        from_account = accounts_dictionary[from_account_id]
        to_account = accounts_dictionary[to_account_id]

        from_currency = from_account.currency
        to_currency = to_account.currency
        if from_currency != to_currency:
            raise CurrencyMismatch(from_currency, to_currency)

        from_balance = from_account.balance
        if amount > from_balance:
            raise InsufficientFunds(from_account_id, from_balance, amount)

        transfer_id = uuid.uuid4()  # TODO(idempotency): reuse the id stored with the key

        from_account.balance -= amount
        from_tx = Transaction(
            account_id=from_account_id,
            amount=-amount,
            kind="transfer_out",
            transfer_id=transfer_id,
        )
        session.add(from_tx)

        to_account.balance += amount
        to_tx = Transaction(
            account_id=to_account_id,
            amount=amount,
            kind="transfer_in",
            transfer_id=transfer_id,
        )
        session.add(to_tx)
    return (from_tx, to_tx)
