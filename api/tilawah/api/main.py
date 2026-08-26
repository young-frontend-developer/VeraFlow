# -*- coding: utf-8 -*-
"""FastAPI app.

Run:  uvicorn tilawah.api.main:app --reload
Docs: http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .. import content
from ..config import settings
from ..content import coaching
from ..db import init_db
from .auth_routes import router as auth_router
from .email_routes import router as email_auth_router
from .lesson_routes import router as lesson_router
from .routes import router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()

    # DEV ONLY tripwire. Some rules are flipped to reviewed=true so the app can
    # be demonstrated before content review is finished. Say so on every boot,
    # loudly, so it cannot quietly reach a real user.
    overrides = content.dev_overrides()
    if overrides:
        bar = "!" * 68
        logging.warning(bar)
        logging.warning("DEV OVERRIDE ACTIVE - NOT FIT TO LAUNCH")
        logging.warning("Showing tajweed corrections NO QORI HAS REVIEWED: %s",
                        ", ".join(overrides))
        logging.warning("Re-gate in tilawah/content/rules.json before launch.")
        logging.warning(bar)

    # Refuse to serve real people while storing their voice without asking.
    if settings.debug_audio and settings.is_production:
        raise RuntimeError(
            "TILAWAH_DEBUG_AUDIO=1 stores every recording with NO consent. "
            "That is a laptop-only diagnostic. Unset it, or set TILAWAH_ENV=dev "
            "if this really is a development box."
        )
    if settings.debug_audio:
        logging.warning("=" * 68)
        logging.warning("DEBUG AUDIO ON - every upload is stored, consent IGNORED")
        logging.warning("Development only. Never set this where real learners can reach.")
        logging.warning("=" * 68)

    # The content gate is derived from TILAWAH_ENV, so "unreviewed corrections
    # reaching a real learner" is no longer one unset variable away - it cannot
    # be configured at all. This assertion is here so that stays true: if a
    # later refactor reintroduces an override, production fails to boot rather
    # than quietly starting with the gate open.
    if settings.is_production and settings.show_unreviewed:
        raise RuntimeError(
            "The content review gate is open in production. Nothing should be "
            "able to do that - settings.show_unreviewed is derived from "
            "TILAWAH_ENV. Telling a learner they erred in the Quran on the "
            "strength of content no qori has read is the trust failure this "
            "project is built to avoid."
        )
    # ── the device-claim window ───────────────────────────────────────────
    #
    # Claiming trades a device id for a session, and a device id is not a
    # secret - it has been in access logs since the first release. The window
    # exists to migrate existing installs exactly once. These checks are what
    # stop "temporary" from meaning "until someone remembers", in the same
    # spirit as the content gate above: structural, not one unset variable away
    # from failing.
    try:
        claim_deadline = settings.claim_deadline
    except ValueError:
        raise RuntimeError(
            f"TILAWAH_DEVICE_CLAIM_UNTIL={settings.device_claim_until!r} is not "
            "an ISO date (YYYY-MM-DD). Refusing to start rather than treat a "
            "typo as 'no deadline', which would leave the claim window open "
            "indefinitely.")

    if settings.is_production and settings.allow_device_claim:
        if claim_deadline is None:
            raise RuntimeError(
                "TILAWAH_ALLOW_DEVICE_CLAIM=1 in production with no "
                "TILAWAH_DEVICE_CLAIM_UNTIL deadline.\n"
                "Device claiming hands a session to anyone presenting a device "
                "id, and device ids are not secrets - they have been in access "
                "logs and browser history since the first release. It is a "
                "migration affordance, never an authentication mechanism.\n"
                "Either set a deadline for the migration window:\n"
                "    TILAWAH_DEVICE_CLAIM_UNTIL=YYYY-MM-DD\n"
                "or, once existing installs have moved onto sessions:\n"
                "    TILAWAH_ALLOW_DEVICE_CLAIM=0")
        if not settings.device_claim_open:
            logging.info("device claim window closed on %s; claiming is off",
                         claim_deadline)

    if settings.device_claim_open:
        bar = "!" * 68
        logging.warning(bar)
        logging.warning("DEVICE CLAIM WINDOW IS OPEN - temporary, close it")
        logging.warning("POST /api/auth/anonymous will hand a session to anyone")
        logging.warning("presenting a known device_id. Device ids are NOT secrets.")
        logging.warning("Closes: %s", claim_deadline or "NO DEADLINE SET (dev only)")
        logging.warning("When existing installs have migrated, set")
        logging.warning("TILAWAH_ALLOW_DEVICE_CLAIM=0 and remove this window.")
        logging.warning(bar)

    # ── session cookie ────────────────────────────────────────────────────
    #
    # A session cookie without Secure is sent over plain http, which puts the
    # credential on the wire for anyone on the path. Dev runs on http and needs
    # the default off; production does not get the choice.
    if settings.is_production and not settings.session_cookie_secure:
        raise RuntimeError(
            "TILAWAH_SESSION_COOKIE_SECURE=0 in production. The session cookie "
            "would be transmitted over plain http, exposing the token to anyone "
            "on the network path. Set TILAWAH_SESSION_COOKIE_SECURE=1.")

    samesite = (settings.session_cookie_samesite or "").lower()
    if samesite not in ("lax", "strict", "none"):
        raise RuntimeError(
            f"TILAWAH_SESSION_COOKIE_SAMESITE={settings.session_cookie_samesite!r} "
            "is not one of lax, strict, none. An unrecognised value is dropped "
            "by the browser, which silently removes the CSRF protection this "
            "relies on.")
    if samesite == "none" and not settings.session_cookie_secure:
        # Browsers reject SameSite=None without Secure outright, so the cookie
        # would simply never be stored - an auth system that fails closed in a
        # way nobody notices until every login stops working.
        raise RuntimeError(
            "TILAWAH_SESSION_COOKIE_SAMESITE=none requires "
            "TILAWAH_SESSION_COOKIE_SECURE=1. Browsers refuse the combination "
            "and the session cookie would never be stored at all.")
    if settings.is_production and samesite == "none":
        logging.warning(
            "session cookie is SameSite=none: the browser will attach it to "
            "cross-site requests, so CSRF protection must come from somewhere "
            "else before any state-changing route moves behind the session.")

    # ── email / password sign-in ──────────────────────────────────────────
    #
    # There is no provider wired yet (tilawah/mailer.py), so verification and
    # password reset generate real tokens that nobody receives. These checks
    # exist so that state is impossible to ship by accident, and so the one
    # combination that locks every learner out cannot boot at all.
    if settings.require_email_verification and not settings.email_sending_enabled:
        raise RuntimeError(
            "TILAWAH_REQUIRE_EMAIL_VERIFICATION=1 with no email provider "
            "configured. Every registration would be told to check an inbox "
            "nothing was ever sent to, and NOBODY WOULD EVER BE ABLE TO SIGN "
            "IN.\n"
            "Either wire a provider - set TILAWAH_EMAIL_PROVIDER, "
            "TILAWAH_EMAIL_API_KEY and TILAWAH_EMAIL_FROM, and implement "
            "mailer._deliver() - or set "
            "TILAWAH_REQUIRE_EMAIL_VERIFICATION=0 for now.")

    if settings.email_echo_links:
        if settings.is_production:
            raise RuntimeError(
                "TILAWAH_EMAIL_ECHO_LINKS=1 in production. It writes "
                "verification and password-reset LINKS into the application "
                "log, and a reset link is a complete account takeover for "
                "anyone who can read logs. It is a laptop-only affordance for "
                "walking the flow with no mail provider.")
        logging.warning("=" * 68)
        logging.warning("EMAIL LINK ECHO ON - verification and reset links are")
        logging.warning("written to this log. Development only.")
        logging.warning("=" * 68)

    if settings.is_production and not settings.require_email_verification:
        bar = "!" * 68
        logging.warning(bar)
        logging.warning("EMAIL VERIFICATION IS OFF IN PRODUCTION")
        logging.warning("Anyone can register any address they do not own, and")
        logging.warning("password reset cannot be trusted to reach its owner.")
        logging.warning("Wire a mail provider and set")
        logging.warning("TILAWAH_REQUIRE_EMAIL_VERIFICATION=1.")
        logging.warning(bar)
    elif not settings.email_sending_enabled:
        logging.info(
            "email sending is not configured; verification and reset tokens "
            "are minted but nothing is delivered. See tilawah/mailer.py.")

    if settings.is_production and any("localhost" in o for o in settings.origins):
        raise RuntimeError(
            "TILAWAH_CORS_ORIGINS contains localhost in production. "
            "Set it to the real origin (e.g. https://veraflow.uz).")

    if settings.show_unreviewed:
        bar = "=" * 68
        logging.warning(bar)
        logging.warning("DEV BUILD - every detected error is rendered, including")
        logging.warning("unreviewed and unauthored codes, with no display cap.")
        logging.warning("Each is marked draft on the wire. Set TILAWAH_ENV=")
        logging.warning("production to close the gate before real learners.")
        logging.warning(bar)
    logging.info("audio retention: collect=%s (per-learner consent still required)",
                 settings.collect_audio)

    # The model is NOT preloaded. First recitation pays ~15 s; every later one
    # is fast. Preloading here would make deploys slow and health checks lie.
    logging.info("Tilawah API ready (model loads on first analyse, dtype=%s)",
                 settings.model_dtype)
    yield


app = FastAPI(title="VeraFlow API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)
# Sessions. Additive in this phase: nothing in `router` requires one yet, and
# the device_id endpoints are untouched. See api/auth_routes.py.
app.include_router(auth_router)
# Email/password, on the same /api/auth prefix and the same session system.
# A separate module for readers, not for the client - see api/email_routes.py.
app.include_router(email_auth_router)
app.include_router(lesson_router)
# The isolated letter recordings a coaching card's practice section plays.
# Mounted unconditionally: the directory is checked in (with a README) so the
# mount cannot fail, and coaching.audio_url() gates each individual button on
# the file actually existing. Nothing here is learner data - it ships with the
# app - so it is served statically rather than through a route.
app.mount("/audio", StaticFiles(directory=coaching.AUDIO_DIR), name="audio")


@app.get("/health")
def health() -> dict:
    return {"ok": True}
