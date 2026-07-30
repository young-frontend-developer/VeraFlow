# -*- coding: utf-8 -*-
"""Expected phonemes + sifat for an ayah.

Decision 1: the target is COMPUTED, not predicted. The learner picks the ayah,
so the correct phoneme sequence is deterministic from Uthmani text + riwayah.
The task is diff-against-known-target, not speech-to-text.

Cached forever - the target for a given ayah never changes.
"""
from dataclasses import dataclass
from functools import lru_cache

from quran_transcript import Aya, quran_phonetizer

from .moshaf import MOSHAF


@dataclass(frozen=True)
class Target:
    sura: int
    aya: int
    uthmani: str
    phonemes: str
    n_sifat: int

    @property
    def key(self) -> str:
        return f"{self.sura:03d}_{self.aya:03d}"


@lru_cache(maxsize=512)
def target_for(sura: int, aya: int) -> Target:
    uthmani = Aya(sura, aya).get().uthmani
    out = quran_phonetizer(uthmani, MOSHAF, remove_spaces=True)
    return Target(sura=sura, aya=aya, uthmani=uthmani,
                  phonemes=out.phonemes, n_sifat=len(out.sifat))


@lru_cache(maxsize=512)
def _phonetized(sura: int, aya: int):
    """The raw phonetizer output - the model needs this object, not the string."""
    return quran_phonetizer(Aya(sura, aya).get().uthmani, MOSHAF, remove_spaces=True)
