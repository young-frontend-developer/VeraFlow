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
    created_at: datetime = Field(default_factory=_now)


class Attempt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user.id")
    sura: int
    aya: int
    created_at: datetime = Field(default_factory=_now, index=True)

    status: str                                 # ok | retry_recording | error
    clean: bool = False
    suppressed: bool = False
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
