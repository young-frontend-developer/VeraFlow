# -*- coding: utf-8 -*-
"""Google sign-in: what a token must prove, and whose account it may touch.

TWO PROPERTIES ARE UNDER TEST AND THEY FAIL DIFFERENTLY.

  VERIFICATION - a token that is expired, forged, meant for another client, or
  missing a subject must be refused. Getting this wrong lets a stranger in.

  OWNERSHIP - a learner who has been practising anonymously must end up with
  the SAME User.id and the SAME history after signing in. Getting this wrong
  does not let anyone in; it silently strands somebody's practice behind an
  account they can no longer reach, and they experience it as the app having
  forgotten them. That is the failure this file spends most of its tests on.

The signature check is stubbed at google_identity._decode, which is the only
part that talks to Google. Everything above it - issuer, audience, expiry,
subject, nonce - is our policy and is exercised for real.
"""
import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from tilawah import auth, google_identity
from tilawah.api import auth_routes
from tilawah.api.main import app
from tilawah.db import get_session
from tilawah.db.models import Attempt, AuthIdentity, AuthSession, User

CLIENT_WEB = "111-web.apps.googleusercontent.com"
CLIENT_ANDROID = "111-android.apps.googleusercontent.com"


def payload(**over):
    """A well-formed Google ID token payload."""
    now = int(time.time())
    base = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_WEB,
        "sub": "google-subject-0001",
        "email": "learner@example.com",
        "email_verified": True,
        "name": "Bir Talaba",
        "iat": now,
        "exp": now + 3600,
    }
    base.update(over)
    return base


# ══ verification policy ═══════════════════════════════════════════════════

def verify(raw="tok", *, claims=None, audiences=None, nonce=None, monkeypatch=None):
    monkeypatch.setattr(google_identity, "_decode",
                        lambda _raw: claims if claims is not None else payload())
    return google_identity.verify(
        raw, audiences=audiences or [CLIENT_WEB], expected_nonce=nonce)


def test_a_good_token_yields_the_subject(monkeypatch):
    got = verify(monkeypatch=monkeypatch)
    assert got.subject == "google-subject-0001"
    assert got.email == "learner@example.com"
    assert got.email_verified is True


def test_expired_token_is_rejected(monkeypatch):
    now = int(time.time())
    with pytest.raises(google_identity.GoogleAuthError) as e:
        verify(claims=payload(exp=now - 3600), monkeypatch=monkeypatch)
    assert e.value.code == "expired"


def test_a_token_expiring_within_the_skew_is_still_refused(monkeypatch):
    now = int(time.time())
    with pytest.raises(google_identity.GoogleAuthError):
        verify(claims=payload(exp=now - google_identity.CLOCK_SKEW_SECONDS - 5),
               monkeypatch=monkeypatch)


def test_wrong_audience_is_rejected(monkeypatch):
    """Somebody else's client id. This is the check that CANNOT be delegated to
    the library, because we accept a list and it accepts one."""
    with pytest.raises(google_identity.GoogleAuthError) as e:
        verify(claims=payload(aud="999-someone-else.apps.googleusercontent.com"),
               monkeypatch=monkeypatch)
    assert e.value.code == "bad_audience"


def test_every_configured_audience_is_accepted(monkeypatch):
    """The Android client id will differ from the web one; both must pass."""
    got = verify(claims=payload(aud=CLIENT_ANDROID),
                 audiences=[CLIENT_WEB, CLIENT_ANDROID], monkeypatch=monkeypatch)
    assert got.audience == CLIENT_ANDROID


def test_wrong_issuer_is_rejected(monkeypatch):
    with pytest.raises(google_identity.GoogleAuthError) as e:
        verify(claims=payload(iss="https://evil.example.com"),
               monkeypatch=monkeypatch)
    assert e.value.code == "bad_issuer"


@pytest.mark.parametrize("iss", ["accounts.google.com",
                                 "https://accounts.google.com"])
def test_both_spellings_of_googles_issuer_are_accepted(iss, monkeypatch):
    assert verify(claims=payload(iss=iss), monkeypatch=monkeypatch).subject


@pytest.mark.parametrize("sub", [None, "", "   ", 12345, {"a": 1}])
def test_a_missing_or_unusable_subject_is_rejected(sub, monkeypatch):
    """No subject means no identity. Falling back to email here is the exact
    mistake the whole module exists to prevent."""
    claims = payload()
    if sub is None:
        claims.pop("sub")
    else:
        claims["sub"] = sub
    with pytest.raises(google_identity.GoogleAuthError) as e:
        verify(claims=claims, monkeypatch=monkeypatch)
    assert e.value.code == "missing_subject"


def test_a_bad_signature_is_rejected(monkeypatch):
    def boom(_raw):
        raise ValueError("Token has wrong signature: <token contents>")
    monkeypatch.setattr(google_identity, "_decode", boom)
    with pytest.raises(google_identity.GoogleAuthError) as e:
        google_identity.verify("tok", audiences=[CLIENT_WEB])
    assert e.value.code == "bad_signature"
    # The library's message can quote the token; ours must not carry it on.
    assert "token contents" not in str(e.value)


def test_an_empty_audience_list_refuses_everything(monkeypatch):
    """Misconfiguration must fail closed, not accept every client."""
    monkeypatch.setattr(google_identity, "_decode", lambda _r: payload())
    with pytest.raises(google_identity.GoogleAuthError) as e:
        google_identity.verify("tok", audiences=[])
    assert e.value.code == "not_configured"


def test_a_token_issued_in_the_future_is_rejected(monkeypatch):
    now = int(time.time())
    with pytest.raises(google_identity.GoogleAuthError) as e:
        verify(claims=payload(iat=now + 600), monkeypatch=monkeypatch)
    assert e.value.code == "issued_in_future"


def test_nonce_mismatch_is_rejected(monkeypatch):
    with pytest.raises(google_identity.GoogleAuthError) as e:
        verify(claims=payload(nonce="theirs"), nonce="ours",
               monkeypatch=monkeypatch)
    assert e.value.code == "nonce_mismatch"


def test_the_fingerprint_is_a_hash_not_a_prefix():
    raw = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMyJ9.payload.signature"
    fp = google_identity.token_fingerprint(raw)
    assert fp not in raw and raw[:12] not in fp
    assert len(fp) == 12


# ══ ownership and linking, through the API ════════════════════════════════

@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'g.db'}",
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
    import dataclasses

    from tilawah.config import settings as base

    monkeypatch.setattr(auth_routes, "settings", dataclasses.replace(
        base, google_client_ids=f"{CLIENT_WEB},{CLIENT_ANDROID}"))

    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def google(monkeypatch):
    """Control what Google 'returns' for the next verification."""
    state = {"claims": payload()}

    def fake_decode(_raw):
        c = dict(state["claims"])
        # The route passes the nonce it just consumed; echo it like Google does.
        if state.get("echo_nonce") is not None:
            c["nonce"] = state["echo_nonce"]
        return c

    monkeypatch.setattr(google_identity, "_decode", fake_decode)
    return state


def start(client, google):
    """POST /google/start and arrange for Google to echo the nonce back."""
    r = client.post("/api/auth/google/start")
    assert r.status_code == 200, r.text
    nonce = r.json()["nonce"]
    google["echo_nonce"] = nonce
    return nonce


def sign_in(client, google, *, token=None, sub=None):
    nonce = start(client, google)
    if sub is not None:
        google["claims"] = payload(sub=sub)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/auth/google",
                       json={"credential": "id-token", "nonce": nonce},
                       headers=headers)


def anon(client, device_id):
    return client.post("/api/auth/anonymous",
                       json={"device_id": device_id}).json()["token"]


def signed_out(client):
    """Really have no session.

    TestClient KEEPS COOKIES between requests, and every auth response sets
    one - so a request with no Authorization header is still authenticated by
    the cookie left over from three lines earlier. That is correct behaviour
    for the client and a trap for the test: "no session" cases silently ran as
    the previous user. Call this wherever a fresh, signed-out browser is what
    is being modelled.
    """
    client.cookies.clear()


def seed(db, uid, *, attempts=0, consented=True, audio=False):
    db.add(User(id=uid, lang="uz", consented=consented, audio_consented=audio,
                consent_seen=True))
    db.commit()
    for i in range(attempts):
        # WRAPPED AT FOUR because al-Ikhlas HAS four ayat. Seeding aya=5 blew
        # up the history endpoint - letters.in_range() asks the real mushaf for
        # the word count and the engine refuses an ayah that does not exist.
        # Right refusal, wrong test data.
        db.add(Attempt(user_id=uid, sura=112, aya=(i % 4) + 1, status="ok"))
        db.commit()


# ── CASE A: anonymous learner links Google ────────────────────────────────

def test_case_a_linking_keeps_the_same_user_id(client, db, google):
    """THE HEADLINE REQUIREMENT. Google must attach to the account in hand."""
    seed(db, "anon-a", attempts=3)
    token = anon(client, "anon-a")

    r = sign_in(client, google, token=token)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_id"] == "anon-a", "a second account was created"
    assert body["linked_now"] is True
    assert body["providers"] == ["google"]


def test_case_a_attempts_survive_the_link(client, db, google):
    seed(db, "anon-b", attempts=4)
    token = anon(client, "anon-b")
    new_token = sign_in(client, google, token=token).json()["token"]

    rows = client.get("/api/attempts",
                      headers={"Authorization": f"Bearer {new_token}"}).json()
    assert len(rows) == 4
    assert db.exec(select(Attempt).where(Attempt.user_id == "anon-b")).all()


def test_case_a_consent_state_is_untouched(client, db, google):
    """Consent is a decision the learner made. Signing in is not re-deciding."""
    seed(db, "anon-c", consented=True, audio=True)
    before = (db.get(User, "anon-c").consented,
              db.get(User, "anon-c").audio_consented,
              db.get(User, "anon-c").consent_seen)

    sign_in(client, google, token=anon(client, "anon-c"))

    db.expire_all()
    after = db.get(User, "anon-c")
    assert (after.consented, after.audio_consented, after.consent_seen) == before


def test_case_a_exactly_one_user_and_one_identity_exist(client, db, google):
    seed(db, "anon-d")
    sign_in(client, google, token=anon(client, "anon-d"))
    assert len(db.exec(select(User)).all()) == 1
    assert len(db.exec(select(AuthIdentity)).all()) == 1


def test_case_a_rotates_the_session(client, db, google):
    """Attaching an identity changes what the session is worth."""
    seed(db, "anon-e")
    old = anon(client, "anon-e")
    new = sign_in(client, google, token=old).json()["token"]
    assert new != old
    assert client.get("/api/auth/me",
                      headers={"Authorization": f"Bearer {old}"}).status_code == 401


def test_google_can_sign_the_same_learner_in_again_later(client, db, google):
    """Second visit, new device, no anonymous session: same account."""
    seed(db, "anon-f", attempts=2)
    sign_in(client, google, token=anon(client, "anon-f"))

    signed_out(client)                          # a genuinely fresh browser
    again = sign_in(client, google)
    assert again.status_code == 200
    assert again.json()["user_id"] == "anon-f"
    assert again.json()["linked_now"] is False

    rows = client.get("/api/attempts", headers={
        "Authorization": f"Bearer {again.json()['token']}"}).json()
    assert len(rows) == 2


# ── CASE B: the Google account belongs to someone else ────────────────────

def test_case_b_conflict_is_refused(client, db, google):
    seed(db, "owner-b", attempts=2)
    sign_in(client, google, token=anon(client, "owner-b"))        # B owns it

    seed(db, "other-a", attempts=5)
    r = sign_in(client, google, token=anon(client, "other-a"))
    assert r.status_code == 409
    assert "already linked" in r.json()["detail"]


def test_case_b_mutates_nothing_at_all(client, db, google):
    seed(db, "owner-b2", attempts=2)
    sign_in(client, google, token=anon(client, "owner-b2"))
    seed(db, "other-a2", attempts=5)
    a_token = anon(client, "other-a2")

    before_users = {u.id for u in db.exec(select(User)).all()}
    before_ids = [(i.user_id, i.subject) for i in db.exec(select(AuthIdentity)).all()]

    assert sign_in(client, google, token=a_token).status_code == 409

    db.expire_all()
    assert {u.id for u in db.exec(select(User)).all()} == before_users
    assert [(i.user_id, i.subject)
            for i in db.exec(select(AuthIdentity)).all()] == before_ids
    # The identity did NOT move.
    ident = db.exec(select(AuthIdentity)).first()
    assert ident.user_id == "owner-b2"


def test_case_b_leaves_both_accounts_reachable(client, db, google):
    seed(db, "owner-b3", attempts=2)
    sign_in(client, google, token=anon(client, "owner-b3"))
    seed(db, "other-a3", attempts=5)
    a_token = anon(client, "other-a3")
    sign_in(client, google, token=a_token)                        # 409

    # A's session still works and still sees A's five attempts.
    rows = client.get("/api/attempts",
                      headers={"Authorization": f"Bearer {a_token}"}).json()
    assert len(rows) == 5
    # B's data is intact.
    assert len(db.exec(select(Attempt).where(
        Attempt.user_id == "owner-b3")).all()) == 2


def test_signing_in_twice_from_the_same_account_is_not_a_conflict(client, db, google):
    seed(db, "same", attempts=1)
    token = anon(client, "same")
    first = sign_in(client, google, token=token)
    assert first.status_code == 200
    second = sign_in(client, google, token=first.json()["token"])
    assert second.status_code == 200
    assert second.json()["user_id"] == "same"
    assert second.json()["linked_now"] is False
    assert len(db.exec(select(AuthIdentity)).all()) == 1


# ── CASE C: no session at all ─────────────────────────────────────────────

def test_case_c_unknown_google_account_creates_one_user(client, db, google):
    r = sign_in(client, google, sub="brand-new-sub")
    assert r.status_code == 200
    assert r.json()["linked_now"] is True
    users = db.exec(select(User)).all()
    assert len(users) == 1 and users[0].id == r.json()["user_id"]
    # A fresh uuid4, not the Google subject - see debug_capture._tag().
    assert len(users[0].id) == 36 and "brand-new-sub" not in users[0].id


# ── identity is `sub`, never email ────────────────────────────────────────

def test_changing_the_email_does_not_change_the_identity(client, db, google):
    """Somebody changes their Gmail address. Same person, same account."""
    seed(db, "stable", attempts=3)
    sign_in(client, google, token=anon(client, "stable"))

    google["claims"] = payload(email="renamed@example.com")
    signed_out(client)
    again = sign_in(client, google)
    assert again.status_code == 200
    assert again.json()["user_id"] == "stable"
    assert len(db.exec(select(AuthIdentity)).all()) == 1
    db.expire_all()
    assert db.exec(select(AuthIdentity)).first().email == "renamed@example.com"


def test_the_same_email_on_a_different_subject_is_a_different_person(client, db, google):
    """An address reused after deletion must NOT inherit the old account."""
    seed(db, "first", attempts=2)
    sign_in(client, google, token=anon(client, "first"))

    google["claims"] = payload(sub="a-completely-different-sub",
                               email="learner@example.com")
    signed_out(client)
    r = sign_in(client, google)
    assert r.status_code == 200
    assert r.json()["user_id"] != "first"
    assert len(db.exec(select(User)).all()) == 2


def test_a_client_supplied_subject_is_ignored(client, db, google):
    """The request body has no subject field; sending one changes nothing."""
    seed(db, "victim-x", attempts=1)
    sign_in(client, google, token=anon(client, "victim-x"))

    signed_out(client)
    nonce = start(client, google)
    google["claims"] = payload(sub="attacker-sub")
    r = client.post("/api/auth/google",
                    json={"credential": "id-token", "nonce": nonce,
                          "subject": "google-subject-0001"})
    assert r.status_code == 200
    # Resolved from the TOKEN's sub, not the body's.
    assert r.json()["user_id"] != "victim-x"


# ── nonce / login-CSRF ────────────────────────────────────────────────────

def test_a_credential_with_no_nonce_is_refused(client, db, google):
    r = client.post("/api/auth/google", json={"credential": "id-token"})
    assert r.status_code == 401


def test_an_unknown_nonce_is_refused(client, db, google):
    r = client.post("/api/auth/google",
                    json={"credential": "id-token", "nonce": "never-issued"})
    assert r.status_code == 401


def test_a_nonce_cannot_be_used_twice(client, db, google):
    """Replaying a captured credential must fail the second time."""
    nonce = start(client, google)
    first = client.post("/api/auth/google",
                        json={"credential": "id-token", "nonce": nonce})
    assert first.status_code == 200
    replay = client.post("/api/auth/google",
                         json={"credential": "id-token", "nonce": nonce})
    assert replay.status_code == 401


def test_an_expired_nonce_is_refused(client, db, google):
    from tilawah.db.models import OAuthNonce
    nonce = start(client, google)
    row = db.exec(select(OAuthNonce)).first()
    row.expires_at = auth.now() - timedelta(seconds=1)
    db.add(row)
    db.commit()
    r = client.post("/api/auth/google",
                    json={"credential": "id-token", "nonce": nonce})
    assert r.status_code == 401


def test_the_nonce_is_stored_only_as_a_hash(client, db, google):
    from tilawah.db.models import OAuthNonce
    nonce = start(client, google)
    row = db.exec(select(OAuthNonce)).first()
    assert row.nonce_hash != nonce
    assert row.nonce_hash == auth.hash_token(nonce)


def test_a_spent_nonce_is_kept_as_evidence_not_deleted(client, db, google):
    from tilawah.db.models import OAuthNonce
    nonce = start(client, google)
    client.post("/api/auth/google",
                json={"credential": "id-token", "nonce": nonce})
    row = db.exec(select(OAuthNonce)).first()
    assert row is not None and row.consumed_at is not None


# ── refusals leak nothing ─────────────────────────────────────────────────

def test_every_verification_failure_looks_identical(client, db, google):
    """Expired vs wrong-audience vs forged must be indistinguishable."""
    bodies = set()
    for claims in (payload(exp=int(time.time()) - 10),
                   payload(aud="someone-else"),
                   payload(iss="https://evil.example.com")):
        nonce = start(client, google)
        google["claims"] = claims
        r = client.post("/api/auth/google",
                        json={"credential": "id-token", "nonce": nonce})
        assert r.status_code == 401
        bodies.add(r.text)
    assert len(bodies) == 1, f"refusals differ and leak the reason: {bodies}"


def test_the_raw_credential_never_reaches_the_logs(client, db, google, caplog):
    secret = "eyJhbGciOiJSUzI1NiJ9.THIS-IS-THE-CREDENTIAL.sig"
    with caplog.at_level("DEBUG"):
        nonce = start(client, google)
        google["claims"] = payload(exp=int(time.time()) - 10)   # force a failure
        client.post("/api/auth/google",
                    json={"credential": secret, "nonce": nonce})
        nonce2 = start(client, google)
        google["claims"] = payload()                            # and a success
        client.post("/api/auth/google",
                    json={"credential": secret, "nonce": nonce2})

    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert secret not in logged
    assert "THIS-IS-THE-CREDENTIAL" not in logged
    for size in (10, 16, 24):
        assert secret[:size] not in logged


# ── switched off, and the rest of the system ──────────────────────────────

def test_google_endpoints_are_503_when_unconfigured(engine, monkeypatch):
    import dataclasses

    from tilawah.config import settings as base
    monkeypatch.setattr(auth_routes, "settings",
                        dataclasses.replace(base, google_client_ids=""))

    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    c = TestClient(app)
    assert c.post("/api/auth/google/start").status_code == 503
    assert c.post("/api/auth/google",
                  json={"credential": "x", "nonce": "y"}).status_code == 503
    app.dependency_overrides.clear()


def test_logout_still_works_on_a_google_session(client, db, google):
    seed(db, "bye-g")
    token = sign_in(client, google, token=anon(client, "bye-g")).json()["token"]
    assert client.post("/api/auth/logout",
                       headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get("/api/auth/me",
                      headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_deleting_the_account_removes_the_google_identity(client, db, google, monkeypatch):
    """Otherwise a stale UNIQUE(provider, subject) row locks that Google
    account out of ever signing up again."""
    from tilawah.api import routes
    monkeypatch.setattr(routes, "delete_stored_audio", lambda _uid: 0)

    seed(db, "erase-me", attempts=1)
    token = sign_in(client, google, token=anon(client, "erase-me")).json()["token"]

    r = client.post("/api/consent", data={"consented": "false"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    db.expire_all()
    assert db.get(User, "erase-me") is None
    assert db.exec(select(AuthIdentity)).all() == []
    assert db.exec(select(AuthSession)).all() == []

    # And the same Google account can start fresh.
    signed_out(client)
    again = sign_in(client, google)
    assert again.status_code == 200


def test_the_anonymous_flow_is_unchanged(client, db):
    """Google must not have altered the path a learner who never signs in takes."""
    seed(db, "still-anon", attempts=2)
    token = anon(client, "still-anon")
    rows = client.get("/api/attempts",
                      headers={"Authorization": f"Bearer {token}"}).json()
    assert len(rows) == 2
    me = client.get("/api/auth/me",
                    headers={"Authorization": f"Bearer {token}"}).json()
    assert me["is_anonymous"] is True and me["providers"] == []


def test_a_second_different_google_account_is_refused_not_a_500(client, db, google):
    """One Google account per Tilawah account.

    Found by the tests above failing with an IntegrityError: the insert hit
    UNIQUE(user_id, provider) and the learner got a 500 for doing something
    entirely reasonable - signing in with their other Google address. It is a
    409 now. Repointing the existing identity instead would be far worse: it
    would hand this account to a different Google login and lock the original
    one out of it.
    """
    seed(db, "two-googles", attempts=2)
    token = sign_in(client, google, token=anon(client, "two-googles")).json()["token"]

    google["claims"] = payload(sub="a-second-google-account")
    r = sign_in(client, google, token=token)
    assert r.status_code == 409
    assert "already linked to a different Google" in r.json()["detail"]

    # Nothing moved: one identity, still the first subject, history intact.
    db.expire_all()
    identities = db.exec(select(AuthIdentity)).all()
    assert len(identities) == 1
    assert identities[0].subject == "google-subject-0001"
    assert len(db.exec(select(Attempt).where(
        Attempt.user_id == "two-googles")).all()) == 2
