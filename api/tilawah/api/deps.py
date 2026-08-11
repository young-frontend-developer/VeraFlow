# -*- coding: utf-8 -*-
"""Request-scoped authentication.

ONE AUTH SYSTEM, TWO TRANSPORTS. A session is a row; how the client carries its
token is a detail of the client, not a second way of logging in:

    Authorization: Bearer <token>     native shells, curl, tests
    Cookie: tilawah_session=<token>   the browser

The header wins when both are present. A browser attaches its cookie to every
request whether or not the caller meant it to, so an explicit header is the
stronger statement of intent - and it lets a native client inside a WebView
override an inherited cookie.

WHY THE COOKIE IS NOT THE ONLY OPTION. httpOnly keeps the token away from XSS,
which is the right default for the web. But SameSite=lax means the browser will
not send it cross-site, and the dev setup - client on :5173, api on :8000 - IS
cross-site. Supporting the header is what keeps one implementation working in
both places instead of growing a second one.

NOTHING HERE IS WIRED INTO THE EXISTING ROUTES YET. Phase 2 adds the machinery;
the device_id endpoints keep working exactly as they did.
"""
from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from .. import auth
from ..config import settings
from ..db import get_session
from ..db.models import AuthSession, Device, User

# One message for every failure mode. See auth.resolve: distinguishing
# "expired" from "unknown" confirms to an attacker that a token was real.
_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def bearer_token(request: Request) -> str | None:
    """The raw token from header or cookie, or None. Never logged."""
    header = request.headers.get("authorization") or ""
    scheme, _, value = header.partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return value.strip()
    return request.cookies.get(settings.session_cookie_name) or None


def optional_auth(request: Request,
                  db: Session = Depends(get_session)
                  ) -> tuple[AuthSession, User] | None:
    """Resolve a session if one was presented and is usable, else None.

    For endpoints that behave differently when signed in but do not require it.
    """
    token = bearer_token(request)
    return auth.resolve(db, token) if token else None


def current_auth(resolved: tuple[AuthSession, User] | None = Depends(optional_auth)
                 ) -> tuple[AuthSession, User]:
    """Require a session. 401 on anything less."""
    if resolved is None:
        raise _UNAUTHORIZED
    return resolved


def current_user(resolved: tuple[AuthSession, User] = Depends(current_auth)) -> User:
    """The authenticated User. THE dependency routes should ask for.

    A route that declares `user: User = Depends(current_user)` cannot be
    reached unauthenticated and cannot read an id off the request body, which
    is the shape of the bug the device_id endpoints have today.
    """
    return resolved[1]


def optional_user(resolved: tuple[AuthSession, User] | None = Depends(optional_auth)
                  ) -> User | None:
    return resolved[1] if resolved else None


# ── legacy device_id, demoted from credential to claim ────────────────────

def owns_device(db: Session, user: User, device_id: str) -> bool:
    """Does this authenticated user own that device id?

    A device id USED TO BE the whole of identity - whoever sent one was
    treated as its owner. It is now a claim like any other, checked against
    the session, and it can only ever narrow what the session already permits.
    It can never widen it and it can never name a different user.

    Two ways to own one, and both are needed:

      * `device_id == user.id`  - every account that predates sign-in has a
        device uuid AS its primary key, because Phase 1 refused to rewrite
        those ids. For those users the two are literally the same string.
      * a Device row pointing at this user - how a second install will be
        recognised once one account can hold several.
    """
    if not device_id:
        return False
    if device_id == user.id:
        return True
    device = db.get(Device, device_id)
    return device is not None and device.user_id == user.id


def require_own_device(db: Session, user: User, device_id: str | None) -> None:
    """Reject a device id the session does not own. No-op when none is sent.

    403 RATHER THAN 404, deliberately, and it is the one place in this module
    that is not a 404. The caller is authenticated and is naming a device id
    they already hold - refusing tells them nothing they did not just supply.
    A 404 here would be a lie about their own request rather than protection
    for anybody. Resource lookups by id keep the 404; see flag_wrong.
    """
    if device_id is None or device_id == "":
        return
    if not owns_device(db, user, device_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "device_id does not belong to the authenticated session")
