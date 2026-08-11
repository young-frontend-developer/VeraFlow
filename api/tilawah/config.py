# -*- coding: utf-8 -*-
"""Settings from environment. See .env.example."""
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Load api/.env before the field defaults below are evaluated. Without this the
# file is decorative: uvicorn only reads .env when you pass --env-file, so every
# value here silently fell back to its default no matter what the file said.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # dotenv rides along with uvicorn[standard]; don't hard-fail
    pass


@dataclass(frozen=True)
class Settings:
    model_id: str = os.getenv("TILAWAH_MODEL_ID", "obadx/muaalem-model-v3_2")
    model_device: str = os.getenv("TILAWAH_MODEL_DEVICE", "cpu")
    # float32, deliberately. bfloat16 halves the model to ~1.3 GB but there is
    # no native bf16 compute path on a typical x86 CPU, so torch emulates it by
    # upconverting every matmul. Measured on the same clip, same output:
    #
    #     float32   1.33 s   2.6 GB peak
    #     bfloat16 19.68 s   1.3 GB peak     <- 15x slower, identical phonemes
    #
    # Trading 1.3 GB of RAM for 15x latency is the wrong way round when memory
    # costs a few euros a month and latency is the practice loop.
    model_dtype: str = os.getenv("TILAWAH_MODEL_DTYPE", "float32")

    database_url: str = os.getenv("TILAWAH_DATABASE_URL", "sqlite:///./tilawah.db")
    cors_origins: str = os.getenv("TILAWAH_CORS_ORIGINS", "http://localhost:5173")

    # 16 kHz 16-bit mono PCM is 32 KB/s, and the longest ayah recited slowly is
    # ~248 s => ~7.9 MB. The old 6 MB ceiling predates whole-ayah practice and
    # would truncate the longest ayat; 12 MB clears the worst case with room to
    # spare. The recorder downsamples to 16 kHz before upload, so this is a
    # bound on duration and not on whatever rate the browser felt like using.
    max_upload_bytes: int = int(os.getenv("TILAWAH_MAX_UPLOAD_BYTES", 12_000_000))

    # The longest recitation the engine will attempt, in seconds.
    #
    # THIS IS A MEMORY LIMIT, NOT A TASTE ONE, and it is quadratic. wav2vec2-BERT
    # relative-position attention allocates a [frames, frames, 64] float32
    # tensor, and the model runs at 47 frames/s:
    #
    #     bytes = (47 * seconds)^2 * 256
    #
    #      52 s ->  1.5 GB   measured OK   (522 s wall, ~10x realtime)
    #      90 s ->  4.6 GB   the default below
    #     129 s ->  9.4 GB   measured FAILURE - DefaultCPUAllocator OOM on 8 GB
    #
    # 90 s covers 99.0% of the Quran recited whole at the slow-reciter rate; the
    # remaining 60 ayat need the "practise part of this ayah" control. Raise it
    # on a box with more RAM - the formula above is how to size it, and the
    # engine degrades to a clean retry rather than a 500 if it is set too high.
    max_audio_seconds: float = float(os.getenv("TILAWAH_MAX_AUDIO_SECONDS", 90))

    # THE PRACTICE PASS MARK - the score a re-read must reach before the next
    # rung of the ladder unlocks.
    #
    # A CONFIG VALUE AND NOT A CONSTANT, deliberately, because nobody knows what
    # it should be yet. The score is the fraction of the range's sounds that
    # produced no error (see pipeline.accuracy), so 0.9 means "at most one
    # sound in ten". That number is a guess made before any learner has used
    # the ladder: set too high it locks a beginner out of their own practice,
    # set too low it waves through the mistake they are drilling. Tune it from
    # real attempts once there are some - the data is already being logged.
    #
    # It is NOT the whole gate. Passing also requires the specific error the
    # card is about to be absent from the re-read; see the recovery loop in
    # Recite.tsx. A learner can score 0.95 while still making exactly the
    # mistake they were sent to fix, and that must not unlock anything.
    # LOWERED FROM 0.9 TO 0.8 on 2026-08-07, by decision rather than by
    # measurement. 0.9 was rejecting recitations at 0.88 and sending learners
    # back to the same ayah six and seven times, which is the failure mode this
    # value was always most likely to have: it is a gate on somebody's practice,
    # and set high it does not raise standards, it just stops the session.
    # Perfection is not what this app is for. The client also caps re-reads at
    # three per card regardless of score - see web/src/lib/retry.ts - so the
    # threshold can no longer trap anybody even if it is still too high.
    practice_pass: float = float(os.getenv("TILAWAH_PRACTICE_PASS", 0.8))

    # Learner voice is never retained unless the learner asked for it to be.
    # This flag only permits the offer to be made; the per-user consent in
    # User.audio_consented is what actually authorises a write. Turning it off
    # disables audio retention for everyone regardless of what they consented to,
    # which is the switch you want if something goes wrong.
    collect_audio: bool = os.getenv("TILAWAH_COLLECT_AUDIO", "0") == "1"

    # OPERATOR DIAGNOSTIC MODE - stores every upload with NO consent at all.
    # For a laptop while debugging, never for a box real people can reach.
    # main.py refuses to start with this on unless TILAWAH_ENV=dev.
    debug_audio: bool = os.getenv("TILAWAH_DEBUG_AUDIO", "0") == "1"
    debug_dir: str = os.getenv("TILAWAH_DEBUG_DIR", "")

    # ── sessions ──────────────────────────────────────────────────────────
    #
    # OPAQUE TOKENS, NOT JWT, and the reason is this app's deletion promise.
    # Revoking consent must really destroy the learner's data; a stateless JWT
    # stays valid until it expires no matter what the database says, so "delete
    # everything" would leave a working credential behind. Every request
    # already touches the database, so the lookup costs nothing worth counting.
    session_ttl_days: int = int(os.getenv("TILAWAH_SESSION_TTL_DAYS", 30))

    # Cookie transport for the browser. The SAME session works as a bearer
    # token for a native client - one auth system, two ways to carry it.
    session_cookie_name: str = os.getenv("TILAWAH_SESSION_COOKIE", "tilawah_session")
    # Secure defaults to off ONLY because dev runs on plain http; production
    # must set it. See the launch checklist in the Phase 2 report.
    session_cookie_secure: bool = os.getenv("TILAWAH_SESSION_COOKIE_SECURE", "0") == "1"
    # lax | strict | none. `lax` refuses to send the cookie on a cross-site
    # POST, which is the CSRF protection this relies on. Note the consequence:
    # the dev client on :5173 talking to the api on :8000 is CROSS-SITE, so the
    # browser will not attach the cookie there - dev uses the bearer header.
    session_cookie_samesite: str = os.getenv("TILAWAH_SESSION_COOKIE_SAMESITE", "lax")

    # ── the device-claim window ───────────────────────────────────────────
    #
    # Whether POST /api/auth/anonymous will hand a session to whoever presents
    # an existing device id.
    #
    # THIS IS A BEARER EXCHANGE AND IT IS NOT AN AUTHENTICATION MECHANISM. A
    # device id proves nothing: it has been travelling in query strings into
    # access logs, browser history and every proxy since the first release, so
    # anyone who harvested one can claim that learner's history while this is
    # open. It exists for exactly one job - carrying existing anonymous installs
    # onto real sessions once - and it is worth the risk only because the same
    # id is ALREADY full authority on /api/attempts and /api/consent today.
    # Closing this window is a strict security improvement over the status quo,
    # never a regression.
    #
    # IT IS TEMPORARY BY CONSTRUCTION, NOT BY INTENTION. Intentions do not
    # survive a busy quarter. Two mechanisms make that real:
    #
    #   * production REFUSES TO BOOT with claiming on and no deadline set
    #     (see api/main.py), so it cannot reach a public deployment by anyone
    #     forgetting a variable;
    #   * past the deadline the endpoint stops claiming on its own, with no
    #     deploy required, so an unattended box closes its own window.
    #
    # NEVER extend this to cover new installs, and never let a client depend on
    # it after the migration. When it is done: TILAWAH_ALLOW_DEVICE_CLAIM=0.
    allow_device_claim: bool = os.getenv("TILAWAH_ALLOW_DEVICE_CLAIM", "1") == "1"
    # ISO date, e.g. 2026-09-30. The last day claiming works. Mandatory in
    # production whenever claiming is on; optional in dev, where an open-ended
    # window is only ever pointed at a laptop.
    device_claim_until: str = os.getenv("TILAWAH_DEVICE_CLAIM_UNTIL", "")

    # ── Google sign-in ────────────────────────────────────────────────────
    #
    # A COMMA-SEPARATED ALLOWLIST, NOT ONE VALUE, and this is the detail that
    # breaks Google integrations most often. The `aud` claim carries whichever
    # OAuth client obtained the token, and a project has several: the web
    # client today, an Android client later. Android's Credential Manager is
    # worse than it looks - it returns a token whose `aud` is the WEB/server
    # client id, not the Android one - so hardcoding a single audience either
    # rejects the web or rejects the phone, and the error says only "wrong
    # audience".
    #
    # Empty means Google sign-in is switched off: the endpoints answer 503 and
    # the client keeps its honest "not ready yet" line rather than showing a
    # button that cannot work.
    google_client_ids: str = os.getenv("TILAWAH_GOOGLE_CLIENT_IDS", "")

    # How long a login nonce stays usable. Short on purpose - it is consumed
    # within seconds of being handed out, and its whole job is to make sure the
    # credential arriving back was requested by THIS browser.
    google_nonce_ttl_seconds: int = int(
        os.getenv("TILAWAH_GOOGLE_NONCE_TTL_SECONDS", 300))

    env: str = os.getenv("TILAWAH_ENV", "dev")           # dev | production
    # Shows the "not yet fully verified" banner. Also raised automatically while
    # any learner-facing correction is unreviewed, so it cannot be forgotten.
    pilot: bool = os.getenv("TILAWAH_PILOT", "1") == "1"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() in ("production", "prod")

    @property
    def google_audiences(self) -> list[str]:
        """Every OAuth client id whose tokens this server will accept."""
        return [c.strip() for c in self.google_client_ids.split(",") if c.strip()]

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_audiences)

    @property
    def claim_deadline(self) -> "date | None":
        """The configured last day of the claim window, or None if unset.

        Raises ValueError on a malformed date rather than shrugging. A typo in
        this variable must not read as "no deadline" - that is precisely the
        failure that would leave the window open forever.
        """
        raw = (self.device_claim_until or "").strip()
        if not raw:
            return None
        return date.fromisoformat(raw)

    @property
    def device_claim_open(self) -> bool:
        """Whether a device id may still be exchanged for a session, right now.

        Three ways to be closed, and the last one needs no deploy:
          * the flag is off;
          * production with no deadline (main.py refuses to boot in that state,
            so this is the belt to that braces);
          * today is past the deadline.
        """
        if not self.allow_device_claim:
            return False
        try:
            deadline = self.claim_deadline
        except ValueError:
            return False
        if deadline is None:
            return not self.is_production
        return date.today() <= deadline

    @property
    def show_unreviewed(self) -> bool:
        """Whether unreviewed corrections reach the screen, marked as drafts.

        DERIVED FROM THE ENVIRONMENT, not from its own flag. It used to be
        TILAWAH_SHOW_UNREVIEWED, defaulting off - which meant the default build
        showed a learner only the codes a qori had signed off. With 2 of 11
        authored codes reviewed, that was almost nothing: three real mistakes
        surfaced as one, or as "we couldn't fully assess". The gate was not
        protecting anyone, it was hiding the product from the person building
        it, and an opt-in flag is the wrong shape for something you want on
        every single development run.

        So the polarity is inverted and the flag is gone. Drafts show by default
        and the gate closes only in production, where the safety property that
        matters - no unreviewed ruling about the Quran presented as settled -
        is now structural rather than one unset variable away from failing.

        Everything unreviewed still travels marked `draft`, and the client must
        render that marker; see pipeline.present().
        """
        return not self.is_production


settings = Settings()
