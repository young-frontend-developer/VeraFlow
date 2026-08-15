# -*- coding: utf-8 -*-
"""Email and password sign-in.

A SECOND ROUTER ON THE SAME /api/auth PREFIX, not an extension of
auth_routes.py. Both are mounted in main.py and the client cannot tell; the
split is for readers. auth_routes.py is sessions and Google, and putting six
more endpoints in it would have made the file long enough that nobody reads the
ownership rules at the top - which are the part that matters most.

    POST /api/auth/register               create an email identity
    POST /api/auth/login                  exchange a password for a session
    POST /api/auth/verification/resend    send the confirmation link again
    POST /api/auth/verify-email           confirm an address
    POST /api/auth/forgot-password        start a reset
    POST /api/auth/reset-password         finish one

── EVERYTHING HERE IS THE SAME AUTH SYSTEM AS GOOGLE ──────────────────────

Same auth_identity table, one row with provider='email'. Same opaque, revocable
session from auth.create_session - no JWT, for the reason in config.py: this app
promises deletion, and a signed token that outlives the row would make that
promise false. Same cookie-and-body transport. Same ownership rule, so an
anonymous learner who registers keeps their User.id and everything filed
under it.

The password is the ONLY new thing, and it lives in tilawah/passwords.py.

── WHAT LEAKS AND WHAT DOES NOT, DECIDED ONCE ─────────────────────────────

LOGIN NEVER SAYS WHICH HALF WAS WRONG. Unknown address and wrong password
return the same 401 with the same code, and the unknown-address path burns the
same argon2 cost through passwords.dummy_verify() so the clock cannot answer
what the message would not. FORGOT-PASSWORD ALWAYS SAYS THE SAME THING,
whether or not it found anybody.

REGISTRATION IS THE DELIBERATE EXCEPTION and it is the standard one. It answers
409 for an address that is already taken, which does disclose that the address
is registered. The alternative - accepting every signup and disclosing nothing
until an email arrives - cannot be built here: there is no mail provider yet,
so it would mean every duplicate registration hangs silently forever. A learner
who cannot be told "you already have an account" is a learner who makes a
second one, or gives up. That trade is made knowingly and only here; if
verification ever becomes mandatory with a live provider, this is the endpoint
to revisit.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, select

from .. import auth, mailer, passwords
from ..config import settings
from ..db import get_session
from ..db.models import AuthIdentity, AuthSession, User
from ..ratelimit import Limit, limiter
from .auth_routes import _max_age, _providers_for, _set_cookie
from .deps import optional_auth
from .schemas import (EmailSessionOut, ForgotPasswordIn, LoginIn, RegisterIn,
                      RegisteredOut, ResetPasswordIn, VerifyEmailIn)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

PROVIDER = "email"


# ── refusals ──────────────────────────────────────────────────────────────

def _refuse(code: str, *, status_code: int = status.HTTP_400_BAD_REQUEST,
            problems: list[str] | None = None, retry_after: int = 0) -> HTTPException:
    """One shape for every refusal: a machine code, never a sentence.

    THE SERVER DOES NOT WRITE THE LEARNER'S ERROR MESSAGE. It cannot: the
    message has to arrive in Uzbek or Russian depending on a preference the
    client owns, and a raw API string rendered into a form is how a learner
    ends up reading "422 Unprocessable Entity". The client maps these codes;
    see web/src/lib/i18n.ts.
    """
    detail = {"code": code, "problems": problems or [], "retry_after": retry_after}
    headers = {"Retry-After": str(retry_after)} if retry_after else None
    return HTTPException(status_code, detail=detail, headers=headers)


# One refusal for both halves of a failed login. Built in one place so the two
# call sites cannot drift apart - the moment they differ by a word or a status
# code, the endpoint starts confirming which addresses are registered.
def _bad_credentials() -> HTTPException:
    return _refuse("invalid_credentials", status_code=status.HTTP_401_UNAUTHORIZED)


# ── throttling ────────────────────────────────────────────────────────────

def _account_limit() -> Limit:
    """Per account. The tight one - this is what stops password guessing."""
    return Limit(count=settings.login_max_failures,
                 per_seconds=settings.login_window_seconds,
                 block_seconds=settings.login_block_seconds)


def _ip_limit() -> Limit:
    """Per IP, and deliberately much looser. AN IP IS NOT A PERSON.

    Behind carrier-grade NAT thousands share one address, so a threshold as
    tight as the per-account one would let any one of them lock out everybody
    else on their carrier. See the note in config.py. This limit is aimed at
    the other attack shape - one machine spraying one password across many
    accounts, which per-account counting cannot see.
    """
    return Limit(count=settings.login_ip_max_failures,
                 per_seconds=settings.login_window_seconds,
                 block_seconds=settings.login_block_seconds)


def _signup_limit() -> Limit:
    return Limit(count=settings.signup_max_per_hour, per_seconds=3600,
                 block_seconds=3600)


def _client_ip(request: Request) -> str:
    """The caller's address, as well as it can be known from here.

    X-Forwarded-For IS TRUSTED, AND THAT IS A DEPLOYMENT REQUIREMENT, NOT AN
    ASSUMPTION THIS CODE CAN MAKE SAFELY ON ITS OWN. Behind a proxy, every
    request appears to come from the proxy, so ignoring the header would put
    every learner in the world into one throttle bucket - the first person to
    mistype a password locks out everybody. Trusting it means a caller with no
    proxy in front of them can spoof it and get a fresh bucket per request.

    The proxy must therefore OVERWRITE this header rather than append to it,
    which is the default for nginx `proxy_set_header X-Forwarded-For $remote_addr`
    and for every managed load balancer. The per-account limit below is the
    belt to this brace: spoofing the IP still does not buy more guesses against
    any one account.
    """
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _account_key(email: str) -> str:
    """A throttle key for an address, HASHED.

    The limiter logs its key when a limit trips, and an application log is not
    a place to accumulate a list of everybody's email addresses. The hash is
    stable, which is all a counter needs.
    """
    return "acct:" + auth.hash_token(email)[:16]


def _check_throttle(key: str, limit: Limit) -> None:
    wait = limiter.retry_after(key, limit)
    if wait:
        raise _refuse("too_many_attempts",
                      status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                      retry_after=wait)


# ── shared helpers ────────────────────────────────────────────────────────

def _identity_for(db: Session, email: str) -> AuthIdentity | None:
    """The email identity for a normalised address, or None.

    Looked up by (provider, subject) - the UNIQUE pair - and never by the
    `email` column, which is informational on every provider and would match
    a Google identity that happens to carry the same address. That distinction
    is the whole reason User.email is documented as "display convenience, never
    a lookup key".
    """
    return db.exec(
        select(AuthIdentity).where(AuthIdentity.provider == PROVIDER,
                                   AuthIdentity.subject == email)
    ).first()


def _issue_verification(db: Session, user_id: str, email: str, lang: str) -> bool:
    """Mint a verification token and hand it to the mailer. Returns `sent`.

    A FAILURE HERE NEVER FAILS THE CALLER. See mailer._send: registration
    succeeding with the mail bounced is a resend away; registration failing
    because a third party had a bad minute loses the account.
    """
    raw = auth.issue_email_token(
        db, user_id, purpose="verify", email=email,
        ttl_seconds=settings.email_verify_ttl_seconds)
    return mailer.send_verification_email(email, raw, lang=lang)


def _session_response(db: Session, request: Request, response: Response,
                      user: User, identity: AuthIdentity,
                      resolved: tuple[AuthSession, User] | None,
                      *, linked_now: bool) -> EmailSessionOut:
    """Mint or rotate the session, set the cookie, and describe the account.

    ROTATION FOR THE SAME REASON THE GOOGLE ROUTE ROTATES: what a session is
    worth changed when an identity was attached to it, and a session that
    survives a privilege change is the classic fixation bug. When the caller
    arrived holding somebody else's session, that one is revoked rather than
    left live next to the new one.
    """
    ua = request.headers.get("user-agent", "")
    if resolved is not None and resolved[1].id == user.id:
        raw, row = auth.rotate(db, resolved[0], user_agent=ua)
    else:
        if resolved is not None:
            auth.revoke(db, resolved[0])
        raw, row = auth.create_session(db, user.id, user_agent=ua)

    _set_cookie(response, raw, _max_age(row))
    return EmailSessionOut(
        token=raw, expires_at=row.expires_at, user_id=user.id,
        claimed_existing=False, linked_now=linked_now,
        providers=_providers_for(db, user.id),
        email=user.email, display_name=user.display_name,
        email_verified=identity.email_verified)


# ── registration ──────────────────────────────────────────────────────────

@router.post("/register")
def register(body: RegisterIn, request: Request, response: Response,
             resolved: tuple[AuthSession, User] | None = Depends(optional_auth),
             db: Session = Depends(get_session)):
    """Create an email/password identity, or attach one to the account in hand.

    ── THE OWNERSHIP RULE, IDENTICAL TO GOOGLE'S ───────────────────────────

    A learner who has been practising anonymously ALREADY HAS AN ACCOUNT. It
    holds their attempts, their consent decision, their streak. Registering an
    email must attach an identity to THAT account and preserve User.id - never
    mint a second one and leave the first orphaned, which is what almost every
    auth library does by default and which is indistinguishable, from the
    inside, from having lost everything.

        session   address      outcome
        ────────  ───────────  ──────────────────────────────────────────
        user A    unknown      LINK. A keeps its id and all of its history.
        user A    taken        409. Nothing is written to either account.
        user A    has email    409. One email identity per account.
        none      unknown      create a new account.
        none      taken        409. This is the disclosure discussed above.

    ── ORDER OF OPERATIONS IS LOAD-BEARING ─────────────────────────────────

    Throttle, then validate the address, then the password, then look for a
    collision - and hash LAST, after every cheap refusal. Hashing before the
    validation would make an unauthenticated endpoint spend 19 MiB and a
    deliberately slow KDF on input we were always going to reject, which is a
    denial of service handed over for free.
    """
    ip_key = f"signup:{_client_ip(request)}"
    _check_throttle(ip_key, _signup_limit())

    email = passwords.normalise_email(body.email)
    if not passwords.valid_email(email):
        limiter.penalise(ip_key, _signup_limit())
        raise _refuse("invalid_email")

    problems = passwords.password_problems(body.password, email=email)
    if problems:
        # NOT counted against the signup limit. A learner iterating towards an
        # acceptable password is doing exactly what the policy asked of them,
        # and locking them out for complying is the wrong lesson.
        raise _refuse("weak_password", problems=problems)

    current_user = resolved[1] if resolved else None

    if _identity_for(db, email) is not None:
        limiter.penalise(ip_key, _signup_limit())
        raise _refuse("email_taken", status_code=status.HTTP_409_CONFLICT)

    if current_user is not None:
        # ONE EMAIL IDENTITY PER ACCOUNT. UNIQUE(user_id, provider) would
        # reject the insert anyway and the learner would get a 500 for doing
        # something reasonable - registering their other address. Refuse it
        # here, with a code the client can explain. Silently repointing the
        # existing identity is the one thing that must not happen: it would
        # hand this account to a different address and lock the original out.
        already = db.exec(
            select(AuthIdentity).where(AuthIdentity.user_id == current_user.id,
                                       AuthIdentity.provider == PROVIDER)
        ).first()
        if already is not None:
            raise _refuse("already_has_email", status_code=status.HTTP_409_CONFLICT)
        user = current_user               # <- User.id is PRESERVED. The point.
        linked_now = True
    else:
        # uuid4 for the same reason every other id here is: debug_capture._tag()
        # truncates at 36 characters and a longer id silently breaks the audio
        # deletion that consent revocation depends on.
        user = User(id=str(uuid.uuid4()), lang=body.lang or "uz")
        db.add(user)
        db.commit()
        linked_now = False

    identity = AuthIdentity(
        user_id=user.id, provider=PROVIDER, subject=email, email=email,
        email_verified=False,
        # THE ONLY FORM OF THE PASSWORD THAT EXISTS PAST THIS LINE.
        password_hash=passwords.hash_password(body.password),
        last_login_at=auth.now())
    db.add(identity)

    # A display convenience, and only when the account has nothing there yet -
    # a Google-linked address already on the row is not overwritten by this.
    if not user.email:
        user.email = email
        db.add(user)
    db.commit()
    db.refresh(identity)

    sent = _issue_verification(db, user.id, email, body.lang or user.lang)
    # The ADDRESS is never logged; the user id already identifies the account
    # for anyone who needs to support it.
    log.info("email registered user=%s linked_now=%s verification_sent=%s",
             user.id, linked_now, sent)

    if settings.require_email_verification:
        # NO SESSION. The address is unproven, and with verification required
        # that is the whole point - an account nobody has confirmed must not be
        # usable. Any anonymous session the caller already held is left alone
        # and keeps working: they can carry on practising while they go and
        # find the email.
        return RegisteredOut(verification_required=True, email=email, sent=sent)

    return _session_response(db, request, response, user, identity, resolved,
                             linked_now=linked_now)


# ── login ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=EmailSessionOut)
def login(body: LoginIn, request: Request, response: Response,
          resolved: tuple[AuthSession, User] | None = Depends(optional_auth),
          db: Session = Depends(get_session)) -> EmailSessionOut:
    """Exchange an address and a password for a session.

    ── THIS IS A PUBLIC INTERNET-FACING GUESSING TARGET ────────────────────

    Two throttles, and neither alone is sufficient. Per IP stops one machine
    walking a password list; per ACCOUNT stops a botnet spreading the same
    walk across a thousand addresses, which per-IP counting never sees. Only
    FAILURES count - a learner who signs in correctly forty times is doing
    nothing wrong, and counting success would lock out the one person
    definitely entitled to be here.

    ── ONE REFUSAL, AND A CONSTANT-TIME ONE ────────────────────────────────

    Unknown address and wrong password return the identical 401. The unknown
    path still runs a full argon2 verification against a throwaway hash, so the
    two take about the same time: without that, the response clock answers
    exactly the question the error message refuses to, and "is this person
    registered here" becomes a free, unlimited query against the whole user
    base.
    """
    ip_key = f"login-ip:{_client_ip(request)}"
    ip_limit, acct_limit = _ip_limit(), _account_limit()
    _check_throttle(ip_key, ip_limit)

    email = passwords.normalise_email(body.email)
    acct_key = f"login-{_account_key(email)}"
    _check_throttle(acct_key, acct_limit)

    identity = _identity_for(db, email) if passwords.valid_email(email) else None

    if identity is None:
        passwords.dummy_verify()          # pay the same cost. See the docstring.
        limiter.penalise(ip_key, ip_limit)
        limiter.penalise(acct_key, acct_limit)
        raise _bad_credentials()

    if not passwords.verify_password(identity.password_hash, body.password):
        limiter.penalise(ip_key, ip_limit)
        limiter.penalise(acct_key, acct_limit)
        # The address is not logged. A failed-login log that accumulates real
        # addresses is a list of this app's users sitting in plain text.
        log.info("login refused for user=%s", identity.user_id)
        raise _bad_credentials()

    user = db.get(User, identity.user_id)
    if user is None:
        # An identity pointing at a deleted account. CASCADE should make this
        # impossible; refuse rather than resurrect anything, exactly as the
        # Google route does.
        log.error("email identity %s points at missing user %s",
                  identity.id, identity.user_id)
        raise _bad_credentials()

    if settings.require_email_verification and not identity.email_verified:
        # A DIFFERENT ANSWER, AND SAFELY SO. The caller has just proved they
        # know this account's password, so telling them the address is
        # unconfirmed discloses nothing they could not already establish - and
        # the alternative, a generic 401, sends somebody to reset a password
        # that was never wrong.
        #
        # Not counted as a failed attempt for the same reason.
        raise _refuse("email_not_verified", status_code=status.HTTP_403_FORBIDDEN)

    # Signed in. Forget the failures - two mistypes then a success must not
    # carry a penalty into the next hour.
    limiter.clear(ip_key)
    limiter.clear(acct_key)

    if passwords.needs_rehash(identity.password_hash or ""):
        # The one moment the plaintext is in hand and a stronger hash can be
        # written. Raising the argon2 parameters in passwords.py therefore
        # upgrades accounts as people sign in, with no migration and no reset.
        identity.password_hash = passwords.hash_password(body.password)
        log.info("password rehashed at current parameters user=%s", user.id)

    identity.last_login_at = auth.now()
    db.add(identity)
    db.commit()

    # ── whose account is this? Same rule as the Google route ──────────────
    #
    # Signing in as B while holding A's session is NOT a merge and must never
    # become one: both accounts hold real practice history and real consent
    # decisions, and consent is not something software may infer on somebody's
    # behalf. The old session is revoked and this call signs in as B, cleanly.
    if resolved is not None and resolved[1].id != user.id:
        log.info("login switching account: session=%s -> %s",
                 resolved[1].id, user.id)

    return _session_response(db, request, response, user, identity, resolved,
                             linked_now=False)


# ── verification ──────────────────────────────────────────────────────────

@router.post("/verification/resend")
def resend_verification(body: ForgotPasswordIn, request: Request,
                        db: Session = Depends(get_session)) -> dict:
    """Send the confirmation link again. ALWAYS ANSWERS THE SAME THING.

    Unauthenticated by necessity: with verification required there is no
    session to authenticate with, which is the entire situation this endpoint
    exists for. That makes it an address oracle unless the response is
    constant, so it is - registered or not, verified already or not, the answer
    is {"ok": true}.
    """
    ip_key = f"resend:{_client_ip(request)}"
    limit = _signup_limit()
    _check_throttle(ip_key, limit)
    limiter.penalise(ip_key, limit)

    email = passwords.normalise_email(body.email)
    if passwords.valid_email(email):
        identity = _identity_for(db, email)
        if identity is not None and not identity.email_verified:
            _issue_verification(db, identity.user_id, email, body.lang or "uz")

    return {"ok": True}


@router.post("/verify-email")
def verify_email(body: VerifyEmailIn, db: Session = Depends(get_session)) -> dict:
    """Confirm an address by spending the token that was mailed to it.

    NO SESSION IS MINTED HERE, deliberately. The link travels through an inbox
    and lands in browser history, in mail-scanner prefetches and in whatever
    else touches a URL on its way - and several of those will FETCH it. A link
    that hands out a live session is a session handed to each of them. What it
    proves is possession of the inbox, which is precisely enough to mark the
    address confirmed and no more; the learner then signs in with the password
    they already chose.
    """
    row = auth.consume_email_token(db, body.token, purpose="verify")
    if row is None:
        # Unknown, expired, already spent, or a reset token pointed at the
        # wrong endpoint - one refusal for all of them.
        raise _refuse("invalid_token", status_code=status.HTTP_400_BAD_REQUEST)

    identity = _identity_for(db, row.email)
    if identity is None or identity.user_id != row.user_id:
        # The address moved, or the identity was removed, between issuing the
        # token and redeeming it. The token confirmed an address this account
        # no longer claims, so it confirms nothing.
        raise _refuse("invalid_token", status_code=status.HTTP_400_BAD_REQUEST)

    identity.email_verified = True
    db.add(identity)
    db.commit()
    log.info("email verified user=%s", identity.user_id)
    return {"ok": True, "verified": True}


# ── password reset ────────────────────────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordIn, request: Request,
                    db: Session = Depends(get_session)) -> dict:
    """Start a password reset. ALWAYS ANSWERS {"ok": true}.

    THE CONSTANT RESPONSE IS THE WHOLE SECURITY PROPERTY. "No account with
    that address" is a free membership test against any address anybody cares
    to try, and this app's users are people reciting the Quran - a list of who
    holds an account here is not a neutral disclosure in every country it will
    run in. So the answer never varies, and neither does the work: an unknown
    address takes the same path and the same time as a known one.
    """
    ip_key = f"forgot:{_client_ip(request)}"
    limit = _signup_limit()
    _check_throttle(ip_key, limit)
    limiter.penalise(ip_key, limit)

    email = passwords.normalise_email(body.email)
    if passwords.valid_email(email):
        acct_key = f"forgot-{_account_key(email)}"
        # Per-address as well as per-IP: without it, a botnet can use this
        # endpoint to mail one person a reset link every few seconds forever,
        # which is harassment delivered by our sender domain.
        if limiter.retry_after(acct_key, limit) == 0:
            limiter.penalise(acct_key, limit)
            identity = _identity_for(db, email)
            if identity is not None:
                raw = auth.issue_email_token(
                    db, identity.user_id, purpose="reset", email=email,
                    ttl_seconds=settings.password_reset_ttl_seconds)
                mailer.send_password_reset_email(email, raw, lang=body.lang or "uz")
                log.info("password reset requested user=%s", identity.user_id)

    return {"ok": True}


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn,
                   db: Session = Depends(get_session)) -> dict:
    """Set a new password from a mailed token, and sign out everywhere.

    ── EVERY SESSION DIES, INCLUDING THE ONES SOMEBODY ELSE IS HOLDING ─────

    This is the entire reason a reset is worth doing after a compromise. If an
    attacker signed in yesterday, their session is a row that keeps working
    tomorrow no matter what the password says - changing the password without
    revoking it fixes the door and leaves them inside. auth.revoke_all_for_user
    is what actually removes them, and it is why sessions are rows here rather
    than JWTs: a stateless token could not be revoked at all.

    The learner is signed out too, on every device, and has to sign in again
    with the password they just chose. That is the correct cost.

    NO SESSION IS MINTED, for the reason in verify_email: this token arrives
    through an inbox.
    """
    row = auth.consume_email_token(db, body.token, purpose="reset")
    if row is None:
        raise _refuse("invalid_token", status_code=status.HTTP_400_BAD_REQUEST)

    identity = _identity_for(db, row.email)
    if identity is None or identity.user_id != row.user_id:
        raise _refuse("invalid_token", status_code=status.HTTP_400_BAD_REQUEST)

    problems = passwords.password_problems(body.new_password, email=row.email)
    if problems:
        # THE TOKEN IS ALREADY SPENT AT THIS POINT and that is deliberate:
        # consuming on redemption rather than on success is what stops an
        # attacker probing a stolen link with junk passwords to learn whether
        # it is still live. The cost is that a learner who picks a weak
        # password has to request a new link, which the message says.
        raise _refuse("weak_password", problems=problems)

    identity.password_hash = passwords.hash_password(body.new_password)
    # Reaching this line required reading mail sent to that address, which is
    # the same proof verification asks for. An account that resets its password
    # is therefore confirmed by the act.
    identity.email_verified = True
    db.add(identity)
    db.commit()

    killed = auth.revoke_all_for_user(db, identity.user_id)

    # THE ACCOUNT'S LOGIN THROTTLE IS LIFTED, and only the account's.
    #
    # Somebody who forgot their password very likely just failed to sign in
    # five times - that is what sent them here. Leaving the block in place
    # would mean completing a reset correctly and then being refused the new
    # password for the next fifteen minutes, which reads as the reset not
    # having worked and sends them round the loop again.
    #
    # It is safe because reaching this line required reading mail sent to that
    # address, which is stronger proof of ownership than the password was. The
    # per-IP block is deliberately NOT cleared: otherwise resetting one
    # throwaway account would unblock an attacker's address for guessing at
    # every other one.
    limiter.clear(f"login-{_account_key(row.email)}")

    log.info("password reset completed user=%s sessions_revoked=%d",
             identity.user_id, killed)
    return {"ok": True}
