"""Account API tests: the *contract* your service has to meet.

Tests marked `needs_service` are skipped until you implement services/accounts.py.
Workflow: implement one function, delete `needs_service` from its tests, run pytest,
repeat. (Tests that don't need your code, like validation and 404s, already run.)
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from ledger_service.models import Transaction

needs_service = pytest.mark.skip(reason="TODO(you): implement services/accounts.py")


def transactions_of(session, account_id):
    return list(
        session.scalars(
            select(Transaction).where(Transaction.account_id == account_id).order_by(Transaction.id)
        )
    )


# --- create account -------------------------------------------------------------------


@needs_service
def test_create_account_defaults_to_usd_and_zero_balance(client, make_customer):
    customer = make_customer()

    response = client.post("/v1/accounts", json={"customer_id": customer.id})

    assert response.status_code == 201
    body = response.json()
    assert body["customer_id"] == customer.id
    assert body["currency"] == "USD"
    assert body["balance"] == "0.00"  # money travels as a string, never a float
    assert response.headers["Location"] == f"/v1/accounts/{body['id']}"


@needs_service
def test_create_account_with_opening_deposit_records_a_deposit(client, session, make_customer):
    customer = make_customer()

    response = client.post(
        "/v1/accounts",
        json={"customer_id": customer.id, "currency": "EUR", "opening_deposit": "250.75"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["currency"] == "EUR"
    assert body["balance"] == "250.75"
    rows = transactions_of(session, body["id"])
    assert [(t.kind, t.amount) for t in rows] == [("deposit", Decimal("250.75"))]


@needs_service
def test_create_account_for_unknown_customer_returns_404(client):
    response = client.post("/v1/accounts", json={"customer_id": 999999})

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        {},  # customer_id missing
        {"customer_id": 1, "currency": "usd"},  # must be upper-case
        {"customer_id": 1, "currency": "US"},
        {"customer_id": 1, "currency": "USDX"},
        {"customer_id": 1, "opening_deposit": "-5.00"},
        {"customer_id": 1, "opening_deposit": "1.234"},  # too many decimals
        {"customer_id": 1, "opening_deposit": "abc"},
    ],
)
def test_create_account_rejects_invalid_payload(client, payload):
    assert client.post("/v1/accounts", json=payload).status_code == 422


# --- read account (does not need your service code) -----------------------------------


def test_get_account_returns_200(client, make_account):
    account = make_account(balance="42.10")

    response = client.get(f"/v1/accounts/{account.id}")

    assert response.status_code == 200
    assert response.json()["id"] == account.id
    assert response.json()["balance"] == "42.10"


def test_get_unknown_account_returns_404(client):
    response = client.get("/v1/accounts/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Account 999999 not found"}


# --- deposits -------------------------------------------------------------------------


@needs_service
def test_deposit_increases_balance_and_records_a_positive_transaction(
    client, session, make_account
):
    account = make_account(balance="100.00")

    response = client.post(f"/v1/accounts/{account.id}/deposits", json={"amount": "25.50"})

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "deposit"
    assert body["amount"] == "25.50"
    assert body["account_id"] == account.id
    assert body["transfer_id"] is None
    assert client.get(f"/v1/accounts/{account.id}").json()["balance"] == "125.50"
    assert [t.amount for t in transactions_of(session, account.id)] == [Decimal("25.50")]


@needs_service
def test_deposit_to_unknown_account_returns_404(client):
    response = client.post("/v1/accounts/999999/deposits", json={"amount": "10.00"})

    assert response.status_code == 404


# --- withdrawals ----------------------------------------------------------------------


@needs_service
def test_withdraw_decreases_balance_and_records_a_negative_transaction(
    client, session, make_account
):
    account = make_account(balance="100.00")

    response = client.post(f"/v1/accounts/{account.id}/withdrawals", json={"amount": "30.00"})

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "withdrawal"
    assert body["amount"] == "-30.00"  # stored signed: money leaving is negative
    assert client.get(f"/v1/accounts/{account.id}").json()["balance"] == "70.00"
    assert [t.amount for t in transactions_of(session, account.id)] == [Decimal("-30.00")]


@needs_service
def test_withdraw_from_unknown_account_returns_404(client):
    response = client.post("/v1/accounts/999999/withdrawals", json={"amount": "10.00"})

    assert response.status_code == 404


# --- amount validation (runs now: the schema rejects these before your code is called) ---


@pytest.mark.parametrize("action", ["deposits", "withdrawals"])
@pytest.mark.parametrize(
    "amount",
    ["0", "0.00", "-5.00", "1.234", "abc", "", None, "1e30", "99999999999999999999.00"],
)
def test_money_movement_rejects_invalid_amounts(client, make_account, action, amount):
    account = make_account(balance="100.00")

    response = client.post(f"/v1/accounts/{account.id}/{action}", json={"amount": amount})

    assert response.status_code == 422


@pytest.mark.parametrize("action", ["deposits", "withdrawals"])
def test_money_movement_requires_an_amount(client, make_account, action):
    account = make_account(balance="100.00")

    assert client.post(f"/v1/accounts/{account.id}/{action}", json={}).status_code == 422
