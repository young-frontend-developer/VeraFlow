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
    _add_missing_columns()


def _add_missing_columns() -> None:
    """create_all() creates tables but never alters them, so columns added after
    a table exists are silently missing until a query blows up. SQLite only, and
    only ever additive - if this ever needs to drop or retype a column, that is
    the moment to bring in Alembic rather than extend this.
    """
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text

    wanted = {
        "user": {
            "audio_consented": "BOOLEAN NOT NULL DEFAULT 0",
            "consent_seen": "BOOLEAN NOT NULL DEFAULT 0",
        },
        "attempt": {
            # num_words defaults to 0 meaning "the whole ayah", which is what
            # every pre-segmentation row was.
            "start_word": "INTEGER NOT NULL DEFAULT 0",
            "num_words": "INTEGER NOT NULL DEFAULT 0",
            "include_bismillah": "BOOLEAN NOT NULL DEFAULT 0",
            # 1, not 0: every row written before this column existed came from
            # a run where the engine did produce a transcription.
            "analysable": "BOOLEAN NOT NULL DEFAULT 1",
        },
    }
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in wanted.items():
            if table not in insp.get_table_names():
                continue
            have = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols.items():
                if name not in have:
                    conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {name} {ddl}'))


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def delete_user(session: Session, user_id: str) -> int:
    """Hard delete. Consent is revocable and this must really remove the data -
    including any stored audio, which lives on disk rather than in the table.
    A promise to delete that leaves the voice recordings behind is not deletion.
    """
    delete_stored_audio(user_id)
    rows = session.query(Attempt).filter(Attempt.user_id == user_id).delete()
    session.query(User).filter(User.id == user_id).delete()
    session.commit()
    return rows


def delete_stored_audio(user_id: str) -> int:
    """Remove every audio artefact recorded for this device. Returns file count."""
    from ..engine.debug_capture import purge_user

    return purge_user(user_id)
