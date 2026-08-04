# -*- coding: utf-8 -*-
"""QPS run-length tokenizer.

Lifted from spike/s5_typed_errors.py, which is the reference implementation and
stays frozen. QPS encodes duration as repeated characters (4-count madd = اااا,
ghunnah = نننن), so a shortened madd and a dropped letter have the same raw
character signature. Collapsing runs into (letter, count) units before diffing
is what separates them.
"""
import unicodedata

QALQALA_MARK = "ڇ"                     # ڇ - appended to a qalqalah letter
MADD_LETTERS = set("اۥۦوي")
# ں and ۾ belong here. QPS writes the ikhfa noon as ں and the iqlab meem as ۾,
# and those are precisely the positions carrying a RULED two-to-three count
# ghunnah - the ones a learner actually shortens. Omitting them sent every
# ikhfa and iqlab duration error through _duration_code's fallback branch and
# out as SHADDA_SHORT, a code with no content, so it vanished silently. No
# learner-visible change today (GHUNNA_SHORT is still status=collect), but the
# calibration harness would otherwise have measured the wrong check.
GHUNNA_LETTERS = set("نمں۾")

# ── QPS NOTATION SYMBOLS THAT ARE NOT ARABIC LETTERS ──────────────────────
# QPS borrows five characters from outside the Arabic alphabet to notate things
# the alphabet has no character for. They are transcription marks, and a
# learner shown one has been handed a symbol they cannot look up, cannot write
# and cannot pronounce:
#
#   ڇ  U+0687  TCHEHEH                     qalqalah, appended to its letter
#   ۥ  U+06E5  SMALL WAW                   waw-madd lengthening
#   ۦ  U+06E6  SMALL YEH                   ya-madd lengthening
#   ں  U+06BA  NOON GHUNNA                 the ikhfa noon
#   ۾  U+06FE  SINDHI POSTPOSITION MEN     the iqlab meem
#
# ⚠️ ۥ AND ۦ ARE ALSO REAL UTHMANI CHARACTERS. The mushaf writes the superscript
# waw and ya in words like «تَأْخُذُهُۥ» and «بِإِذْنِهِۦ», so their presence in the
# TEXT is legitimate; what is not legitimate is naming one as the letter a
# mistake happened on. Both facts are true at once, which is why resolution
# walks back to a base letter rather than testing membership in this set alone.
#
# See segments.unit_letters(), which turns a unit index into the real letter,
# and the pipeline, which applies it before anything reaches a card.
MARKS = frozenset("ڇۥۦں۾")

# What each mark SOUNDS like, for the one case the mushaf cannot answer: a
# symbol in the PREDICTION. `heard` is what the model thought it heard, so
# there is no reference character to look up - the learner inserted something
# that is not in the text. This is a transcription fact (which sound the symbol
# notates), not a ruling about tajweed.
#
# ڇ maps to nothing on purpose. A qalqalah is an echo ON a letter, not a letter
# of its own, so "you added an extra ڇ" has no honest rewrite as "you added an
# extra X" - there is no X. Insertions of ڇ are classified as QALQALA_EXCESSIVE
# instead, which is a code the registry already has words for; see
# typed_errors._added().
MARK_SOUND = {"ۥ": "و", "ۦ": "ي", "ں": "ن", "۾": "م", "ڇ": ""}


def tokenize(ph: str) -> list[tuple[str, int, str]]:
    """Phoneme string -> [(base_letter, count, marks)].

    Consecutive identical base letters merge ONLY while no diacritic has been
    attached, so نننن is one 4-count run but ءَء stays two hamzas.
    """
    units: list[list] = []
    for ch in ph:
        if unicodedata.combining(ch):
            if units:
                units[-1][2] += ch
            continue
        if units and units[-1][0] == ch and not units[-1][2]:
            units[-1][1] += 1
        else:
            units.append([ch, 1, ""])
    return [(b, c, m) for b, c, m in units]
