"""Moving money between two accounts, atomically.

This is the hardest function in the project and the one interviewers love, because it
combines transactions, locking, deadlock avoidance and the ledger invariant.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from ledger_service.models import Transaction


# TODO(you): transfer. Hints, in the order you'd write the code:
#
#   1. GUARDS FIRST (no DB work yet):
#        - amount must be positive (reuse `_require_positive` from services/accounts.py;
#          it is underscore-private, so either import it anyway or rename it to a public
#          name in accounts.py: your call, be ready to justify it).
#        - from_account_id == to_account_id  ->  raise SameAccountTransfer(...)
#
#   2. ONE TRANSACTION for everything: `with session.begin():`
#
#   3. LOCK BOTH ACCOUNTS IN A FIXED ORDER: ascending account id, whichever direction the
#      money flows. Lock one at a time with `_get_account_for_update` (it raises
#      AccountNotFound for a missing id).
#        Why the order matters: transfer A->B locks A then B; a simultaneous B->A locks B
#        then A. Each waits for the other forever = DEADLOCK (Postgres kills one with
#        error 40P01). If both lock the lower id first, one simply waits for the other.
#      After locking, you still need to know which is the source and which the destination.
#
#   4. CHECKS, now that both rows are locked and their values can't change under you:
#        - currencies differ  ->  raise CurrencyMismatch(from_currency, to_currency)
#        - source balance < amount  ->  raise InsufficientFunds(...) (same as withdraw)
#
#   5. WRITE BOTH LEGS with ONE shared transfer id (`uuid.uuid4()`):
#        - debit : Transaction(account_id=source.id, amount=-amount,
#                              kind="transfer_out", transfer_id=tid)
#        - credit: Transaction(account_id=destination.id, amount=+amount,
#                              kind="transfer_in", transfer_id=tid)
#        and update both balances. Everything commits together when the `with` block ends,
#        or nothing does.
#
#   6. return (debit, credit): the router turns them into the response.
#
#   Invariant to keep true forever: money is neither created nor destroyed. The sum of
#   both balances before == after, and the two ledger rows sum to exactly zero.
def transfer(
    session: Session,
    from_account_id: int,
    to_account_id: int,
    amount: Decimal,
) -> tuple[Transaction, Transaction]:
    raise NotImplementedError("TODO(you): implement transfer")
