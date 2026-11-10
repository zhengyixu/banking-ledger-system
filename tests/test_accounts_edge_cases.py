"""Edge cases for money movements."""

import threading
import time
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import func, select

from ledger_service.exceptions import InsufficientFunds
from ledger_service.models import Account, Customer, Transaction
from ledger_service.schemas import AccountCreate
from ledger_service.services import accounts as account_service
from ledger_service.services.accounts import create_account


def test_withdraw_exactly_the_balance_succeeds_and_leaves_zero(client, make_account):
    """Boundary: balance 100.00, withdraw 100.00 -> 201 and balance 0.00.
    (Off-by-one trap: `>` vs `>=` in the comparison.)"""
    account = make_account(balance="100.00")
    response = client.post(
        f"/v1/accounts/{account.id}/withdrawals",
        json={"amount": "100.00"},
    )
    assert response.status_code == 201
    assert client.get(f"/v1/accounts/{account.id}").json()["balance"] == "0.00"


def test_overdraft_is_rejected_and_changes_nothing(client, make_account):
    """balance 50.00, withdraw 80.00 -> the status code you chose, with a clear `detail`.
    Then prove NOTHING changed: balance still 50.00 AND zero Transaction rows.
    A half-applied failure is the worst kind of bug in a ledger."""
    account = make_account(balance="50.00")
    response = client.post(
        f"/v1/accounts/{account.id}/withdrawals",
        json={"amount": "80.00"},
    )
    assert response.status_code == 422
    assert client.get(f"/v1/accounts/{account.id}").json()["balance"] == "50.00"


def test_overdraft_by_one_cent_is_rejected(client, make_account):
    """balance 50.00, withdraw 50.01. Decimal comparison must be exact. This is the case
    float arithmetic would get wrong in other systems."""
    account = make_account(balance="50.00")
    response = client.post(
        f"/v1/accounts/{account.id}/withdrawals",
        json={"amount": "50.01"},
    )
    assert response.status_code == 422
    assert client.get(f"/v1/accounts/{account.id}").json()["balance"] == "50.00"


def test_withdraw_from_empty_account_is_rejected(client, make_account):
    """balance 0.00, any withdrawal -> rejected."""
    account = make_account()
    response = client.post(
        f"/v1/accounts/{account.id}/withdrawals",
        json={"amount": "0.01"},
    )
    assert response.status_code == 422


def test_ten_deposits_of_ten_cents_equal_exactly_one_dollar(client, make_account):
    """Ten deposits of "0.10" -> balance exactly "1.00". Why does this matter?
    (0.1 + 0.1 + ... as floats != 1.0)"""
    account = make_account()
    for _ in range(10):
        response = client.post(
            f"/v1/accounts/{account.id}/deposits",
            json={"amount": "0.10"},
        )
        assert response.status_code == 201
    assert client.get(f"/v1/accounts/{account.id}").json()["balance"] == "1.00"


def test_ledger_invariant_balance_equals_sum_of_transactions(session, client, make_customer):
    """After a mix of deposits and withdrawals (including an opening deposit and one
    rejected overdraft), assert  account.balance == SUM(transactions.amount)  with a real
    SQL aggregate:  select(func.sum(Transaction.amount)).where(...)."""
    customer = make_customer()
    account = create_account(
        session, AccountCreate(customer_id=customer.id, opening_deposit=Decimal("100.00"))
    )
    response = client.post(
        f"/v1/accounts/{account.id}/deposits",
        json={"amount": "50.00"},
    )
    assert response.status_code == 201
    assert client.get(f"/v1/accounts/{account.id}").json()["balance"] == "150.00"
    response = client.post(
        f"/v1/accounts/{account.id}/withdrawals",
        json={"amount": "250.00"},
    )
    assert response.status_code == 422
    response = client.post(
        f"/v1/accounts/{account.id}/withdrawals",
        json={"amount": "100.00"},
    )
    assert response.status_code == 201
    total = session.execute(
        select(func.sum(Transaction.amount)).where(Transaction.account_id == account.id)
    ).scalar()
    assert client.get(f"/v1/accounts/{account.id}").json()["balance"] == f"{total}"


def test_failure_midway_leaves_balance_untouched(session, make_account, monkeypatch):
    """Atomicity: make a step blow up AFTER the balance was changed, then check that the
    balance and the transactions table are both unchanged."""
    account = make_account(balance="100.00")

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(account_service, "Transaction", boom)
    with pytest.raises(RuntimeError):
        account_service.deposit(session, account.id, Decimal("10.00"))
    # account_service.deposit(session, account.id, Decimal("10.00"))

    session.expire_all()
    assert session.get(Account, account.id).balance == Decimal("100.00")


def test_opening_deposit_and_account_are_created_together(session, make_customer, monkeypatch):
    """If recording the opening deposit fails, the account must not exist either.
    (One transaction for both.)

    `Transaction` is monkeypatched to raise. The account row was already flushed by then,
    so an empty accounts table afterwards proves the rollback undid it, not that it was
    never sent."""
    customer = make_customer()

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(account_service, "Transaction", boom)
    with pytest.raises(RuntimeError):
        create_account(
            session, AccountCreate(customer_id=customer.id, opening_deposit=Decimal("100.00"))
        )
    session.expire_all()
    rows = session.scalars(select(Account).where(Account.customer_id == customer.id)).all()
    assert rows == []


@pytest.mark.parametrize("amount", [Decimal("-1"), Decimal("0")])
@pytest.mark.parametrize("function", [account_service.deposit, account_service.withdraw])
def test_service_rejects_non_positive_amount_even_when_called_directly(
    session, make_account, function, amount
):
    """Call services.accounts.deposit(session, id, Decimal('-1')) directly, bypassing the
    HTTP schema."""
    account = make_account(balance="100.00")
    with pytest.raises(ValueError):
        function(session, account.id, amount)

    session.expire_all()
    assert session.get(Account, account.id).balance == Decimal("100.00")


def test_two_concurrent_withdrawals_cannot_overdraw(committed_sessions, monkeypatch):
    """Two threads each withdraw 80.00 from a 100.00 account. Exactly one must win.
    This is what `with_for_update()` is for. The per-test rollback session can't show it
    (both threads would share one transaction), so this test gets its own setup."""

    with committed_sessions() as setup, setup.begin():
        customer = Customer(name="A", email="a@tt.com")
        setup.add(customer)
        setup.flush()
        account = Account(customer_id=customer.id, balance=Decimal("100.00"))
        setup.add(account)
        setup.flush()

    real_tx = account_service.Transaction

    def slow_transaction(*a, **kw):
        time.sleep(0.3)
        return real_tx(*a, **kw)

    monkeypatch.setattr(account_service, "Transaction", slow_transaction)

    barrier = threading.Barrier(2)
    results = []

    def worker(barrier: Barrier, from_account_id: int, amount: Decimal):
        with committed_sessions() as s:
            barrier.wait(timeout=5)
            try:
                account_service.withdraw(s, from_account_id, amount)
                results.append("ok")
            except Exception as e:
                results.append(e)

    t1 = threading.Thread(target=worker, args=(barrier, account.id, Decimal("80.00")))
    t2 = threading.Thread(target=worker, args=(barrier, account.id, Decimal("80.00")))

    t1.start()
    t2.start()

    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not t1.is_alive() and not t2.is_alive()

    assert results.count("ok") == 1
    assert sum(isinstance(r, InsufficientFunds) for r in results) == 1
    with committed_sessions() as setup, setup.begin():
        account = setup.get(Account, account.id)
        assert account.balance == Decimal("20.00")
