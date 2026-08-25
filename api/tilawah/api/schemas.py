# -*- coding: utf-8 -*-
"""Wire types. Deliberately does NOT expose silent_errors - those are internal
promotion evidence, not learner-facing."""
from datetime import datetime

from pydantic import BaseModel


class SegmentOut(BaseModel):
    """One letter-group of the ayah. `start`/`end` index the Uthmani string so
    the client can measure a Range without splitting the text - Arabic is
    cursive and slicing it into separate elements breaks the joining forms."""
    text: str
    start: int
    end: int
    units: list[int]


class AyahOut(BaseModel):
    sura: int
    aya: int
    slug: str
    level: int
    uthmani: str
    name_uz: str
    name_ru: str
    segments: list[SegmentOut]


class SuraOut(BaseModel):
    """One row of the picker. `search` is a prefolded haystack - number,
    both transliterations and the Arabic name - so the client filters with a
    plain substring test and every spelling finds the same sura."""
    number: int
    name_ar: str
    translit: str
    uz: str
    n_ayat: int
    search: str
    # makki | madani, for the picker's filter pills.
    #
    # Defaulted rather than required, so a server running against a suras.json
    # built before this column existed answers with an empty string instead of
    # failing validation on all 114 rows. The client treats "" as "unknown" and
    # such a sura simply does not match either filter - it is never guessed
    # into one. See the provenance note in suras.json's _meta: this follows the
    # Cairo mushaf's designation and is compiled, not reviewed.
    place: str = ""


class AyahBriefOut(BaseModel):
    """Enough to read an ayah and choose it, not enough to score one."""
    aya: int
    uthmani: str
    n_words: int
    n_segments: int
    seconds: float
    # Translation in the requested language. Carried on the ayah rather than
    # fetched per verse so the verse-by-verse reader's arrows are instant -
    # a round trip per tap would make paging through a sura feel broken.
    translation: str = ""


class SuraAyatOut(BaseModel):
    sura: int
    name_ar: str
    translit: str
    n_ayat: int
    ayat: list[AyahBriefOut]
    # Whether the sura opens with the basmala as a separate line in the mushaf.
    # True everywhere except al-Fatiha (where it is ayah 1) and at-Tawba (where
    # there is none) - so it cannot be assumed and cannot be hardcoded to one
    # exception. Drives the mushaf view's opening line.
    has_basmala: bool = False
    bismillah: str = ""


class ReciterOut(BaseModel):
    """One everyayah reciter, verified present at build time."""
    id: str                    # the everyayah folder
    name: str
    style: str                 # muallim | murattal | mujawwad
    bitrate_kbps: int = 0


class RecitersOut(BaseModel):
    default: str
    base_url: str
    reciters: list[ReciterOut]


class RuleBadgeOut(BaseModel):
    """A tajweed rule that is STRUCTURALLY PRESENT in a range.

    Not an error. This says "this passage contains a madd lozim", which is a
    fact about the Qur'an and true whether or not the learner read it well -
    the whole point is that a flawless recitation still shows what it just
    executed. See engine/rule_presence.py.

    `reviewed` travels with each badge for the same reason it travels with an
    error: the gate is the server's decision, not the client's, and a client
    that had to infer it from `status` would eventually infer it wrong.
    """
    code: str
    color: str
    name: str
    rule: str
    example: str = ""
    target: str = ""
    source: str = ""
    reviewed: bool = False
    #: Uthmani character ranges this rule governs, so the client can colour the
    #: GLYPHS and not just name the rule underneath them. Same coordinates as an
    #: error mark's `span`, from the same map, so a rule colour and an error
    #: mark on one sound cannot disagree about where that sound is.
    #:
    #: Empty is a real answer and means "found in this passage but not placed" -
    #: the idgham token-count proxy is the standing example. The client must
    #: draw nothing for those rather than fall back to colouring the whole word.
    spans: list[list[int]] = []


class PracticeSegmentOut(BaseModel):
    """One practice-sized range of an ayah, indexed relative to the ayah.

    `seconds` is the median-reciter estimate - the honest number for most
    people. The slow-reciter rate that decides whether a range fits under the
    cap is deliberately not exposed: it reads as pessimistic and wrong.

    `text_segments` are the letter-groups for THIS range, with unit indices
    relative to the range. They travel with the segment so that picking one
    gives the client everything it needs to preview it and, later, to place a
    highlight on it - without a second round trip per selection.

    `rules` are the tajweed rules that occur in THIS range, computed from the
    reference script. They ride along with the segment for the same reason the
    letter-groups do: the client needs them to draw the range and must not have
    to ask a second time per selection.
    """
    index: int
    start_word: int
    num_words: int
    n_phonemes: int
    seconds: float
    uthmani: str
    text_segments: list[SegmentOut] = []
    rules: list[RuleBadgeOut] = []


class AyahSegmentsOut(BaseModel):
    """The whole ayah, plus the optional way to break it up.

    `whole` is THE practice range. It is always present, for every ayah, at any
    length, and it is what the client selects unless the learner asks for
    something narrower. Segmentation used to decide this - 72% of ayat were
    split before anyone was asked - and that was the wrong call: the model reads
    long ayat correctly, and everyayah serves whole-ayah audio only, so a split
    range also had no reciter recording to play against it.

    `parts` is the optional "practise part of this ayah" list. Empty when the
    ayah is short enough to be a single part anyway, so a non-empty `parts` is
    exactly the condition for offering the control.
    """
    sura: int
    aya: int
    n_words: int
    legal_cuts: list[int]
    whole: PracticeSegmentOut
    parts: list[PracticeSegmentOut] = []


class ReviewEntryOut(BaseModel):
    """One registry entry awaiting a qori's decision.

    `uz` is the full Uzbek block, sent verbatim — the review screen renders it
    in the learner's own card layout, because a reviewer has to sign off what a
    learner will actually read, not a JSON dump of it.
    """
    code: str
    group: str
    severity: str
    detection_confidence: str
    source_ref: str = ""
    status: str                       # draft | reviewed | rejected
    reviewed_by: str = ""
    reviewed_at: str = ""
    review_note: str = ""
    uz_edited_fields: list[str] = []
    uz: dict = {}
    # Straight from the frequency ranking — this is the review ORDER, and the
    # reach that justifies it.
    review_order: int = 0
    beginner_pct: float = 0.0
    all_pct: float = 0.0


class ReviewQueueOut(BaseModel):
    total: int                        # in-scope, rankable entries
    reviewed: int
    rejected: int
    remaining: int
    entries: list[ReviewEntryOut]
    ranking_stale: bool = False       # ranking file missing entries in scope


class ReviewDecisionIn(BaseModel):
    action: str                       # approve | reject | edit | reset
    reviewed_by: str = ""
    note: str = ""
    uz: dict = {}


class AttemptOut(BaseModel):
    id: int | None = None
    sura: int = 0
    aya: int = 0
    start_word: int = 0
    num_words: int = 0
    include_bismillah: bool = False
    status: str                 # ok | retry_recording | error
    reason: str = ""            # too_noisy | too_short | ...
    clean: bool = False
    # Detected something, showed nothing - the production content gate withheld
    # every correction. A judgement WAS formed.
    suppressed: bool = False
    # The model returned nothing to compare against, so no judgement was formed
    # at all. Kept separate from `suppressed` because the two are different
    # failures and printing one sentence for both makes them indistinguishable.
    analysable: bool = True
    errors: list = []
    snr_db: float = 0.0
    duration_s: float = 0.0
    # Fraction of the recited range's sounds with no error against them, and the
    # mark a practice rung must clear before the next unlocks. `pass_score` is
    # sent rather than hard-coded in the client so it can be tuned from real
    # usage without shipping a new bundle - see Settings.practice_pass.
    score: float = 0.0
    pass_score: float = 0.0
    # WHEN IT HAPPENED. Added for the Today screen's week view and its
    # "last practiced N ago" line, and it is the only reason both of those can
    # exist: without a real timestamp the alternatives were to draw a week
    # strip with invented days on it or to leave the section out. The column
    # has always been on the row (Attempt.created_at, indexed); it simply was
    # never sent. None on legacy rows written before it was populated, and the
    # client omits the day rather than guessing one.
    created_at: datetime | None = None
    # HOW MANY ARABIC LETTERS WERE IN WHAT THEY RECITED.
    #
    # The hasanat total on Home is built on this and on nothing else. It is
    # computed on the server from the Uthmani text of the stored range - see
    # content/letters.py, which documents what does and does not count as a
    # letter, and why, against the wording of the hadith it rests on.
    #
    # Sent rather than derived in the browser because the client only ever
    # holds one sura's text at a time while history spans many; deriving it
    # there would have meant estimating, and an estimated number with a hadith
    # attached to it is the one thing this must not be.
    #
    # 0 on a range that cannot be resolved. Never a guess.
    letters: int = 0
    wrong_flag: bool = False


class HadithOut(BaseModel):
    """The day's hadith, with its citation.

    The citation is three separate fields rather than one joined string so the
    client formats it and a reviewer can see exactly which collection and
    number is being claimed. `draft` obliges the client to mark it, the same as
    a draft correction card.
    """
    id: str = ""
    ar: str = ""
    text: str = ""
    collection: str = ""
    ref: str = ""
    grading: str = ""
    draft: bool = True


class WrongFlagIn(BaseModel):
    note: str | None = None


class MetaOut(BaseModel):
    """Client-visible state of the deployment itself.

    `pilot` drives the "not yet fully verified" banner. It is derived from the
    content review state as well as an env flag, so the banner cannot outlive
    the condition it warns about, and cannot be forgotten either.
    """
    pilot: bool = False
    unverified_codes: list[str] = []
    collect_audio_offered: bool = False   # may the audio consent even be shown
    # The review gate is open, so unreviewed errors arrive carrying `draft`.
    # True outside production. Exposed so the client can say so at the top of
    # the screen rather than leaving the marker on individual cards to carry it.
    show_unreviewed: bool = False
    # Longest recitation the engine will attempt, in seconds. Sent so the client
    # can warn BEFORE recording: the wall-clock cost is ~10x realtime, so
    # discovering the limit after the fact means a multi-minute wait for a
    # rejection. See Settings.max_audio_seconds.
    max_audio_seconds: float = 0.0
    # Coaching registries the server expected and could not find. Non-empty
    # means some codes are still rendering their older rules.json wording; it
    # is surfaced rather than logged once at boot so the gap cannot quietly
    # become permanent.
    missing_registries: list[str] = []
    # Registry entries naming an isolated letter recording that is not on disk.
    # Every one of these is a practice button the client is hiding. Surfaced for
    # the same reason as missing_registries: the alternative to a dead control
    # is a missing one, and a missing one has to stay countable.
    missing_audio: list[str] = []
    # Every field this server puts on an error object. The client compares it
    # against what its card component dereferences and says so plainly when
    # they disagree.
    #
    # This exists because a stale API process is invisible from the browser: a
    # server started before a field was added keeps answering happily, the
    # client throws on every card, and the only symptom is a broken results
    # screen with no cause attached. Declaring the shape turns that into a
    # named, actionable message.
    error_fields: list[str] = []
    version: str = "0.1.0"


# ── academy ──────────────────────────────────────────────────────────────

class LessonSummaryOut(BaseModel):
    id: int
    order: int
    slug: str
    difficulty: str
    title_uz: str
    title_ru: str
    practice_sura: int
    practice_aya: int
    video_url: str | None = None
    rule_codes: list[str] = []
    # per-user progress, filled at query time
    status: str = "locked"                  # locked | available | completed
    quiz_score: int | None = None
    practice_done: bool = False


class QuizQuestionOut(BaseModel):
    id: int
    order: int
    question_uz: str
    question_ru: str
    options_uz: list[str]
    options_ru: list[str]


class LessonDetailOut(BaseModel):
    id: int
    order: int
    slug: str
    difficulty: str
    title_uz: str
    title_ru: str
    body_uz: str
    body_ru: str
    practice_sura: int
    practice_aya: int
    video_url: str | None = None
    rule_codes: list[str] = []
    pass_score: int = 70
    quiz: list[QuizQuestionOut] = []
    status: str = "locked"
    quiz_score: int | None = None
    practice_done: bool = False


class QuizAnswerIn(BaseModel):
    answers: list[int]


class QuizResultOut(BaseModel):
    score: int
    passed: bool
    total: int
    correct_count: int
    results: list[dict]


# ── sessions ──────────────────────────────────────────────────────────────

class AnonymousSessionIn(BaseModel):
    """Bootstrap a session.

    `device_id` IS A MIGRATION AFFORDANCE, NOT A CREDENTIAL BY DESIGN. Sending
    one that already exists hands back a session for that learner, so their
    history survives the move to accounts. Omit it and a brand new anonymous
    user is created instead.

    It is a bearer exchange and it is temporary: device ids have been visible
    in access logs since the first release. Gated by settings.allow_device_claim
    so the window can be closed the moment the client stops needing it.
    """
    device_id: str | None = None


class SessionOut(BaseModel):
    """A freshly minted session.

    `token` IS RETURNED EXACTLY ONCE AND NEVER AGAIN. Only its hash is stored,
    so it cannot be re-read, re-sent, or recovered from the database - if the
    client loses it, the only remedy is a new session.
    """
    token: str
    token_type: str = "bearer"
    expires_at: datetime
    user_id: str
    # True when this session was issued against an existing device id rather
    # than a newly created user. The client can tell "your practice came with
    # you" from "welcome, you are new".
    claimed_existing: bool = False


class MeOut(BaseModel):
    """Who the current session belongs to.

    `providers` is always empty in this phase - AuthIdentity exists but nothing
    writes to it yet. It is present so the client has a stable shape to read
    before Google lands, rather than a field that appears later.
    """
    user_id: str
    lang: str
    consented: bool
    audio_consented: bool
    consent_seen: bool
    # Anonymous is a first-class state, not a lesser one. Derived from whether
    # any AuthIdentity row points here - never stored, so it cannot drift.
    is_anonymous: bool
    email: str | None = None
    display_name: str | None = None
    picture: str | None = None
    providers: list[str] = []
    session_expires_at: datetime


# ── Google sign-in ────────────────────────────────────────────────────────

class GoogleStartOut(BaseModel):
    """What the client needs before it may ask Google for a credential.

    The nonce is single-use and short-lived. Google embeds it in the ID token,
    and a token carrying a nonce this server did not just issue is refused -
    which is what stops an attacker pushing their own Google credential into
    someone else's browser and silently signing them into the wrong account.
    """
    nonce: str
    client_id: str
    expires_in: int


class GoogleSignInIn(BaseModel):
    """The ID token exactly as Google handed it to the browser.

    THERE IS NO `subject` FIELD AND THERE MUST NEVER BE ONE. The Google account
    is whatever the signature proves, never what the caller says it is.
    """
    credential: str
    nonce: str | None = None


class GoogleSessionOut(SessionOut):
    """A session, plus what just happened to the account behind it."""
    # True when this call attached Google to an existing anonymous account.
    # The client uses it to say "your practice came with you" rather than
    # guessing from the absence of an error.
    linked_now: bool = False
    providers: list[str] = []
    email: str | None = None
    display_name: str | None = None


# ── email / password sign-in ──────────────────────────────────────────────
#
# NO TYPE IN THIS SECTION CARRIES A PASSWORD OUTWARDS. The two `In` models take
# one and nothing else does - a response model has no password field to
# accidentally populate, which is a stronger guarantee than remembering to
# strip one. Do not add `password` to any `Out`.

class RegisterIn(BaseModel):
    """Create an email identity.

    The password is validated SERVER-SIDE by passwords.password_problems(),
    not by a pydantic constraint. Two reasons: the policy is more than a
    length (a blocklist, and a check against the address itself), and a
    pydantic violation returns 422 with the offending value echoed back inside
    the error detail - which would put the password in the response body and,
    from there, into whatever logs the client's errors.
    """
    email: str
    password: str
    #: Which language the verification mail should be written in. Defaults to
    #: the app's default rather than being required; a missing preference is
    #: not worth a 422 on a signup.
    lang: str = "uz"


class LoginIn(BaseModel):
    email: str
    password: str


class EmailSessionOut(SessionOut):
    """The result of a register or login that produced a session.

    Shaped like GoogleSessionOut on purpose: the client stores the token the
    same way whichever provider produced it, because it is the same session
    system underneath.
    """
    #: True when this call attached email to an existing ANONYMOUS account -
    #: i.e. the learner kept their practice history instead of starting over.
    linked_now: bool = False
    providers: list[str] = []
    email: str | None = None
    display_name: str | None = None
    #: Whether this address has been confirmed. False is a normal state, not an
    #: error: with verification not required, an account works unverified.
    email_verified: bool = False


class RegisteredOut(BaseModel):
    """Registration that did NOT produce a session, because verification is
    required and this address has not been confirmed yet.

    A SEPARATE SHAPE FROM EmailSessionOut, so the client cannot read a `token`
    field that is absent and treat "" as a session. The two responses are
    distinguished by `verification_required`.
    """
    verification_required: bool = True
    email: str
    #: Whether a message actually went out. False means no provider is wired -
    #: surfaced so a developer sees why no mail arrived instead of assuming a
    #: bug. It is NOT a per-address answer and never leaks whether an address
    #: exists; see the forgot-password route.
    sent: bool = False


class VerifyEmailIn(BaseModel):
    token: str


class ForgotPasswordIn(BaseModel):
    email: str
    lang: str = "uz"


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str


class EmailAuthErrorOut(BaseModel):
    """The body of a refused email-auth request.

    `code` is a STABLE MACHINE STRING and `problems` are the password policy
    codes from passwords.password_problems(). The client renders its own
    sentence in the learner's language; the server does not choose the wording
    and never returns a raw exception. See web/src/lib/i18n.ts.
    """
    code: str
    problems: list[str] = []
    #: Seconds until a throttled caller may retry. 0 when not throttled.
    retry_after: int = 0
