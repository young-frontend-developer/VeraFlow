# -*- coding: utf-8 -*-
"""The web client's half of the session contract, and the flow it performs.

TWO KINDS OF TEST IN ONE FILE, on purpose.

  READ FROM api.ts   - the same trick test_client_contract.py plays on
                       Feedback.tsx. The server can be perfectly locked down
                       and the client can still be leaking a device id into a
                       query string; only the client's source says whether it
                       does. These assertions fail if someone reintroduces
                       device_id as a credential.

  DRIVEN THROUGH THE REAL API - the exact request sequence the browser makes,
                       in order, against the real routes: bootstrap, read,
                       record, flag, consent, refresh, logout, and the 401
                       recovery in between.

NOTHING HERE TOUCHES api/tilawah.db. get_session is overridden onto a
throwaway file per test.
"""
import re
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from tilawah import auth
from tilawah.api import routes
from tilawah.api.main import app
from tilawah.db import get_session
from tilawah.db.models import Attempt, AuthSession, User

WEB = Path(__file__).resolve().parents[2] / "web" / "src"
API_TS = WEB / "lib" / "api.ts"


# ══ part one: what the client's source is allowed to send ═════════════════

@pytest.fixture(scope="module")
def src() -> str:
    assert API_TS.is_file(), f"cannot find the client api layer at {API_TS}"
    return API_TS.read_text(encoding="utf-8")


def test_no_device_id_in_any_query_string(src):
    """THE BIGGEST LEAK THIS CLOSES. A credential in a URL is written into
    access logs, browser history, referrer headers and every proxy."""
    assert "device_id=" not in src


def test_no_device_id_in_any_form_body(src):
    assert 'fd.append("device_id"' not in src
    assert "fd.append('device_id'" not in src


def test_device_id_is_sent_exactly_once_and_only_to_bootstrap(src):
    """It may claim an account. It may not authenticate a request."""
    sends = re.findall(r"device_id:\s*deviceId\(\)", src)
    assert len(sends) == 1, f"device_id is sent {len(sends)} times, expected 1"

    # ...and that one send must be inside the bootstrap call.
    bootstrap = src[src.index("async function bootstrapSession"):]
    bootstrap = bootstrap[: bootstrap.index("\n}\n")]
    assert "/api/auth/anonymous" in bootstrap
    assert "device_id: deviceId()" in bootstrap


@pytest.mark.parametrize("path", ["/api/attempts", "/api/consent"])
def test_learner_data_never_uses_a_bare_fetch(src, path):
    """Every learner-data call must go through authedFetch, which attaches the
    session and handles the 401. A bare fetch would simply 401 forever."""
    assert f"fetch(`${{BASE}}{path}" not in src, (
        f"{path} is being called with an unauthenticated fetch")
    assert f"authedFetch(`{path}" in src


def test_the_four_learner_data_calls_are_authenticated(src):
    for fn in ("history", "submitAttempt", "flagWrong", "setConsent"):
        start = src.index(f"function {fn}") if f"function {fn}" in src \
            else src.index(f"const {fn}")
        window = src[start:start + 1400]
        assert "authedFetch" in window, f"{fn} does not use authedFetch"


def test_public_content_calls_are_still_unauthenticated(src):
    """Auth must not creep onto Tajweed content - it is not learner data and
    requiring a session for it would be a regression in reach, not security."""
    for path in ("/api/suras", "/api/ayat", "/api/meta", "/api/reciters",
                 "/api/hadith/today"):
        assert f"fetch(`${{BASE}}{path}" in src, f"{path} lost its plain fetch"


def test_the_session_layer_exists(src):
    for symbol in ("ensureSession", "refreshSession", "logout", "clearSession",
                   "hasSession", "authedFetch", "SESSION_KEY"):
        assert symbol in src, f"{symbol} is missing from the client"


def test_401_is_retried_exactly_once(src):
    """One retry. A loop would turn a broken server into a request storm."""
    fn = src[src.index("async function authedFetch"):]
    fn = fn[: fn.index("\n}\n")]
    assert fn.count("r.status === 401") == 1
    assert fn.count("await send(") == 2, "expected exactly one retry"


def test_the_401_path_clears_only_the_token_it_used(src):
    """COMPARE-AND-CLEAR, not a blind clear.

    401s arrive in parallel - the app fires several learner-data calls at
    once, so one expired token yields several 401s. A blind clearSession()
    lets the second 401 wipe the fresh token the first just fetched, and each
    request bootstraps again. e2e-session.mjs measured exactly that: two
    sessions minted per reload, the loser left live on the server.
    """
    fn = src[src.index("async function authedFetch"):]
    fn = fn[: fn.index("\n}\n")]
    assert "clearSessionIf(used)" in fn, "the 401 path must not clear blindly"

    guard = src[src.index("function clearSessionIf"):]
    guard = guard[: guard.index("\n}\n")]
    assert "storedToken() === token" in guard


def test_bootstrap_is_single_flight(src):
    """Ten calls on load must mint one session, not ten."""
    assert "bootstrapping" in src
    fn = src[src.index("export async function ensureSession"):]
    fn = fn[: fn.index("\n}\n")]
    assert "if (!bootstrapping)" in fn
    assert "finally" in fn, "a failed bootstrap must not wedge the promise"


def test_revoking_consent_drops_the_local_session(src):
    """The account is deleted server-side and the session cascades with it."""
    fn = src[src.index("export async function setConsent"):]
    fn = fn[: fn.index("\n}\n")]
    assert "clearSession()" in fn


# ══ part two: the flow, against the real API ══════════════════════════════

@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'client.db'}",
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
def client(engine, monkeypatch):
    """The app with a throwaway database and inference stubbed out."""
    from tilawah.engine.pipeline import Feedback

    def fake_analyze(*_a, **_k):
        return Feedback(status="ok", sura=112, aya=1, analysable=True,
                        clean=True, errors=[], silent_errors=[],
                        snr_db=40.0, duration_s=2.0)

    monkeypatch.setattr(routes, "analyze", fake_analyze)

    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def bootstrap(client, device_id):
    """What the client does on its first authenticated call."""
    r = client.post("/api/auth/anonymous", json={"device_id": device_id})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


def wav():
    return {"audio": ("recitation.wav", b"RIFF0000WAVEfmt ", "audio/wav")}


def form(**kw):
    """The client's attempt payload - note the absence of device_id."""
    base = {"sura": "112", "aya": "1", "lang": "uz", "start_word": "0",
            "num_words": "0", "include_bismillah": "false"}
    base.update(kw)
    return base


# ── the migration path: an install that predates sessions ─────────────────

def test_an_existing_install_keeps_its_history(client, db):
    """THE WHOLE POINT OF PHASE 3B. A learner who has been practising
    anonymously must see the same history after the client switches to
    sessions - no sign-in, nothing lost."""
    db.add(User(id="old-phone", lang="ru", consented=True, consent_seen=True))
    db.commit()
    for aya in (1, 2, 3):
        db.add(Attempt(user_id="old-phone", sura=112, aya=aya, status="ok",
                       analysable=True))
    db.commit()

    token = bootstrap(client, "old-phone")
    r = client.get("/api/attempts?limit=200", headers=hdr(token))
    assert r.status_code == 200
    assert len(r.json()) == 3

    me = client.get("/api/auth/me", headers=hdr(token)).json()
    assert me["user_id"] == "old-phone"
    assert me["consented"] is True and me["lang"] == "ru"


def test_a_first_time_learner_gets_a_working_session(client, db):
    token = bootstrap(client, "brand-new-install")
    assert client.get("/api/attempts", headers=hdr(token)).json() == []
    assert db.get(User, "brand-new-install") is not None


def test_history_needs_no_device_id_at_all(client, db):
    db.add(User(id="p", consented=True))
    db.commit()
    db.add(Attempt(user_id="p", sura=112, aya=1, status="ok"))
    db.commit()
    token = bootstrap(client, "p")
    r = client.get("/api/attempts?limit=20", headers=hdr(token))
    assert r.status_code == 200 and len(r.json()) == 1


# ── the full learner loop over one session ────────────────────────────────

def test_record_read_flag_over_one_session(client, db):
    db.add(User(id="learner", consented=True, consent_seen=True))
    db.commit()
    token = bootstrap(client, "learner")

    posted = client.post("/api/attempts", data=form(), files=wav(),
                         headers=hdr(token))
    assert posted.status_code == 200, posted.text
    attempt_id = posted.json()["id"]
    assert attempt_id is not None, "a consenting learner's attempt must persist"

    rows = client.get("/api/attempts", headers=hdr(token)).json()
    assert len(rows) == 1 and rows[0]["id"] == attempt_id

    flagged = client.post(f"/api/attempts/{attempt_id}/wrong",
                          json={"note": None}, headers=hdr(token))
    assert flagged.status_code == 200
    db.expire_all()
    assert db.get(Attempt, attempt_id).wrong_flag is True


def test_an_attempt_is_filed_for_the_session_not_the_form(client, db):
    """No device_id is sent any more; the row must still land on the right
    account."""
    db.add(User(id="who", consented=True))
    db.commit()
    token = bootstrap(client, "who")
    client.post("/api/attempts", data=form(), files=wav(), headers=hdr(token))
    rows = db.exec(select(Attempt)).all()
    assert len(rows) == 1 and rows[0].user_id == "who"


def test_unauthenticated_learner_calls_are_refused(client):
    assert client.get("/api/attempts").status_code == 401
    assert client.post("/api/attempts", data=form(), files=wav()).status_code == 401
    assert client.post("/api/consent", data={"consented": "true"}).status_code == 401
    assert client.post("/api/attempts/1/wrong", json={"note": None}).status_code == 401


# ── 401 recovery, which is what the client's retry relies on ──────────────

def test_a_dead_token_can_be_replaced_by_re_bootstrapping(client, db):
    """The client's 401 path: clear, bootstrap again, retry. The device id is
    what carries the learner back to the same account."""
    db.add(User(id="steady", consented=True))
    db.commit()
    db.add(Attempt(user_id="steady", sura=112, aya=1, status="ok"))
    db.commit()

    first = bootstrap(client, "steady")
    row = db.exec(select(AuthSession).where(
        AuthSession.token_hash == auth.hash_token(first))).first()
    auth.revoke(db, row)
    assert client.get("/api/attempts", headers=hdr(first)).status_code == 401

    second = bootstrap(client, "steady")
    assert second != first
    again = client.get("/api/attempts", headers=hdr(second))
    assert again.status_code == 200 and len(again.json()) == 1


def test_an_expired_token_recovers_the_same_way(client, db):
    db.add(User(id="lapsed", consented=True))
    db.commit()
    token = bootstrap(client, "lapsed")
    row = db.exec(select(AuthSession).where(
        AuthSession.token_hash == auth.hash_token(token))).first()
    row.expires_at = auth.now() - timedelta(seconds=1)
    db.add(row)
    db.commit()

    assert client.get("/api/attempts", headers=hdr(token)).status_code == 401
    assert client.get("/api/attempts",
                      headers=hdr(bootstrap(client, "lapsed"))).status_code == 200


# ── refresh and logout ────────────────────────────────────────────────────

def test_refresh_rotates_and_keeps_the_same_account(client, db):
    db.add(User(id="rot", consented=True))
    db.commit()
    db.add(Attempt(user_id="rot", sura=112, aya=1, status="ok"))
    db.commit()

    old = bootstrap(client, "rot")
    fresh = client.post("/api/auth/refresh", headers=hdr(old)).json()["token"]
    assert fresh != old
    assert client.get("/api/attempts", headers=hdr(old)).status_code == 401
    kept = client.get("/api/attempts", headers=hdr(fresh))
    assert kept.status_code == 200 and len(kept.json()) == 1


def test_logout_revokes_and_the_device_can_come_back(client, db):
    db.add(User(id="bye", consented=True))
    db.commit()
    token = bootstrap(client, "bye")
    assert client.post("/api/auth/logout", headers=hdr(token)).status_code == 200
    assert client.get("/api/attempts", headers=hdr(token)).status_code == 401
    # Logging out is not deleting: the account and its device id still work.
    assert client.get("/api/attempts",
                      headers=hdr(bootstrap(client, "bye"))).status_code == 200


# ── consent, including the destructive path ───────────────────────────────

def test_consent_round_trip_over_a_session(client, db):
    db.add(User(id="c1", consented=False))
    db.commit()
    token = bootstrap(client, "c1")
    r = client.post("/api/consent",
                    data={"consented": "true", "audio_consented": "false"},
                    headers=hdr(token))
    assert r.status_code == 200
    db.expire_all()
    assert db.get(User, "c1").consented is True


def test_declining_consent_deletes_the_account_and_kills_the_session(
        client, db, monkeypatch):
    monkeypatch.setattr(routes, "delete_stored_audio", lambda _uid: 0)
    db.add(User(id="forget-me", consented=True))
    db.commit()
    db.add(Attempt(user_id="forget-me", sura=112, aya=1, status="ok"))
    db.commit()

    token = bootstrap(client, "forget-me")
    r = client.post("/api/consent",
                    data={"consented": "false", "audio_consented": "false"},
                    headers=hdr(token))
    assert r.status_code == 200

    db.expire_all()
    assert db.get(User, "forget-me") is None
    assert db.exec(select(Attempt)).all() == []
    # The client calls clearSession() here for exactly this reason.
    assert client.get("/api/attempts", headers=hdr(token)).status_code == 401


def test_the_learner_can_keep_using_the_app_after_being_forgotten(
        client, db, monkeypatch):
    """Deleting your data is not deleting your ability to practise."""
    monkeypatch.setattr(routes, "delete_stored_audio", lambda _uid: 0)
    db.add(User(id="again", consented=True))
    db.commit()
    token = bootstrap(client, "again")
    client.post("/api/consent", data={"consented": "false"}, headers=hdr(token))

    fresh = bootstrap(client, "again")          # what clearSession() leads to
    r = client.get("/api/attempts", headers=hdr(fresh))
    assert r.status_code == 200 and r.json() == []


# ── the cookie transport, which a same-origin deployment would use ────────

def test_the_cookie_alone_authenticates_learner_data(client, db):
    db.add(User(id="cook", consented=True))
    db.commit()
    db.add(Attempt(user_id="cook", sura=112, aya=1, status="ok"))
    db.commit()

    client.post("/api/auth/anonymous", json={"device_id": "cook"})
    r = client.get("/api/attempts")          # no Authorization header
    assert r.status_code == 200 and len(r.json()) == 1
