# Banking Ledger System

[![CI](https://github.com/zhengyixu/banking-ledger-system/actions/workflows/ci.yml/badge.svg)](https://github.com/zhengyixu/banking-ledger-system/actions/workflows/ci.yml)

A small banking-style ledger API: customers, accounts, deposits, withdrawals, atomic
transfers and a paginated transaction history. Built with **FastAPI, SQLAlchemy 2.1,
Alembic, PostgreSQL and pytest**.

The point of the project is the hard parts of money handling, done and *tested*
properly: atomicity, row locking, deadlock avoidance, exact decimal arithmetic and keyset
pagination.

## Highlights

- **Atomic transfers.** A transfer is two ledger rows sharing a `transfer_id` plus both
  balance updates, all in one database transaction. A failure on the second leg rolls
  back the first.
- **Concurrency-safe.** Accounts are locked with `SELECT ... FOR UPDATE`, always in
  ascending id order, so opposite-direction transfers cannot deadlock. The balance is
  checked only *after* the lock is held, so two concurrent withdrawals cannot overdraw.
- **Append-only ledger.** `Transaction.amount` is signed and never updated. Invariant:
  `account.balance == SUM(transactions.amount)`, asserted in tests.
- **Money is `Decimal` end to end.** `Numeric(18,2)` in Postgres, `Decimal` in Python,
  strings in JSON. Never `float`.
- **Defence in depth.** The database also enforces the rules: `CHECK (balance >= 0)`,
  `CHECK` on transaction kinds, `UNIQUE` on customer email.
- **Keyset pagination** for the history (`limit` + opaque `cursor`), sorted by
  `(created_at, id)` so rows that share a timestamp are neither skipped nor repeated.
  Backed by a composite index, so every page costs the same (see Performance).
- **Runs anywhere with Docker.** `docker compose up --build` starts Postgres, runs the
  migrations once, then starts the API.

## API

All routes are under `/v1`. Interactive docs at `/docs`.

| Method | Path | Notes |
|---|---|---|
| POST | `/customers` | 201 + `Location`; duplicate email -> 409 |
| GET | `/customers`, `/customers/{id}` | 404 if unknown |
| POST | `/accounts` | optional `opening_deposit` is recorded in the ledger |
| GET | `/accounts/{id}` | |
| POST | `/accounts/{id}/deposits` | body `{"amount": "125.50"}`; 201 |
| POST | `/accounts/{id}/withdrawals` | overdraft -> 422 |
| POST | `/transfers` | returns both legs; same account / currency mismatch / insufficient funds -> 422 |
| GET | `/accounts/{id}/transactions?limit=50&cursor=...` | newest first, `next_cursor` is `null` on the last page |
| GET | `/health` | |

## Architecture

```
routers/   HTTP only: parse request, call a service, shape the response
services/  business rules + the transaction boundary (commit / rollback happens here)
models.py  SQLAlchemy 2.1 ORM models (the tables)
schemas.py Pydantic API contract (kept separate from the ORM models)
errors.py  the one place domain exceptions become HTTP status codes
```

- Domain exceptions (`InsufficientFunds`, `AccountNotFound`, ...) carry no HTTP knowledge.
  `errors.py` maps base classes: `NotFound` -> 404, `Conflict` -> 409,
  `BusinessRuleViolation` -> 422, so new rules need no new handler.
- Services take plain values (`Decimal`, ids), not request schemas, so they can be reused
  from a CLI, a worker or an MCP server.
- Pydantic schemas are separate from ORM models, so a new column never leaks into the API.

## Testing

`uv run pytest` runs 125 tests against a real Postgres (`ledger_test`), not SQLite.

- **Isolation:** every test runs in an outer transaction that is rolled back
  (`join_transaction_mode="create_savepoint"`), and each HTTP request gets its own Session
  on that connection, like production. The schema is built by `alembic upgrade head` on
  every run, so the migrations are tested too.
- **Real concurrency tests** use threads with separate connections: concurrent transfers
  cannot overdraw, opposite-direction transfers do not deadlock, concurrent withdrawals
  cannot overdraw.
- **Tests that can fail.** Each concurrency and invariant test was checked by removing the
  thing it protects (the row lock, the lock ordering, the `id` tie-break) and confirming it
  goes red. A short `sleep` inside the critical section makes the race reproducible.
- Atomicity is tested by forcing a failure midway and asserting that balances *and* ledger
  rows are unchanged.

## Performance

The history query on the hot account (300k of the 500k seeded rows),
`EXPLAIN (ANALYZE, BUFFERS)`, warm cache, limit 50:

| | Plan | Buffers | Time |
|---|---|---|---|
| Before, first page | Parallel Seq Scan + top-N sort | 3,763 | 25.1 ms |
| Index `(account_id, created_at DESC, id DESC)`, first page | Index Scan | 4 | 0.06 ms |
| Index, page at depth 150k, `OR` cursor filter | Index Scan, cursor in `Filter` | 1,846 | 16.4 ms |
| Index, page at depth 150k, `(created_at, id) < (...)` | Index Scan, cursor in `Index Cond` | 5 | 0.08 ms |

The index alone fixed the first page but not deep pages: the portable form of the cursor,
`created_at < c OR (created_at = c AND id < x)`, cannot be used as an index boundary, so
Postgres walked the account's entries and filtered. The row-value comparison
`(created_at, id) < (c, x)` is a real index condition, so a page at depth 150k costs
the same as page 1. `created_at` is `timestamptz`; the migration converts the existing UTC values with
an explicit `AT TIME ZONE 'UTC'` and round-trips on downgrade.

## Run it

Everything in Docker (Postgres, one-shot migrations, then the API on port 8000):

```bash
docker compose up --build
curl localhost:8000/health
```

For development (API and tests on the host, only Postgres in Docker):

```bash
cp .env.example .env
docker compose up -d --wait db       # Postgres 17 on localhost:5455
uv sync
uv run alembic upgrade head
uv run uvicorn ledger_service.main:app --reload
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Optional: `uv run python scripts/seed.py` fills the dev database with ~500k transactions
(one account with 300k) for practising `EXPLAIN ANALYZE`.

## Known limitations / roadmap

- No authentication yet.
- `POST /transfers` is not idempotent: a client retry after a timeout transfers twice.
  Planned fix: an `Idempotency-Key` header with a unique constraint.
- CI builds the Docker image but does not yet start the stack and hit `/health`.

## Built with AI assistance

Developed with Claude Code as a pair-programmer. Working agreement: the assistant
scaffolds boilerplate and reviews; I write and debug the core logic (transfers, the
history query, most tests), and every test is validated by deliberately breaking the code
it covers. The mistakes caught along the way are part of the story: a test that could not
fail, a concurrency test that locked inside the test instead of the service, and a
sleep that made a "deadlock" appear in fixture teardown instead of the code.
