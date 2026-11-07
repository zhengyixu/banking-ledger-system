"""Account business logic: opening accounts and moving money.

This is the heart of the project. The rules here are what an interviewer will probe, so
the three TODO functions below are yours to write. Read the hints, then make
tests/test_accounts_api.py and tests/test_accounts_edge_cases.py pass.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from ledger_service.exceptions import AccountNotFound
from ledger_service.models import Account, Transaction
from ledger_service.schemas import AccountCreate


def get_account(session: Session, account_id: int) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise AccountNotFound(account_id)
    return account


# TODO(you): create_account. Hints:
#   - the customer must exist: reuse `customers.get_customer` (raises CustomerNotFound).
#   - create the Account with data.currency and a zero balance.
#   - if data.opening_deposit > 0, the account must start with a matching DEPOSIT
#     transaction, and the account and that transaction must be saved in ONE commit:
#     if either fails, neither exists. Easiest: build both, session.add them, commit once
#     (you need account.id for the transaction: session.flush() gives you it without
#     committing).
#   - invariant to keep true forever: account.balance == SUM(transaction.amount).
def create_account(session: Session, data: AccountCreate) -> Account:
    raise NotImplementedError("TODO(you): implement create_account")


# TODO(you): deposit. Hints:
#   - load the account with a row lock so two concurrent requests can't both read the same
#     balance:  select(Account).where(Account.id == account_id).with_for_update()
#     (raise AccountNotFound if it isn't there).
#   - add a Transaction(kind="deposit", amount=+amount), increase account.balance, then
#     commit ONCE. Both changes succeed together or not at all.
#   - return the new Transaction.
#   - `amount` arrives already validated by the schema (> 0, 2 decimal places), but a
#     service can be called from elsewhere too. Consider guarding it anyway
#     (what should you raise?).
def deposit(session: Session, account_id: int, amount: Decimal) -> Transaction:
    raise NotImplementedError("TODO(you): implement deposit")


# TODO(you): withdraw. Same shape as deposit, with the key business rule:
#   - lock the row, then check balance >= amount BEFORE changing anything; if not, raise
#     InsufficientFunds (and leave the database untouched: no balance change, no
#     transaction row).
#   - the stored Transaction.amount is NEGATIVE for a withdrawal: kind="withdrawal".
#   - the CHECK (balance >= 0) constraint is your safety net, NOT your plan. Your code
#     should refuse the withdrawal first, with a clear error, instead of relying on the
#     database to blow up with an IntegrityError.
#   - why compare AFTER taking the lock and not before? Be ready to explain the race.
def withdraw(session: Session, account_id: int, amount: Decimal) -> Transaction:
    raise NotImplementedError("TODO(you): implement withdraw")
