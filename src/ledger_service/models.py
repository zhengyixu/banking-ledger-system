from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ledger_service.db import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    accounts: Mapped[list["Account"]] = relationship(back_populates="customer")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    kind: Mapped[str] = mapped_column(String)
    transfer_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="transactions")

    __table_args__ = (
        CheckConstraint(
            "kind IN ('deposit', 'withdrawal', 'transfer_in', 'transfer_out')",
            name="ck_transactions_kind",
        ),
        Index("ix_transactions_account_created_id", "account_id", created_at.desc(), id.desc()),
    )


class Account(Base):
    __tablename__ = "accounts"
    # Defence in depth: the database itself refuses a negative balance,
    # even if a bug in our Python code lets one through.
    __table_args__ = (CheckConstraint("balance >= 0", name="ck_accounts_balance_nonneg"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    # Numeric, never float, for money.
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    customer: Mapped[Customer] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
