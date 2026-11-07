from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ledger_service.config import settings


class Base(DeclarativeBase):
    """All ORM models inherit from this; Alembic reads Base.metadata."""


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    with SessionLocal() as session:
        yield session


# Use as a parameter annotation: `def endpoint(session: SessionDep): ...`
SessionDep = Annotated[Session, Depends(get_session)]
