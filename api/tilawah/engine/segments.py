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


# Characters that appear in a segment but can never be "the letter the mistake
# happened on", so they are skipped when reading a letter out of one.
#
#   ٱ  U+0671  alef wasla   carries no sound of its own
#   ـ  U+0640  TATWEEL      not a letter at all - it is the elongation stroke a
#                           superscript alef is drawn on, as in «صَـٰ»
#
# TATWEEL IS THE ONE THAT WAS LEAKING. It is not a combining mark, so it
# survived the filter, and it sits inside the codepoint range is_letter() tests
# (U+0640 is between ء and ي). A dagger-alif madd therefore resolved to «ـ» and
# the practice ladder told the learner to say a kashida, with a syllable rung
# offering «ـَ ـُ ـِ». Found by replaying a real 2:7 recitation, where segment
# «ـٰ» of «أَبْصَـٰرِهِمْ» resolved exactly that way.
_SKIP = "ٱـ"


def _base_letters(text: str) -> str:
    """The real Arabic letters in a segment's text, marks and diacritics gone."""
    from .runlength import MARKS

    return "".join(c for c in text
                   if not unicodedata.combining(c)
                   and not c.isspace()
                   and c not in MARKS
                   and c not in _SKIP)


def unit_letters(uthmani: str, segments: list[dict]) -> dict[int, str]:
    """unit index -> the real Arabic letter that unit belongs to.

    WHY THIS EXISTS. A TypedError's `letter` came straight off the QPS phoneme
    string, so five of the engine's error families named a NOTATION SYMBOL as
    the letter the learner got wrong: qalqalah errors all said ڇ, madd errors
    said ۥ or ۦ, ikhfa said ں and iqlab said ۾. A learner cannot look those up,
    write them, or say them - and the card asked them to practise one.

    IT WAS ALSO A MERGE BUG, which is the part that was invisible. Cards merge
    on (code, letter), so every qalqalah mistake in an ayah carried the SAME
    letter and collapsed into a single card no matter which of ق ط ب ج د it
    happened on. Two real mistakes, one card, no way to tell from the outside.
    Resolving the letter fixes the display and the merge in one move, because
    they were never two problems.

    DERIVED FROM THE MUSHAF, NOT FROM A TABLE. The segment that owns a unit
    already carries the Uthmani characters that generated it, so the real letter
    is read out of the text rather than decided here. That matters most for
    iqlab: whether ۾ "is" ن or م is a tajweed question, and the mushaf answers
    it without anyone having to rule on it - the text says ن, so the card says
    ن.

    THE WALK BACKWARDS is a script fact, not a ruling. All five marks are
    SUFFIXED notation: qalqalah is appended to the letter it echoes, a madd
    lengthens the vowel before it, the ghunna marks sit on their noon. So when a
    segment yields no base letter of its own - which happens where the mushaf
    itself writes ۥ or ۦ as a superscript, as in «تَأْخُذُهُۥ» - the letter being
    marked is the nearest one before it. Measured at 25/25 marker units
    resolved across 12 ayat including 2:255.

    Units with no resolvable letter map to "" and NEVER to the mark. An empty
    letter degrades honestly: the card omits its letter chip and the practice
    ladder starts at the word. A mark would be a lie with a glyph on it.
    """
    ordered = [s for s in segments if s["units"]]
    out: dict[int, str] = {}
    for i, seg in enumerate(ordered):
        letters = ""
        for back in range(i, -1, -1):
            letters = _base_letters(ordered[back]["text"])
            if letters:
                break
        # The LAST base letter in the group: a segment like «دْ» has one, but a
        # run that swept up a preceding cluster ends on the letter the mark is
        # actually attached to.
        for u in seg["units"]:
            out.setdefault(u, letters[-1] if letters else "")
    return out


@lru_cache(maxsize=1024)
def unit_spans_for_range(sura: int, aya: int, start_word: int,
                         num_words: int) -> dict[int, tuple[int, int]]:
    """unit index -> the Uthmani character span that unit ALONE occupies.

    RULE 2: HIGHLIGHT THE SOUND, NOT THE LETTER-GROUP. A segment groups the
    characters that share units, so marking one painted the whole group - and
    for a madd that group is the CONSONANT plus its lengthening mark. A learner
    told "madd — 2 harakat needed" saw «صَـٰ» lit up entire and had no way to
    know the instruction was about the ـٰ rather than about the ص.

    Derived from the same phonetizer mappings the segments are, so it can only
    ever narrow a segment, never point outside it. A character contributes to
    whichever unit its own mapping names; the marks sitting on it come along.

    Segments carrying ONE unit answer with the whole segment, which is both
    correct and the overwhelmingly common case. This narrows only where a group
    really does hold several sounds - which is exactly the madd case.
    """
    from .ranges import Range, reference

    uthmani, out = reference(Range(sura, aya, start_word, num_words))
    spans = unit_char_spans(out.phonemes)
    char_to_unit: dict[int, int] = {}
    for unit, (a, b) in enumerate(spans):
        for c in range(a, b):
            char_to_unit[c] = unit

    # Uthmani character -> the first unit it generates. A combining mark
    # generates nothing of its own and joins the character it sits on.
    bounds: dict[int, list[int]] = {}
    owner: int | None = None
    for i, ch in enumerate(uthmani):
        if ch.isspace():
            owner = None
            continue
        unit = None
        if i < len(out.mappings):
            mp = out.mappings[i]
            if not mp.deleted:
                for c in range(mp.pos[0], mp.pos[1]):
                    if c in char_to_unit:
                        unit = char_to_unit[c]
                        break
        if unit is None:
            if unicodedata.combining(ch) and owner is not None:
                unit = owner          # the mark belongs to its base letter
            else:
                continue
        else:
            owner = unit
        got = bounds.setdefault(unit, [i, i + 1])
        got[0] = min(got[0], i)
        got[1] = max(got[1], i + 1)

    # UNITS NO CHARACTER GENERATES. The qalqalah ڇ is derived from the sukun on
    # a qalqalah letter rather than written, so nothing in the mushaf maps to
    # it and it would come back with no span at all - no highlight on the very
    # error the learner is being asked to fix. It borrows the span of the
    # letter it is an echo of, which is the unit before it: the same backward
    # walk, and for the same reason, as unit_letters.
    total = len(unit_char_spans(out.phonemes))
    for unit in range(total):
        if unit in bounds:
            continue
        for back in range(unit - 1, -1, -1):
            if back in bounds:
                bounds[unit] = list(bounds[back])
                break
    return {u: (a, b) for u, (a, b) in bounds.items()}


def occurrence_ordinal(uthmani: str, span: tuple[int, int],
                       letter: str) -> tuple[int, int]:
    """(which occurrence of `letter` in its word this span is, how many there are).

    RULE 10. «أَبْصَـٰرِهِمْ» has two ه-shaped letters and «ٱلرَّحْمَـٰنِ» has two ن. A
    card saying only "the letter ه was wrong" leaves the learner scanning the
    word to find which one, and the red mark is on only one of them - so the
    words and the highlight disagree about how many mistakes there were.

    COUNTED OVER CHARACTERS, NOT UNITS, and that distinction is the whole
    correctness of it. Several units can resolve to the same letter without
    there being two of that letter written down: a madd unit walks back to the
    consonant it lengthens, and a qalqalah unit walks back to the letter it
    echoes. Counting units therefore reported «صَـٰ» as "the 2nd ص" in a word
    containing exactly one. Characters are also what the LEARNER counts, since
    they are what is on the page.

    Returns (1, 1) when the letter occurs once - the ordinary case - so a caller
    can render an ordinal only where there is genuinely something to
    disambiguate.
    """
    if not letter:
        return (1, 1)
    start, end = 0, len(uthmani)
    for a, b in word_spans(uthmani):
        if span[0] < b and span[1] > a:
            start, end = a, b
            break
    word = uthmani[start:end]
    total = word.count(letter)
    if total <= 1:
        return (1, max(total, 1))
    # How many of them lie at or before this span. `min` guards the walked-back
    # case, where the span can start after the last written instance.
    before = word.count(letter, 0, max(span[0] - start, 0))
    return (min(before + 1, total), total)


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
