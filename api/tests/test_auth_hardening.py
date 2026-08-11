# -*- coding: utf-8 -*-
"""The device-claim window, and the production session-cookie guards.

WHAT IS BEING PROTECTED. Claiming trades a device id for a real session, and a
device id is not a secret - it has been travelling in query strings into access
logs, browser history and every proxy since the first release. The exchange is
worth its risk for exactly one job, migrating existing anonymous installs onto
sessions, and only because that same id is ALREADY full authority on
/api/attempts and /api/consent today.

So the property under test is not "claiming works". It is that claiming STOPS -
on the flag, on the deadline, and on a production deployment that forgot both.
A temporary mechanism guarded only by good intentions is a permanent one.
"""
import dataclasses
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import anyio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from tilawah.api import auth_routes, main
from tilawah.config import Settings, settings
from tilawah.db import get_session
from tilawah.db.models import User

API_DIR = Path(__file__).resolve().parents[1]


# ── fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'claim.db'}",
                        connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_connection, _record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def client(engine):
    def _override():
        with Session(engine) as s:
            yield s

    app_ = main.app
    app_.dependency_overrides[get_session] = _override
    yield TestClient(app_)
    app_.dependency_overrides.clear()


@pytest.fixture
def known_device(engine):
    """An existing anonymous install, the thing claiming exists to migrate."""
    with Session(engine) as s:
        s.add(User(id="legacy-install", lang="uz", consented=True,
                   consent_seen=True))
        s.commit()
    return "legacy-install"


def with_settings(monkeypatch, **overrides):
    """Point auth_routes at a patched settings object. Frozen dataclass, so
    replace it wholesale - the pattern test_show_unreviewed.py established."""
    monkeypatch.setattr(auth_routes, "settings",
                        dataclasses.replace(settings, **overrides))


def boot(monkeypatch, **overrides):
    """Run the real lifespan with patched settings.

    debug_audio is pinned off for the same reason boot() in
    test_show_unreviewed.py pins it: settings is built from the developer's
    api/.env, which sets TILAWAH_DEBUG_AUDIO=1, and that guard fires first and
    belongs to its own test.
    """
    overrides.setdefault("debug_audio", False)
    monkeypatch.setattr(main, "settings",
                        dataclasses.replace(settings, **overrides))

    async def run():
        async with main.lifespan(main.app):
            pass

    anyio.run(run)


YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


# ── requirement 3: the env var actually closes the endpoint ───────────────

def test_env_var_zero_closes_the_window_in_a_real_process():
    """TILAWAH_ALLOW_DEVICE_CLAIM=0, read the way production reads it.

    A SUBPROCESS, not monkeypatch. Settings is a frozen dataclass whose field
    defaults are evaluated once at import, so patching os.environ inside a
    running test proves nothing about what the variable does at boot. This is
    the only test here that exercises the actual operator-facing control.
    """
    script = (
        "from tilawah.config import settings\n"
        "print(settings.allow_device_claim, settings.device_claim_open)\n"
    )
    env = dict(os.environ, TILAWAH_ALLOW_DEVICE_CLAIM="0", TILAWAH_ENV="dev")
    out = subprocess.run([sys.executable, "-c", script], cwd=API_DIR, env=env,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["False", "False"]


def test_env_var_one_leaves_the_window_open_in_dev():
    """The control has two positions; a test that only proves 'off' could pass
    against a setting that is always off."""
    script = (
        "from tilawah.config import settings\n"
        "print(settings.allow_device_claim, settings.device_claim_open)\n"
    )
    env = dict(os.environ, TILAWAH_ALLOW_DEVICE_CLAIM="1", TILAWAH_ENV="dev",
               TILAWAH_DEVICE_CLAIM_UNTIL="")
    out = subprocess.run([sys.executable, "-c", script], cwd=API_DIR, env=env,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["True", "True"]


# ── requirement 4: the disabled state, over HTTP ──────────────────────────

def test_claim_disabled_returns_410(client, known_device, monkeypatch):
    with_settings(monkeypatch, allow_device_claim=False)
    r = client.post("/api/auth/anonymous", json={"device_id": known_device})
    assert r.status_code == 410
    assert "sign in" in r.json()["detail"]


def test_claim_disabled_does_not_silently_mint_a_different_account(
        client, known_device, monkeypatch, engine):
    """THE FAILURE MODE THIS GUARDS. Falling back to a fresh anonymous user
    would answer 200 while the learner's practice appeared to vanish - data
    loss that looks like success. Refusing is the kind thing."""
    with_settings(monkeypatch, allow_device_claim=False)
    client.post("/api/auth/anonymous", json={"device_id": known_device})

    with Session(engine) as s:
        assert len(s.exec(SQLModel.metadata.tables["user"].select()).all()) == 1


def test_claim_disabled_still_allows_brand_new_anonymous_sessions(
        client, monkeypatch):
    """Closing the window must not break anonymous use. Anonymous is how this
    app works; only the device-id EXCHANGE is temporary."""
    with_settings(monkeypatch, allow_device_claim=False)
    r = client.post("/api/auth/anonymous", json={})
    assert r.status_code == 200
    assert r.json()["claimed_existing"] is False


def test_claim_enabled_still_migrates_an_existing_install(
        client, known_device, monkeypatch):
    with_settings(monkeypatch, allow_device_claim=True, device_claim_until="")
    r = client.post("/api/auth/anonymous", json={"device_id": known_device})
    assert r.status_code == 200
    assert r.json()["claimed_existing"] is True
    assert r.json()["user_id"] == known_device


# ── the deadline closes the window with no deploy ─────────────────────────

def test_a_passed_deadline_closes_the_window(client, known_device, monkeypatch):
    """An unattended box must close its own window."""
    with_settings(monkeypatch, allow_device_claim=True,
                  device_claim_until=YESTERDAY)
    r = client.post("/api/auth/anonymous", json={"device_id": known_device})
    assert r.status_code == 410


def test_a_future_deadline_keeps_it_open(client, known_device, monkeypatch):
    with_settings(monkeypatch, allow_device_claim=True,
                  device_claim_until=TOMORROW)
    assert client.post("/api/auth/anonymous",
                       json={"device_id": known_device}).status_code == 200


def test_today_is_the_last_day_inclusive(client, known_device, monkeypatch):
    with_settings(monkeypatch, allow_device_claim=True,
                  device_claim_until=date.today().isoformat())
    assert client.post("/api/auth/anonymous",
                       json={"device_id": known_device}).status_code == 200


def test_a_malformed_deadline_fails_closed(client, known_device, monkeypatch):
    """A typo must not read as 'no deadline'."""
    with_settings(monkeypatch, allow_device_claim=True,
                  device_claim_until="30-09-2026")
    assert client.post("/api/auth/anonymous",
                       json={"device_id": known_device}).status_code == 410


def test_production_without_a_deadline_is_closed_even_if_boot_were_skipped():
    """Belt to the boot guard's braces: the property holds in settings itself."""
    s = dataclasses.replace(settings, env="production",
                            allow_device_claim=True, device_claim_until="")
    assert s.device_claim_open is False


# ── boot guards: the window cannot reach production unattended ────────────

def test_production_refuses_to_boot_with_claiming_on_and_no_deadline(monkeypatch):
    with pytest.raises(RuntimeError, match="TILAWAH_DEVICE_CLAIM_UNTIL"):
        boot(monkeypatch, env="production", allow_device_claim=True,
             device_claim_until="", session_cookie_secure=True)


def test_production_boots_with_claiming_off(monkeypatch):
    boot(monkeypatch, env="production", allow_device_claim=False,
         device_claim_until="", session_cookie_secure=True)


def test_production_boots_with_a_dated_migration_window(monkeypatch):
    """A real migration must still be possible in production - with an end."""
    boot(monkeypatch, env="production", allow_device_claim=True,
         device_claim_until=TOMORROW, session_cookie_secure=True)


def test_boot_refuses_a_malformed_deadline(monkeypatch):
    with pytest.raises(RuntimeError, match="not an ISO date"):
        boot(monkeypatch, env="production", allow_device_claim=True,
             device_claim_until="soon", session_cookie_secure=True)


# ── boot guards: session cookie ───────────────────────────────────────────

def test_production_refuses_an_insecure_session_cookie(monkeypatch):
    """REQUIREMENT 5. Secure is not optional once real people are on https."""
    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE"):
        boot(monkeypatch, env="production", session_cookie_secure=False,
             allow_device_claim=False)


def test_boot_refuses_an_unrecognised_samesite(monkeypatch):
    """A value the browser does not understand is dropped, which silently
    removes the only CSRF protection in place."""
    with pytest.raises(RuntimeError, match="samesite|SAMESITE"):
        boot(monkeypatch, env="dev", session_cookie_samesite="sometimes")


def test_boot_refuses_samesite_none_without_secure(monkeypatch):
    """Browsers reject the combination outright - the cookie would never be
    stored, and every login would fail for a reason nobody could see."""
    with pytest.raises(RuntimeError, match="requires"):
        boot(monkeypatch, env="dev", session_cookie_samesite="none",
             session_cookie_secure=False)


def test_production_accepts_samesite_none_when_secure(monkeypatch):
    """The split-origin deployment shape: api and client on different hosts."""
    boot(monkeypatch, env="production", session_cookie_samesite="none",
         session_cookie_secure=True, allow_device_claim=False)


def test_dev_defaults_still_boot(monkeypatch):
    """The developer's laptop must not need any of this configured."""
    boot(monkeypatch, env="dev")


# ── the shipped defaults are the safe ones ────────────────────────────────

def test_shipped_defaults_are_safe_for_a_fresh_checkout():
    """Read from a clean environment, not from the developer's api/.env."""
    script = (
        "from tilawah.config import Settings\n"
        "s = Settings()\n"
        "print(s.session_cookie_samesite, s.session_cookie_secure, s.env)\n"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("TILAWAH_")}
    env["PATH"] = os.environ.get("PATH", "")
    out = subprocess.run([sys.executable, "-c", script], cwd=API_DIR, env=env,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    samesite, secure, env_name = out.stdout.split()
    # lax, so a cross-site POST cannot carry the session cookie.
    assert samesite == "lax"
    # secure defaults off ONLY because dev is http - and production refuses to
    # boot in that state, which is what makes the default acceptable.
    assert secure == "False" and env_name == "dev"
