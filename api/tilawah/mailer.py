# -*- coding: utf-8 -*-
"""The one place this application sends email. Deliberately unwired.

── WHAT THIS IS AND WHY IT IS EMPTY ───────────────────────────────────────

There is no email provider configured for this project yet. Choosing one needs
an account, a verified sender domain and an API key - the same kind of external
setup the Google OAuth client ids needed, and the same kind that cannot be
guessed from inside the codebase.

So the flow above this module is COMPLETE - tokens are generated, hashed,
stored, expired and consumed, and the endpoints that do all that are real - and
the delivery step lands here, in two functions with a fixed signature, one
provider-shaped seam, and NO SDK IMPORT ANYWHERE. Wiring Resend, SendGrid, SES
or plain SMTP is then an edit to `_deliver()` and nothing else.

Guessing a provider now would be the expensive mistake. A provider SDK is not
an implementation detail: it decides how sender identity is verified, how
bounces come back, what the retry semantics are, and which of those the rest of
the code has to know about. Half-wiring the wrong one costs more than not
wiring one at all.

── WHAT HAPPENS UNTIL THEN ────────────────────────────────────────────────

`_deliver()` logs the message and returns. In dev with
TILAWAH_EMAIL_ECHO_LINKS=1 it logs the LINK ITSELF so the verification and
reset flows can be walked end to end on a laptop with no provider at all.

THAT FLAG IS A DEVELOPMENT AFFORDANCE AND PRODUCTION REFUSES TO BOOT WITH IT
SET (see api/main.py). A verification link in a log file is a password reset
for whoever can read the logs.

── THE RULE THAT OUTLIVES THE PROVIDER CHOICE ─────────────────────────────

A send failure must NEVER fail the request that triggered it. Registration
succeeding and the mail bouncing is a resend away; registration returning 500
because a third party had a bad minute loses the account entirely. Both public
functions swallow their own errors and say so in the log.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import settings

log = logging.getLogger(__name__)


class EmailNotConfigured(RuntimeError):
    """No provider is wired. Raised only by the strict paths, never by send."""


@dataclass(frozen=True)
class Message:
    to: str
    subject: str
    text: str
    #: The single actionable URL in the body, kept separate so the dev echo can
    #: print it without parsing the message.
    link: str = ""


def is_configured() -> bool:
    """Whether a real provider could send right now.

    Reads as False for the whole of this phase. It exists so that callers -
    and the boot checks in main.py - can ask the question rather than infer it
    from a missing env var they happen to know the name of.
    """
    return bool(settings.email_provider and settings.email_api_key
                and settings.email_from)


# ── the seam ──────────────────────────────────────────────────────────────

def _deliver(msg: Message) -> None:
    """THE ONLY FUNCTION THAT WILL TALK TO A PROVIDER. Replace this body.

    When the provider is chosen, this becomes a dispatch on
    settings.email_provider and nothing else in the codebase moves:

        if settings.email_provider == "resend":   ...
        elif settings.email_provider == "sendgrid": ...
        elif settings.email_provider == "ses":    ...
        elif settings.email_provider == "smtp":   ...

    Everything a provider needs is already carried on settings:
    email_from, email_from_name, email_api_key, email_provider, app_base_url.

    NEVER log `msg.text` or `msg.link` outside the dev echo below. The link IS
    the credential - it is the whole of what the recipient has to prove.
    """
    if not is_configured():
        log.warning(
            "email NOT SENT (no provider configured): to=%s subject=%r. "
            "Wire tilawah/mailer.py:_deliver() - see the module docstring.",
            _redact(msg.to), msg.subject)
        if settings.email_echo_links and msg.link:
            # DEV ONLY. main.py refuses to start in production with this on.
            log.warning("DEV EMAIL LINK for %s -> %s", _redact(msg.to), msg.link)
        return

    # Unreachable today: is_configured() cannot be true without a provider
    # branch above it. Raising rather than silently dropping means a
    # half-finished configuration is discovered at the first send, not by a
    # learner who never receives their verification mail.
    raise EmailNotConfigured(
        f"TILAWAH_EMAIL_PROVIDER={settings.email_provider!r} is set but "
        "mailer._deliver() has no branch for it. Implement it there.")


def _redact(address: str) -> str:
    """`a***@example.com`. Enough to correlate a support report, not enough to
    turn the application log into a mailing list."""
    local, _, domain = (address or "").partition("@")
    if not domain:
        return "***"
    return f"{local[:1]}***@{domain}"


def _link(path: str, token: str) -> str:
    """A one-time link into the web client.

    Built from settings.app_base_url rather than from the incoming request:
    a URL taken from the Host header is a URL an attacker can set, and this one
    is about to be mailed to somebody as though we chose it.
    """
    base = (settings.app_base_url or "").rstrip("/")
    return f"{base}{path}?token={token}"


# ── what the rest of the app calls ────────────────────────────────────────

def send_verification_email(to: str, token: str, *, lang: str = "uz") -> bool:
    """Confirm this address really belongs to whoever just signed up.

    Returns whether it went out. THE CALLER MUST NOT FAIL ON False - see the
    module docstring - and must not tell the client either way, because "that
    address got no mail" is "that address is not registered" said slowly.
    """
    subject = ("VeraFlow: emailingizni tasdiqlang" if lang == "uz"
               else "VeraFlow: подтвердите ваш email")
    link = _link("/verify-email", token)
    body = (
        f"{'Tasdiqlash uchun havolani oching' if lang == 'uz' else 'Откройте ссылку для подтверждения'}:\n\n"
        f"{link}\n\n"
        f"{'Havola 24 soat amal qiladi.' if lang == 'uz' else 'Ссылка действительна 24 часа.'}\n"
    )
    return _send(Message(to=to, subject=subject, text=body, link=link))


def send_password_reset_email(to: str, token: str, *, lang: str = "uz") -> bool:
    """The link that lets somebody set a new password.

    Same contract as above, and the same reason for it: whether an address
    received a reset mail must not be observable from the response.
    """
    subject = ("VeraFlow: parolni tiklash" if lang == "uz"
               else "VeraFlow: сброс пароля")
    link = _link("/reset-password", token)
    body = (
        f"{'Yangi parol oʻrnatish uchun havolani oching' if lang == 'uz' else 'Откройте ссылку, чтобы задать новый пароль'}:\n\n"
        f"{link}\n\n"
        f"{'Havola 1 soat amal qiladi. Agar bu siz boʻlmasangiz, bu xatni eʼtiborsiz qoldiring.' if lang == 'uz' else 'Ссылка действительна 1 час. Если это были не вы, просто проигнорируйте письмо.'}\n"
    )
    return _send(Message(to=to, subject=subject, text=body, link=link))


def _send(msg: Message) -> bool:
    """Deliver, and turn any failure into False rather than an exception.

    A provider outage must not be able to fail a registration. This is the
    boundary where that promise is kept, so neither caller has to remember it.
    """
    try:
        _deliver(msg)
        return True
    except Exception:            # noqa: BLE001 - deliberately everything
        log.exception("email delivery failed: to=%s subject=%r",
                      _redact(msg.to), msg.subject)
        return False
