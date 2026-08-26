# -*- coding: utf-8 -*-
"""Session tokens: minting, resolving, rotating, revoking.

NO HTTP IN THIS MODULE. It takes a database session and strings, and it is
tested without a client. The FastAPI wiring lives in api/deps.py and the
endpoints in api/auth_routes.py.

── THE THREE RULES ────────────────────────────────────────────────────────

1. THE RAW TOKEN IS SHOWN TO THE CLIENT ONCE AND NEVER WRITTEN DOWN. Only its
   sha256 reaches the database. A dumped `auth_session` table must not hand
   anyone a working credential - it should be as useless as a table of
   password hashes, and for the same reason.

2. A SESSION IS A ROW, SO IT CAN BE KILLED. That is the whole argument for
   opaque tokens over a JWT here. This app promises that revoking consent
   really destroys the learner's data; a token that stays valid because it is
   signed rather than stored would make that promise false.

3. NEVER LOG THE TOKEN. Not at debug, not in a traceback, not "just the first
   few characters" - a prefix of a secret is still part of a secret. Where a
   log line needs to identify a session, it logs a prefix of the HASH, which
   is not a credential. See _tag().

── ON EXPIRY AND CLOCKS ───────────────────────────────────────────────────

sqlite has no timezone-aware datetime, so what goes in as aware UTC comes back
naive. Comparing the two raises TypeError, and it would do so at the exact
moment a session is checked - i.e. on every authenticated request. _utc()
normalises both sides. Do not remove it because "the model already uses UTC";
the model does, the driver does not.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from .config import settings
from .db.models import AuthSession, EmailToken, OAuthNonce, User

log = logging.getLogger(__name__)

# 32 bytes = 256 bits of entropy, url-safe base64 (43 chars). Well past the
# point where guessing is the attack anyone would choose.
TOKEN_BYTES = 32


def new_token() -> str:
    """A fresh opaque token. Never stored; returned to the caller once."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(raw: str) -> str:
    """sha256 hex of the token, which is the only form the database sees.

    A plain hash rather than a slow KDF ON PURPOSE. bcrypt/argon2 exist to make
    guessing a LOW-ENTROPY human password expensive. This input is 256 random
    bits - there is nothing to guess - and a slow hash would only add latency
    to every single authenticated request. The hash is here to make a leaked
    database useless, and sha256 does that.
    """
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _tag(token_hash: str) -> str:
    """A short, non-secret handle for logs. NEVER pass a raw token to this."""
    return token_hash[:12]


def _utc(dt: datetime | None) -> datetime | None:
    """Read a datetime back as aware UTC whether or not the driver kept it."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def now() -> datetime:
    """Aware UTC. A seam so tests can freeze time without patching datetime."""
    return datetime.now(timezone.utc)


def create_session(db: Session, user_id: str, *, user_agent: str = "",
                   ttl_days: int | None = None) -> tuple[str, AuthSession]:
    """Mint a session for a user. Returns (raw_token, row).

    THE RAW TOKEN IN THE FIRST SLOT IS THE ONLY COPY THAT WILL EVER EXIST.
    Hand it to the client and drop it; it cannot be recovered from the row.
    """
    raw = new_token()
    ttl = timedelta(days=ttl_days if ttl_days is not None else settings.session_ttl_days)
    row = AuthSession(
        token_hash=hash_token(raw),
        user_id=user_id,
        expires_at=now() + ttl,
        user_agent=(user_agent or "")[:200],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log.info("session created id=%s user=%s hash=%s", row.id, user_id, _tag(row.token_hash))
    return raw, row


def is_live(row: AuthSession, at: datetime | None = None) -> bool:
    """Not revoked and not expired. The single definition of 'usable'."""
    at = at or now()
    if row.revoked_at is not None:
        return False
    expires = _utc(row.expires_at)
    return expires is not None and expires > at


def resolve(db: Session, raw_token: str) -> tuple[AuthSession, User] | None:
    """The token -> (session, user) lookup that guards every request.

    Returns None for every failure - unknown, revoked, expired, or pointing at
    a user who no longer exists - and the caller turns that into one identical
    401. The distinction is deliberately not available to the client: telling
    an attacker that a token is real but expired is telling them the token is
    real.

    The user check is not paranoia. ON DELETE CASCADE removes sessions with
    their user, but that clause only fires when sqlite is enforcing foreign
    keys, and a row written by some other tool with the pragma off would
    otherwise authenticate as a ghost.
    """
    if not raw_token:
        return None

    row = db.exec(
        select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token))
    ).first()
    if row is None or not is_live(row):
        return None

    user = db.get(User, row.user_id)
    if user is None:
        log.warning("session %s references missing user %s", _tag(row.token_hash), row.user_id)
        return None

    _touch(db, row)
    return row, user


# How stale last_used_at is allowed to get. Updating it on every request would
# put a WRITE on the hot path of every authenticated GET, and sqlite serialises
# writers - this codebase already carries a lock in routes.py because two
# concurrent consent writes killed the connection. last_used_at exists to answer
# "when was this session last seen", and a minute's resolution answers that
# just as well as a millisecond's.
TOUCH_INTERVAL = timedelta(minutes=1)


def _touch(db: Session, row: AuthSession) -> None:
    at = now()
    last = _utc(row.last_used_at)
    if last is not None and at - last < TOUCH_INTERVAL:
        return
    row.last_used_at = at
    db.add(row)
    db.commit()


def revoke(db: Session, row: AuthSession) -> None:
    """Kill one session. Idempotent - revoking twice keeps the first time."""
    if row.revoked_at is None:
        row.revoked_at = now()
        db.add(row)
        db.commit()
        log.info("session revoked id=%s hash=%s", row.id, _tag(row.token_hash))


def revoke_all_for_user(db: Session, user_id: str) -> int:
    """Kill every live session a user holds. Returns how many were killed.

    Wanted whenever the account's security state changes - a future unlink, a
    password-equivalent event, or an explicit 'sign out everywhere'.
    """
    rows = db.exec(
        select(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))  # type: ignore[union-attr]
    ).all()
    for row in rows:
        row.revoked_at = now()
        db.add(row)
    if rows:
        db.commit()
        log.info("revoked %d session(s) for user %s", len(rows), user_id)
    return len(rows)


def rotate(db: Session, row: AuthSession, *, user_agent: str = "") -> tuple[str, AuthSession]:
    """Issue a successor and revoke the old one, atomically enough.

    ROTATION IS THE POINT OF REFRESH. Handing back the same token would make
    the endpoint a no-op that only moved the expiry; replacing it limits how
    long a token that leaked from a log or a backup stays useful.
    """
    fresh_raw, fresh = create_session(db, row.user_id,
                                      user_agent=user_agent or row.user_agent)
    revoke(db, row)
    return fresh_raw, fresh


# ── login nonces ──────────────────────────────────────────────────────────

def issue_nonce(db: Session, *, ttl_seconds: int) -> str:
    """Hand out a single-use login nonce. Only its hash is kept."""
    raw = new_token()
    db.add(OAuthNonce(nonce_hash=hash_token(raw),
                      expires_at=now() + timedelta(seconds=ttl_seconds)))
    db.commit()
    return raw


def consume_nonce(db: Session, raw: str | None) -> bool:
    """Spend a nonce. True only if it was ours, unspent, and unexpired.

    CONSUMED, NOT DELETED, and consumed BEFORE the caller acts on the token -
    so a replay of the same credential finds the row already spent rather than
    racing a delete. An expired or missing nonce and a replayed one are all
    False here; the route turns every one of them into the same refusal.
    """
    if not raw:
        return False
    row = db.exec(
        select(OAuthNonce).where(OAuthNonce.nonce_hash == hash_token(raw))
    ).first()
    if row is None or row.consumed_at is not None:
        return False
    expires = _utc(row.expires_at)
    if expires is None or expires <= now():
        return False
    row.consumed_at = now()
    db.add(row)
    db.commit()
    return True


def purge_expired_nonces(db: Session, *, before: datetime | None = None) -> int:
    """Housekeeping. A spent or expired nonce authorises nothing either way."""
    cutoff = before or now()
    rows = db.exec(
        select(OAuthNonce).where(OAuthNonce.expires_at <= cutoff)
    ).all()
    for row in rows:
        db.delete(row)
    if rows:
        db.commit()
    return len(rows)


# ── email tokens: verification and password reset ─────────────────────────
#
# SAME THREE RULES AS A SESSION TOKEN, and for a sharper reason. A reset token
# is not a convenience - it is the complete proof required to take an account
# over. It is minted from the same CSPRNG, only its hash is stored, and it is
# never logged.

def issue_email_token(db: Session, user_id: str, *, purpose: str, email: str,
                      ttl_seconds: int) -> str:
    """Mint a one-shot token for `purpose`. Returns the raw value ONCE.

    ANY UNSPENT TOKEN OF THE SAME PURPOSE IS KILLED FIRST. Without that, every
    "resend" leaves its predecessor live, and a year of forgotten resets is a
    pile of working credentials for one account, each one only as safe as the
    inbox it landed in. The newest link is the only one that works, which is
    also what a learner expects when they click "send it again".
    """
    for row in db.exec(
        select(EmailToken).where(EmailToken.user_id == user_id,
                                 EmailToken.purpose == purpose,
                                 EmailToken.consumed_at.is_(None))  # type: ignore[union-attr]
    ).all():
        row.consumed_at = now()
        db.add(row)

    raw = new_token()
    db.add(EmailToken(token_hash=hash_token(raw), user_id=user_id,
                      purpose=purpose, email=email,
                      expires_at=now() + timedelta(seconds=ttl_seconds)))
    db.commit()
    log.info("email token issued user=%s purpose=%s", user_id, purpose)
    return raw


def consume_email_token(db: Session, raw: str | None, *,
                        purpose: str) -> EmailToken | None:
    """Spend a token. Returns the row, or None for every kind of no.

    THE PURPOSE IS PART OF THE LOOKUP, not a check made afterwards on a row
    already marked spent. A verification token presented to the reset endpoint
    must not be consumed by it: consuming first and validating second would
    burn the learner's real token on an attacker's probe.

    None covers unknown, already spent, expired, wrong purpose, and pointing at
    a user who no longer exists - and the caller turns all of them into one
    identical refusal, exactly as resolve() does.
    """
    if not raw:
        return None
    row = db.exec(
        select(EmailToken).where(EmailToken.token_hash == hash_token(raw))
    ).first()
    if row is None or row.purpose != purpose or row.consumed_at is not None:
        return None
    expires = _utc(row.expires_at)
    if expires is None or expires <= now():
        return None
    if db.get(User, row.user_id) is None:
        log.warning("email token %s references missing user %s",
                    _tag(row.token_hash), row.user_id)
        return None

    row.consumed_at = now()
    db.add(row)
    db.commit()
    return row


def purge_expired_email_tokens(db: Session, *, before: datetime | None = None) -> int:
    """Housekeeping. A spent or expired token authorises nothing either way."""
    cutoff = before or now()
    rows = db.exec(
        select(EmailToken).where(EmailToken.expires_at <= cutoff)
    ).all()
    for row in rows:
        db.delete(row)
    if rows:
        db.commit()
    return len(rows)


def purge_expired(db: Session, *, before: datetime | None = None) -> int:
    """Delete sessions that expired before `before` (default: now).

    Housekeeping, not security - an expired row cannot authenticate anything
    whether or not it is still on disk. Nothing calls this yet; it is here so
    the table has a defined way not to grow forever.
    """
    cutoff = before or now()
    rows = db.exec(
        select(AuthSession).where(AuthSession.expires_at <= cutoff)
    ).all()
    for row in rows:
        db.delete(row)
    if rows:
        db.commit()
    return len(rows)
