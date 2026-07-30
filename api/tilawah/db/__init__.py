# -*- coding: utf-8 -*-
"""Database session handling.

SQLModel with no migration tool for MVP - create_all() is enough while the
schema is yours alone. Add Alembic the first time you need to change a column
without dropping data.
"""
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from ..config import settings
from .models import Attempt, User  # noqa: F401 - registers tables

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def delete_user(session: Session, user_id: str) -> int:
    """Hard delete. Consent is revocable and this must really remove the rows."""
    rows = session.query(Attempt).filter(Attempt.user_id == user_id).delete()
    session.query(User).filter(User.id == user_id).delete()
    session.commit()
    return rows
