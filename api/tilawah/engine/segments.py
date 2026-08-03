# -*- coding: utf-8 -*-
"""Split an ayah into letter-groups aligned to the engine's error units.

This is what lets the UI point at the letter it means. A TypedError carries
`at`, an index into the run-length units of the QPS phoneme string, which has no
relationship to character positions in the Uthmani text. The phonetizer's
`mappings` bridges them: one MappingPos per Uthmani character giving that
character's span in the phoneme string.

    Uthmani char --mappings--> phoneme span --run-length--> unit index

Two things make this less tidy than it sounds:

  - One Uthmani character can own SEVERAL units. In ٱللَّهُ the fatha generates
    both the lam and the madd that follows it, so that character carries two.
    Segments therefore hold a list of units, not one.

  - Characters the phonetizer drops (alef wasla, sukun, waqf kasra) own none.
    They still have to appear on screen, so they attach by script rule:
    combining marks sit on the letter before, base letters join the letter after.

Segments carry `start`/`end` offsets rather than only text because the UI must
NOT slice the ayah into separate elements - Arabic is cursive, and splitting a
word across DOM nodes breaks the joining forms. The client renders one text node
and measures a Range over these offsets to place a highlight.

    وَٱلْعَصْرِ  ->  وَ | ٱلْ | عَ | صْ | رِ     units [0] [1] [2] [3] [4]
"""
import unicodedata
from functools import lru_cache

from quran_transcript import Aya

from .target import _phonetized


def unit_char_spans(phonemes: str) -> list[tuple[int, int]]:
    """Character span of each run-length unit within the phoneme string.

    Mirrors runlength.tokenize exactly. If that changes this must change with
    it, which is what test_segments_match_runlength_units guards.
    """
    spans: list[list[int]] = []
    for i, ch in enumerate(phonemes):
        if unicodedata.combining(ch):
            if spans:
                spans[-1][1] = i + 1
            continue
        merges = (
            spans
            and phonemes[spans[-1][0]] == ch
            and not any(unicodedata.combining(c)
                        for c in phonemes[spans[-1][0]:spans[-1][1]])
        )
        if merges:
            spans[-1][1] = i + 1
        else:
            spans.append([i, i + 1])
    return [(a, b) for a, b in spans]


@lru_cache(maxsize=512)
def segments_for(sura: int, aya: int) -> list[dict]:
    """[{text, start, end, units}] covering the whole ayah in Uthmani order."""
    return _build(Aya(sura, aya).get().uthmani, _phonetized(sura, aya))


@lru_cache(maxsize=1024)
def segments_for_range(sura: int, aya: int, start_word: int,
                       num_words: int) -> list[dict]:
    """The same, for a practice sub-range.

    Unit indices must be relative to the RANGE, because that is what the engine
    diffs and therefore what TypedError.at counts against. Reusing the whole
    ayah's segments for a sub-range would land every highlight on the wrong
    letter, silently, and only when the learner practised part of an ayah.
    """
    from .ranges import Range, reference

    uthmani, out = reference(Range(sura, aya, start_word, num_words))
    return _build(uthmani, out)


def _build(uthmani: str, out) -> list[dict]:
    """`units` is empty for word gaps and for anything the phonetizer drops.

    Concatenating every `text` reproduces the Uthmani text exactly, and the
    spans tile it without gaps or overlap - the UI must never invent, drop or
    reorder a character.
    """
    spans = unit_char_spans(out.phonemes)

    char_to_unit: dict[int, int] = {}
    for unit, (start, end) in enumerate(spans):
        for c in range(start, end):
            char_to_unit[c] = unit

    def units_of(i: int) -> list[int]:
        if i >= len(out.mappings):
            return []
        mp = out.mappings[i]
        if mp.deleted:
            return []
        found: list[int] = []
        for c in range(mp.pos[0], mp.pos[1]):
            u = char_to_unit.get(c)
            if u is not None and u not in found:
                found.append(u)
        return found

    segments: list[dict] = []
    current: dict | None = None
    pending_start: int | None = None       # base letters waiting for their letter

    def flush_pending_into(seg: dict) -> None:
        nonlocal pending_start
        if pending_start is not None:
            seg["start"] = pending_start
            pending_start = None

    for i, ch in enumerate(uthmani):
        if ch.isspace():
            if pending_start is None:
                segments.append({"start": i, "end": i + 1, "units": []})
            else:
                pass                        # keep the gap with the pending run
            current = None
            continue

        units = units_of(i)

        if not units:
            if unicodedata.combining(ch) and current is not None:
                current["end"] = i + 1       # mark sits on the previous letter
            elif pending_start is None:
                pending_start = i            # base letter joins the next one
            continue

        if current is not None and set(units) & set(current["units"]):
            current["end"] = i + 1
            for u in units:
                if u not in current["units"]:
                    current["units"].append(u)
        else:
            current = {"start": i, "end": i + 1, "units": list(units)}
            flush_pending_into(current)
            segments.append(current)

    if pending_start is not None:
        if segments:
            segments[-1]["end"] = len(uthmani)
        else:
            segments.append({"start": pending_start, "end": len(uthmani), "units": []})

    for seg in segments:
        seg["text"] = uthmani[seg["start"]:seg["end"]]
    return segments


def unit_to_segment(sura: int, aya: int, unit: int) -> dict | None:
    """The letter-group an error at `unit` should highlight."""
    for seg in segments_for(sura, aya):
        if unit in seg["units"]:
            return seg
    return None


def word_spans(uthmani: str) -> list[tuple[int, int]]:
    """(start, end) of every whitespace-delimited word, in character offsets."""
    spans, start = [], None
    for i, ch in enumerate(uthmani):
        if ch.isspace():
            if start is not None:
                spans.append((start, i))
                start = None
        elif start is None:
            start = i
    if start is not None:
        spans.append((start, len(uthmani)))
    return spans


def unit_words(uthmani: str, segments: list[dict]) -> dict[int, str]:
    """unit index -> the Uthmani word containing it.

    Every coaching headline opens with the word ("«{word}» — you said X for
    Y"), and an error located only to a letter is nearly useless: ص appears
    many times in an ayah and the learner needs to know which one.

    Built from the segments rather than by re-deriving offsets, so it agrees
    with the highlight by construction: whatever character span the UI marks,
    this reports the word that span sits in. A unit spanning a word boundary
    cannot happen - the phonetizer does not merge across whitespace - but if it
    ever did, the first word wins rather than the lookup failing.
    """
    spans = word_spans(uthmani)
    out: dict[int, str] = {}
    for seg in segments:
        if not seg["units"]:
            continue
        for start, end in spans:
            if seg["start"] < end and seg["end"] > start:
                word = uthmani[start:end]
                for u in seg["units"]:
                    out.setdefault(u, word)
                break
    return out


def unit_word_indices(uthmani: str, segments: list[dict]) -> dict[int, int]:
    """unit index -> the ORDINAL of the word containing it, counting from 0.

    The same walk as unit_words, reporting the position rather than the text,
    because "re-record just this word" needs a number to feed `start_word` and
    two identical words in one ayah must not collapse to the same range.

    Indices count within whatever text is passed in. When that text is a
    practice sub-range, the caller must add the range's own `start_word` to get
    an ayah-relative index - which is what the practice API expects.
    """
    spans = word_spans(uthmani)
    out: dict[int, int] = {}
    for seg in segments:
        if not seg["units"]:
            continue
        for w, (start, end) in enumerate(spans):
            if seg["start"] < end and seg["end"] > start:
                for u in seg["units"]:
                    out.setdefault(u, w)
                break
    return out
