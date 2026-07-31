# -*- coding: utf-8 -*-
"""Split an ayah into practice-sized ranges that never cut an Uthmani word.

Why segment at all: 16.5% of ayat exceed 30 s of recitation and the longest is
over three minutes, but inference costs ~1.4x realtime on 2 vCPU. A 12 s target
costs ~17 s of waiting, which is about the ceiling for a loop someone repeats;
the old 30 s cap would have meant 42 s per attempt.

Two rules the packing obeys:
  * break only at legal cuts (see ranges.py) - never mid-uthmani-word;
  * measure at RATE_GATE, the slow-reciter rate, so a deliberate reciter is not
    cut off by a segment sized for a fast one.

Ayat that already fit stay whole - a single segment covering the ayah, no
artificial subdivision.

SPEED: the greedy search needs the phoneme length of many candidate ranges.
Phonetizing each one costs ~140 ms and there are 6236 ayat, so instead the ayah
is phonetized ONCE and `mappings` (uthmani char -> phoneme span) gives every
candidate's length for free. That estimate can differ from phonetizing a range
standalone by a phoneme or two at the boundaries, so the chosen segments are
then verified exactly - the artifact stores the standalone count, not the
estimate.
"""
from dataclasses import dataclass

from quran_transcript import Aya

from .ranges import (HARD_CAP_SECONDS, TARGET_SECONDS, Range, estimate_seconds,
                     legal_cuts, n_words, reference, word_map)
from .target import _phonetized


@dataclass(frozen=True)
class Segment:
    sura: int
    aya: int
    start_word: int
    num_words: int
    n_phonemes: int

    @property
    def seconds(self) -> float:
        return estimate_seconds(self.n_phonemes)

    @property
    def seconds_gate(self) -> float:
        return estimate_seconds(self.n_phonemes, gate=True)

    def as_range(self) -> Range:
        return Range(self.sura, self.aya, self.start_word, self.num_words)


def _phoneme_offsets(sura: int, aya: int) -> list[int]:
    """Phoneme position of every legal cut, parallel to legal_cuts(sura, aya).

    Derived from one whole-ayah phonetization: imlaey cut -> uthmani word ->
    character offset -> phoneme position via `mappings`.
    """
    out = _phonetized(sura, aya)
    g = Aya(sura, aya).get()
    words = g.uthmani_words
    m = dict(word_map(sura, aya))          # imlaey word idx -> uthmani word idx

    # character offset where each uthmani word begins, in g.uthmani
    char_at: list[int] = []
    pos = 0
    for w in words:
        idx = g.uthmani.find(w, pos)
        char_at.append(idx if idx >= 0 else pos)
        pos = char_at[-1] + len(w)
    char_at.append(len(g.uthmani))

    def phoneme_at(char_idx: int) -> int:
        """First phoneme position at or after this character."""
        for i in range(char_idx, len(out.mappings)):
            mp = out.mappings[i]
            if not mp.deleted:
                return mp.pos[0]
        return len(out.phonemes)

    offsets = []
    n = n_words(sura, aya)
    for c in legal_cuts(sura, aya):
        if c >= n:
            offsets.append(len(out.phonemes))
        else:
            offsets.append(phoneme_at(char_at[m[c]]))
    return offsets


def segment_ayah(sura: int, aya: int, *, verify: bool = True) -> list[Segment]:
    """Greedy pack into <=TARGET_SECONDS chunks, breaking only at legal cuts."""
    cuts = legal_cuts(sura, aya)
    offsets = _phoneme_offsets(sura, aya)
    total = offsets[-1]

    # Fits whole: no artificial subdivision.
    if estimate_seconds(total, gate=True) <= TARGET_SECONDS:
        n = n_words(sura, aya)
        seg = Segment(sura, aya, 0, n, total)
        return [_verified(seg)] if verify else [seg]

    segments: list[Segment] = []
    i = 0
    while i < len(cuts) - 1:
        # furthest cut whose chunk still fits the target
        j = i + 1
        for k in range(len(cuts) - 1, i, -1):
            if estimate_seconds(offsets[k] - offsets[i], gate=True) <= TARGET_SECONDS:
                j = k
                break
        # j == i + 1 means even the smallest step overruns; take it anyway -
        # there is no legal way to split an uthmani word. Phase 0 measured the
        # longest atomic unit at 4.17 s, so this stays well under the hard cap.
        start, end = cuts[i], cuts[j]
        seg = Segment(sura, aya, start, end - start, offsets[j] - offsets[i])
        segments.append(_verified(seg) if verify else seg)
        i = j
    return segments


def _verified(seg: Segment) -> Segment:
    """Replace the estimated phoneme count with the real one."""
    _, out = reference(seg.as_range())
    return Segment(seg.sura, seg.aya, seg.start_word, seg.num_words,
                   len(out.phonemes))


def exceeds_cap(seg: Segment) -> bool:
    return seg.seconds_gate > HARD_CAP_SECONDS
