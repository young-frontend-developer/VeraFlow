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
