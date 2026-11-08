from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledger_service.exceptions import AccountNotFound, InsufficientFunds
from ledger_service.models import Account, Transaction
from ledger_service.schemas import AccountCreate
from ledger_service.services.customers import get_customer


def _get_account_for_update(session: Session, account_id: int) -> Account:
    account = session.execute(
        select(Account).where(Account.id == account_id).with_for_update()
    ).scalar_one_or_none()
    if account is None:
        raise AccountNotFound(account_id)
    return account


def get_account(session: Session, account_id: int) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise AccountNotFound(account_id)
    return account


def create_account(session: Session, data: AccountCreate) -> Account:
    with session.begin():
        customer = get_customer(session, data.customer_id)
        new_account = Account(
            customer_id=customer.id, currency=data.currency, balance=Decimal("0.00")
        )
        session.add(new_account)
        session.flush()

        if data.opening_deposit > 0:
            amount = data.opening_deposit
            new_account.balance += amount
            tx = Transaction(account_id=new_account.id, amount=amount, kind="deposit")
            session.add(tx)

        return new_account


def deposit(session: Session, account_id: int, amount: Decimal) -> Transaction:
    with session.begin():
        account = _get_account_for_update(session, account_id)
        account.balance += amount
        tx = Transaction(account_id=account_id, amount=amount, kind="deposit")
        session.add(tx)
        return tx


def withdraw(session: Session, account_id: int, amount: Decimal) -> Transaction:
    with session.begin():
        account = _get_account_for_update(session, account_id)
        balance = account.balance
        if amount > balance:
            raise InsufficientFunds(account_id=account_id, balance=balance, requested=amount)
        account.balance -= amount
        tx = Transaction(account_id=account_id, amount=-amount, kind="withdrawal")
        session.add(tx)
        return tx
