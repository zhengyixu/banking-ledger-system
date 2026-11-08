"""Transfer API tests: the HTTP *contract* your transfer service has to meet.

Tests marked `needs_service` are skipped until you implement services/transfers.py.
Delete the marker once `transfer()` works. Validation tests already run: the schema
rejects those requests before your code is called.

Rules for the service itself (atomicity, locking, guards, the ledger invariant) belong in
tests/test_transfers_service.py, which is yours to write.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from ledger_service.models import Account, Transaction

needs_service = pytest.mark.skip(reason="TODO(you): implement services/transfers.py")


def post_transfer(client, source, destination, amount):
    return client.post(
        "/v1/transfers",
        json={
            "from_account_id": source.id,
            "to_account_id": destination.id,
            "amount": amount,
        },
    )


def balance_of(client, account) -> str:
    return client.get(f"/v1/accounts/{account.id}").json()["balance"]


@needs_service
def test_transfer_moves_money_and_returns_both_legs(client, make_account):
    source = make_account(balance="100.00")
    destination = make_account(balance="20.00")

    response = post_transfer(client, source, destination, "30.00")

    assert response.status_code == 201
    body = response.json()
    assert body["from_account_id"] == source.id
    assert body["to_account_id"] == destination.id
    assert body["amount"] == "30.00"
    assert body["debit"]["kind"] == "transfer_out"
    assert body["debit"]["amount"] == "-30.00"
    assert body["debit"]["account_id"] == source.id
    assert body["credit"]["kind"] == "transfer_in"
    assert body["credit"]["amount"] == "30.00"
    assert body["credit"]["account_id"] == destination.id
    # Both legs carry the SAME transfer id: that is what pairs them.
    assert body["debit"]["transfer_id"] == body["credit"]["transfer_id"] == body["transfer_id"]
    assert balance_of(client, source) == "70.00"
    assert balance_of(client, destination) == "50.00"


@needs_service
def test_transfer_writes_exactly_two_ledger_rows(client, session, make_account):
    source = make_account(balance="100.00")
    destination = make_account()

    post_transfer(client, source, destination, "40.00")

    rows = list(session.scalars(select(Transaction).order_by(Transaction.id)))
    assert [(r.account_id, r.kind, r.amount) for r in rows] == [
        (source.id, "transfer_out", Decimal("-40.00")),
        (destination.id, "transfer_in", Decimal("40.00")),
    ]
    assert rows[0].transfer_id is not None
    assert rows[0].transfer_id == rows[1].transfer_id


@needs_service
def test_transfer_in_either_direction_between_the_same_accounts(client, make_account):
    a = make_account(balance="100.00")
    b = make_account(balance="100.00")

    assert post_transfer(client, a, b, "10.00").status_code == 201
    assert post_transfer(client, b, a, "25.00").status_code == 201

    assert balance_of(client, a) == "115.00"
    assert balance_of(client, b) == "85.00"


@needs_service
def test_transfer_from_unknown_account_returns_404(client, make_account):
    destination = make_account()
    response = client.post(
        "/v1/transfers",
        json={"from_account_id": 999999, "to_account_id": destination.id, "amount": "1.00"},
    )

    assert response.status_code == 404
    assert "999999" in response.json()["detail"]


@needs_service
def test_transfer_to_unknown_account_returns_404(client, make_account):
    source = make_account(balance="10.00")
    response = client.post(
        "/v1/transfers",
        json={"from_account_id": source.id, "to_account_id": 999999, "amount": "1.00"},
    )

    assert response.status_code == 404
    assert balance_of(client, source) == "10.00"


@needs_service
def test_transfer_with_insufficient_funds_returns_422_and_changes_nothing(
    client, session, make_account
):
    source = make_account(balance="50.00")
    destination = make_account(balance="5.00")

    response = post_transfer(client, source, destination, "50.01")

    assert response.status_code == 422
    assert balance_of(client, source) == "50.00"
    assert balance_of(client, destination) == "5.00"
    assert list(session.scalars(select(Transaction))) == []


@needs_service
def test_transfer_to_the_same_account_returns_422(client, make_account):
    account = make_account(balance="100.00")

    response = post_transfer(client, account, account, "10.00")

    assert response.status_code == 422
    assert balance_of(client, account) == "100.00"


@needs_service
def test_transfer_between_different_currencies_returns_422(client, make_account):
    usd = make_account(balance="100.00", currency="USD")
    eur = make_account(balance="100.00", currency="EUR")

    response = post_transfer(client, usd, eur, "10.00")

    assert response.status_code == 422
    assert balance_of(client, usd) == "100.00"
    assert balance_of(client, eur) == "100.00"


@needs_service
def test_total_money_is_conserved_by_a_transfer(client, session, make_account):
    source = make_account(balance="100.00")
    destination = make_account(balance="23.45")

    post_transfer(client, source, destination, "33.33")

    session.expire_all()
    total = sum(a.balance for a in session.scalars(select(Account)))
    assert total == Decimal("123.45")


# --- validation (runs now: the schema rejects these before your code is called) ---------


@pytest.mark.parametrize("amount", ["0", "0.00", "-5.00", "1.234", "abc", "", None])
def test_transfer_rejects_invalid_amounts(client, make_account, amount):
    source = make_account(balance="100.00")
    destination = make_account()

    assert post_transfer(client, source, destination, amount).status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"from_account_id": 1, "to_account_id": 2},  # amount missing
        {"to_account_id": 2, "amount": "1.00"},  # source missing
        {"from_account_id": 1, "amount": "1.00"},  # destination missing
        {"from_account_id": "x", "to_account_id": 2, "amount": "1.00"},
    ],
)
def test_transfer_rejects_incomplete_payloads(client, payload):
    assert client.post("/v1/transfers", json=payload).status_code == 422
