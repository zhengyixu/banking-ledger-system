"""Shared pytest fixtures.

How the pieces fit together:

    engine (once per test run)   -> wipes the *_test database, runs `alembic upgrade head`
        |
    connection (once per test)   -> one connection + outer transaction, rolled back at the end,
        |                           even if the code under test called session.commit()
    session (once per test)      -> the test's own Session on that connection (factories,
        |                           assertions)
    client (once per test)       -> FastAPI TestClient; every REQUEST gets a fresh Session on
                                    the same connection, exactly like production

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
from sqlalchemy import Connection, Engine, create_engine, text
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
def connection(engine: Engine) -> Iterator[Connection]:
    """One connection + one outer transaction per test, rolled back at the end."""
    with engine.connect() as conn:
        outer = conn.begin()
        yield conn
        outer.rollback()


def _new_session(connection: Connection) -> Session:
    # "create_savepoint": session.commit() only releases a SAVEPOINT, it does not commit the
    # outer transaction. Every Session built on `connection` sees the same data.
    return Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


@pytest.fixture
def session(connection: Connection) -> Iterator[Session]:
    """The test's own Session (factories, assertions)."""
    with _new_session(connection) as test_session:
        yield test_session


@pytest.fixture
def client(connection: Connection) -> Iterator[TestClient]:
    """TestClient where EVERY REQUEST gets its own fresh Session, like production."""

    def per_request_session() -> Iterator[Session]:
        with _new_session(connection) as request_session:
            yield request_session

    app.dependency_overrides[get_session] = per_request_session
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
        # commit, not just flush: factory data stands in for rows that already exist in the
        # DB. If a test then makes the service call session.rollback() (e.g. on an
        # overdraft), only work done AFTER this commit is undone, like in real life.
        session.commit()
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
        session.commit()  # factories commit; see make_customer
        return account

    return _make
