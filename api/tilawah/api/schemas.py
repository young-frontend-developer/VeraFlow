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


class AttemptOut(BaseModel):
    id: int | None = None
    sura: int = 0
    aya: int = 0
    status: str                 # ok | retry_recording | error
    reason: str = ""            # too_noisy | too_short | ...
    clean: bool = False
    suppressed: bool = False
    errors: list = []
    snr_db: float = 0.0
    duration_s: float = 0.0


class WrongFlagIn(BaseModel):
    note: str | None = None
