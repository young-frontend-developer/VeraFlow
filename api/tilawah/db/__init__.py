# -*- coding: utf-8 -*-
"""Database session handling.

ALEMBIC OWNS THE SCHEMA. NOTHING HERE CREATES OR ALTERS IT.

This module used to run `SQLModel.metadata.create_all()` on every boot, plus an
additive `_add_missing_columns()` patcher for the columns create_all() could not
add. Both are gone, and the reason is specific rather than tidy-minded: the
moment the auth tables were declared in models.py, a create_all() at startup
would have raced Alembic and won. The server would have created auth_identity,
device and auth_session itself - correctly shaped, but with no migration
recorded - and `alembic current` would still have read the old revision. Every
later autogenerate would then diff against a database Alembic did not know it
had, and the drift would be invisible to the very check built to catch it.

So startup now VERIFIES and never writes. If the database is behind, the app
refuses to boot and says which command to run. A server that quietly repairs
its own schema is a server that can quietly repair it wrongly.

    py -3.13 -m alembic upgrade head      (run from api/)

FOREIGN KEYS ARE ENFORCED HERE, per connection. sqlite defaults the pragma to
OFF, which is why attempt.user_id has been a decorative constraint all along -
deleting a user would have orphaned their history in silence. The new tables
declare ON DELETE CASCADE and that clause does nothing at all without this.
"""
from collections.abc import Iterator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine  # noqa: F401 - SQLModel re-exported

from ..config import settings
from .models import (Attempt, AuthIdentity, AuthSession,  # noqa: F401
                     Device, EmailToken, OAuthNonce,       # - registers tables
                     User)

_is_sqlite = settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)


if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:
        """PRAGMA foreign_keys is per-connection and defaults to OFF.

        Bound to this engine rather than to the Engine class so that a test or
        a tool holding its own connection is not silently changed underneath it.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class SchemaOutOfDate(RuntimeError):
    """The database is not at the migration head the code expects."""


def init_db() -> None:
    """Verify the schema. NEVER create it - see the module docstring.

    Kept as init_db() because main.py's lifespan calls it and the name still
    describes the job: make sure the database is fit to serve before serving.
    """
    check_schema()


def check_schema() -> None:
    """Refuse to run against a database Alembic has not brought up to head.

    Raises SchemaOutOfDate with the exact remedy. Deliberately loud: the
    failure this replaces was silent, and a silent schema mismatch surfaces
    later as a query blowing up in front of a learner.
    """
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import inspect, text

    api_dir = Path(__file__).resolve().parents[2]
    cfg = Config(str(api_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(api_dir / "migrations"))
    head = ScriptDirectory.from_config(cfg).get_current_head()

    with engine.connect() as conn:
        if "alembic_version" not in inspect(conn).get_table_names():
            raise SchemaOutOfDate(
                "This database has no alembic_version table, so Alembic has "
                "never run against it. If it is a fresh database:\n"
                "    py -3.13 -m alembic upgrade head\n"
                "If it predates Alembic and already has the tables, stamp it "
                "instead - upgrading would try to create tables that exist:\n"
                "    py -3.13 -m alembic stamp head\n"
                "(run from api/)")
        got = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    if got != head:
        raise SchemaOutOfDate(
            f"Database is at revision {got!r}, code expects {head!r}. "
            f"Run:  py -3.13 -m alembic upgrade head   (from api/)")


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def delete_user(session: Session, user_id: str) -> int:
    """Hard delete. Consent is revocable and this must really remove the data -
    including any stored audio, which lives on disk rather than in the table.
    A promise to delete that leaves the voice recordings behind is not deletion.

    THE ORDER IS NOW LOAD-BEARING. attempt.user_id is ON DELETE NO ACTION, and
    foreign keys are enforced from this release onward, so deleting the user
    while their attempts still reference it raises FOREIGN KEY constraint
    failed. Attempts first, user second - as it already did, but by luck rather
    than by rule until now. Do not reorder these two statements.

    auth_identity, device, auth_session and email_token need no lines here:
    they declare ON DELETE CASCADE and sqlite removes them with the user. That
    is deliberate - a leftover identity row would hold UNIQUE(provider,
    subject) against a person who no longer exists and lock that Google account
    out of signing up again, and a leftover email_token row would be a live
    password-reset credential for an account that no longer exists.
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
