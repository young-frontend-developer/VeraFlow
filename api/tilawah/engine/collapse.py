# -*- coding: utf-8 -*-
"""Detect the muqatta'at collapse directly, from the model's own output.

When the model is given audio it cannot resolve - a truncated take, a half-said
ayah, a bad mic moment - it does not return low confidence. It returns huruf
muqatta'at, fluently, at 0.92-0.97 mean probability:

    103:1 t04  1.12 s  ->  ءَلِفلَااممرَاا      (alif-lam-meem-ra)
    103:1 t06  1.61 s  ->  ءَلِفلَااااممممِۦۦ   (alif-lam-meem)
    103:1 t07  1.48 s  ->  كَفهَايَااعِقَدڇ      (kaf-ha-ya-ain-sad)
    103:1 t08          ->  ءَلِفلَمرَ           (alif-lam-meem-ra)

versus every good take of the same ayah:

    experts x5         ->  وَلعَصر
    t01 t02 t03 t05    ->  وَلعَسر / وَلءَسر

This is the failure the recording-quality gate was built to prevent, and it is
far easier to catch here than upstream: the collapse output is a small, closed
set of letter names, and it separates perfectly on all 13 clips measured. The
audio statistic that was previously used as a proxy did not separate them at all
- it was tracking how much silence each clip contained.

Confidence is useless as a signal here (the collapse is high-confidence by
nature), so this matches on content, not on probability.
"""
import re

# Letter-name spellings the model emits when it collapses. Matched against the
# predicted phoneme string with harakat stripped, because the collapse output
# carries arbitrary vowel and madd decoration (لَااممرَاا, لَااااممممِۦۦ).
_MUQATTAAT_UNITS = (
    "ءلف",    # alif
    "لم",     # lam
    "مم",     # meem
    "صد",     # sad
    "كف",     # kaf
    "هاي",    # ha-ya
    "عق", "عن",  # ain (as emitted in عِقَد / عِنصَد)
    "طا",     # ta
    "سن",     # seen
    "قف",     # qaf
    "نن",     # noon
    "حام",    # ha-meem
    "را",     # ra
)

# Everything that is not a base Arabic letter: harakat, madd marks, sukun, etc.
_DECORATION = re.compile(r"[^ء-ي]")

# Ayat that legitimately ARE huruf muqatta'at. Reciting 2:1 correctly must never
# be reported as a collapse. (sura, aya) pairs.
MUQATTAAT_AYAT = {
    (2, 1), (3, 1), (7, 1), (10, 1), (11, 1), (12, 1), (13, 1), (14, 1),
    (15, 1), (19, 1), (20, 1), (26, 1), (27, 1), (28, 1), (29, 1), (30, 1),
    (31, 1), (32, 1), (36, 1), (38, 1), (40, 1), (41, 1), (42, 1), (42, 2),
    (43, 1), (44, 1), (45, 1), (46, 1), (50, 1), (68, 1),
}

# Two independent letter names is the trigger. One can occur by chance inside a
# normal word; two in sequence is the signature.
MIN_UNITS = 2
# Letter names must account for at least this much of the prediction.
MIN_COVERED = 0.40
# Above this similarity to the target, treat it as a real recitation regardless.
MAX_SIMILARITY = 0.50


def _bare(text: str) -> str:
    return _DECORATION.sub("", text or "")


def _similarity(a: str, b: str) -> float:
    """Normalised similarity in [0, 1]. Ratio of the longest common subsequence
    to the longer string - order-sensitive, unlike a bag-of-letters overlap."""
    if not a or not b:
        return 0.0
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b):
            cur.append(prev[j] + 1 if ca == cb else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1] / max(len(a), len(b))


def looks_collapsed(predicted: str, sura: int, aya: int,
                    expected: str = "") -> tuple[bool, str]:
    """(collapsed, detail). `expected` is the computed target for this ayah."""
    if (sura, aya) in MUQATTAAT_AYAT:
        return False, "ayah_is_muqattaat"

    bare_pred = _bare(predicted)
    bare_exp = _bare(expected)
    if not bare_pred:
        return False, "empty"

    hits, pos = [], 0
    while pos < len(bare_pred):
        for unit in _MUQATTAAT_UNITS:
            if bare_pred.startswith(unit, pos):
                hits.append(unit)
                pos += len(unit)
                break
        else:
            pos += 1

    if len(hits) < MIN_UNITS:
        return False, f"units={len(hits)}"

    covered = sum(len(u) for u in hits) / max(1, len(bare_pred))
    if covered < MIN_COVERED:
        # Letter names that account for only a sliver of a long prediction are
        # more likely to be ordinary words (مسلم, ممن) than a collapse.
        return False, f"units={len(hits)} covered={covered:.2f}"

    # The defining property of a collapse is that the output is unrelated to the
    # ayah. A learner reciting correctly lands near the target no matter which
    # letters happen to appear in it, so similarity is the guard that actually
    # discriminates - coverage alone flagged good takes and missed real ones.
    sim = _similarity(bare_pred, bare_exp) if bare_exp else 0.0
    if bare_exp and sim >= MAX_SIMILARITY:
        return False, (f"units={len(hits)} covered={covered:.2f} "
                       f"sim={sim:.2f} (close to target)")

    return True, (f"muqattaat units={'+'.join(hits)} covered={covered:.2f} "
                  f"sim={sim:.2f}")
