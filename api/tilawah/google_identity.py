# -*- coding: utf-8 -*-
"""Verifying a Google ID token, and nothing else.

NO DATABASE, NO HTTP ROUTES, NO LINKING DECISIONS. This module answers exactly
one question - "which Google account does this token prove, if any" - so the
answer can be tested without a server and the linking rules can be tested
without a token.

── WHY THE CHECKS ARE REPEATED HERE ───────────────────────────────────────

google-auth already validates the signature, and `verify_oauth2_token` checks
issuer and expiry too. Every one of those is checked AGAIN below. That is not
distrust of the library, it is where the blast radius is: these claims decide
who the caller is, and the cost of re-asserting them is a few comparisons
against the cost of finding out later that a version bump quietly relaxed one.
The audience check in particular CANNOT be delegated, because a project has
several client ids and the library takes one.

── THE THREE RULES ────────────────────────────────────────────────────────

1. `sub` IS THE IDENTITY. Not email. An email address can be changed, reused
   after deletion, or - once Apple arrives - be a per-app relay that differs
   from the real one. Matching accounts on email is how you build an account
   takeover; `sub` is stable for the life of the Google account.

2. THE RAW TOKEN NEVER REACHES A LOG. Not on failure, not truncated. It is a
   bearer credential for as long as it is valid, and a log line is a place
   secrets go to be archived. Failures log a reason code and nothing else.

3. EVERY FAILURE LOOKS THE SAME TO THE CALLER. The reason code stays server
   side; the route answers one 401. "Expired" versus "wrong audience" tells an
   attacker which half of their guess was right.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

log = logging.getLogger(__name__)

# Google mints tokens under both spellings and has done for years.
ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})

# Tolerance for the two clocks disagreeing. Small: this is a laptop-to-Google
# skew allowance, not a grace period for expired credentials.
CLOCK_SKEW_SECONDS = 10


class GoogleAuthError(Exception):
    """Verification failed. `code` is for logs and tests, never for the client."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


@dataclass(frozen=True)
class GoogleClaims:
    """The parts of a verified token this application is allowed to care about."""
    subject: str                 # `sub` - THE identity key
    email: str | None            # informational only; never a lookup key
    email_verified: bool
    name: str | None
    nonce: str | None
    audience: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def token_fingerprint(raw: str) -> str:
    """A short non-secret handle for correlating log lines to one attempt.

    Hash, not a prefix. A prefix of a credential is part of a credential.
    """
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _decode(raw: str) -> dict:
    """Signature check against Google's published keys. Network call.

    audience=None ON PURPOSE - the library accepts a single audience and this
    server accepts a list, so the check is done in verify() instead. Skipping
    it here would be a hole if verify() did not do it; test_google_identity.py
    asserts that it does.

    This is the seam the tests replace: everything above it is our policy and
    runs offline.
    """
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    return google_id_token.verify_oauth2_token(
        raw, google_requests.Request(), audience=None,
        clock_skew_in_seconds=CLOCK_SKEW_SECONDS)


def verify(raw_token: str, *, audiences: list[str],
           expected_nonce: str | None = None) -> GoogleClaims:
    """Verify a Google ID token and return the claims worth trusting.

    Raises GoogleAuthError on anything at all. Callers must map every failure
    to one identical response.
    """
    if not raw_token or not isinstance(raw_token, str):
        raise GoogleAuthError("missing_token")
    if not audiences:
        # Refusing beats accepting everything if the allowlist is empty.
        raise GoogleAuthError("not_configured")

    try:
        payload = _decode(raw_token)
    except GoogleAuthError:
        raise
    except Exception as exc:
        # google-auth raises ValueError for a bad signature, a malformed token
        # and a failed certificate fetch alike. None of them are the caller's
        # business, and the exception text can quote the token.
        raise GoogleAuthError("bad_signature", type(exc).__name__) from None

    if not isinstance(payload, dict):
        raise GoogleAuthError("bad_payload")

    issuer = payload.get("iss")
    if issuer not in ISSUERS:
        raise GoogleAuthError("bad_issuer", str(issuer))

    audience = payload.get("aud")
    if not audience or audience not in audiences:
        # Do not log the value: an unexpected aud is somebody else's client id.
        raise GoogleAuthError("bad_audience")

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        raise GoogleAuthError("missing_exp")
    if exp + CLOCK_SKEW_SECONDS < _now().timestamp():
        raise GoogleAuthError("expired")

    iat = payload.get("iat")
    if isinstance(iat, (int, float)) and iat - CLOCK_SKEW_SECONDS > _now().timestamp():
        # Issued in the future: a wrong clock, or a forged claim set.
        raise GoogleAuthError("issued_in_future")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        # Without a stable subject there is no identity to link to, and falling
        # back to email here is exactly the mistake this module exists to avoid.
        raise GoogleAuthError("missing_subject")

    nonce = payload.get("nonce")
    if expected_nonce is not None and nonce != expected_nonce:
        raise GoogleAuthError("nonce_mismatch")

    email = payload.get("email")
    return GoogleClaims(
        subject=subject.strip(),
        email=email if isinstance(email, str) and email else None,
        email_verified=bool(payload.get("email_verified", False)),
        name=payload.get("name") if isinstance(payload.get("name"), str) else None,
        nonce=nonce if isinstance(nonce, str) else None,
        audience=audience,
    )
