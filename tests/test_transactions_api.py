"""Transaction history API: the HTTP *contract* for GET /v1/accounts/{id}/transactions.

Tests marked `needs_service` are skipped until you implement services/transactions.py.
Delete the marker once `list_transactions()` works. The validation tests already run: the
bad `limit` / `cursor` is rejected before your code is called.

NOTE for the tie-break: inside a test, every row gets the SAME `created_at`, because
Postgres `now()` is the start time of the (never-committed) test transaction. So these
tests only pass if `id` really is used as the tie-breaker. That is on purpose.

The last two tests are yours: they target the two classic keyset-pagination bugs.
"""

import base64
import datetime
from decimal import Decimal

import pytest

from ledger_service.models import Transaction

needs_service = pytest.mark.skip(reason="TODO(you): implement services/transactions.py")
todo = pytest.mark.skip(reason="TODO(you): write this test")


def deposit(client, account, amount):
    response = client.post(f"/v1/accounts/{account.id}/deposits", json={"amount": amount})
    assert response.status_code == 201
    return response.json()


def history(client, account, **params):
    return client.get(f"/v1/accounts/{account.id}/transactions", params=params)


def test_empty_history_is_an_empty_page(client, make_account):
    account = make_account()
    response = history(client, account)
    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


def test_unknown_account_is_404(client):
    response = client.get("/v1/accounts/999999/transactions")
    assert response.status_code == 404


def test_history_is_newest_first_and_has_the_transaction_fields(client, make_account):
    account = make_account()
    for amount in ("1.00", "2.00", "3.00"):
        deposit(client, account, amount)

    items = history(client, account).json()["items"]

    assert [item["amount"] for item in items] == ["3.00", "2.00", "1.00"]
    assert set(items[0]) == {"id", "account_id", "amount", "kind", "transfer_id", "created_at"}


def test_history_only_contains_this_accounts_rows(client, make_account):
    mine, other = make_account(), make_account()
    deposit(client, mine, "1.00")
    deposit(client, other, "2.00")

    items = history(client, mine).json()["items"]

    assert [item["account_id"] for item in items] == [mine.id]


def test_walking_the_pages_returns_every_row_exactly_once(client, make_account):
    account = make_account()
    expected_ids = [deposit(client, account, "1.00")["id"] for _ in range(5)][::-1]

    seen, page_sizes, cursor = [], [], None
    while True:
        params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        body = history(client, account, **params).json()
        seen += [item["id"] for item in body["items"]]
        page_sizes.append(len(body["items"]))
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert page_sizes == [2, 2, 1]
    assert seen == expected_ids


def test_exact_multiple_of_limit_has_no_phantom_next_page(client, make_account):
    """4 rows, limit 2: the second page is the last one, so next_cursor must be null.
    (Off-by-one trap with the `limit + 1` trick.)"""
    account = make_account()
    for _ in range(4):
        deposit(client, account, "1.00")

    first = history(client, account, limit=2).json()
    second = history(client, account, limit=2, cursor=first["next_cursor"]).json()

    assert len(second["items"]) == 2
    assert second["next_cursor"] is None


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_limit_out_of_range_is_422(client, make_account, limit):
    account = make_account()
    assert history(client, account, limit=limit).status_code == 422


@pytest.mark.parametrize(
    "cursor",
    [
        "not-base64!!",
        base64.urlsafe_b64encode(b"garbage").decode(),
        base64.urlsafe_b64encode(b"not-a-date|7").decode(),
        base64.urlsafe_b64encode(b"2024-01-01T00:00:00|not-an-int").decode(),
    ],
)
def test_garbage_cursor_is_422_not_500(client, make_account, cursor):
    account = make_account()
    response = history(client, account, cursor=cursor)
    assert response.status_code == 422


def test_new_rows_between_pages_do_not_shift_or_duplicate_results(client, make_account):
    """Why keyset beats OFFSET. Create 4 deposits, fetch page 1 with limit=2, then make
    ANOTHER deposit, then fetch page 2 with the cursor. Page 2 must be exactly the two
    OLDEST rows, with no row repeated from page 1 and the new deposit absent (it is newer
    than the cursor, so it belongs to a page the client has already passed).
    With OFFSET 2 the new row would push page-1 rows onto page 2 (duplicates)."""
    account = make_account()
    ids = []
    for _ in range(4):
        response = deposit(client, account, "1.00")
        ids.append(response["id"])

    first = history(client, account, limit=2).json()
    first_page = first["items"]

    response = deposit(client, account, "1.00")
    new_id = response["id"]

    second = history(client, account, limit=2, cursor=first["next_cursor"]).json()
    second_page = second["items"]

    first_page_ids = [tx["id"] for tx in first_page]
    second_page_ids = [tx["id"] for tx in second_page]

    assert first_page_ids == [ids[3], ids[2]]
    assert second_page_ids == [ids[1], ids[0]]

    assert second["next_cursor"] is None
    assert new_id not in first_page_ids + second_page_ids


def test_rows_with_the_same_created_at_are_neither_skipped_nor_repeated(
    session, client, make_account
):
    """The tie-break test. Insert Transaction rows DIRECTLY (session.add + commit), several
    sharing one explicit `created_at` and a few with other timestamps, then page through
    with limit=1. Every row must appear exactly once, in (created_at, id) descending order.
    Prove it can fail: drop `id` from the ORDER BY / comparison in your service and watch
    rows go missing or repeat."""
    account = make_account()
    with session.begin():
        txs = [
            Transaction(
                account_id=account.id,
                created_at=datetime.datetime(2026, 2, 11),
                amount=Decimal("1.00"),
                kind="deposit",
            ),
            Transaction(
                account_id=account.id,
                created_at=datetime.datetime(2026, 2, 9),
                amount=Decimal("1.00"),
                kind="deposit",
            ),
            Transaction(
                account_id=account.id,
                created_at=datetime.datetime(2026, 2, 10),
                amount=Decimal("1.00"),
                kind="deposit",
            ),
            Transaction(
                account_id=account.id,
                created_at=datetime.datetime(2026, 2, 10),
                amount=Decimal("1.00"),
                kind="deposit",
            ),
        ]
        session.add_all(txs)

    expected = [t.id for t in sorted(txs, key=lambda t: (t.created_at, t.id), reverse=True)]

    page_ids = []
    cursor = None
    for _ in range(10):
        body = history(client, account, limit=1, cursor=cursor).json()
        page = body["items"]
        cursor = body["next_cursor"]
        ids = [tx["id"] for tx in page]
        page_ids = page_ids + ids
        if cursor is None:
            break

    assert page_ids == expected
    assert cursor is None
