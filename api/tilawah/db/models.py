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

from sqlmodel import JSON, Column, Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: str = Field(primary_key=True)          # anonymous device id for MVP
    lang: str = Field(default="uz")
    consented: bool = Field(default=False)     # gates retention of attempts
    # Separate and stricter than `consented`. Keeping a transcript of what you
    # recited is not the same as keeping a recording of your voice, and one does
    # not imply the other - so it is asked separately and defaults to off.
    audio_consented: bool = Field(default=False)
    consent_seen: bool = Field(default=False)  # has been shown the choice
    created_at: datetime = Field(default_factory=_now)


class Attempt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user.id")
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
