"""HTTP layer for accounts and money movement. Thin on purpose: see services/accounts.py."""

from fastapi import APIRouter, Response, status

from ledger_service.db import SessionDep
from ledger_service.schemas import (
    AccountCreate,
    AccountRead,
    MoneyMovement,
    TransactionRead,
)
from ledger_service.services import accounts as account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(data: AccountCreate, session: SessionDep, response: Response):
    account = account_service.create_account(session, data)
    response.headers["Location"] = f"/v1/accounts/{account.id}"
    return account


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, session: SessionDep):
    return account_service.get_account(session, account_id)


# Deposits and withdrawals are modelled as resources you CREATE (nouns, not verbs):
# POST /accounts/7/deposits  ->  a new deposit now exists  ->  201.
@router.post(
    "/{account_id}/deposits",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def deposit(account_id: int, body: MoneyMovement, session: SessionDep):
    return account_service.deposit(session, account_id, body.amount)


@router.post(
    "/{account_id}/withdrawals",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def withdraw(account_id: int, body: MoneyMovement, session: SessionDep):
    return account_service.withdraw(session, account_id, body.amount)
