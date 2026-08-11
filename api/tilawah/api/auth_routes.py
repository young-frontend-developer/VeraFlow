# -*- coding: utf-8 -*-
"""Session endpoints. NO EXTERNAL IDENTITY - no Google, no Apple, not yet.

Four routes, and between them they are the whole of "who is this request":

    POST /api/auth/anonymous   get a session (new user, or claim a device id)
    POST /api/auth/refresh     rotate the token, extend the expiry
    POST /api/auth/logout      revoke it
    GET  /api/auth/me          who the current session belongs to

WHAT THIS PHASE DELIBERATELY DOES NOT DO. The existing device_id endpoints -
/api/attempts, /api/consent - are untouched and keep working exactly as they
did. Nothing here is required to use the app. The router is additive so that
sessions can be built, tested and reviewed before anything depends on them,
which is the opposite of the usual auth rollout where the cutover and the
implementation land together and neither can be examined alone.

THE TOKEN IS SET AS A COOKIE *AND* RETURNED IN THE BODY. Not redundancy - the
browser wants httpOnly (unreadable by XSS) and a native client cannot read a
cookie jar it does not have. Same session either way; see api/deps.py.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, select

from .. import auth, google_identity
from ..config import settings
from ..db import get_session
from ..db.models import AuthIdentity, AuthSession, User
from .deps import current_auth, optional_auth
from .schemas import (AnonymousSessionIn, GoogleSessionOut, GoogleSignInIn,
                      GoogleStartOut, MeOut, SessionOut)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(response: Response, raw_token: str, max_age_s: int) -> None:
    """Attach the session cookie.

    httpOnly so script cannot read it, which is the one protection localStorage
    cannot offer. `secure` and `samesite` come from settings because dev is
    plain http and same-site rules differ between the dev split-origin setup
    and a same-origin deployment.
    """
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=max_age_s,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/")


def _session_out(raw: str, row: AuthSession, *, claimed: bool) -> SessionOut:
    return SessionOut(token=raw, expires_at=row.expires_at,
                      user_id=row.user_id, claimed_existing=claimed)


def _max_age(row: AuthSession) -> int:
    delta = auth._utc(row.expires_at) - auth.now()
    return max(0, int(delta.total_seconds()))


@router.post("/anonymous", response_model=SessionOut)
def create_anonymous_session(body: AnonymousSessionIn, request: Request,
                             response: Response,
                             db: Session = Depends(get_session)) -> SessionOut:
    """Get a session without signing in to anything.

    ANONYMOUS IS HOW THIS APP WORKS, not a waiting room. Auth.tsx has said so
    since before there was a backend for it, and this endpoint is what makes
    that true on the server: a learner with no account still gets a real,
    revocable session rather than an id passed around in form fields.

    Two paths:

      device_id present and known  -> a session for THAT user, history intact.
      anything else                -> a new anonymous User.

    An UNKNOWN device_id creates a new user under that id rather than 404ing.
    The alternative leaks which device ids exist to anyone who cares to probe,
    and the id came from the client in the first place - there is nothing to
    protect by refusing it.
    """
    device_id = (body.device_id or "").strip()
    claimed = False

    if device_id and not settings.device_claim_open:
        # 410 GONE, and never a silent fallback to a fresh account. Minting a
        # different user here would return 200 while the learner's practice
        # appeared to vanish - the failure would look like data loss and be
        # reported as one. Closed means closed, and says so.
        #
        # `device_claim_open` rather than the raw flag: the window also closes
        # by itself once TILAWAH_DEVICE_CLAIM_UNTIL has passed, with no deploy.
        raise HTTPException(
            status.HTTP_410_GONE,
            "device_id sessions are no longer issued; sign in instead")

    if device_id:
        user = db.get(User, device_id)
        if user is None:
            user = User(id=device_id)
            db.add(user)
        else:
            claimed = True
            # Bookkeeping for the migration window. First claim wins the
            # timestamp; a re-claim is not an error (a reinstall is normal).
            if user.claimed_at is None:
                user.claimed_at = auth.now()
                db.add(user)
        db.commit()
    else:
        # A fresh anonymous user. The id is a uuid4 for the same reason legacy
        # ids were: debug_capture._tag() truncates to 36 characters, and a
        # longer id would silently break audio deletion.
        import uuid
        user = User(id=str(uuid.uuid4()))
        db.add(user)
        db.commit()

    raw, row = auth.create_session(db, user.id,
                                   user_agent=request.headers.get("user-agent", ""))
    _set_cookie(response, raw, _max_age(row))
    log.info("anonymous session user=%s claimed=%s", user.id, claimed)
    return _session_out(raw, row, claimed=claimed)


@router.post("/refresh", response_model=SessionOut)
def refresh_session(request: Request, response: Response,
                    resolved: tuple[AuthSession, User] = Depends(current_auth),
                    db: Session = Depends(get_session)) -> SessionOut:
    """Trade a live session for a fresh one and revoke the old.

    ROTATION, NOT RENEWAL. Extending the expiry in place would leave a token
    that leaked into a log or a backup usable for as long as the client kept
    refreshing. The old token stops working the moment this returns, so a
    client must replace what it holds - there is no grace window, deliberately.
    """
    row, _user = resolved
    raw, fresh = auth.rotate(db, row,
                             user_agent=request.headers.get("user-agent", ""))
    _set_cookie(response, raw, _max_age(fresh))
    return _session_out(raw, fresh, claimed=False)


@router.post("/logout")
def logout(response: Response,
           resolved: tuple[AuthSession, User] = Depends(current_auth),
           db: Session = Depends(get_session)) -> dict:
    """Revoke this session. The row stays, marked dead, as an audit trail.

    Only THIS session. Signing out on a laptop must not sign the learner out
    of their phone; auth.revoke_all_for_user exists for when that is what is
    wanted.
    """
    row, _user = resolved
    auth.revoke(db, row)
    _clear_cookie(response)
    return {"ok": True}


# ── Google ────────────────────────────────────────────────────────────────

def _google_or_503() -> list[str]:
    if not settings.google_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Google sign-in is not configured on this server")
    return settings.google_audiences


def _providers_for(db: Session, user_id: str) -> list[str]:
    return sorted(r.provider for r in db.exec(
        select(AuthIdentity).where(AuthIdentity.user_id == user_id)).all())


@router.post("/google/start", response_model=GoogleStartOut)
def google_start(db: Session = Depends(get_session)) -> GoogleStartOut:
    """Issue the single-use nonce the browser must present to Google.

    Deliberately unauthenticated: a learner signing in on a fresh install has
    no session yet, and requiring one would make the first sign-in impossible.
    A nonce grants nothing on its own - it only makes a credential traceable to
    a login this server started.
    """
    audiences = _google_or_503()
    raw = auth.issue_nonce(db, ttl_seconds=settings.google_nonce_ttl_seconds)
    return GoogleStartOut(nonce=raw, client_id=audiences[0],
                          expires_in=settings.google_nonce_ttl_seconds)


@router.post("/google", response_model=GoogleSessionOut)
def google_sign_in(body: GoogleSignInIn, request: Request, response: Response,
                   resolved: tuple[AuthSession, User] | None = Depends(optional_auth),
                   db: Session = Depends(get_session)) -> GoogleSessionOut:
    """Sign in with Google, or attach Google to the account already in hand.

    ── THE OWNERSHIP RULE, WHICH IS THE WHOLE POINT ────────────────────────

    A learner who has been practising anonymously ALREADY HAS AN ACCOUNT. It
    holds their attempts, their consent decision, their streak. Signing in with
    Google must attach an identity to that account - never mint a second one
    and leave the first orphaned, which is the default behaviour of almost
    every auth library and is indistinguishable, from the inside, from having
    lost everything.

        session   sub          outcome
        ────────  ───────────  ──────────────────────────────────────────
        user A    unknown      LINK. A keeps its id and all of its history.
        user A    -> A         already linked; rotate and carry on.
        user A    -> B         409 CONFLICT. Nothing is written. See below.
        none      -> B         sign in as B.
        none      unknown      create a new account.

    ── WHY THE CONFLICT IS NOT RESOLVED HERE ───────────────────────────────

    When the session is user A and the Google account already belongs to user
    B, both accounts hold real practice history and there is no correct answer
    this endpoint can pick. Moving the identity would strand B; merging would
    have to reconcile two consent states and two sets of recordings, and
    consent is not something software may infer on someone's behalf. So it
    refuses, writes nothing to either account, and hands the decision back.

    Merging is a deliberate, separate, and much later piece of work.
    """
    audiences = _google_or_503()

    # SPENT BEFORE THE TOKEN IS TRUSTED. Checking the nonce afterwards would
    # leave a window where a replayed credential still did work.
    if not auth.consume_nonce(db, body.nonce):
        log.warning("google sign-in refused: unusable nonce (token %s)",
                    google_identity.token_fingerprint(body.credential or ""))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "sign-in could not be verified")

    try:
        claims = google_identity.verify(body.credential, audiences=audiences,
                                        expected_nonce=body.nonce)
    except google_identity.GoogleAuthError as exc:
        # The reason stays here. One refusal reaches the client, because
        # "expired" versus "wrong audience" tells an attacker which half of
        # their guess landed. The token itself is never logged - only a hash.
        log.warning("google sign-in refused: %s (token %s)", exc.code,
                    google_identity.token_fingerprint(body.credential or ""))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "sign-in could not be verified")

    current_user = resolved[1] if resolved else None
    existing = db.exec(
        select(AuthIdentity).where(AuthIdentity.provider == "google",
                                   AuthIdentity.subject == claims.subject)
    ).first()

    linked_now = False

    if existing is not None and current_user is not None \
            and existing.user_id != current_user.id:
        # CASE B. Nothing has been written; nothing will be.
        log.info("google sign-in conflict: session=%s identity=%s",
                 current_user.id, existing.user_id)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This Google account is already linked to a different Tilawah "
            "account. Sign out first to continue with it, or continue without "
            "signing in to keep using this one.")

    if existing is not None:
        user = db.get(User, existing.user_id)
        if user is None:
            # An identity pointing at a deleted account. CASCADE should make
            # this impossible; refuse rather than resurrect anything.
            log.error("google identity %s points at missing user %s",
                      existing.id, existing.user_id)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                                "sign-in could not be verified")
        existing.last_login_at = auth.now()
        # Refreshed because Google is the source of truth for these and people
        # change their name and address. NEITHER IS AN IDENTITY KEY - the row
        # is found by `subject` and only ever by `subject`.
        existing.email = claims.email
        existing.email_verified = claims.email_verified
        db.add(existing)
    else:
        # CASE A (session in hand) or CASE C (no session at all).
        #
        # ONE GOOGLE ACCOUNT PER TILAWAH ACCOUNT. If this user already has a
        # different Google identity, UNIQUE(user_id, provider) would reject the
        # insert and the learner would get a 500 for doing something perfectly
        # reasonable - signing in with their other Google account. Refuse it
        # here, deliberately and with an explanation, rather than at the
        # database. Silently repointing the existing identity is the one thing
        # that must not happen: it would hand this account to a different
        # Google login and lock the original one out.
        if current_user is not None:
            already = db.exec(
                select(AuthIdentity).where(
                    AuthIdentity.user_id == current_user.id,
                    AuthIdentity.provider == "google")
            ).first()
            if already is not None:
                log.info("google sign-in refused: user %s already has google %s",
                         current_user.id, already.id)
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "This Tilawah account is already linked to a different "
                    "Google account. Sign out first to use another one.")

        if current_user is None:
            import uuid
            # uuid4 for the same reason every other id here is: _tag()
            # truncates at 36 characters and a longer id silently breaks
            # audio deletion.
            user = User(id=str(uuid.uuid4()))
            db.add(user)
            db.commit()
        else:
            user = current_user          # <- User.id is PRESERVED. The point.
        db.add(AuthIdentity(user_id=user.id, provider="google",
                            subject=claims.subject, email=claims.email,
                            email_verified=claims.email_verified,
                            last_login_at=auth.now()))
        linked_now = True

    # Profile fields are a convenience for the UI and never a lookup key.
    if claims.name and not user.display_name:
        user.display_name = claims.name
    if claims.email:
        user.email = claims.email
    db.add(user)
    db.commit()

    # ROTATE. Attaching an identity changes what the session is worth, and a
    # session that outlives a privilege change is the classic fixation bug.
    ua = request.headers.get("user-agent", "")
    if resolved is not None and resolved[1].id == user.id:
        raw, row = auth.rotate(db, resolved[0], user_agent=ua)
    else:
        if resolved is not None:
            # Signed in as somebody else entirely (no session -> B is handled
            # above; this is the belt for a future path). Kill the old one.
            auth.revoke(db, resolved[0])
        raw, row = auth.create_session(db, user.id, user_agent=ua)

    _set_cookie(response, raw, _max_age(row))
    log.info("google sign-in ok: user=%s linked_now=%s", user.id, linked_now)
    return GoogleSessionOut(
        token=raw, expires_at=row.expires_at, user_id=user.id,
        claimed_existing=False, linked_now=linked_now,
        providers=_providers_for(db, user.id),
        email=user.email, display_name=user.display_name)


@router.get("/me", response_model=MeOut)
def me(resolved: tuple[AuthSession, User] = Depends(current_auth),
       db: Session = Depends(get_session)) -> MeOut:
    """The current session's user, and the consent state that governs them.

    Consent is reported here, not owned here: this endpoint reads the same
    columns /api/consent writes, so the two can never disagree about whether
    a learner's attempts are being kept.
    """
    row, user = resolved
    providers = [
        r.provider for r in
        db.exec(select(AuthIdentity).where(AuthIdentity.user_id == user.id)).all()
    ]
    return MeOut(
        user_id=user.id, lang=user.lang,
        consented=user.consented, audio_consented=user.audio_consented,
        consent_seen=user.consent_seen,
        # Derived, never stored - a cached flag would drift the first time an
        # identity was linked or unlinked in a path that forgot to update it.
        is_anonymous=not providers,
        email=user.email, display_name=user.display_name,
        providers=sorted(providers),
        session_expires_at=row.expires_at,
    )
