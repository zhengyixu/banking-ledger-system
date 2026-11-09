"""Pydantic schemas: the *API contract*, deliberately separate from the ORM models.

Why separate? `Customer` (ORM) mirrors the table. `CustomerCreate` / `CustomerRead` mirror
what clients may send and see. Keeping them apart means a new DB column never leaks into
the API by accident, and a client can't set fields like `id` or `created_at`.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerCreate(BaseModel):
    # Trim whitespace before validating, so "   " counts as empty and fails min_length.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        # Emails are treated as case-insensitive: "A@x.com" and "a@x.com" are one person.
        # Normalising here (not in the DB) keeps the unique constraint simple.
        return value.lower()


class CustomerRead(BaseModel):
    # from_attributes lets Pydantic read straight off an ORM object (customer.id, ...).
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


# --- Accounts & money movement --------------------------------------------------------
# Money rules live in the *type*: Decimal (never float), at most 2 decimal places, at most
# 18 digits to match Numeric(18, 2). Anything else is rejected with a 422 before our code
# runs. In JSON responses Pydantic writes Decimals as strings ("125.50"), so clients never
# parse money through a float.

PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]


class AccountCreate(BaseModel):
    customer_id: int
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")  # ISO-4217 shape, e.g. USD
    opening_deposit: NonNegativeMoney = Decimal("0.00")


class MoneyMovement(BaseModel):
    """Body for both deposits and withdrawals: always a positive amount.

    The *endpoint* says which direction it goes; the stored transaction is signed.
    """

    amount: PositiveMoney


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    currency: str
    balance: Decimal
    created_at: datetime


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    amount: Decimal  # signed: + deposit, - withdrawal
    kind: str
    transfer_id: UUID | None
    created_at: datetime


class TransferCreate(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: PositiveMoney


class TransferRead(BaseModel):
    """A transfer is two ledger rows sharing one transfer_id: a debit and a credit."""

    transfer_id: UUID
    from_account_id: int
    to_account_id: int
    amount: Decimal  # always positive here; the signed amounts are inside debit/credit
    debit: TransactionRead  # kind="transfer_out", negative amount, on the source account
    credit: TransactionRead  # kind="transfer_in", positive amount, on the destination


class TransactionPage(BaseModel):
    """One page of an account's history, newest first.

    `next_cursor` is an opaque string: pass it back as `?cursor=` to get the next page.
    `None` means this was the last page.
    """

    items: list[TransactionRead]
    next_cursor: str | None
