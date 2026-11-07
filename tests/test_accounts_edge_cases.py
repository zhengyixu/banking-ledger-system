"""Edge cases for money movement: YOUR tests.

Each stub below has a hint. Write the test, watch it fail for the right reason (or, for
the ones that should already pass, break the code on purpose to see it go red), then make
it green. Remove the `@todo` line from a stub once you've written the body.

An interviewer who asks "how did you test this?" wants to hear about THESE cases, not the
happy path.
"""

import pytest

todo = pytest.mark.skip(reason="TODO(you): write this test")


@todo
def test_withdraw_exactly_the_balance_succeeds_and_leaves_zero():
    """Boundary: balance 100.00, withdraw 100.00 -> 201 and balance 0.00.
    (Off-by-one trap: `>` vs `>=` in your comparison.)"""


@todo
def test_overdraft_is_rejected_and_changes_nothing():
    """balance 50.00, withdraw 80.00 -> the status code you chose, with a clear `detail`.
    Then prove NOTHING changed: balance still 50.00 AND zero Transaction rows.
    A half-applied failure is the worst kind of bug in a ledger."""


@todo
def test_overdraft_by_one_cent_is_rejected():
    """balance 50.00, withdraw 50.01. Decimal comparison must be exact. This is the case
    float arithmetic would get wrong in other systems."""


@todo
def test_withdraw_from_empty_account_is_rejected():
    """balance 0.00, any withdrawal -> rejected."""


@todo
def test_ten_deposits_of_ten_cents_equal_exactly_one_dollar():
    """Ten deposits of "0.10" -> balance exactly "1.00". Why does this matter?
    (0.1 + 0.1 + ... as floats != 1.0)"""


@todo
def test_ledger_invariant_balance_equals_sum_of_transactions():
    """After a mix of deposits and withdrawals (including an opening deposit and one
    rejected overdraft), assert  account.balance == SUM(transactions.amount)  with a real
    SQL aggregate:  select(func.sum(Transaction.amount)).where(...)."""


@todo
def test_failure_midway_leaves_balance_untouched(monkeypatch):
    """Atomicity: make the commit blow up (monkeypatch session.commit to raise) and check
    the balance and the transactions table are both unchanged after rolling back.
    Think: what does your service need to do on an unexpected exception?"""


@todo
def test_opening_deposit_and_account_are_created_together():
    """If recording the opening deposit fails, the account must not exist either.
    (One commit for both. Prove it.)"""


@todo
def test_service_rejects_non_positive_amount_even_when_called_directly():
    """Call services.accounts.deposit(session, id, Decimal('-1')) directly, bypassing the
    HTTP schema. Which exception do you raise, and why guard here at all?"""


@pytest.mark.skip(reason="LATER (phase 3): needs separate DB connections, not the rollback session")
def test_two_concurrent_withdrawals_cannot_overdraw():
    """Two threads each withdraw 80.00 from a 100.00 account. Exactly one must win.
    This is what `with_for_update()` is for. The per-test rollback session can't show it
    (both threads would share one transaction), so this test gets its own setup."""
