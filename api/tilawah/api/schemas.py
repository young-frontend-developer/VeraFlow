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


class PracticeSegmentOut(BaseModel):
    """One practice-sized range of an ayah, indexed relative to the ayah.

    `seconds` is the median-reciter estimate - the honest number for most
    people. The slow-reciter rate that decides whether a range fits under the
    cap is deliberately not exposed: it reads as pessimistic and wrong.
    """
    index: int
    start_word: int
    num_words: int
    n_phonemes: int
    seconds: float
    uthmani: str


class AyahSegmentsOut(BaseModel):
    sura: int
    aya: int
    n_words: int
    legal_cuts: list[int]
    segments: list[PracticeSegmentOut]


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
    version: str = "0.1.0"
