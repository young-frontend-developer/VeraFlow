# -*- coding: utf-8 -*-
"""Persistence. Decision 7: the moat is learner data, not the model.

Two things make this table worth more than the model itself:
  - `silent_errors` captures what the engine SAW but chose not to show. That is
    your promotion evidence for moving a code from collect -> teacher -> ship.
  - `wrong_flag` is the learner telling you the feedback was wrong. That is the
    label you cannot buy.

Consent is explicit and revocable: `consented` gates retention, and delete_user()
must actually delete. Get this right on day one - retrofitting deletion into a
system that assumed permanence is painful and, for this audience, a trust
failure you do not recover from.
"""
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlmodel import JSON, Column, Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """The person. NOT the device, and NOT the Google account.

    `id` HOLDS A DEVICE UUID FOR EVERY ROW WRITTEN BEFORE ACCOUNTS EXISTED, and
    it keeps it forever. That value is never rewritten - not when a Google
    identity is linked, not ever. Three things depend on that promise:

      * attempt.user_id points here, and sqlite does not enforce the foreign
        key retroactively, so rewriting an id would silently orphan a
        learner's whole history with no error anywhere.
      * stored audio is named with the same string (debug_capture._tag), so
        rewriting an id would make someone's voice recordings undeletable by
        the consent-revocation path. Deletion that misses the audio is not
        deletion.
      * it is a surrogate key. It means "this person", and it costs nothing to
        let it go on looking like a uuid.

    Provider identities hang off AuthIdentity instead, which is what lets Apple
    be a row rather than a migration.
    """
    id: str = Field(primary_key=True)          # opaque; a device uuid on legacy rows
    lang: str = Field(default="uz")
    consented: bool = Field(default=False)     # gates retention of attempts
    # Separate and stricter than `consented`. Keeping a transcript of what you
    # recited is not the same as keeping a recording of your voice, and one does
    # not imply the other - so it is asked separately and defaults to off.
    audio_consented: bool = Field(default=False)
    consent_seen: bool = Field(default=False)  # has been shown the choice
    created_at: datetime = Field(default_factory=_now)

    # ── account fields. All nullable: an anonymous user has none of them, and
    # anonymous is a first-class state here, not a lesser one.
    #
    # `email` IS A DISPLAY CONVENIENCE AND NEVER A LOOKUP KEY. Matching accounts
    # on email is how you build an account-takeover: an unverified address, or
    # Apple's private-relay address, is not proof that two identities are the
    # same person. Joins go through AuthIdentity.subject and nowhere else.
    email: str | None = Field(default=None)
    display_name: str | None = Field(default=None)
    # When a device id was exchanged for a real session. Bookkeeping for the
    # migration window; nothing reads it yet.
    claimed_at: datetime | None = Field(default=None)


class AuthIdentity(SQLModel, table=True):
    """One provider's claim about who a User is.

    SEPARATE TABLE ON PURPOSE. Google today, Apple later, and neither one is
    the account - they are both just ways of proving you are it. A user may
    hold several; unlinking one must not delete the person.

    UNIQUE(provider, subject) is the constraint the whole sign-in flow rests
    on: it is what makes "has this Google account been seen before?" a lookup
    rather than a guess. UNIQUE(user_id, provider) stops one user quietly
    accumulating two Google identities.
    """
    __tablename__ = "auth_identity"
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_identity_provider_subject"),
        UniqueConstraint("user_id", "provider", name="uq_identity_user_provider"),
    )

    id: int | None = Field(default=None, primary_key=True)
    # CASCADE so that delete_user() cannot leave a live UNIQUE(provider,
    # subject) row pointing at a person who no longer exists - which would lock
    # that Google account out of ever signing up again.
    user_id: str = Field(index=True, foreign_key="user.id", ondelete="CASCADE")
    provider: str                              # 'google' | 'apple' | 'email'
    # The provider's stable subject claim. NOT the email - Google's `sub` and
    # Apple's `sub` are permanent, addresses are not.
    #
    # FOR provider='email' THE SUBJECT *IS* THE NORMALISED ADDRESS, and that is
    # not a contradiction of the paragraph above. There, the address is one of
    # several things Google says about a person and the `sub` is the stable
    # one. Here there is no external authority at all: the address is the
    # account name, chosen by the learner, and the thing being proven is
    # possession of a password matched to it. It is normalised through
    # passwords.normalise_email() before it is ever written or looked up, so
    # UNIQUE(provider, subject) is what enforces one account per address -
    # including against a full-width or differently-cased spelling of one that
    # already exists.
    subject: str
    email: str | None = Field(default=None)    # informational; may be a relay address
    email_verified: bool = Field(default=False)
    picture: str | None = Field(default=None)
    # Argon2id, encoded with its own parameters and salt. NULL for every
    # provider except 'email', where it is the whole credential.
    #
    # NULLABLE AND NOT A SEPARATE TABLE because an identity row is exactly the
    # right grain: it is one way of proving you are a user, and for this
    # provider the proof is a password. A `password` table would need its own
    # answer to "what happens on delete" and would be one more thing that can
    # disagree with auth_identity about who the account belongs to.
    #
    # NEVER selected into a response model. See api/schemas.py - no wire type
    # carries this field, which is a stronger guarantee than remembering to
    # strip it.
    password_hash: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_now)
    last_login_at: datetime | None = Field(default=None)


class Device(SQLModel, table=True):
    """One install. Was the identity; is now a handle attached to one.

    Kept AFTER a Google account is linked, deliberately: stored audio is named
    with the id that recorded it, so throwing away the device row would strand
    those files. It also becomes the row that lets one account own several
    installs.
    """
    __tablename__ = "device"

    id: str = Field(primary_key=True)          # the device uuid the client holds
    user_id: str = Field(index=True, foreign_key="user.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=_now)
    last_seen_at: datetime = Field(default_factory=_now)


class OAuthNonce(SQLModel, table=True):
    """A one-shot value proving a Google credential was asked for by THIS browser.

    THE ATTACK THIS STOPS IS LOGIN CSRF, which reads backwards the first time.
    The attacker does not steal the victim's account - they push their OWN
    Google credential into the victim's browser, so the victim silently ends up
    signed in as the attacker and every recitation they make afterwards lands
    in the attacker's account. Nothing looks wrong from the inside.

    So the browser asks for a nonce first, Google embeds it in the ID token,
    and the token is refused unless the nonce is one we handed out and have not
    already spent. A credential minted for somebody else's login attempt
    carries the wrong nonce and dies here.

    ONLY THE HASH IS STORED, for the same reason auth_session stores only a
    hash: a leaked table should not hand anyone a usable value. Rows are
    consumed rather than deleted so a replay is distinguishable from an
    expiry - and because deleting the evidence of an attack is a poor trade.
    """
    __tablename__ = "oauth_nonce"

    id: int | None = Field(default=None, primary_key=True)
    nonce_hash: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=_now)
    expires_at: datetime
    consumed_at: datetime | None = Field(default=None)


class EmailToken(SQLModel, table=True):
    """A one-shot secret mailed to an address, for verifying it or for a reset.

    ONE TABLE FOR BOTH PURPOSES, separated by `purpose`, because they have
    identical mechanics - issue, mail, expire, consume once - and two tables
    would be two places to get "consumed" wrong. The purpose is checked on
    redemption, so a verification token cannot be spent as a password reset.
    That check is not optional: without it, the weaker of the two flows
    (verification, which may be issued on nothing more than a signup) would
    mint credentials for the stronger one (reset, which changes a password).

    ONLY THE HASH IS STORED, for the same reason as auth_session and
    oauth_nonce: a leaked table must not hand anyone a working credential, and
    a reset token IS a working credential - it is the entire proof required to
    take over an account.

    CONSUMED, NOT DELETED, matching OAuthNonce: a replay then finds the row
    already spent rather than racing a delete, and the evidence of an attempted
    replay survives.
    """
    __tablename__ = "email_token"

    id: int | None = Field(default=None, primary_key=True)
    token_hash: str = Field(index=True, unique=True)
    # CASCADE for the same reason every other auth row has it: this app
    # promises that deleting an account really deletes it, and a live reset
    # token pointing at a deleted user would be a credential outliving the
    # thing it authenticates.
    user_id: str = Field(index=True, foreign_key="user.id", ondelete="CASCADE")
    purpose: str = Field(index=True)           # 'verify' | 'reset'
    # The address it was SENT TO, normalised - which is not necessarily the
    # address on the identity row today. Verification must confirm the address
    # that was actually mailed, so that changing the address on the account
    # invalidates a verification already in flight rather than confirming the
    # new one on the strength of mail sent to the old one.
    email: str
    created_at: datetime = Field(default_factory=_now)
    expires_at: datetime
    consumed_at: datetime | None = Field(default=None)


class AuthSession(SQLModel, table=True):
    """A signed-in session. Opaque and revocable, not a JWT.

    NAMED AuthSession, NOT Session, because `sqlmodel.Session` is the database
    session and both are imported side by side all over this package. One of
    those collisions costs an afternoon.

    ONLY THE HASH IS STORED. A stolen database must not hand over working
    credentials, and this app already promises that revoking consent really
    destroys data - a token nobody can revoke would make that promise false.
    """
    __tablename__ = "auth_session"

    id: int | None = Field(default=None, primary_key=True)
    # sha256 of the bearer value. The value itself is shown to the client once
    # and never written down.
    token_hash: str = Field(index=True, unique=True)
    user_id: str = Field(index=True, foreign_key="user.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=_now)
    last_used_at: datetime = Field(default_factory=_now)
    expires_at: datetime
    revoked_at: datetime | None = Field(default=None)
    user_agent: str = Field(default="")


class Attempt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(sa_column=Column(ForeignKey("user.id", ondelete="CASCADE"), index=True))
    sura: int
    aya: int
    # The practice range, indexed RELATIVE TO THE AYAH. Never store encoded
    # indices: include_bismillah prepends the basmala into the index space, so
    # the same words carry different numbers depending on a flag, and history
    # would silently corrupt the moment bismillah handling changed.
    start_word: int = Field(default=0)
    num_words: int = Field(default=0)          # 0 = the whole ayah
    include_bismillah: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_now, index=True)

    status: str                                 # ok | retry_recording | error
    clean: bool = False
    suppressed: bool = False
    # Defaults true so rows written before this column existed read as "the
    # engine had an opinion", which is what they were.
    analysable: bool = True
    snr_db: float = 0.0
    duration_s: float = 0.0
    mean_prob: float = 0.0

    expected_phonemes: str = ""
    heard_phonemes: str = ""
    errors: list = Field(default=[], sa_column=Column(JSON))
    silent_errors: list = Field(default=[], sa_column=Column(JSON))

    audio_url: str | None = None                # only when consented + store_audio
    wrong_flag: bool = Field(default=False)     # "this feedback was wrong"
    wrong_note: str | None = None


# ── academy ──────────────────────────────────────────────────────────────

class Lesson(SQLModel, table=True):
    """One tajweed topic in the learning curriculum.

    Ordered sequentially: lesson N is available when lesson N-1 is completed.
    Content is bilingual (uz/ru) and ingested from partner-authored JSON via
    tools/ingest_lessons.py.
    """
    __tablename__ = "lesson"

    id: int | None = Field(default=None, primary_key=True)
    order: int = Field(index=True, unique=True)
    slug: str = Field(index=True, unique=True)
    difficulty: str = Field(default="beginner")   # beginner | intermediate | advanced
    title_uz: str = ""
    title_ru: str = ""
    body_uz: str = ""
    body_ru: str = ""
    rule_codes: list = Field(default=[], sa_column=Column(JSON))
    practice_sura: int = 0
    practice_aya: int = 0
    video_url: str | None = None
    pass_score: int = Field(default=70)
    published: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_now)


class QuizQuestion(SQLModel, table=True):
    """Multiple-choice question belonging to a lesson. 3-5 per lesson."""
    __tablename__ = "quiz_question"

    id: int | None = Field(default=None, primary_key=True)
    lesson_id: int = Field(index=True, foreign_key="lesson.id", ondelete="CASCADE")
    order: int = Field(default=0)
    question_uz: str = ""
    question_ru: str = ""
    options_uz: list = Field(default=[], sa_column=Column("options_uz", JSON))
    options_ru: list = Field(default=[], sa_column=Column("options_ru", JSON))
    correct: int = Field(default=0)
    explanation_uz: str | None = None
    explanation_ru: str | None = None


class LessonProgress(SQLModel, table=True):
    """Per-user completion state for a lesson."""
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user.id", ondelete="CASCADE")
    lesson_id: int = Field(index=True, foreign_key="lesson.id", ondelete="CASCADE")
    quiz_score: int | None = None
    practice_done: bool = Field(default=False)
    completed_at: datetime | None = None
    attempts: int = Field(default=0)
