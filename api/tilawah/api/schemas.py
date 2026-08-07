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
