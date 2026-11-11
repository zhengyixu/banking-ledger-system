# CLAUDE.md

Project guide for AI coding assistants (and humans). A banking-style ledger API: FastAPI,
SQLAlchemy 2.1, Alembic, PostgreSQL 17, pytest. Money correctness matters more than speed.

## Commands

```bash
docker compose up -d --wait db                   # Postgres on localhost:5455 (plain `up` also starts migrate + app on :8000)
uv sync
uv run alembic upgrade head                      # dev database
uv run pytest -q                                 # needs the ledger_test database (compose creates it)
uv run ruff check . && uv run ruff format --check .
uv run python scripts/seed.py [--reset]          # ~500k fake transactions in the DEV db
```

The test suite drops and recreates the schema of the `*_test` database on every run and
refuses to run against any other database name. Never point `TEST_DATABASE_URL` at dev data.

## Architecture (keep these boundaries)

- `routers/` HTTP only: parse, call a service, shape the response. No business rules, no
  `session.commit()`.
- `services/` business rules and the **transaction boundary**. Services open
  `with session.begin():` themselves, so they must receive a session that has not run a
  query yet (SQLAlchemy autobegin otherwise raises "A transaction is already begun").
- `models.py` ORM tables. `schemas.py` Pydantic API contract: keep them separate.
- `exceptions.py` domain errors with no HTTP knowledge; `errors.py` is the only place they
  become status codes (`NotFound` 404, `Conflict` 409, `BusinessRuleViolation` 422). Add a
  subclass of the right base class instead of a new handler.
- Services take plain values (`Decimal`, ids), not request schemas, so they stay reusable.

## Rules that must not be broken

1. **Money is `Decimal`, never `float`.** `Numeric(18,2)` in the database, strings in JSON.
2. **The ledger is append-only.** Never update or delete a `Transaction`. Invariant:
   `account.balance == SUM(transactions.amount)`; tests assert it.
3. **Lock before you check.** Read a balance for a decision only after
   `get_account_for_update` (`SELECT ... FOR UPDATE`). When locking two accounts, lock in
   **ascending id order** to avoid deadlocks.
4. **One database transaction per business operation.** A transfer is two ledger rows plus
   two balance updates, all or nothing.
5. **Keyset pagination, not OFFSET.** Sort by `(created_at DESC, id DESC)`; `id` is the
   tie-breaker because rows from one transaction share `created_at`.
6. Migrations: every schema change is an Alembic migration, committed with its model change.
   Never edit a migration that has been applied.

## Testing expectations

- Tests run against real Postgres. Each test is wrapped in a rolled-back transaction
  (`create_savepoint`), and every HTTP request gets its own Session on that connection.
- Concurrency tests need real separate connections: use the `committed_sessions` fixture,
  one Session per thread, a `threading.Barrier`, and always `join(timeout=...)`.
- **A test that cannot fail is worthless.** After writing a test, break the code it covers
  (remove the lock, reverse the lock order, drop the tie-break, change `>` to `>=`) and
  confirm it goes red, then restore the code. This has caught several vacuous tests here.
- Assert on real expected values, not on values read back from the same row or from a
  sorted copy of the result.
- Race tests widen the window with a short `time.sleep` inside the critical section
  (monkeypatch `Transaction`), never with a random delay.

## Working style

- Small conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`); a model and its
  migration go in the same commit.
- Review AI-generated code by running it and mutation-checking its tests, not only reading it.
- Do not commit `.env`, scratch files or local notes.
