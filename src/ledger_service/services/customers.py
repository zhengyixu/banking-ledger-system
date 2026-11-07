"""Customer business logic. Knows about the database and domain rules, not about HTTP."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ledger_service.exceptions import CustomerNotFound, DuplicateEmail
from ledger_service.models import Customer
from ledger_service.schemas import CustomerCreate


def create_customer(session: Session, data: CustomerCreate) -> Customer:
    customer = Customer(name=data.name, email=data.email)
    session.add(customer)
    try:
        session.commit()
    except IntegrityError as exc:
        # We rely on the UNIQUE constraint rather than "SELECT first, then INSERT".
        # A pre-check has a race: two requests can both see "no such email" and both insert.
        # The constraint is the only check that is race-free.
        session.rollback()
        raise DuplicateEmail(data.email) from exc
    return customer


def get_customer(session: Session, customer_id: int) -> Customer:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise CustomerNotFound(customer_id)
    return customer


def list_customers(session: Session, *, limit: int, offset: int) -> list[Customer]:
    # ORDER BY is required for stable pages; without it Postgres may return rows in any order.
    stmt = select(Customer).order_by(Customer.id).limit(limit).offset(offset)
    return list(session.scalars(stmt))
