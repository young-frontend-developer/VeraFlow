# -*- coding: utf-8 -*-
"""Alembic environment.

THE URL COMES FROM THE APP, NOT FROM alembic.ini. settings.database_url
defaults to `sqlite:///./tilawah.db` - a RELATIVE path, which resolves against
the process working directory. Run alembic from a different folder and it would
happily create a second, empty database and report success against it. So the
sqlite path is resolved against api/ here, and alembic.ini carries no url at
all rather than a copy that can drift from config.py.

render_as_batch=True is not optional on SQLite. SQLite cannot ALTER a column or
add a constraint in place; batch mode makes Alembic rebuild the table instead.
Without it, every migration past "add a nullable column" fails.
"""
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# api/ on the path so `tilawah` imports whatever the app itself would import.
import sys

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlmodel import SQLModel  # noqa: E402

from tilawah.config import settings  # noqa: E402
# Every table must be imported here or autogenerate will not see it - and an
# unseen table is not "skipped", it is DETECTED AS REMOVED and the migration
# drops it.
from tilawah.db.models import (Attempt, AuthIdentity,  # noqa: E402,F401
                               AuthSession, Device, OAuthNonce, User)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _url() -> str:
    """The app's url, with any relative sqlite path anchored to api/."""
    url = settings.database_url
    prefix = "sqlite:///"
    if url.startswith(prefix):
        raw = url[len(prefix):]
        if raw.startswith("./"):
            raw = raw[2:]
        path = Path(raw)
        if not path.is_absolute():
            path = API_DIR / path
        return f"{prefix}{path}"
    return url


config.set_main_option("sqlalchemy.url", _url().replace("%", "%%"))

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
