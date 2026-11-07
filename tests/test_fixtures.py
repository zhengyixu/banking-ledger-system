"""Tests for the test infrastructure itself.

If isolation silently broke, every later test would become order-dependent and flaky,
so it's worth proving it once, explicitly.
"""

from decimal import Decimal

from sqlalchemy import func, select

from ledger_service.db import get_session
from ledger_service.main import app
from ledger_service.models import Customer


def count_customers(session) -> int:
    return session.scalar(select(func.count()).select_from(Customer))


def test_isolation_part_1_data_is_committed_inside_the_test(session, make_customer):
    make_customer(email="same@example.com")
    session.commit()  # a real commit as far as the code under test can tell
    assert count_customers(session) == 1


def test_isolation_part_2_previous_test_left_nothing_behind(session, make_customer):
    # Same unique email as part 1. If part 1 had really committed, this would raise
    # IntegrityError, and the count below would be 2.
    assert count_customers(session) == 0
    make_customer(email="same@example.com")
    assert count_customers(session) == 1


def test_make_account_defaults(make_account):
    account = make_account()
    assert account.id is not None
    assert account.balance == Decimal("0.00")
    assert account.currency == "USD"
    assert account.customer_id is not None


def test_make_account_accepts_balance_and_shared_customer(make_customer, make_account):
    customer = make_customer()
    a = make_account(customer=customer, balance="125.50")
    b = make_account(customer=customer)
    assert a.customer_id == b.customer_id == customer.id
    assert a.balance == Decimal("125.50")


def test_client_fixture_overrides_the_session_dependency(client, session):
    # The override must point at the test session, not the real SessionLocal.
    assert app.dependency_overrides[get_session]() is session
    assert client.get("/health").status_code == 200
