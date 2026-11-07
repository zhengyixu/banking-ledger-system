"""Shared pytest fixtures.

How the pieces fit together:

    engine (once per test run)   -> wipes the *_test database, runs `alembic upgrade head`
        |
    session (once per test)      -> opens a transaction, binds a Session to it, and rolls
        |                           everything back afterwards, even if the code under
        |                           test called session.commit()
    client (once per test)       -> FastAPI TestClient whose `get_session` dependency is
                                    replaced by that same session

So every test starts with empty tables, and tests can't affect each other.
"""

import itertools
from collections.abc import Callable, Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from ledger_service.config import settings
from ledger_service.db import get_session
from ledger_service.main import app
from ledger_service.models import Account, Customer

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = make_url(settings.test_database_url)

    # Safety net: this fixture DROPs the whole schema. Never let it near the dev database.
    if not (url.database or "").endswith("_test"):
        pytest.exit(f"Refusing to run tests against non-test database {url.database!r}")

    test_engine = create_engine(url)

    # Start from a blank slate, then build the schema with the real migrations.
    # That means every test run also proves `alembic upgrade head` works on an empty DB.
    with test_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    # Config() with no .ini file: no logging reconfiguration to interfere with pytest.
    cfg = Config()
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    cfg.attributes["url"] = url.render_as_string(hide_password=False)  # read by migrations/env.py
    command.upgrade(cfg, "head")

    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A Session whose work is always rolled back at the end of the test."""
    with engine.connect() as connection:
        outer = connection.begin()
        # "create_savepoint": session.commit() only releases a SAVEPOINT, it does not
        # commit `outer`. That's what lets code under test call commit() freely.
        with Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as test_session:
            yield test_session
        outer.rollback()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """TestClient wired to the per-test session instead of the real database."""
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- Test-data factories -------------------------------------------------------------
# Small builders beat giant fixtures: each test says only what matters to it.


@pytest.fixture
def make_customer(session: Session) -> Callable[..., Customer]:
    counter = itertools.count(1)

    def _make(**overrides) -> Customer:
        n = next(counter)
        customer = Customer(
            name=overrides.get("name", f"Customer {n}"),
            email=overrides.get("email", f"customer{n}@example.com"),
        )
        session.add(customer)
        session.flush()  # sends the INSERT so customer.id is populated
        return customer

    return _make


@pytest.fixture
def make_account(
    session: Session, make_customer: Callable[..., Customer]
) -> Callable[..., Account]:
    def _make(
        customer: Customer | None = None,
        balance: str | Decimal = "0.00",
        currency: str = "USD",
    ) -> Account:
        account = Account(
            customer_id=(customer or make_customer()).id,
            balance=Decimal(balance),
            currency=currency,
        )
        session.add(account)
        session.flush()
        return account

    return _make
