# Ledger Service

A small banking-style ledger API: customers, accounts, and atomic transfers.
Built as a hands-on project with FastAPI, SQLAlchemy 2.1, Alembic, PostgreSQL and pytest.

## Quick start

```bash
cp .env.example .env
docker compose up -d --wait          # Postgres on localhost:5455
uv sync
uv run alembic upgrade head          # create tables
uv run uvicorn ledger_service.main:app --reload
uv run pytest
```

Docs at http://localhost:8000/docs once the server is running.

## Layout

- `src/ledger_service/` application code (`models.py`, `db.py`, `config.py`, `main.py`)
- `migrations/` Alembic migrations (`uv run alembic revision --autogenerate -m "..."`)
- `tests/` pytest suite
- `docker-compose.yml` local Postgres (creates `ledger` and `ledger_test` databases)
