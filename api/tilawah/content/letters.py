# -*- coding: utf-8 -*-
"""Counting the letters of a recited range.

── WHY THIS FILE EXISTS ───────────────────────────────────────────────────

The app shows a hasanat total, and it is built on a specific hadith:

    "Whoever reads a letter from the Book of Allah has a hasana for it, and a
     hasana is multiplied tenfold. I do not say Alif-Lam-Mim is a letter, but
     Alif is a letter, Lam is a letter and Mim is a letter."
        - Jami' at-Tirmidhi 2910, in content/hadith.json

Read that second sentence carefully, because it is the whole specification. The
Prophet's clarification is explicitly about ORTHOGRAPHIC LETTERS - the written
consonantal glyphs - and not about words, syllables or phonemes. So the count
here is a count of Arabic letters in the Uthmani text of exactly what the
learner recited, and it is computed on the server from that text rather than
estimated on the client from a duration or an ayah number.

── WHAT IS AND IS NOT A LETTER ────────────────────────────────────────────

Excluded, on purpose:

  harakat and sukun      fatha, damma, kasra, shadda, sukun, tanwin. Vowel
                         marks are not letters; the hadith's own example counts
                         Alif-Lam-Mim as three, not as three plus their marks.
  Qur'anic annotation    the small madd, sajda and waqf signs (U+06D6-U+06ED)
                         and the superscript alif. These are recitation
                         instructions printed above the line, not letters of
                         the text.
  tatweel                U+0640, a typographic stretch with no phonetic or
                         orthographic content at all.
  spaces and digits      obviously.

Included: every letter in the Arabic block, U+0621-U+064A, plus the extended
forms U+0671-U+06D3 that appear in Uthmani orthography.

── THE HONEST LIMIT, STATED OUT LOUD ──────────────────────────────────────

This counts what the TEXT contains, not what the learner pronounced. Someone
who recites half an ayah and stops has the whole range's letters counted if the
attempt is stored against that range; someone who mispronounces every letter
still read them. The counter is a record of letters recited, and the client must
label it as exactly that - it is NOT a claim about accepted reward, which is not
a thing software is in a position to compute. See the copy on the hasanat card.
"""
import re
from functools import lru_cache

# Arabic letters, in the two ranges Uthmani orthography actually uses.
# Deliberately a whitelist, not a "strip the marks" blacklist: a blacklist
# silently counts anything new that appears in the text, and this number is
# attached to a hadith.
_LETTER = re.compile(r"[ء-يٱ-ۓ]")


def count(text: str) -> int:
    """Arabic letters in `text`. See the module docstring for the definition."""
    return len(_LETTER.findall(text or ""))


@lru_cache(maxsize=8192)
def in_range(sura: int, aya: int, start_word: int, num_words: int) -> int:
    """Letters in one recited range, or 0 if it cannot be resolved.

    Zero rather than an estimate. A range that fails to resolve - a legacy row
    with a word span that no longer exists, say - contributes nothing to the
    total instead of contributing a guess, which is the same rule every other
    number in this app follows.
    """
    from ..engine.ranges import Range, uthmani_of

    try:
        return count(uthmani_of(Range(sura, aya, start_word, num_words)))
    except Exception:
        return 0
