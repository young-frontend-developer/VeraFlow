# -*- coding: utf-8 -*-
"""Session tokens: what authenticates, what must not, and what is stored.

EVERY TEST HERE USES ITS OWN THROWAWAY DATABASE. The rest of this suite talks
to the real api/tilawah.db - which is why rows like `contract-test` are sitting
in it - and auth tests create and delete users, so borrowing that habit would
mean the suite mutating live learner data. The fixtures below build a fresh
sqlite file per test, with foreign keys ON, because ON DELETE CASCADE is one of
the properties under test and it does nothing without the pragma.

The security-relevant assertions are the negative ones. A test that proves a
valid token works proves very little; the ones that matter are expired,
revoked, unknown, and "the user is gone".
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlmodel import Session, SQLModel, create_engine, select

from tilawah import auth
from tilawah.api.main import app
from tilawah.db import get_session
from tilawah.db.models import Attempt, AuthIdentity, AuthSession, Device, User


@pytest.fixture
def engine(tmp_path):
    """A private database with foreign keys enforced, as production has."""
    eng = create_engine(f"sqlite:///{tmp_path / 'auth.db'}",
                        connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_connection, _record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    # create_all is banned from application startup (it would race Alembic);
    # building a throwaway schema in a test is exactly what it is still for.
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def user(db):
    u = User(id="user-under-test", lang="uz", consented=True, consent_seen=True)
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def client(engine):
    """The real app, with the database pointed at the throwaway file."""
    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── the token itself ──────────────────────────────────────────────────────

def test_only_the_hash_is_stored_never_the_token(db, user):
    """THE CENTRAL STORAGE PROPERTY. A dumped table must be worthless."""
    raw, row = auth.create_session(db, user.id)

    assert row.token_hash != raw
    assert row.token_hash == auth.hash_token(raw)
    assert len(row.token_hash) == 64          # sha256 hex

    # Not "the column does not equal the token" - the token must not appear in
    # ANY column of ANY row, in case a later field starts carrying it.
    dumped = db.exec(text("SELECT * FROM auth_session")).all()
    flat = " ".join(str(v) for row_ in dumped for v in row_)
    assert raw not in flat, "the raw token reached the database"


def test_tokens_are_unique_and_unguessable(db, user):
    tokens = {auth.create_session(db, user.id)[0] for _ in range(25)}
    assert len(tokens) == 25
    # token_urlsafe(32) is 43 chars of base64. Anything materially shorter
    # would mean TOKEN_BYTES was lowered without anyone noticing.
    assert all(len(t) >= 40 for t in tokens)


def test_token_hash_column_is_unique(db, user):
    """Two sessions cannot share a hash - the index is what makes lookup safe."""
    raw, _ = auth.create_session(db, user.id)
    clash = AuthSession(token_hash=auth.hash_token(raw), user_id=user.id,
                        expires_at=auth.now() + timedelta(days=1))
    db.add(clash)
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


# ── what resolves, and what must not ──────────────────────────────────────

def test_valid_session_resolves_to_its_user(db, user):
    raw, row = auth.create_session(db, user.id)
    got = auth.resolve(db, raw)
    assert got is not None
    session_row, resolved_user = got
    assert session_row.id == row.id
    assert resolved_user.id == user.id


def test_unknown_token_does_not_resolve(db, user):
    auth.create_session(db, user.id)
    assert auth.resolve(db, "not-a-real-token") is None
    assert auth.resolve(db, "") is None
    assert auth.resolve(db, auth.new_token()) is None


def test_expired_session_does_not_resolve(db, user):
    raw, row = auth.create_session(db, user.id, ttl_days=-1)
    assert auth.is_live(row) is False
    assert auth.resolve(db, raw) is None


def test_session_expiring_exactly_now_does_not_resolve(db, user):
    """The boundary is strict: expires_at must be in the FUTURE, not >=."""
    raw, row = auth.create_session(db, user.id)
    row.expires_at = auth.now()
    db.add(row)
    db.commit()
    assert auth.resolve(db, raw) is None


def test_revoked_session_does_not_resolve(db, user):
    raw, row = auth.create_session(db, user.id)
    assert auth.resolve(db, raw) is not None
    auth.revoke(db, row)
    assert auth.resolve(db, raw) is None


def test_revoke_is_idempotent_and_keeps_the_first_timestamp(db, user):
    _raw, row = auth.create_session(db, user.id)
    auth.revoke(db, row)
    first = row.revoked_at
    auth.revoke(db, row)
    assert row.revoked_at == first


def test_session_for_a_nonexistent_user_does_not_resolve(db, engine, user):
    """A row pointing at a ghost must not authenticate.

    Reachable only by writing with the pragma off - which is exactly what every
    tool in this repo did before Phase 1, so the defensive check earns its keep.
    """
    raw, row = auth.create_session(db, user.id)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("DELETE FROM user WHERE id = :i"), {"i": user.id})
        conn.commit()
    db.expire_all()
    assert auth.resolve(db, raw) is None


# ── deletion and revocation ───────────────────────────────────────────────

def test_deleting_a_user_cascades_their_sessions_away(db, user):
    """REQUIREMENT: sessions must not outlive the person they belong to."""
    raw, _ = auth.create_session(db, user.id)
    auth.create_session(db, user.id)
    assert len(db.exec(select(AuthSession)).all()) == 2

    db.delete(db.get(User, user.id))
    db.commit()

    assert db.exec(select(AuthSession)).all() == []
    assert auth.resolve(db, raw) is None


def test_delete_user_helper_removes_sessions_identities_and_devices(db, user, monkeypatch):
    """db.delete_user() is what consent revocation calls. Nothing may survive it."""
    from tilawah import db as dbmod

    monkeypatch.setattr(dbmod, "delete_stored_audio", lambda _uid: 0)

    raw, _ = auth.create_session(db, user.id)
    db.add(Device(id="dev-1", user_id=user.id))
    db.add(AuthIdentity(user_id=user.id, provider="google", subject="sub-xyz"))
    db.add(Attempt(user_id=user.id, sura=112, aya=1, status="ok"))
    db.commit()

    dbmod.delete_user(db, user.id)

    assert db.get(User, user.id) is None
    assert db.exec(select(AuthSession)).all() == []
    assert db.exec(select(Device)).all() == []
    assert db.exec(select(AuthIdentity)).all() == []
    assert db.exec(select(Attempt)).all() == []
    assert auth.resolve(db, raw) is None


def test_revoke_all_kills_every_live_session_for_one_user(db, user):
    other = User(id="somebody-else")
    db.add(other)
    db.commit()

    mine = [auth.create_session(db, user.id)[0] for _ in range(3)]
    theirs, _ = auth.create_session(db, other.id)

    assert auth.revoke_all_for_user(db, user.id) == 3
    assert all(auth.resolve(db, t) is None for t in mine)
    assert auth.resolve(db, theirs) is not None, "revoked the wrong user's session"


def test_rotate_issues_a_new_token_and_kills_the_old(db, user):
    old_raw, old_row = auth.create_session(db, user.id)
    new_raw, new_row = auth.rotate(db, old_row)

    assert new_raw != old_raw
    assert new_row.id != old_row.id
    assert auth.resolve(db, old_raw) is None, "the old token still works"
    assert auth.resolve(db, new_raw) is not None


def test_purge_expired_removes_only_dead_rows(db, user):
    live_raw, _ = auth.create_session(db, user.id)
    auth.create_session(db, user.id, ttl_days=-1)
    auth.create_session(db, user.id, ttl_days=-5)

    assert auth.purge_expired(db) == 2
    assert len(db.exec(select(AuthSession)).all()) == 1
    assert auth.resolve(db, live_raw) is not None


# ── nothing secret reaches the logs ───────────────────────────────────────

def test_the_raw_token_is_never_logged(db, user, caplog):
    """REQUIREMENT 11. A prefix of a secret is still part of a secret."""
    with caplog.at_level("DEBUG"):
        raw, row = auth.create_session(db, user.id)
        auth.resolve(db, raw)
        auth.revoke(db, row)
        auth.revoke_all_for_user(db, user.id)

    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert raw not in logged
    for size in (8, 12, 16):
        assert raw[:size] not in logged, f"a {size}-char prefix of the token was logged"


# ── the HTTP surface ──────────────────────────────────────────────────────

def test_anonymous_creates_a_user_and_returns_a_working_token(client, engine):
    r = client.post("/api/auth/anonymous", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token"] and body["token_type"] == "bearer"
    assert body["claimed_existing"] is False

    me = client.get("/api/auth/me",
                    headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200
    assert me.json()["user_id"] == body["user_id"]
    assert me.json()["is_anonymous"] is True
    assert me.json()["providers"] == []


def test_anonymous_with_a_known_device_id_claims_that_user(client, db):
    existing = User(id="an-old-install", lang="ru", consented=True,
                    consent_seen=True)
    db.add(existing)
    # Committed BEFORE the attempt, deliberately. Foreign keys are enforced
    # now, and SQLAlchemy has no relationship() here to tell it the user must
    # be inserted first - flushing both together can emit the child insert
    # first and fail. Application code already commits the user separately
    # (routes._user), which is why this only bites in tests.
    db.commit()
    db.add(Attempt(user_id=existing.id, sura=112, aya=1, status="ok"))
    db.commit()

    r = client.post("/api/auth/anonymous", json={"device_id": "an-old-install"})
    assert r.status_code == 200
    assert r.json()["user_id"] == "an-old-install"
    assert r.json()["claimed_existing"] is True

    # The point of claiming: the history came with them, and consent stands.
    me = client.get("/api/auth/me",
                    headers={"Authorization": f"Bearer {r.json()['token']}"}).json()
    assert me["consented"] is True and me["lang"] == "ru"
    assert db.exec(select(Attempt)).all(), "claiming must not touch attempts"


def test_claim_can_be_switched_off(client, db, monkeypatch):
    import dataclasses

    from tilawah.api import auth_routes
    from tilawah.config import settings as s

    db.add(User(id="an-old-install"))
    db.commit()
    # Settings is a frozen dataclass; replace it wholesale on the module under
    # test rather than assigning to a field. Same pattern as
    # test_show_unreviewed.py.
    monkeypatch.setattr(auth_routes, "settings",
                        dataclasses.replace(s, allow_device_claim=False))

    r = client.post("/api/auth/anonymous", json={"device_id": "an-old-install"})
    assert r.status_code == 410, "closing the window must fail loudly"


def test_me_requires_a_session(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me",
                      headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/api/auth/me",
                      headers={"Authorization": "Basic nope"}).status_code == 401


def test_the_cookie_authenticates_too_and_is_httponly(client):
    r = client.post("/api/auth/anonymous", json={})
    raw = r.json()["token"]

    set_cookie = r.headers.get("set-cookie", "")
    assert "httponly" in set_cookie.lower(), "the session cookie is script-readable"
    assert client.cookies.get("tilawah_session") == raw

    # No Authorization header - the cookie alone must carry it.
    assert client.get("/api/auth/me").status_code == 200


def test_the_header_wins_when_both_are_present(client, db):
    first = client.post("/api/auth/anonymous", json={}).json()   # sets the cookie
    second = client.post("/api/auth/anonymous", json={"device_id": "other"}).json()

    me = client.get("/api/auth/me",
                    headers={"Authorization": f"Bearer {second['token']}"}).json()
    assert me["user_id"] == second["user_id"] != first["user_id"]


def test_refresh_rotates_and_the_old_token_dies(client):
    old = client.post("/api/auth/anonymous", json={}).json()
    hdr = {"Authorization": f"Bearer {old['token']}"}

    new = client.post("/api/auth/refresh", headers=hdr)
    assert new.status_code == 200
    fresh = new.json()
    assert fresh["token"] != old["token"]
    assert fresh["user_id"] == old["user_id"]

    assert client.get("/api/auth/me", headers=hdr).status_code == 401
    assert client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {fresh['token']}"}).status_code == 200


def test_refresh_requires_a_live_session(client):
    assert client.post("/api/auth/refresh").status_code == 401


def test_logout_revokes_only_this_session(client, db):
    a = client.post("/api/auth/anonymous", json={"device_id": "shared-user"}).json()
    b = client.post("/api/auth/anonymous", json={"device_id": "shared-user"}).json()
    assert a["user_id"] == b["user_id"]

    out = client.post("/api/auth/logout",
                      headers={"Authorization": f"Bearer {a['token']}"})
    assert out.status_code == 200

    assert client.get("/api/auth/me",
                      headers={"Authorization": f"Bearer {a['token']}"}).status_code == 401
    assert client.get("/api/auth/me",
                      headers={"Authorization": f"Bearer {b['token']}"}).status_code == 200


def test_expired_session_is_rejected_over_http(client, db):
    r = client.post("/api/auth/anonymous", json={}).json()
    row = db.exec(select(AuthSession).where(
        AuthSession.token_hash == auth.hash_token(r["token"]))).first()
    row.expires_at = auth.now() - timedelta(seconds=1)
    db.add(row)
    db.commit()

    client.cookies.clear()
    assert client.get("/api/auth/me",
                      headers={"Authorization": f"Bearer {r['token']}"}).status_code == 401


def test_auth_endpoints_do_not_disturb_consent(client, db):
    """REQUIREMENT 13. Sessions must not touch the consent columns."""
    db.add(User(id="consenting", consented=True, audio_consented=False,
                consent_seen=True))
    db.commit()

    r = client.post("/api/auth/anonymous", json={"device_id": "consenting"}).json()
    hdr = {"Authorization": f"Bearer {r['token']}"}
    client.post("/api/auth/refresh", headers=hdr)

    db.expire_all()
    after = db.get(User, "consenting")
    assert (after.consented, after.audio_consented, after.consent_seen) == (True, False, True)
