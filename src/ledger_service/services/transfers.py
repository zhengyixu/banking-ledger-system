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
) -> tuple[Transaction, Transaction]:
    require_positive(amount)

    if from_account_id == to_account_id:
        raise SameAccountTransfer(from_account_id)

    with session.begin():
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

        transfer_id = uuid.uuid4()

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
