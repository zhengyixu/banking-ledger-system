"""HTTP layer for transfers. All the interesting work is in services/transfers.py."""

from fastapi import APIRouter, status

from ledger_service.db import SessionDep
from ledger_service.schemas import TransactionRead, TransferCreate, TransferRead
from ledger_service.services import transfers as transfer_service

router = APIRouter(prefix="/transfers", tags=["transfers"])


# POST creates a transfer resource  ->  201.
@router.post("", response_model=TransferRead, status_code=status.HTTP_201_CREATED)
def create_transfer(data: TransferCreate, session: SessionDep):
    debit, credit = transfer_service.transfer(
        session, data.from_account_id, data.to_account_id, data.amount
    )
    return TransferRead(
        transfer_id=debit.transfer_id,
        from_account_id=debit.account_id,
        to_account_id=credit.account_id,
        amount=credit.amount,
        debit=TransactionRead.model_validate(debit),
        credit=TransactionRead.model_validate(credit),
    )
