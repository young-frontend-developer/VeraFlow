# -*- coding: utf-8 -*-
"""Typed error extraction - the spine of the product.

Every downstream feature (lessons, drills, Hifz weighting) consumes the typed
error list, never a score. Ported from spike/s5_typed_errors.py; keep the two in
sync or delete the spike copy once you trust this one.
"""
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher

from .runlength import (GHUNNA_LETTERS, MADD_LETTERS, MARKS, QALQALA_MARK,
                        tokenize)

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


# ALIF IS NOT A CONSONANT. It has no makhraj of its own - it is a madd letter,
# a lengthening of the vowel before it - so "you read ء as ا" is not a
# statement about articulation, it is a category error. The aligner can still
# pair them: typed_diff matches on base letters, and when a hamza and an alif
# land in the same slot with no other anchor it reports a substitution, which
# rendered as «ء» ni «ا» kabi o'qidingiz - nonsense a learner cannot act on.
#
# و and ي are deliberately NOT here. They are dual-nature: madd letters when
# sakin after a matching haraka, ordinary consonants with real makharij
# otherwise. MAKHARIJ_WAW_TO_FA and MAKHARIJ_JEEM_TO_YA are about the
# consonantal use and must keep firing.
BARE_ALIF = "ا"

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


# EVERY code this module can put on a TypedError, stated rather than inferred.
# test_code_mapping.py walks it and fails on any entry that reaches neither a
# registry entry nor an alias, which is the check that was missing while the
# engine emitted MADD_SHORT at a registry holding only MADD_TOO_SHORT.
#
# The substitution codes read out of the registry at runtime are NOT listed:
# they are registry keys by construction, so they cannot fail to resolve. What
# is listed is everything this module names itself.
EMITTED_CODES = frozenset({
    # duration, from _duration_code
    "MADD_SHORT", "MADD_LONG",
    "GHUNNA_SHORT", "GHUNNA_LONG",
    "SHADDA_SHORT", "SHADDA_LONG",
    # structure
    "QALQALA_DROP", "QALQALAH_EXCESSIVE", "LETTER_DROPPED", "LETTER_ADDED",
    # vowels
    "HARAKA_SUBSTITUTED", "HARAKA_TO_SUKUN", "SUKUN_TO_HARAKA",
    # fallback
    "GENERIC_LETTER_SUBSTITUTED",
} | set(L1_PAIRS.values()))


@dataclass
class TypedError:
    code: str           # joins to the coaching registries, then rules.json
    at: int             # unit index, for highlighting the ayah
    letter: str
    expected: str = ""
    heard: str = ""
    expected_count: int = 0
    heard_count: int = 0
    # Which ṣifa disagreed, for errors that came from the ṣifa comparison
    # rather than from the phoneme diff - "tafkheem_or_taqeeq", "qalqla".
    # Empty for every phoneme-level error. Carried so the card can group and
    # explain by ṣifa, and so a routing bug is visible in the debug capture
    # instead of being flattened into a bare code.
    sifa: str = ""
    # The Uthmani word the error falls in. Filled in by the pipeline, which is
    # the only layer that knows the text - typed_diff sees phoneme strings and
    # has no idea where a word begins. Every coaching headline opens with it,
    # because "you said X instead of Y" is useless without "in which word".
    word: str = ""
    # That word's index WITHIN THE AYAH, so the client can re-record just this
    # word through the existing range machinery instead of the whole ayah.
    # Ayah-relative, not range-relative: `start_word` in the practice API counts
    # from the start of the ayah, so a range-relative index would re-record the
    # wrong word whenever the learner was practising part of an ayah. -1 when
    # the unit could not be placed in a word.
    word_index: int = -1

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


def _added(unit, at) -> TypedError:
    """An extra unit in the prediction. The mirror of _missing().

    THE QALQALAH BRANCH IS THE POINT. _missing() has always special-cased ڇ -
    a dropped qalqalah is QALQALA_DROP, not a dropped letter - but the
    symmetric case had no such branch, so an ADDED qalqalah came out as
    LETTER_ADDED carrying ڇ in both `letter` and `heard`. That produced a card
    reading "you added an extra ڇ", naming a notation symbol as though it were
    a letter the learner had inserted.

    It cannot be fixed by resolving the symbol the way the reference side is:
    `heard` describes the PREDICTION, so there is no mushaf character to look
    up, and a qalqalah is an echo on a letter rather than a letter of its own -
    there is no "extra X" to name. The honest description is that the qalqalah
    was overdone, which is a error the registry already has words for.

    So this routes to QALQALAH_EXCESSIVE. That is a classification change rather
    than a detection change: the same audio produces the same finding at the
    same position, and only the name it is filed under moves - from a code
    whose card could not be written truthfully to one whose card already is.
    `letter` still carries the mark here and is resolved against the mushaf by
    the pipeline, like every other error.

    THE NAME IS THE REGISTRY'S, NOT THE ENGINE'S. This emitted QALQALA_EXCESSIVE
    while the registry entry is QALQALAH_EXCESSIVE, so it resolved to nothing and
    rendered the unauthored stand-in - a card with a location and no words -
    over an entry that says exactly what to do. EMITTED_CODES did not list it
    either, so test_code_mapping could not catch it.
    """
    if unit[0] == QALQALA_MARK:
        return TypedError(code="QALQALAH_EXCESSIVE", at=at, letter=QALQALA_MARK)
    return TypedError(code="LETTER_ADDED", at=at, letter=unit[0], heard=unit[0])


def _substitution_code(expected: str, heard: str) -> str | None:
    """The most specific code for one letter confusion, or None to say nothing.

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

    Tier 1 only wins if it RESOLVES. SUB_HA_HEH (ح -> ه) is a real L1 prior with
    no entry in any registry generation, and returning it unconditionally put a
    code with no content ahead of the generic that would have described the
    confusion perfectly well. A prior that nobody has written content for is not
    more specific than the generic - it is less useful than it.

    TIER 0 IS A REFUSAL. A pairing involving a bare alif is not a substitution
    at all - see BARE_ALIF - so no code describes it and none is invented. The
    caller drops the error entirely rather than reporting a confusion that
    cannot happen. This trades a little recall for correctness: an attempt whose
    only finding was such a pairing now reports nothing about that letter, which
    is the right side of "a wrong correction is worse than a missing one".
    """
    from ..content import coaching

    if expected == BARE_ALIF or heard == BARE_ALIF:
        return None

    pair = L1_PAIRS.get((expected, heard))
    if pair and coaching.has(pair):
        return pair

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
                # A QPS MARK IS NOT A LETTER, SO IT CANNOT BE SUBSTITUTED FOR
                # ONE. The aligner happily pairs a ڇ against whatever the model
                # emitted in its slot, and this branch then reported a letter
                # confusion - which _resolve_marks made WORSE rather than
                # better, because turning the ڇ in `expected` into the real
                # letter produced a fluent, plausible, entirely invented card:
                #
                #     2:7 «أَبْصَـٰرِهِمْ», unit 30 = the qalqalah on بْ
                #     -> GENERIC_LETTER_SUBSTITUTED  expected «ب»  heard «ء»
                #     -> "you read «ب» as «ء»", about a letter the learner said
                #
                # The true finding is that the reference sound was not produced,
                # which is exactly what _missing() reports - and it already
                # knows a dropped ڇ is QALQALA_DROP and not a dropped letter.
                # Nothing is claimed about what was said instead: on this side
                # of the alignment there is no honest answer, and a wrong
                # correction is worse than a missing one.
                if e[0] in MARKS or g[0] in MARKS:
                    out.append(_missing(e, i1 + k))
                    continue
                code = _substitution_code(e[0], g[0])
                if code is None:
                    continue        # bare alif on one side - not a substitution
                out.append(TypedError(code=code,
                                      at=i1 + k, letter=e[0],
                                      expected=e[0], heard=g[0]))
            for k in range(n, i2 - i1):
                out.append(_missing(exp_u[i1 + k], i1 + k))
            for k in range(n, j2 - j1):
                out.append(_added(got_u[j1 + k], i1))

        elif op == "delete":
            for k in range(i1, i2):
                out.append(_missing(exp_u[k], k))

        elif op == "insert":
            for k in range(j1, j2):
                out.append(_added(got_u[k], i1))

    return out
