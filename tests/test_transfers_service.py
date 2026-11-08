"""Service-level transfer tests: YOUR tests.

These call `transfer()` directly (no HTTP), because they are about the rules, not the API.
Each stub has a hint. Write the test, make sure it can FAIL (remove the thing it protects
and watch it go red), then restore the code. Remove the `@todo` line once it's written.

The two concurrency tests at the bottom are the real interview material. They need the
`committed_sessions` fixture (sessions that truly commit and compete for locks).
"""

import pytest

todo = pytest.mark.skip(reason="TODO(you): write this test")


@todo
def test_transfer_conserves_money_and_the_two_legs_sum_to_zero():
    """After a transfer: balance_a + balance_b is unchanged, and
    SUM(transactions.amount) over the two legs (select ... where transfer_id == X) is
    exactly 0. Use a real SQL aggregate, not Python arithmetic on the objects."""


@todo
def test_each_account_balance_equals_the_sum_of_its_ledger_rows():
    """Build the accounts with create_account(... opening_deposit=...) so each already has
    a ledger row (factories do NOT create ledger rows). Do a few transfers both ways, then
    for each account assert balance == SUM(its transactions)."""


@todo
def test_failure_on_the_second_leg_rolls_back_the_first():
    """Atomicity: monkeypatch `transfers.Transaction` (the name as services/transfers.py
    sees it) with a function that raises on its SECOND call only (a counter in a closure).
    After pytest.raises, session.expire_all() and prove: both balances unchanged and zero
    ledger rows. This is the 'debit saved, credit lost' bug that real money systems fear."""


@todo
def test_same_account_is_rejected_before_touching_the_database():
    """Expect SameAccountTransfer. Hint: how could you prove no lock/query happened?
    (e.g. pass an id that doesn't exist: if the guard runs first you get
    SameAccountTransfer, not AccountNotFound)."""


@todo
def test_currency_mismatch_is_rejected_and_changes_nothing():
    """Expect CurrencyMismatch; both balances and the ledger unchanged."""


@todo
def test_exact_balance_can_be_transferred_and_one_cent_more_cannot():
    """Boundary on the SERVICE: balance 50.00 -> transfer 50.00 works (source ends at
    0.00); 50.01 raises InsufficientFunds. (Off-by-one: < vs <=.)"""


@todo
def test_non_positive_amounts_are_rejected_when_called_directly():
    """Same idea as the deposit/withdraw guard test: parametrize -1 and 0, expect
    ValueError, and prove balances/ledger unchanged."""


@pytest.mark.skip(reason="TODO(you): concurrency test #1. Setup hints in the docstring.")
def test_two_concurrent_transfers_cannot_overdraw_the_source():
    """Account A has 100.00. Two threads each transfer 80.00 from A to different
    destinations at the same moment. EXACTLY ONE must succeed; the other must raise
    InsufficientFunds; A must end at 20.00, never negative.

    Setup:
      - make the accounts with `committed_sessions()`: it returns a NEW Session each call
        and its data is really committed (the fixture wipes the tables afterwards).
      - run each transfer in its own thread with its own Session (sessions are not
        thread-safe; never share one).
      - use a threading.Barrier so both threads call transfer() at the same instant.
      - collect each thread's result or exception, join the threads, then read the final
        balances with a fresh Session.
    Prove it can fail, RELIABLY: I tried removing `.with_for_update()` and running this a
    few times; the race window is so small the test kept passing, so don't trust that.
    Widen the window instead: monkeypatch `transfers.Transaction` with a wrapper that does
    `time.sleep(0.3)` and then builds the real `Transaction`. That sleep sits between
    "read the balance" and "commit", so without the lock both threads read 100.00 and both
    go ahead. I measured it: with the lock this test passes every time; without it BOTH
    transfers succeed and 160.00 leaves a 100.00 account (money created). With the lock the
    second thread simply waits, then sees 20.00 and is refused.
    Restore `.with_for_update()` afterwards.
    (Interview point: a concurrency test that cannot fail is worthless; make the bug
    reproducible before you claim the fix works.)"""


@pytest.mark.skip(reason="TODO(you): concurrency test #2. Setup hints in the docstring.")
def test_opposite_direction_transfers_do_not_deadlock():
    """Accounts A and B hold 1000.00 each. Thread 1 does A->B and thread 2 does B->A,
    each repeated ~25 times with 1.00. Nothing may raise (no deadlock, no
    OperationalError / 40P01), and in the end balance_a + balance_b == 2000.00.

    Prove it can fail: change your service to lock in the order (source, destination)
    instead of ascending id, and run the test. I measured this: one thread dies with
    sqlalchemy.exc.OperationalError (Postgres' "deadlock detected") and the other finishes,
    so the totals no longer line up. Then restore the ordered locking.
    Same setup as the first concurrency test (committed_sessions, one Session per thread,
    a Barrier to start together)."""
