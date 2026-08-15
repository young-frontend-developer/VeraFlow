# -*- coding: utf-8 -*-
"""Email/password sign-in: what a password must clear, and whose account it gets.

FOUR PROPERTIES ARE UNDER TEST AND THEY FAIL DIFFERENTLY.

  CREDENTIALS - a password is hashed, never stored or returned in plaintext,
  and a wrong one is refused. Getting this wrong lets a stranger in.

  DISCLOSURE - "no such address" and "wrong password" must be indistinguishable,
  and forgot-password must answer identically for a stranger and a learner.
  Getting this wrong does not let anyone in; it turns the login form into a
  membership test against any address anybody cares to try.

  OWNERSHIP - a learner who has been practising anonymously must end up with the
  SAME User.id and the SAME history after registering. Getting this wrong
  silently strands somebody's practice behind an account they cannot reach, and
  they experience it as the app having forgotten them.

  THROTTLING - repeated failures must actually stop. This is the only defence
  against someone simply trying passwords until one works.

Nothing is stubbed except the mailer, which has nothing behind it to stub out
yet - the tests read the token straight from the database, which is exactly
what a provider would put in the link.
"""
import dataclasses

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from tilawah import auth, mailer, passwords
from tilawah.api import auth_routes, email_routes
from tilawah.api.main import app
from tilawah.db import get_session
from tilawah.db.models import Attempt, AuthIdentity, AuthSession, EmailToken, User
from tilawah.ratelimit import limiter

EMAIL = "learner@example.com"
PASSWORD = "a decent passphrase"


# ══ fixtures ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'e.db'}",
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


@pytest.fixture(autouse=True)
def fresh_limiter():
    """The limiter is process-wide state, so it MUST be reset between tests.

    Without this, the throttling tests leave a block behind and every later
    test that logs in gets a 429 - which reads as a broken login endpoint and
    is really a dirty fixture.
    """
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def no_mail(monkeypatch):
    """Capture what would have been sent instead of pretending to send it.

    There is no provider wired, so `_deliver` already only logs - but pinning
    it here means these tests do not start sending real mail on the day one is.
    """
    sent: list[mailer.Message] = []
    monkeypatch.setattr(mailer, "_deliver", lambda msg: sent.append(msg))
    return sent


@pytest.fixture
def client(engine, monkeypatch):
    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def verifying(monkeypatch):
    """Turn TILAWAH_REQUIRE_EMAIL_VERIFICATION on for one test."""
    from tilawah.config import settings as base
    monkeypatch.setattr(email_routes, "settings", dataclasses.replace(
        base, require_email_verification=True))


def register(client, *, email=EMAIL, password=PASSWORD, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/auth/register",
                       json={"email": email, "password": password},
                       headers=headers)


def login(client, *, email=EMAIL, password=PASSWORD, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/auth/login",
                       json={"email": email, "password": password},
                       headers=headers)


def anon(client, device_id):
    return client.post("/api/auth/anonymous",
                       json={"device_id": device_id}).json()["token"]


def signed_out(client):
    """Really have no session.

    TestClient KEEPS COOKIES between requests and every auth response sets one,
    so a request with no Authorization header is still authenticated by the
    cookie left over from three lines earlier. Same trap as test_google_identity.
    """
    client.cookies.clear()


def code(response) -> str:
    """The machine code out of a refusal body."""
    return response.json()["detail"]["code"]


def token_for(db, user_id, purpose) -> str | None:
    """There is no way to read a token back - only its hash is stored - so
    tests mint their own through the same function the routes use. Anything
    else would be testing a different token than the one learners get."""
    row = db.exec(select(EmailToken).where(EmailToken.user_id == user_id,
                                           EmailToken.purpose == purpose)).first()
    return row


# ══ the password policy ═══════════════════════════════════════════════════

def test_hash_is_not_the_password():
    hashed = passwords.hash_password(PASSWORD)
    assert PASSWORD not in hashed
    assert hashed.startswith("$argon2id$")


def test_the_same_password_hashes_differently_every_time():
    """Salting. Two learners with the same password must not have equal rows -
    otherwise one cracked hash opens every account that shares it."""
    assert passwords.hash_password(PASSWORD) != passwords.hash_password(PASSWORD)


def test_verify_accepts_the_right_password_and_rejects_others():
    hashed = passwords.hash_password(PASSWORD)
    assert passwords.verify_password(hashed, PASSWORD)
    assert not passwords.verify_password(hashed, PASSWORD + "x")
    assert not passwords.verify_password(hashed, "")


def test_verify_never_raises_on_rubbish():
    """Every kind of no is False, so the caller cannot accidentally turn one
    of them into a different HTTP response."""
    assert not passwords.verify_password(None, PASSWORD)
    assert not passwords.verify_password("", PASSWORD)
    assert not passwords.verify_password("not a hash at all", PASSWORD)


def test_long_passwords_are_not_truncated():
    """The bcrypt trap, checked explicitly. Two passphrases sharing a long
    prefix must not be interchangeable."""
    a = "x" * 71 + "A"
    b = "x" * 71 + "B"
    assert not passwords.verify_password(passwords.hash_password(a), b)


@pytest.mark.parametrize("password,expected", [
    ("short", "too_short"),
    ("password123", "too_common"),
    ("x" * 300, "too_long"),
])
def test_policy_refuses(password, expected):
    assert expected in passwords.password_problems(password)


def test_policy_refuses_a_password_containing_the_address():
    assert "looks_like_email" in passwords.password_problems(
        "learner-and-more", email=EMAIL)


def test_policy_accepts_a_reasonable_passphrase():
    assert passwords.password_problems(PASSWORD, email=EMAIL) == []


def test_policy_accepts_non_latin_scripts():
    """A passphrase in Uzbek or Arabic is a fine password, and a composition
    rule that demanded an ASCII capital would say otherwise."""
    assert passwords.password_problems("парол ва яна бир нечта сўз") == []


@pytest.mark.parametrize("raw,expected", [
    ("  Learner@Example.COM ", EMAIL),
    ("LEARNER@EXAMPLE.COM", EMAIL),
])
def test_addresses_normalise_to_one_form(raw, expected):
    assert passwords.normalise_email(raw) == expected


# ══ registration ══════════════════════════════════════════════════════════

def test_register_mints_a_session_and_an_identity(client, db):
    r = register(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token"]
    assert body["providers"] == ["email"]
    assert body["email_verified"] is False

    identity = db.exec(select(AuthIdentity)).one()
    assert identity.provider == "email"
    assert identity.subject == EMAIL


def test_register_never_returns_the_password_anywhere(client):
    r = register(client)
    assert PASSWORD not in r.text
    assert "password" not in r.json()


def test_register_stores_a_hash_and_not_the_plaintext(client, db):
    register(client)
    identity = db.exec(select(AuthIdentity)).one()
    assert identity.password_hash and PASSWORD not in identity.password_hash
    assert passwords.verify_password(identity.password_hash, PASSWORD)


def test_register_refuses_a_duplicate_address(client):
    register(client)
    signed_out(client)
    r = register(client)
    assert r.status_code == 409
    assert code(r) == "email_taken"


def test_register_refuses_a_duplicate_in_different_case(client):
    """The normalisation, tested where it matters. Without it, Learner@ and
    learner@ are two accounts and only one has the learner's history."""
    register(client)
    signed_out(client)
    r = register(client, email="LEARNER@Example.com")
    assert r.status_code == 409


def test_register_refuses_a_weak_password_with_reasons(client):
    r = register(client, password="short")
    assert r.status_code == 400
    assert code(r) == "weak_password"
    assert "too_short" in r.json()["detail"]["problems"]


def test_register_refuses_a_malformed_address(client):
    r = register(client, email="not-an-address")
    assert r.status_code == 400
    assert code(r) == "invalid_email"


def test_a_refused_registration_writes_nothing(client, db):
    register(client, email="not-an-address")
    register(client, password="short")
    assert db.exec(select(User)).all() == []
    assert db.exec(select(AuthIdentity)).all() == []


# ── the ownership rule ────────────────────────────────────────────────────

def test_registering_keeps_the_anonymous_user_id(client, db):
    """THE POINT OF THE WHOLE FLOW. Same account, now with a password on it."""
    token = anon(client, "anon-keep")
    before = client.get("/api/auth/me",
                        headers={"Authorization": f"Bearer {token}"}).json()["user_id"]

    r = register(client, token=token)
    assert r.status_code == 200, r.text
    assert r.json()["user_id"] == before
    assert r.json()["linked_now"] is True


def test_registering_keeps_the_practice_history(client, db):
    token = anon(client, "anon-history")
    uid = client.get("/api/auth/me",
                     headers={"Authorization": f"Bearer {token}"}).json()["user_id"]
    for aya in (1, 2, 3):
        db.add(Attempt(user_id=uid, sura=112, aya=aya, status="ok"))
    db.commit()

    new_token = register(client, token=token).json()["token"]
    rows = client.get("/api/attempts",
                      headers={"Authorization": f"Bearer {new_token}"}).json()
    assert len(rows) == 3


def test_registering_keeps_the_consent_state(client, db):
    """Consent is a decision somebody made. Signing up is not a reason to
    re-ask it, and it is certainly not a reason to silently reset it."""
    token = anon(client, "anon-consent")
    uid = client.get("/api/auth/me",
                     headers={"Authorization": f"Bearer {token}"}).json()["user_id"]
    user = db.get(User, uid)
    user.consented, user.consent_seen = True, True
    db.add(user)
    db.commit()

    register(client, token=token)
    db.expire_all()
    user = db.get(User, uid)
    assert user.consented is True
    assert user.consent_seen is True


def test_registering_creates_exactly_one_user_and_one_identity(client, db):
    """The orphaned-account bug, stated as a count. A second User row here is
    the failure that looks like lost history."""
    token = anon(client, "anon-count")
    register(client, token=token)
    assert len(db.exec(select(User)).all()) == 1
    assert len(db.exec(select(AuthIdentity)).all()) == 1


def test_registering_rotates_the_session(client):
    """Attaching an identity changes what the session is worth; a session that
    survives a privilege change is the classic fixation bug."""
    old = anon(client, "anon-rotate")
    new = register(client, token=old).json()["token"]
    assert new != old
    signed_out(client)
    assert client.get("/api/auth/me",
                      headers={"Authorization": f"Bearer {old}"}).status_code == 401


def test_one_email_identity_per_account(client):
    token = register(client).json()["token"]
    r = register(client, email="second@example.com", token=token)
    assert r.status_code == 409
    assert code(r) == "already_has_email"


# ══ login ═════════════════════════════════════════════════════════════════

def test_login_returns_a_working_session(client):
    register(client)
    signed_out(client)
    r = login(client)
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["is_anonymous"] is False
    assert me.json()["providers"] == ["email"]


def test_login_is_the_same_user_as_registration(client):
    uid = register(client).json()["user_id"]
    signed_out(client)
    assert login(client).json()["user_id"] == uid


def test_login_accepts_a_differently_cased_address(client):
    register(client)
    signed_out(client)
    assert login(client, email=" LEARNER@EXAMPLE.com ").status_code == 200


def test_wrong_password_and_unknown_address_are_indistinguishable(client):
    """THE DISCLOSURE TEST. If these two responses ever differ - by status, by
    code, by anything - this endpoint becomes a way to ask whether any given
    person has an account here."""
    register(client)
    signed_out(client)
    wrong = login(client, password="the wrong passphrase")
    signed_out(client)
    unknown = login(client, email="nobody@example.com")

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_login_never_echoes_the_password(client):
    register(client)
    signed_out(client)
    r = login(client, password="the wrong passphrase")
    assert "the wrong passphrase" not in r.text


def test_login_does_not_merge_a_different_account(client, db):
    """Signing in as B while holding A's session signs in as B, cleanly. It
    must not merge them: both hold real history and real consent decisions,
    and consent is not something software may infer on somebody's behalf."""
    a = anon(client, "anon-a")
    a_id = client.get("/api/auth/me",
                      headers={"Authorization": f"Bearer {a}"}).json()["user_id"]
    # SIGNED OUT FIRST, and it is not decoration: TestClient still holds A's
    # cookie, and registering with it would LINK email to A - which is correct
    # behaviour (see the ownership rule) and the wrong setup for this test.
    signed_out(client)
    register(client)                       # creates B, a different account
    signed_out(client)

    r = login(client, token=a)
    assert r.status_code == 200
    assert r.json()["user_id"] != a_id
    # A's session is revoked rather than left live alongside the new one.
    signed_out(client)
    assert client.get("/api/auth/me",
                      headers={"Authorization": f"Bearer {a}"}).status_code == 401
    # A itself still exists - signing in elsewhere does not delete anybody.
    assert db.get(User, a_id) is not None


# ══ throttling ════════════════════════════════════════════════════════════

def test_repeated_failures_are_throttled(client):
    register(client)
    signed_out(client)
    for _ in range(5):
        login(client, password="wrong one")
    r = login(client, password="wrong one")
    assert r.status_code == 429
    assert code(r) == "too_many_attempts"
    assert r.json()["detail"]["retry_after"] > 0
    assert r.headers["retry-after"]


def test_throttling_blocks_the_right_password_too(client):
    """A block that let the correct password straight through would be no
    protection at all - guessing is exactly the activity that ends in one."""
    register(client)
    signed_out(client)
    for _ in range(6):
        login(client, password="wrong one")
    assert login(client).status_code == 429


def test_success_clears_the_counter(client):
    """A learner who mistypes twice and then gets it right must not carry
    those two failures into the next hour."""
    register(client)
    signed_out(client)
    login(client, password="wrong one")
    login(client, password="wrong one")
    assert login(client).status_code == 200
    signed_out(client)
    # FOUR MORE, one short of the limit. Had the first two carried over, this
    # would be the sixth failure and the account would be blocked - so a
    # successful login here is the evidence that the counter really reset.
    for _ in range(4):
        login(client, password="wrong one")
    assert login(client).status_code == 200


def test_one_locked_account_does_not_lock_the_others(client):
    """THE CARRIER-NAT CASE, and the reason the two limits differ.

    This app's learners are largely on mobile networks where thousands share
    one address. If the per-IP threshold matched the per-account one, any one
    of them could lock out everybody else on their carrier by mistyping their
    own password five times - a denial of service the attacker gets for free.
    """
    register(client)
    signed_out(client)
    register(client, email="second@example.com", password="another fine phrase")
    signed_out(client)

    for _ in range(6):
        login(client, password="wrong one")
    assert login(client).status_code == 429           # the first account is out

    signed_out(client)
    # ...and the second, from the very same address, is unaffected.
    r = login(client, email="second@example.com", password="another fine phrase")
    assert r.status_code == 200


def test_spraying_many_accounts_from_one_address_is_still_caught(client):
    """The attack the per-IP limit is actually for: one guess against each of
    many accounts, which per-account counting never sees because no single
    account gets more than a couple."""
    for i in range(20):
        login(client, email=f"target{i}@example.com", password="one guess")
    r = login(client, email="target99@example.com", password="one guess")
    assert r.status_code == 429


def test_an_unknown_address_is_throttled_too(client):
    """Otherwise the cheapest attack is to spray addresses rather than
    passwords, and nothing counts it."""
    for _ in range(6):
        login(client, email="nobody@example.com", password="guessing")
    r = login(client, email="nobody@example.com", password="guessing")
    assert r.status_code == 429


# ══ verification ══════════════════════════════════════════════════════════

def test_registration_issues_a_verification_token(client, db):
    uid = register(client).json()["user_id"]
    row = token_for(db, uid, "verify")
    assert row is not None
    assert row.email == EMAIL
    assert row.consumed_at is None


def test_the_stored_token_is_a_hash_not_the_token(client, db, no_mail):
    """Same rule as a session token: a dumped table must not hand anyone a
    working credential, and a verification link IS one."""
    uid = register(client).json()["user_id"]
    link = no_mail[-1].link
    raw = link.split("token=")[1]
    row = token_for(db, uid, "verify")
    assert row.token_hash != raw
    assert row.token_hash == auth.hash_token(raw)


def test_verify_email_confirms_the_address(client, db, no_mail):
    register(client)
    raw = no_mail[-1].link.split("token=")[1]
    r = client.post("/api/auth/verify-email", json={"token": raw})
    assert r.status_code == 200
    assert r.json()["verified"] is True
    db.expire_all()
    assert db.exec(select(AuthIdentity)).one().email_verified is True


def test_a_verification_token_works_only_once(client, no_mail):
    register(client)
    raw = no_mail[-1].link.split("token=")[1]
    client.post("/api/auth/verify-email", json={"token": raw})
    r = client.post("/api/auth/verify-email", json={"token": raw})
    assert r.status_code == 400
    assert code(r) == "invalid_token"


def test_a_junk_token_is_refused(client):
    r = client.post("/api/auth/verify-email", json={"token": "made up"})
    assert r.status_code == 400


def test_a_reset_token_cannot_be_spent_as_a_verification(client, no_mail):
    """The purpose check. Without it the weaker flow mints credentials for the
    stronger one."""
    register(client)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    reset_raw = no_mail[-1].link.split("token=")[1]
    r = client.post("/api/auth/verify-email", json={"token": reset_raw})
    assert r.status_code == 400


def test_resending_kills_the_previous_token(client, no_mail):
    """Otherwise a year of resends is a pile of live credentials for one
    account, each as safe as the inbox it landed in."""
    register(client)
    first = no_mail[-1].link.split("token=")[1]
    client.post("/api/auth/verification/resend", json={"email": EMAIL})
    second = no_mail[-1].link.split("token=")[1]
    assert first != second
    assert client.post("/api/auth/verify-email", json={"token": first}).status_code == 400
    assert client.post("/api/auth/verify-email", json={"token": second}).status_code == 200


def test_resend_answers_the_same_for_an_unknown_address(client):
    known = client.post("/api/auth/verification/resend", json={"email": EMAIL})
    unknown = client.post("/api/auth/verification/resend",
                          json={"email": "nobody@example.com"})
    assert known.json() == unknown.json() == {"ok": True}


# ── the gate, when it is switched on ──────────────────────────────────────

def test_with_verification_required_registration_mints_no_session(client, verifying):
    r = register(client)
    assert r.status_code == 200
    assert r.json()["verification_required"] is True
    assert "token" not in r.json()


def test_with_verification_required_login_is_refused_until_confirmed(
        client, verifying, no_mail):
    register(client)
    signed_out(client)
    r = login(client)
    assert r.status_code == 403
    assert code(r) == "email_not_verified"

    raw = no_mail[-1].link.split("token=")[1]
    client.post("/api/auth/verify-email", json={"token": raw})
    signed_out(client)
    assert login(client).status_code == 200


def test_without_the_flag_login_works_unverified(client):
    """THE DEVELOPMENT PATH, and the reason the flag exists: there is no mail
    provider yet, so a required verification would mean nobody can ever sign
    in."""
    register(client)
    signed_out(client)
    r = login(client)
    assert r.status_code == 200
    assert r.json()["email_verified"] is False


# ══ password reset ════════════════════════════════════════════════════════

def test_forgot_password_answers_identically_for_a_stranger(client):
    """The membership test, closed. A list of who holds an account here is not
    a neutral disclosure for this audience."""
    register(client)
    known = client.post("/api/auth/forgot-password", json={"email": EMAIL})
    unknown = client.post("/api/auth/forgot-password",
                          json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json() == {"ok": True}


def test_reset_changes_the_password(client, no_mail):
    register(client)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    raw = no_mail[-1].link.split("token=")[1]

    new = "an entirely different phrase"
    r = client.post("/api/auth/reset-password",
                    json={"token": raw, "new_password": new})
    assert r.status_code == 200

    signed_out(client)
    assert login(client, password=PASSWORD).status_code == 401
    signed_out(client)
    assert login(client, password=new).status_code == 200


def test_reset_revokes_every_existing_session(client, db, no_mail):
    """THE WHOLE REASON A RESET IS WORTH DOING. If an attacker signed in
    yesterday, changing the password without revoking their session fixes the
    door and leaves them inside."""
    token = register(client).json()["token"]
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    raw = no_mail[-1].link.split("token=")[1]
    client.post("/api/auth/reset-password",
                json={"token": raw, "new_password": "an entirely different phrase"})

    signed_out(client)
    assert client.get("/api/auth/me",
                      headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert all(row.revoked_at is not None for row in db.exec(select(AuthSession)).all())


def test_a_reset_token_works_only_once(client, no_mail):
    register(client)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    raw = no_mail[-1].link.split("token=")[1]
    first = "an entirely different phrase"
    client.post("/api/auth/reset-password", json={"token": raw, "new_password": first})
    r = client.post("/api/auth/reset-password",
                    json={"token": raw, "new_password": "yet another phrase"})
    assert r.status_code == 400
    signed_out(client)
    assert login(client, password=first).status_code == 200


def test_reset_enforces_the_password_policy(client, no_mail):
    """Server-side, which is the only side that counts - a client that skipped
    its own check must not be able to set '123'."""
    register(client)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    raw = no_mail[-1].link.split("token=")[1]
    r = client.post("/api/auth/reset-password",
                    json={"token": raw, "new_password": "short"})
    assert r.status_code == 400
    assert code(r) == "weak_password"


def test_reset_confirms_the_address(client, db, no_mail):
    """Reaching a reset link required reading mail sent to that address, which
    is the same proof verification asks for."""
    register(client)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    raw = no_mail[-1].link.split("token=")[1]
    client.post("/api/auth/reset-password",
                json={"token": raw, "new_password": "an entirely different phrase"})
    db.expire_all()
    assert db.exec(select(AuthIdentity)).one().email_verified is True


def test_reset_lifts_the_account_lockout(client, no_mail):
    """Found by walking the flow by hand rather than by reasoning about it.

    Somebody who forgot their password has very likely just failed to sign in
    five times - that is what sent them to the reset in the first place. Before
    this, completing the reset correctly then left them refused for another
    fifteen minutes, which reads as the reset not having worked.
    """
    register(client)
    signed_out(client)
    for _ in range(6):
        login(client, password="wrong one")
    assert login(client).status_code == 429

    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    raw = no_mail[-1].link.split("token=")[1]
    new = "an entirely different phrase"
    client.post("/api/auth/reset-password", json={"token": raw, "new_password": new})

    signed_out(client)
    assert login(client, password=new).status_code == 200


def test_a_junk_reset_token_is_refused(client):
    r = client.post("/api/auth/reset-password",
                    json={"token": "made up", "new_password": "a fine passphrase"})
    assert r.status_code == 400
    assert code(r) == "invalid_token"


# ══ deletion ══════════════════════════════════════════════════════════════

def test_deleting_the_user_removes_the_identity_and_tokens(client, db, engine):
    """The hard-delete promise, extended to the new tables. A leftover identity
    row would hold UNIQUE(provider, subject) against somebody who no longer
    exists and lock that address out of signing up again; a leftover email
    token would be a live reset credential for a deleted account."""
    from tilawah.db import delete_user

    uid = register(client).json()["user_id"]
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    assert db.exec(select(EmailToken)).all()

    with Session(engine) as s:
        delete_user(s, uid)

    db.expire_all()
    assert db.exec(select(AuthIdentity)).all() == []
    assert db.exec(select(EmailToken)).all() == []
    # And the address is free again, which is the point of cascading.
    signed_out(client)
    assert register(client).status_code == 200
