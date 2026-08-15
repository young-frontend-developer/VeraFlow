# -*- coding: utf-8 -*-
"""Throttling for the endpoints a stranger can hammer.

NO HTTP IN THIS MODULE, same rule as auth.py. It answers one question - "has
this key had too many goes recently?" - and the routes decide what to do about
the answer.

── WHY IN-PROCESS MEMORY AND NOT THE DATABASE ─────────────────────────────

This deployment runs ONE uvicorn worker, deliberately and permanently: each
worker would load its own ~1.3 GB copy of the acoustic model, so the process
count is pinned at one by something far more expensive than auth. See the
Dockerfile. With one process, a dict is a correct shared counter.

The alternative was a table, and it is worse HERE specifically: sqlite
serialises writers, this codebase already carries a lock in routes.py because
two concurrent consent writes killed the connection, and a rate limiter writes
on every failed attempt - which is exactly the traffic pattern an attacker
controls. A brute-force attempt should not be able to turn into a write storm
against the same database that holds everybody's practice.

WHAT THAT COSTS, STATED PLAINLY: the counters reset when the process restarts,
so an attacker who can trigger restarts gets a fresh allowance, and a second
worker or a second box would each keep their own. If either ever becomes true,
this module is the seam to move to Redis - the routes call `check()` and
`penalise()` and would not change.

── THE TWO KEYS, AND WHY BOTH ─────────────────────────────────────────────

Per-IP alone: one attacker with a botnet spreads a password-spray across
thousands of addresses and never trips it. Per-account alone: one attacker from
one machine walks the whole user list, one guess per account, and never trips
that either. Neither is sufficient and together they cover both shapes, so the
routes check both.

── WHY FAILURES COUNT AND SUCCESSES DO NOT ────────────────────────────────

A learner who signs in correctly forty times in an hour is doing nothing wrong.
Counting success would lock out the one person who is definitely entitled to be
here, which is a self-inflicted denial of service. Only `penalise()` - called
on a REFUSED attempt - moves the counter.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Limit:
    """`count` attempts inside `per_seconds`, then locked for `block_seconds`.

    THE BLOCK IS SEPARATE FROM THE WINDOW ON PURPOSE. A plain sliding window
    lets an attacker settle into a steady drip - exactly at the limit, forever,
    which over a night is a lot of guesses. A block turns the fifth failure
    into a real pause rather than a queue position.
    """
    count: int
    per_seconds: int
    block_seconds: int


class RateLimiter:
    """Sliding-window counters with a cooldown, keyed by arbitrary strings.

    Thread-safe because uvicorn runs sync endpoints in a threadpool: two
    requests really can be inside this at once, and a read-modify-write on a
    plain dict would drop counts under precisely the concurrent load a
    brute-force attempt produces.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._blocked: dict[str, float] = {}
        self._lock = threading.Lock()

    # ── queries ───────────────────────────────────────────────────────────

    def retry_after(self, key: str, limit: Limit, *, now: float | None = None) -> int:
        """Seconds until `key` may try again. 0 means it may try now.

        READ-ONLY. Call this BEFORE doing the work; a limiter that only counted
        after the fact would still let the expensive part run.
        """
        at = now if now is not None else time.monotonic()
        with self._lock:
            until = self._blocked.get(key)
            if until is not None:
                if until > at:
                    return max(1, int(until - at) + 1)
                del self._blocked[key]
            return 0

    def allowed(self, key: str, limit: Limit, *, now: float | None = None) -> bool:
        return self.retry_after(key, limit, now=now) == 0

    # ── mutation ──────────────────────────────────────────────────────────

    def penalise(self, key: str, limit: Limit, *, now: float | None = None) -> int:
        """Record ONE failed attempt. Returns the block in seconds, or 0.

        Called only on refusal. The window is pruned on the way in, which is
        also the only garbage collection this structure gets - a key nobody
        touches keeps a few floats until `sweep()` runs.
        """
        at = now if now is not None else time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            cutoff = at - limit.per_seconds
            while hits and hits[0] <= cutoff:
                hits.popleft()
            hits.append(at)
            if len(hits) >= limit.count:
                self._blocked[key] = at + limit.block_seconds
                hits.clear()
                # The KEY is logged, and callers hash the account half of it -
                # see _account_key. An email address in an application log is a
                # disclosure in its own right.
                log.warning("rate limit tripped: key=%s blocked=%ds",
                            key, limit.block_seconds)
                return limit.block_seconds
            return 0

    def clear(self, key: str) -> None:
        """Forget a key. Called on SUCCESS, so a learner who mistypes twice and
        then gets it right does not carry those two failures into tomorrow."""
        with self._lock:
            self._hits.pop(key, None)
            self._blocked.pop(key, None)

    def reset(self) -> None:
        """Everything. For tests - nothing in the app calls this."""
        with self._lock:
            self._hits.clear()
            self._blocked.clear()

    def sweep(self, *, now: float | None = None, older_than: int = 3600) -> int:
        """Drop keys nobody has touched. Housekeeping, not security.

        Unbounded growth here is a real memory leak with an attacker's hand on
        the tap: every distinct address tried creates a key.
        """
        at = now if now is not None else time.monotonic()
        gone = 0
        with self._lock:
            for key in [k for k, v in self._hits.items()
                        if not v or v[-1] < at - older_than]:
                del self._hits[key]
                gone += 1
            for key in [k for k, v in self._blocked.items() if v < at]:
                del self._blocked[key]
        return gone


#: The process-wide limiter. One instance, because one worker.
limiter = RateLimiter()
