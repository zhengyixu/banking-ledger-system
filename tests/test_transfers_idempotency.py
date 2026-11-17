"""Idempotency-Key on POST /transfers. One TODO test per rule; each must be able to fail.

Delete the skip marker of a test only when you write its body. Mutation checks to do at the
end: drop ON CONFLICT / the unique constraint (concurrent test must go red), skip the
request_hash comparison (reuse test must go red), insert the key outside the transfer
transaction (failure test must go red).
"""

import pytest

pytestmark = pytest.mark.skip(reason="TODO: idempotency not implemented yet")


def test_retry_with_same_key_returns_the_same_transfer_and_moves_money_once():
    """POST twice with the same key and body. Both 201 with the same transfer_id; balances
    changed once; exactly 2 Transaction rows exist (use the `session` fixture to count)."""


def test_same_key_with_a_different_body_returns_422():
    """Same key, different amount -> 422 and balances unchanged by the second call."""


def test_failed_transfer_does_not_consume_the_key():
    """Key + insufficient funds -> 422. Deposit enough, retry with the SAME key and body ->
    201. (Failures are not cached.)"""


def test_no_header_behaves_exactly_as_before():
    """Two identical POSTs without the header create two separate transfers."""


def test_concurrent_requests_with_the_same_key_create_one_transfer():
    """Real threads (committed_sessions, one Session per thread, Barrier, join(timeout=...)).
    Two threads call the service with the same key at the same moment. Exactly 2 ledger rows
    in total, the balances moved once, and both threads got the same transfer_id."""
