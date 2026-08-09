# -*- coding: utf-8 -*-
"""Which tajweed rules are STRUCTURALLY PRESENT in a segment.

The counterpart to engine/coverage.possible_codes, and the opposite question.
coverage asks "what could the learner get WRONG here"; this asks "what rules
apply here at all". Every entry in the error registry describes a mistake, so
a flawless recitation surfaced nothing and the learner was never told which
rules they had just executed correctly. These badges answer that.

Both are derived from the REFERENCE PHONETIC SCRIPT alone. No recording is
involved and none may be: a badge says "this ayah contains a madd lozim",
which is a fact about the Qur'an, not about a performance.

CONTENT AND DETECTION ARE SEPARATE, AND ONLY ONE OF THEM IS MINE
---------------------------------------------------------------
The strings live in content/rule_badges.json, transcribed from the printed
Uzbek text (see that file's _meta). This module decides only WHERE each rule
occurs. Every precondition below is written against QPS output that was
printed and read, not reasoned about from the Arabic script - the two disagree
in ways that matter, and the phonetizer is the thing the engine actually sees.

WHAT QPS GIVES US, verified by running the phonetizer on the book's own
examples:

    length is a REPEAT COUNT      اا = 2 harakat, اااا = 4, اااااا = 6
    ں   ikhfa noon                مِن شَرِّ  -> مِںںںشَررِ
    ۾   hidden meem               iqlab, and ikhfa shafawiya
    ڇ   qalqalah mark             أَحَدْ -> ءَحَدڇ
    shadda = a doubled consonant  ٱلَّذِينَ -> للَذِ,  مُتَّقِينَ -> مُتتَقِ
    a shadda'd NASAL doubles to 4 ٱلنَّاسَ -> ننننَ    (the ghunnah is held)

The moshaf config sets madd monfasel, mottasel, aared and leen all to 4, so a
run of SIX is madd lozim and nothing else. That is what makes RULE_MADD_LOZIM
a clean signal rather than a guess, and it is why the muqatta'at fall out of it
for free: الٓمٓ phonetizes to لَااااااممممِۦۦۦۦۦۦ - two six-counts. The book is
right that they carry real madd content, and the engine agrees.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from .coverage import HARAKAT, MADD_LETTERS

_BADGES_PATH = Path(__file__).resolve().parents[1] / "content" / "rule_badges.json"

HAMZA = "ء"
IKHFA_NOON = "ں"
NASALS = set("نم")
#: 4-5-darslar. The letters that are always heavy, named in the authored rule.
ISTILA = set("خصضطظغق")


@lru_cache(maxsize=1)
def badges() -> dict:
    """The authored badge content, keyed by rule code. `_meta` stripped."""
    if not _BADGES_PATH.exists():
        return {}
    raw = json.loads(_BADGES_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def is_reviewed(code: str) -> bool:
    """The same gate the error registry uses. Draft content reaches nobody."""
    return badges().get(code, {}).get("status") == "reviewed"


def _runs(text: str):
    """(start, char, length) for every maximal run of one character."""
    for m in re.finditer(r"(.)\1*", text):
        yield m.start(), m.group(1), len(m.group(0))


def _madd_runs(text: str):
    """Maximal runs of a madd letter, which is how QPS writes length."""
    for start, ch, n in _runs(text):
        if ch in MADD_LETTERS and n >= 2:
            yield start, ch, n


def rules_present(phonemes: str, sifat, phonemes_spaced: str = "",
                  n_words: int = 0) -> list[str]:
    """Rule codes that structurally occur on this reference. Sorted, stable.

    `phonemes_spaced` is required for the two rules that turn on a WORD
    BOUNDARY - muttasil and munfasil differ by nothing else, and
    remove_spaces=True destroys exactly the information that separates them.
    Without it those two are skipped rather than guessed at.
    """
    src = phonemes_spaced or ""
    tokens = src.split()
    found: set[str] = set()

    # ── madd ──────────────────────────────────────────────────────────────
    # SIX IS LOZIM. Every other madd in this moshaf is 4 or 2, so the length
    # alone settles it - and it settles the muqatta'at with it.
    for _i, _ch, n in _madd_runs(phonemes):
        if n >= 6:
            found.add("RULE_MADD_LOZIM")
            break

    for tok in tokens:
        for start, _ch, n in _madd_runs(tok):
            after = tok[start + n] if start + n < len(tok) else ""
            # MUTTASIL: the hamza is inside the same word as the madd.
            if after == HAMZA:
                found.add("RULE_MADD_MUTTASIL")
            # TABIIY: a plain two-count, with no hamza and no sukun behind it.
            # Restricted to runs of exactly 2 because a longer run is by
            # definition one of the other three and would double-badge.
            elif n == 2:
                found.add("RULE_MADD_TABIIY")

    # MUNFASIL: the madd ends its word and the hamza opens the next one.
    for a, b in zip(tokens, tokens[1:]):
        if not b.startswith(HAMZA):
            continue
        runs = list(_madd_runs(a))
        if runs and runs[-1][0] + runs[-1][2] == len(a):
            found.add("RULE_MADD_MUNFASIL")
            break

    # ── ikhfo and ghunna ──────────────────────────────────────────────────
    # The authored trigger names two things and QPS distinguishes both: the
    # ikhfa noon has its own character, and a shadda'd nasal is a run. Every
    # noon and meem is inherently maghnoon in the sifat, so the flag itself
    # would match nearly every segment and mean nothing - the ruling has to be
    # found positionally. Same reasoning as coverage.possible_codes.
    if IKHFA_NOON in phonemes or any(
        ch in NASALS and n >= 2 for _i, ch, n in _runs(phonemes)
    ):
        found.add("RULE_IKHFO_GHUNNA")

    # ── idgham ────────────────────────────────────────────────────────────
    #
    # HONEST ABOUT ITS REACH. The authored trigger names four subtypes and this
    # catches three of them cleanly plus part of the fourth. QPS writes an
    # idgham and a root shadda identically - both are a doubled consonant - so
    # there is no signal that separates مُتَّقِينَ (tashdid) from مِمَّا (idgham of
    # nun-sakin into meem) inside a word. What CAN be seen:
    #
    #   (a) a token that BEGINS with a doubled consonant. The definite
    #       article's laam has vanished into a sun letter (شمسية: للَذِينَ,
    #       صصَلَااتَ, ضضَاااااا) or a nun-sakin has assimilated into the next
    #       word's opening letter.
    #   (b) a run of meem - idgham mislayn. Shared with the precondition for
    #       MIM_IDGHAM_MISLAYN_MISSING, and it carries that entry's known
    #       weakness: a root shadda on meem (أُمَّة) also produces a run.
    #   (c) FEWER TOKENS THAN WORDS, beyond what the ikhfa/iqlab characters
    #       account for. An assimilation that swallows a word boundary merges
    #       two tokens into one (هُدًى لِّلْمُتَّقِينَ -> هُدَللِلمُتتَقِۦۦۦۦن), and if no
    #       ں or ۾ explains the merge, an idgham did it. This is the only
    #       thing that reaches mutajanisayn and mutaqaribayn, and it is a
    #       PROXY - it cannot say which letter assimilated, only that one did.
    #
    # (c) is why `n_words` is a parameter. Callers that cannot supply it get
    # (a) and (b), which is a smaller claim rather than a wrong one.
    if any(len(t) > 1 and t[0] == t[1] and t[0] not in MADD_LETTERS
           and t[0] not in HARAKAT for t in tokens):
        found.add("RULE_IDGHOM")
    elif any(ch == "م" and n >= 2 for _i, ch, n in _runs(phonemes)):
        found.add("RULE_IDGHOM")
    elif n_words and tokens:
        nasal_merges = sum(1 for _i, ch, _n in _runs(phonemes) if ch in "ں۾")
        if (n_words - len(tokens)) > nasal_merges:
            found.add("RULE_IDGHOM")

    # ── sifat ─────────────────────────────────────────────────────────────
    # Straight from the authored rule, which names the seven letters rather
    # than a sifa flag. `mofakham` would also catch every heavy ر and the alif
    # after one, which the printed rule does not claim.
    if any(ch in ISTILA for ch in phonemes):
        found.add("RULE_TAFXIM")

    # The qalqalah MARK, not the letter: ڇ is written only where the letter
    # actually carries sukun, so the ruling is already resolved for us.
    if "ڇ" in phonemes:
        found.add("RULE_QALQALA")

    return sorted(found & set(badges()))
