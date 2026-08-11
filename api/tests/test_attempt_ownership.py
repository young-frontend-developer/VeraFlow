# -*- coding: utf-8 -*-
"""Learner data belongs to the session, not to whoever names an id.

WHAT THIS FILE EXISTS TO PREVENT. Before Phase 3A every one of these passed:

  * GET /api/attempts?device_id=<someone else's>  returned their whole history
  * POST /api/attempts/{id}/wrong                 had no ownership check AT ALL,
    and attempt_id is a sequential integer, so 1..n walked every learner
  * POST /api/consent with consented=false        hard-deleted the account named
    in a form field, attempts and stored voice recordings included, 200 OK

Each test below is one of those, asserted in the negative. Two users are set up
in every case - a victim with real data and an attacker with a valid session of
their own - because the interesting failure is not "no auth", it is "auth as
the wrong person", which is what device_id let anybody do.

NOTHING HERE TOUCHES THE LIVE DATABASE. get_session is overridden onto a
throwaway file per test; see the `engine` fixture.
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from tilawah import auth
from tilawah.api import routes
from tilawah.api.main import app
from tilawah.db import get_session
from tilawah.db.models import Attempt, AuthSession, Device, User


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'own.db'}",
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
def db(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine):
    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, uid, *, consented=True, n_attempts=0):
    db.add(User(id=uid, lang="uz", consented=consented, consent_seen=True))
    db.commit()                       # before the attempts: FKs are enforced
    ids = []
    for i in range(n_attempts):
        row = Attempt(user_id=uid, sura=112, aya=(i % 4) + 1, status="ok",
                      clean=True, analysable=True)
        db.add(row)
        db.commit()
        db.refresh(row)
        ids.append(row.id)
    return ids


def token_for(db, uid):
    return auth.create_session(db, uid)[0]


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def two_users(db):
    """Victim with history, attacker with a valid session of their own."""
    victim_attempts = make_user(db, "victim", n_attempts=3)
    make_user(db, "attacker", n_attempts=1)
    return {
        "victim": {"id": "victim", "attempts": victim_attempts,
                   "token": token_for(db, "victim")},
        "attacker": {"id": "attacker", "token": token_for(db, "attacker")},
    }


# ── 1. a learner can reach their own data ─────────────────────────────────

def test_user_can_read_their_own_attempts(client, two_users):
    v = two_users["victim"]
    r = client.get("/api/attempts", headers=hdr(v["token"]))
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_response_shape_is_unchanged(client, two_users):
    """REQUIREMENT: preserve existing response shapes."""
    r = client.get("/api/attempts", headers=hdr(two_users["victim"]["token"]))
    row = r.json()[0]
    for field in ("id", "sura", "aya", "status", "clean", "suppressed",
                  "analysable", "errors", "snr_db", "duration_s", "created_at",
                  "letters"):
        assert field in row, f"{field} disappeared from the history payload"


def test_own_device_id_is_still_accepted(client, two_users):
    """Legacy clients send it; for pre-account users user.id IS the device id."""
    v = two_users["victim"]
    r = client.get(f"/api/attempts?device_id={v['id']}", headers=hdr(v["token"]))
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_a_device_row_also_grants_ownership(client, db, two_users):
    """The second-install path: one account, several devices."""
    db.add(Device(id="phone-2", user_id="victim"))
    db.commit()
    r = client.get("/api/attempts?device_id=phone-2",
                   headers=hdr(two_users["victim"]["token"]))
    assert r.status_code == 200
    assert len(r.json()) == 3


# ── 2. device_id cannot reach another user's history ──────────────────────

def test_attacker_cannot_read_victim_history_via_device_id(client, two_users):
    """THE HEADLINE VULNERABILITY. This returned 3 rows before Phase 3A."""
    r = client.get("/api/attempts?device_id=victim",
                   headers=hdr(two_users["attacker"]["token"]))
    assert r.status_code == 403
    assert "victim" not in r.text or "does not belong" in r.text


def test_device_id_cannot_widen_scope_even_when_omitted(client, two_users):
    """Without any device_id the attacker still sees only their own row."""
    r = client.get("/api/attempts", headers=hdr(two_users["attacker"]["token"]))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_history_requires_a_session_at_all(client, two_users):
    assert client.get("/api/attempts?device_id=victim").status_code == 401
    assert client.get("/api/attempts").status_code == 401


def test_an_unknown_device_id_is_refused_not_silently_ignored(client, two_users):
    r = client.get("/api/attempts?device_id=never-existed",
                   headers=hdr(two_users["attacker"]["token"]))
    assert r.status_code == 403


# ── 3 & 4. attempt_id cannot cross accounts ───────────────────────────────

def test_attacker_cannot_flag_victims_attempt(client, two_users):
    """No ownership check existed here at all. attempt_id is sequential."""
    target = two_users["victim"]["attempts"][0]
    r = client.post(f"/api/attempts/{target}/wrong",
                    json={"note": "poisoning the review queue"},
                    headers=hdr(two_users["attacker"]["token"]))
    assert r.status_code == 404, "must not confirm the attempt even exists"


def test_a_refused_flag_leaves_the_row_untouched(client, db, two_users):
    target = two_users["victim"]["attempts"][0]
    client.post(f"/api/attempts/{target}/wrong", json={"note": "x"},
                headers=hdr(two_users["attacker"]["token"]))
    db.expire_all()
    row = db.get(Attempt, target)
    assert row.wrong_flag is False and row.wrong_note is None


def test_owner_can_still_flag_their_own_attempt(client, db, two_users):
    """REQUIREMENT 7: legitimate behaviour intact."""
    v = two_users["victim"]
    target = v["attempts"][0]
    r = client.post(f"/api/attempts/{target}/wrong",
                    json={"note": "the sad was fine"}, headers=hdr(v["token"]))
    assert r.status_code == 200 and r.json() == {"ok": True}
    db.expire_all()
    row = db.get(Attempt, target)
    assert row.wrong_flag is True and row.wrong_note == "the sad was fine"


def test_enumeration_returns_the_same_404_as_a_missing_row(client, two_users):
    """A real-but-foreign id and a nonexistent id must be indistinguishable."""
    foreign = two_users["victim"]["attempts"][0]
    a = client.post(f"/api/attempts/{foreign}/wrong", json={"note": "x"},
                    headers=hdr(two_users["attacker"]["token"]))
    b = client.post("/api/attempts/999999/wrong", json={"note": "x"},
                    headers=hdr(two_users["attacker"]["token"]))
    assert a.status_code == b.status_code == 404
    assert a.json() == b.json()


def test_flagging_requires_a_session(client, two_users):
    target = two_users["victim"]["attempts"][0]
    assert client.post(f"/api/attempts/{target}/wrong",
                       json={"note": "x"}).status_code == 401


# ── consent: the destructive route ────────────────────────────────────────

def test_attacker_cannot_delete_victims_account(client, db, two_users):
    """consented=false hard-deletes attempts AND stored voice recordings.
    Before Phase 3A a form field chose whose."""
    r = client.post("/api/consent",
                    data={"consented": "false", "audio_consented": "false",
                          "device_id": "victim"},
                    headers=hdr(two_users["attacker"]["token"]))
    assert r.status_code == 403

    db.expire_all()
    assert db.get(User, "victim") is not None
    assert len(db.exec(select(Attempt).where(Attempt.user_id == "victim")).all()) == 3


def test_consent_requires_a_session(client, db):
    assert client.post("/api/consent",
                       data={"consented": "false", "device_id": "victim"}
                       ).status_code == 401


def test_a_learner_can_still_revoke_their_own_consent(client, db, two_users, monkeypatch):
    """REQUIREMENT 7 and 13: the real behaviour, including the deletion, stands."""
    monkeypatch.setattr(routes, "delete_stored_audio", lambda _uid: 0)
    v = two_users["victim"]

    r = client.post("/api/consent",
                    data={"consented": "false", "audio_consented": "false"},
                    headers=hdr(v["token"]))
    assert r.status_code == 200
    assert r.json() == {"ok": True, "consented": False, "audio_consented": False}

    db.expire_all()
    assert db.get(User, "victim") is None
    assert db.exec(select(Attempt).where(Attempt.user_id == "victim")).all() == []
    # The account is gone, so the token that authorised it must be gone too.
    assert client.get("/api/auth/me", headers=hdr(v["token"])).status_code == 401


def test_granting_consent_still_works_and_is_scoped_to_the_session(client, db):
    make_user(db, "quiet", consented=False)
    tok = token_for(db, "quiet")
    r = client.post("/api/consent", data={"consented": "true"},
                    headers=hdr(tok))
    assert r.status_code == 200
    db.expire_all()
    u = db.get(User, "quiet")
    assert u.consented is True and u.consent_seen is True


# ── 5. dead sessions cannot reach learner data ────────────────────────────

def test_revoked_session_cannot_read_attempts(client, db, two_users):
    v = two_users["victim"]
    row = db.exec(select(AuthSession).where(
        AuthSession.token_hash == auth.hash_token(v["token"]))).first()
    auth.revoke(db, row)
    assert client.get("/api/attempts", headers=hdr(v["token"])).status_code == 401


def test_expired_session_cannot_read_attempts(client, db, two_users):
    v = two_users["victim"]
    row = db.exec(select(AuthSession).where(
        AuthSession.token_hash == auth.hash_token(v["token"]))).first()
    row.expires_at = auth.now() - timedelta(seconds=1)
    db.add(row)
    db.commit()
    assert client.get("/api/attempts", headers=hdr(v["token"])).status_code == 401


def test_revoked_session_cannot_revoke_consent(client, db, two_users):
    """The destructive route must be dead for a dead session too."""
    v = two_users["victim"]
    row = db.exec(select(AuthSession).where(
        AuthSession.token_hash == auth.hash_token(v["token"]))).first()
    auth.revoke(db, row)

    r = client.post("/api/consent", data={"consented": "false"},
                    headers=hdr(v["token"]))
    assert r.status_code == 401
    db.expire_all()
    assert db.get(User, "victim") is not None


# ── 6. anonymous sessions keep working end to end ─────────────────────────

def test_anonymous_session_reaches_its_own_data(client, db):
    """A learner with no account at all: /auth/anonymous -> read own history."""
    make_user(db, "legacy-phone", n_attempts=2)

    got = client.post("/api/auth/anonymous",
                      json={"device_id": "legacy-phone"}).json()
    assert got["claimed_existing"] is True

    r = client.get("/api/attempts", headers=hdr(got["token"]))
    assert r.status_code == 200 and len(r.json()) == 2


def test_a_brand_new_anonymous_session_sees_an_empty_history(client):
    got = client.post("/api/auth/anonymous", json={}).json()
    r = client.get("/api/attempts", headers=hdr(got["token"]))
    assert r.status_code == 200 and r.json() == []


def test_cookie_transport_works_for_learner_data_too(client, db):
    make_user(db, "cookie-user", n_attempts=1)
    client.post("/api/auth/anonymous", json={"device_id": "cookie-user"})
    # No Authorization header - the cookie set above must carry it.
    r = client.get("/api/attempts")
    assert r.status_code == 200 and len(r.json()) == 1


# ── 7. the content routes are untouched and still public ──────────────────

@pytest.mark.parametrize("path", [
    "/api/meta", "/api/suras", "/api/ayat", "/api/reciters",
    "/api/segments/112/1", "/api/hadith/today", "/health",
])
def test_content_routes_need_no_session(client, path):
    """Tajweed and catalogue content is not learner data and must stay open."""
    assert client.get(path).status_code == 200
