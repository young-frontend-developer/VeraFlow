# -*- coding: utf-8 -*-
"""Typed error extraction - the spine of the product.

Every downstream feature (lessons, drills, Hifz weighting) consumes the typed
error list, never a score. Ported from spike/s5_typed_errors.py; keep the two in
sync or delete the spike copy once you trust this one.
"""
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher

from .runlength import GHUNNA_LETTERS, MADD_LETTERS, QALQALA_MARK, tokenize

# ── harakat ───────────────────────────────────────────────────────────────
# THE CATEGORY THAT HAD NO DETECTOR. The QPS phoneme string has carried the
# vowel all along - tokenize() returns it as the third element of every unit -
# but typed_diff compared only base letters and run lengths, so a learner who
# read بَ for بِ was told nothing. Classically this is lahn jaliy, the most
# serious class of error, because it changes the meaning: أَنْعَمْتَ ("You
# bestowed") against أَنْعَمْتُ ("I bestowed").
#
# QPS emits exactly three vowels and nothing else in the mark slot - verified
# over the whole reference set, no sukun, no tanween, no shadda. A SAKIN letter
# is one with an EMPTY mark, which is what makes the sukun pair below testable
# rather than a guess.
FATHA, DAMMA, KASRA = "َ", "ُ", "ِ"
HARAKAT = {FATHA, DAMMA, KASRA}

# Named, not printed raw: "«ب» ni fatha bilan" reads; "«ب» ni َ bilan" does not.
# The names are transliterations of the Arabic terms, identical in both target
# languages, so one table serves uz and ru.
HARAKA_NAME = {FATHA: "fatha", DAMMA: "zamma", KASRA: "kasra", "": "sukun"}


def haraka_of(marks: str) -> str:
    """The vowel on a unit, or "" for a sakin one."""
    for ch in marks or "":
        if ch in HARAKAT:
            return ch
    return ""


# Uzbek/Russian L1 interference pairs. Decision 6: these priors are the cheap
# differentiator - nobody has built this for these languages.
L1_PAIRS = {
    ("ع", "ء"): "SUB_AYN_HAMZA",
    ("ح", "خ"): "SUB_HA_KHA",
    ("ح", "ه"): "SUB_HA_HEH",
    ("ص", "س"): "SUB_SAD_SEEN",
    ("ط", "ت"): "SUB_TA_PLAIN",
    ("ض", "د"): "SUB_DAD_DAL",
    ("ظ", "ز"): "SUB_DHA_ZAY",
    ("ق", "ك"): "SUB_QAF_KAF",
    ("ذ", "ز"): "SUB_DHAL_ZAY",
    ("ث", "س"): "SUB_THA_SEEN",
    ("و", "ف"): "SUB_WAW_V",
}


@dataclass
class TypedError:
    code: str           # joins to the coaching registries, then rules.json
    at: int             # unit index, for highlighting the ayah
    letter: str
    expected: str = ""
    heard: str = ""
    expected_count: int = 0
    heard_count: int = 0
    # The Uthmani word the error falls in. Filled in by the pipeline, which is
    # the only layer that knows the text - typed_diff sees phoneme strings and
    # has no idea where a word begins. Every coaching headline opens with it,
    # because "you said X instead of Y" is useless without "in which word".
    word: str = ""

    def dict(self):
        return asdict(self)


def _duration_code(letter: str, exp_n: int, got_n: int) -> str:
    if letter in MADD_LETTERS:
        base = "MADD"
    elif letter in GHUNNA_LETTERS:
        base = "GHUNNA"
    else:
        base = "SHADDA"
    return f"{base}_{'SHORT' if got_n < exp_n else 'LONG'}"


def _missing(unit, at) -> TypedError:
    if unit[0] == QALQALA_MARK:
        return TypedError(code="QALQALA_DROP", at=at, letter=QALQALA_MARK)
    return TypedError(code="LETTER_DROPPED", at=at, letter=unit[0],
                      expected=unit[0])


def _substitution_code(expected: str, heard: str) -> str:
    """The most specific code for one letter confusion.

    Three tiers, narrowest first:
      1. L1_PAIRS      - the Uzbek/Russian interference pairs, which carry
                         reviewed content and language-specific coaching
      2. the registry  - explicit "phoneme substitution: X -> Y" signals
      3. the generic   - GENERIC_LETTER_SUBSTITUTED

    Tier 3 is the important one. 28 letters give over 750 ordered pairs before
    vowels or length, so a registry can never enumerate them; without a generic
    every unlisted confusion fell through to a code with no content and the
    learner was told "we couldn't fully assess" about an error the engine had
    located precisely.
    """
    pair = L1_PAIRS.get((expected, heard))
    if pair:
        return pair
    from ..content import coaching

    return coaching.substitution_pairs().get((expected, heard),
                                             "GENERIC_LETTER_SUBSTITUTED")


def _haraka_error(exp_unit, got_unit, at) -> TypedError | None:
    """Vowel disagreement on a letter both sides agree about.

    Only reached from the `equal` branch, where the base letters matched - so
    this is genuinely "right letter, wrong vowel" and not the tail of a
    misalignment.
    """
    want, got = haraka_of(exp_unit[2]), haraka_of(got_unit[2])
    if want == got:
        return None
    if want and got:
        code = "HARAKA_SUBSTITUTED"
    elif want and not got:
        code = "HARAKA_TO_SUKUN"
    else:
        code = "SUKUN_TO_HARAKA"
    # `expected`/`actual` are the NAMES, because that is what the headline puts
    # into a sentence.
    return TypedError(code=code, at=at, letter=exp_unit[0],
                      expected=HARAKA_NAME[want], heard=HARAKA_NAME[got])


def typed_diff(expected: str, predicted: str) -> list[TypedError]:
    exp_u, got_u = tokenize(expected), tokenize(predicted)
    sm = SequenceMatcher(None, [u[0] for u in exp_u], [u[0] for u in got_u])
    out: list[TypedError] = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                e, g = exp_u[i1 + k], got_u[j1 + k]
                # Run length: the case a raw character diff misreports as a
                # missing letter.
                if e[1] != g[1]:
                    out.append(TypedError(
                        code=_duration_code(e[0], e[1], g[1]), at=i1 + k,
                        letter=e[0], expected_count=e[1], heard_count=g[1]))
                # Vowel. Independent of length: a letter can be held for the
                # right count and still carry the wrong haraka, and the two are
                # different errors with different corrections.
                haraka = _haraka_error(e, g, i1 + k)
                if haraka:
                    out.append(haraka)

        elif op == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                e, g = exp_u[i1 + k], got_u[j1 + k]
                out.append(TypedError(code=_substitution_code(e[0], g[0]),
                                      at=i1 + k, letter=e[0],
                                      expected=e[0], heard=g[0]))
            for k in range(n, i2 - i1):
                out.append(_missing(exp_u[i1 + k], i1 + k))
            for k in range(n, j2 - j1):
                out.append(TypedError(code="LETTER_ADDED", at=i1,
                                      letter=got_u[j1 + k][0],
                                      heard=got_u[j1 + k][0]))

        elif op == "delete":
            for k in range(i1, i2):
                out.append(_missing(exp_u[k], k))

        elif op == "insert":
            for k in range(j1, j2):
                out.append(TypedError(code="LETTER_ADDED", at=i1,
                                      letter=got_u[k][0], heard=got_u[k][0]))

    return out
