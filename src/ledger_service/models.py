from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ledger_service.db import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    accounts: Mapped[list["Account"]] = relationship(back_populates="customer")


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


# TODO(you): add the `Transaction` model here. Hints:
#   - table "transactions": id, account_id (FK -> accounts.id), amount (Numeric(18, 2),
#     signed: + deposit / - withdrawal), kind (String, e.g. "deposit" | "withdrawal" |
#     "transfer_in" | "transfer_out"), transfer_id (UUID, nullable: pairs the two legs of
#     a transfer), created_at (server_default=func.now()).
#   - add `transactions` relationship on Account (back_populates both ways).
#   - do NOT add an index yet; we'll add one in phase 4 after looking at EXPLAIN.
#   - then generate migration #2 yourself:
#       uv run alembic revision --autogenerate -m "add transactions"
#     and READ the generated file before applying it.
