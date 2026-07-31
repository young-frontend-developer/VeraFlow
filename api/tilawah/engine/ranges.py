# -*- coding: utf-8 -*-
"""Word ranges: which cuts are legal, how long a range takes to recite.

CUT POINTS
----------
quran_transcript indexes ranges by IMLAEY word but returns UTHMANI text, and the
two do not map one-to-one - 363 of 6236 ayat have at least one uthmani word
spelled as several imlaey words. Asking for a range that ends inside one raises
PartOfUthmaniWord, from utils.py::_decode_uthmani:

    if end in imlaey2uthmani:
        if imlaey2uthmani[end - 1] == imlaey2uthmani[end]:
            raise PartOfUthmaniWord(...)

So a boundary at imlaey index c is legal iff the words either side of it belong
to different uthmani words. The library only applies that check to `end`, but
`start` is a boundary too and fails identically - the Phase 0 audit found this
empirically (a predictor checking only `end` scored 98.79%; every miss was a
start-boundary case). Checking both scored 5042/5042.

That makes every failure predictable up front, so the UI offers only legal cuts
instead of catching exceptions - which matters, because probing them costs
~60 ms per call.

DURATION
--------
QPS repeats characters to encode length (madd letters repeat, ghunnah repeats),
so phoneme-string length is close to linear in recitation time. Calibrated
against Husary and Alafasy over 30 ayat spanning 7-267 phonemes:

    seconds = 0.186 x n_phonemes     R^2 = 0.912

but reciters vary a lot - 0.132 s/phoneme at p05, 0.232 at p95. One constant
cannot serve both jobs, so there are two:

    RATE_DISPLAY (median) - what the learner is told. Honest for most people.
    RATE_GATE   (slow p95) - what decides whether a range fits under the cap,
                             so a deliberate reciter is not cut off mid-ayah.

RATE_GATE is never shown to a learner: it reads as pessimistic and wrong for
the majority.
"""
from dataclasses import dataclass
from functools import lru_cache

from quran_transcript import Aya, quran_phonetizer

from .moshaf import MOSHAF

# seconds per phoneme - see module docstring for the calibration
RATE_DISPLAY = 0.1814
RATE_GATE = 0.2319

TARGET_SECONDS = 12.0      # what segmentation aims for
HARD_CAP_SECONDS = 20.0    # what nothing may exceed, measured at RATE_GATE


@dataclass(frozen=True)
class Range:
    """A practice range, indexed RELATIVE TO THE AYAH.

    Never store encoded indices: include_bismillah prepends the basmala into the
    index space, so the same words carry different numbers depending on a flag.
    Storing those would silently corrupt history the moment bismillah handling
    changed. `aya_imlaey_span_words` converts at call time - see reference().
    """
    sura: int
    aya: int
    start_word: int
    num_words: int
    include_bismillah: bool = False

    @property
    def key(self) -> str:
        b = "+b" if self.include_bismillah else ""
        return f"{self.sura:03d}_{self.aya:03d}_{self.start_word}_{self.num_words}{b}"


@lru_cache(maxsize=4096)
def word_map(sura: int, aya: int) -> tuple[tuple[int, int], ...]:
    """imlaey word index -> uthmani word index, as a hashable tuple of pairs."""
    enc = Aya(sura, aya)._encode_imlaey_to_uthmani()
    return tuple(sorted(dict(enc.imlaey2uthmani).items()))


@lru_cache(maxsize=4096)
def n_words(sura: int, aya: int) -> int:
    return len(Aya(sura, aya).get().imlaey_words)


def _as_dict(sura: int, aya: int) -> dict[int, int]:
    return dict(word_map(sura, aya))


def is_legal_cut(sura: int, aya: int, c: int) -> bool:
    """May the ayah be cut just before imlaey word `c`?"""
    n = n_words(sura, aya)
    if c <= 0 or c >= n:
        return True                     # the ends of the ayah always are
    m = _as_dict(sura, aya)
    return m.get(c - 1) != m.get(c)


@lru_cache(maxsize=4096)
def legal_cuts(sura: int, aya: int) -> tuple[int, ...]:
    """Every legal boundary position, 0..n inclusive."""
    n = n_words(sura, aya)
    return tuple(c for c in range(n + 1) if is_legal_cut(sura, aya, c))


def is_legal_range(sura: int, aya: int, start_word: int, num_words: int) -> bool:
    n = n_words(sura, aya)
    if num_words < 1 or start_word < 0 or start_word + num_words > n:
        return False
    return (is_legal_cut(sura, aya, start_word)
            and is_legal_cut(sura, aya, start_word + num_words))


def estimate_seconds(n_phonemes: int, *, gate: bool = False) -> float:
    """Recitation time. `gate=True` uses the slow-reciter rate - for deciding
    whether something fits, never for anything shown to a learner."""
    return n_phonemes * (RATE_GATE if gate else RATE_DISPLAY)


def reference(r: Range):
    """The phonetizer output for a range - the engine's target.

    Uses include_bismillah rather than joining strings. Hand-concatenating
    reference texts is unsupported: it is reported to crash the model's
    multi-level tokenizer, and test_no_manual_reference_concatenation exists to
    keep it from creeping back in.
    """
    aya = Aya(r.sura, r.aya)
    if not r.include_bismillah:
        seg = aya.get_by_imlaey_words(r.start_word, r.num_words)
    else:
        if r.start_word != 0:
            raise ValueError(
                "include_bismillah only applies to a range starting at word 0 - "
                "the basmala precedes the ayah, it does not appear mid-ayah")
        # The basmala is prepended INTO the index space, so encoded indices are
        # shifted. Ask the library where the ayah starts rather than assuming 4.
        enc = aya._encode_imlaey_to_uthmani(include_bismillah=True)
        offset = enc.aya_imlaey_span_words[0]
        seg = aya.get_by_imlaey_words(0, offset + r.num_words,
                                      include_bismillah=True)
    return seg.uthmani, quran_phonetizer(seg.uthmani, MOSHAF, remove_spaces=True)


def uthmani_of(r: Range) -> str:
    return reference(r)[0]
