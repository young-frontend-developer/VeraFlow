# -*- coding: utf-8 -*-
"""Wire types. Deliberately does NOT expose silent_errors - those are internal
promotion evidence, not learner-facing."""
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


class AyahBriefOut(BaseModel):
    """Enough to choose an ayah, not enough to recite one."""
    aya: int
    uthmani: str
    n_words: int
    n_segments: int
    seconds: float


class SuraAyatOut(BaseModel):
    sura: int
    name_ar: str
    translit: str
    n_ayat: int
    ayat: list[AyahBriefOut]


class PracticeSegmentOut(BaseModel):
    """One practice-sized range of an ayah, indexed relative to the ayah.

    `seconds` is the median-reciter estimate - the honest number for most
    people. The slow-reciter rate that decides whether a range fits under the
    cap is deliberately not exposed: it reads as pessimistic and wrong.

    `text_segments` are the letter-groups for THIS range, with unit indices
    relative to the range. They travel with the segment so that picking one
    gives the client everything it needs to preview it and, later, to place a
    highlight on it - without a second round trip per selection.
    """
    index: int
    start_word: int
    num_words: int
    n_phonemes: int
    seconds: float
    uthmani: str
    text_segments: list[SegmentOut] = []


class AyahSegmentsOut(BaseModel):
    sura: int
    aya: int
    n_words: int
    legal_cuts: list[int]
    segments: list[PracticeSegmentOut]


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
    suppressed: bool = False
    errors: list = []
    snr_db: float = 0.0
    duration_s: float = 0.0


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
    # TILAWAH_SHOW_UNREVIEWED is on: the review gate is bypassed and errors
    # arrive carrying `draft`. Exposed so the client can say so at the top of
    # the screen rather than leaving the marker on individual cards to carry it.
    show_unreviewed: bool = False
    version: str = "0.1.0"
