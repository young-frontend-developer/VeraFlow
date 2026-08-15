# -*- coding: utf-8 -*-
"""Password hashing and the policy a password has to clear.

NO HTTP AND NO DATABASE IN THIS MODULE, the same rule auth.py follows. It takes
strings and returns strings or a list of reasons, and it is tested without a
client.

── WHY ARGON2id AND NOT BCRYPT ────────────────────────────────────────────

bcrypt SILENTLY TRUNCATES AT 72 BYTES. A learner who types a long passphrase
gets a password that is not the one they typed, and - worse - any other string
sharing its first 72 bytes opens the account. There is no error; the library
just stops reading. Argon2 has no such limit.

The second reason is the one the RFC cares about: bcrypt is cheap in MEMORY,
and memory is the resource an attacker with a rack of GPUs does not have a lot
of per core. Argon2id is deliberately memory-hard, so the same hardware that
makes bcrypt cracking fast buys much less here.

── WHY THE PARAMETERS ARE PINNED HERE ─────────────────────────────────────

The library's defaults move between releases. That is fine for a new hash and
NOT fine for verification, because an old hash must keep verifying with the
parameters it was written with - which is why they travel inside the encoded
hash string, and why `verify()` never passes its own parameters in. What the
pins below control is only what a NEW hash costs. They follow the OWASP
minimum (19 MiB, t=2, p=1); raise them on a box with headroom and old hashes
keep working, being rehashed on the next successful login.

── WHY THE SESSION TOKEN DOES NOT COME THROUGH HERE ───────────────────────

auth.hash_token() is a bare sha256 and that is correct: it hashes 256 random
bits, where there is nothing to guess and a slow KDF would only add latency to
every authenticated request. This module hashes what a human chose, which is
the opposite problem. Do not unify them.
"""
from __future__ import annotations

import re
import unicodedata

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# OWASP's argon2id floor. `hash_len` and `salt_len` are the library defaults,
# named explicitly so a library change cannot move them silently.
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19 * 1024,   # KiB, i.e. 19 MiB
    parallelism=1,
    hash_len=32,
    salt_len=16,
)

# THE FLOOR, NOT THE ADVICE. NIST SP 800-63B asks for 8 and drops composition
# rules (no "one capital, one digit") because they push people towards
# Password1! and nothing else. Ten is a deliberate step above the floor for an
# account that is created once and kept for years; the only other rules below
# are a length CEILING and a blocklist, both of which have a real reason.
MIN_LENGTH = 10

# A CEILING EXISTS BECAUSE THE HASH IS DELIBERATELY EXPENSIVE. Without it a
# megabyte of "password" in the body is a megabyte argon2 must chew through
# before the request can be refused - a denial of service handed over in the
# one place that is guaranteed to be unauthenticated. 200 is far past any real
# passphrase.
MAX_LENGTH = 200

# The handful of strings that show up at the top of every breach corpus. NOT a
# real blocklist - a serious one is tens of thousands of entries and belongs in
# a file - but these are the ones a bored tester types, and letting them
# through makes the minimum length look like the whole policy.
_COMMON = {
    "password", "password1", "password123", "12345678", "123456789",
    "1234567890", "qwertyuiop", "qwerty123", "iloveyou", "letmein",
    "welcome1", "admin123", "adminadmin", "changeme", "passw0rd",
    "parol123", "parolparol", "123456789a",
}

# Deliberately permissive, and it is not RFC 5322. Anything stricter rejects
# real addresses (they are stranger than people think) while proving nothing:
# the only real check on an address is sending mail to it and seeing whether
# anybody answers, which is exactly what verification is for. This catches
# typos and nothing else.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")

# The longest address the standard permits.
MAX_EMAIL_LENGTH = 254


def normalise_email(raw: str | None) -> str:
    """Fold an address to the ONE form that is stored and looked up.

    Trimmed, NFKC-normalised, and lowercased. Lowercasing the local part is
    technically a liberty - the standard says it may be case-sensitive - but
    every mail provider a learner will actually use treats it as insensitive,
    and not folding it means Ali@ and ali@ are two accounts that both look
    right and only one of which has their history in it.

    NFKC because a full-width or otherwise decomposed address must not be able
    to sneak past the UNIQUE(provider, subject) row that already exists for the
    plain one.
    """
    return unicodedata.normalize("NFKC", (raw or "").strip()).lower()


def valid_email(address: str) -> bool:
    """Shape only. Whether anybody reads that inbox is verification's job."""
    return bool(address) and len(address) <= MAX_EMAIL_LENGTH \
        and _EMAIL_RE.match(address) is not None


def password_problems(password: str, *, email: str = "") -> list[str]:
    """Every reason this password is refused, as stable machine codes.

    A LIST AND NOT A BOOLEAN, so the client can say what is actually wrong
    instead of "invalid password" - and CODES rather than sentences, because
    the sentence has to arrive in the learner's own language and the server
    does not pick that. The client maps these; see web/src/lib/i18n.ts.

    Returning EVERY problem rather than the first also means a learner is not
    walked through a one-at-a-time interrogation of their own password.
    """
    problems: list[str] = []
    pw = password or ""

    if len(pw) < MIN_LENGTH:
        problems.append("too_short")
    if len(pw) > MAX_LENGTH:
        problems.append("too_long")
    # Whitespace-only, and the check is deliberately not "must contain a
    # letter": a passphrase of Arabic, Cyrillic or emoji is a fine password.
    if pw and not pw.strip():
        problems.append("blank")
    if pw.lower().strip() in _COMMON:
        problems.append("too_common")

    local = normalise_email(email).split("@")[0]
    # The address is public knowledge and is the first thing anyone guessing
    # this account already has in hand.
    if local and len(local) >= 3 and local in pw.lower():
        problems.append("looks_like_email")

    return problems


def hash_password(password: str) -> str:
    """The encoded argon2id hash. THE ONLY FORM THAT MAY REACH THE DATABASE.

    The returned string carries its own algorithm, parameters and salt, which
    is what lets needs_rehash() upgrade an old hash later without a migration.
    """
    return _hasher.hash(password)


def verify_password(stored_hash: str | None, password: str) -> bool:
    """Does this password match that hash? False for every kind of no.

    NEVER RAISES, and never distinguishes "wrong password" from "there is no
    hash here" or "that hash is corrupt". The caller turns all of them into one
    identical refusal, and a caller that had three exceptions to catch would
    eventually let one of them turn into a different response - which is how a
    login endpoint starts telling strangers which addresses are registered.
    """
    if not stored_hash or not password:
        return False
    try:
        return _hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """True when this hash predates the current parameters.

    Called after a SUCCESSFUL verification, which is the only moment the
    plaintext is in hand and therefore the only moment a stronger hash can be
    written. See the login route.
    """
    try:
        return _hasher.check_needs_rehash(stored_hash)
    except (InvalidHashError, ValueError):
        return False


def dummy_verify() -> None:
    """Burn the cost of a real verification against a throwaway hash.

    THIS IS A TIMING DEFENCE AND IT IS NOT DECORATION. Login must take about
    the same time whether or not the address exists: returning early on an
    unknown address makes that case measurably faster than a wrong password,
    and the difference is a free, unlimited check on whether any given person
    has an account here. The identical error message means nothing if the
    clock answers the question anyway.
    """
    verify_password(_DUMMY_HASH, "not the password")


# Computed once at import so the cost lands at boot rather than inside the
# first login that needs it.
_DUMMY_HASH = hash_password("a password nobody has, used only for timing")
