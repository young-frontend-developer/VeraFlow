# -*- coding: utf-8 -*-
"""Detected errors -> the cards a learner actually reads.

Two jobs, both of which used to leak straight through to the screen.

MERGING. typed_diff reports every occurrence separately, because that is what a
detector should do - five units, five errors. A learner reading five identical
cards for the same ل in the same word learns nothing from cards two through
five and concludes the app is broken. So occurrences are folded into ONE card
per (code, letter), carrying where it happened and how often. Nothing is
discarded: every occurrence survives as an entry in `occurrences`, so the ayah
can still mark every affected letter red.

NAMING. The engine's codes are internal. LETTER_ADDED and
GENERIC_SIFAT_MISMATCH are diagnostic vocabulary, and a learner shown either
one has been handed a debugging artifact. Every card carries a `kind` from a
small closed set instead, which the client renders as a localised title. The
code still travels for logging and for the draft marker's audit trail, but the
client is expected never to print it.

`kind` is a WIRE CONTRACT, not a display string. The titles live in the
client's i18n table, so adding a language does not touch the engine.
"""
from . import practice
from .typed_errors import TypedError

# ── code -> kind ──────────────────────────────────────────────────────────
# The closed set. Anything not named here falls back to its registry `group`,
# and anything with no group falls back to "pronunciation" - never to the raw
# code.
EXTRA = "extra_letter"
MISSING = "missing_letter"
WRONG = "wrong_letter"
PRONUNCIATION = "pronunciation"
TAJWEED = "tajweed"
MADD = "madd"
GHUNNA = "ghunna"
HARAKA = "haraka"

KINDS = (EXTRA, MISSING, WRONG, PRONUNCIATION, TAJWEED, MADD, GHUNNA, HARAKA)

# Explicit overrides, checked before the group fallback. These are the codes
# whose registry group does not describe what the learner experienced:
# LETTER_ADDED is filed under `haraka` in v5 but is not a vowel error, and the
# qalqalah entries are filed under `sifat` but read as a tajweed ruling.
_BY_CODE = {
    "LETTER_ADDED": EXTRA,
    "LETTER_DROPPED": MISSING,
    # Both generics are filed under group `fallback`, which says where the
    # entry came from and nothing about what the learner did. They land on
    # opposite titles: one is the wrong letter, the other the right letter
    # said wrongly.
    "GENERIC_LETTER_SUBSTITUTED": WRONG,
    "GENERIC_SIFAT_MISMATCH": PRONUNCIATION,
    "QALQALA_DROP": TAJWEED,
    "QALQALAH_MISSING": TAJWEED,
    "QALQALAH_EXCESSIVE": TAJWEED,
    "QALQALAH_ON_WRONG_LETTER": TAJWEED,
}

_BY_GROUP = {
    "makharij": WRONG,
    "sifat": PRONUNCIATION,
    "madd": MADD,
    "ghunna": GHUNNA,
    "ahkam": TAJWEED,
    "haraka": HARAKA,
    "fallback": PRONUNCIATION,
}


def kind_of(code: str, group: str = "") -> str:
    """The learner-facing category for one code."""
    if code in _BY_CODE:
        return _BY_CODE[code]
    if group in _BY_GROUP:
        return _BY_GROUP[group]
    # A duration error on a letter that is neither madd nor nasal - the
    # SHADDA_* family. It is a length error, so it reads as one.
    if code.startswith(("MADD_", "SHADDA_")):
        return MADD
    if code.startswith("GHUNNA_"):
        return GHUNNA
    if code.startswith(("HARAKA_", "SUKUN_")):
        return HARAKA
    if code.startswith(("SUB_", "MAKHARIJ_", "GENERIC_LETTER")):
        return WRONG
    return PRONUNCIATION


# ── the wire contract ─────────────────────────────────────────────────────
# Every key a rendered error carries to the client. The client indexes these
# directly - `error.words.map(...)` - so a missing one is not a degraded card,
# it is a TypeError that unmounts the results screen.
#
# This tuple is the contract. test_wire_shape.py asserts present() produces
# exactly it, so a field cannot be added to the client and forgotten here, or
# removed here and still expected there.
WIRE_KEYS = (
    "code", "kind", "at", "letter", "expected", "heard",
    "expected_count", "heard_count", "sifa",
    "word", "word_index", "words", "count", "occurrences",
    "status", "draft", "needs_teacher", "content", "practice",
)


def ensure_shape(err: dict) -> dict:
    """Guarantee one error dict carries every WIRE_KEY.

    NOT a defensive shrug over present(), which already produces the full shape.
    This exists for a durable source of half-shaped records: attempts PERSISTED
    BEFORE merging existed. Those rows are in SQLite with no `words`, no
    `occurrences`, no `count` and no `kind`, they are replayed verbatim by the
    history endpoint, and no amount of care in present() changes what is already
    written down.

    Repaired from what the row does have rather than filled with blanks: a
    legacy error knows its own `at` and `word`, which is exactly one
    occurrence, so it reconstructs into a correct single-occurrence card rather
    than an empty one. `kind` is recomputed from the code, which never changed.
    """
    out = dict(err)
    out.setdefault("code", "")
    out.setdefault("at", 0)
    out.setdefault("letter", "")
    for key in ("expected", "heard", "sifa", "word", "status"):
        out.setdefault(key, "")
    for key in ("expected_count", "heard_count"):
        out.setdefault(key, 0)
    out.setdefault("word_index", -1)
    out.setdefault("draft", False)
    out.setdefault("needs_teacher", False)
    out.setdefault("content", None)

    body = out.get("content") or {}
    if not out.get("kind"):
        out["kind"] = kind_of(out["code"], body.get("group", ""))

    # One legacy error IS one occurrence. Rebuilding it that way keeps the
    # ayah's red letter working for old attempts instead of silently marking
    # nothing.
    if not out.get("occurrences"):
        out["occurrences"] = [{"at": out["at"], "word": out["word"],
                               "word_index": out["word_index"]}]
    if not out.get("words"):
        out["words"] = [out["word"]] if out["word"] else []
    if not out.get("count"):
        out["count"] = len(out["occurrences"])

    # Rebuilt, not blanked, for the same reason as `occurrences`. The ladder is
    # DERIVED from the letter and the word, both of which a legacy row already
    # carries, so a replayed attempt gets a working practice section rather than
    # an empty one - and no migration is needed to give it one.
    if not out.get("practice"):
        out["practice"] = practice.ladder(
            out["letter"], out["word"], out["word_index"])
    return out


def merge(errors: list[TypedError]) -> list[list[TypedError]]:
    """Group into one bucket per (registry code, letter), first occurrence first.

    Order is the order the buckets first appear, so the ranking `present()`
    applied - severity, then position - survives the merge. Sorting again here
    would silently undo it.

    Grouping is by (code, letter) rather than (code, word, letter): the same
    letter mispronounced in four different words is ONE thing to learn and one
    drill to do, and four cards saying it is four chances to stop reading.

    THE KEY IS THE RESOLVED CODE, NOT THE ENGINE CODE, and that is the whole
    reason this comment exists. Two detectors can find the SAME event: the
    phoneme diff reports a dropped qalqalah as QALQALA_DROP, and the ṣifa
    comparison reports it as QALQALAH_MISSING. Both are about one letter in one
    word, both alias to one registry entry, and so both render an identical
    headline, an identical instruction and an identical practice ladder. Keyed
    on the raw code they are two buckets, and a learner who softened one د was
    shown the same card twice.

    Found by driving a real recitation of 112:3 through the API - not by any
    unit test, because both halves are correct in isolation and only the
    combination is wrong.

    coaching.ALIAS is the authority for what counts as the same error, and it
    is the right one: it already exists, it is documented as holding only
    genuine synonyms, and a test fails on any engine code missing from it. The
    letter stays in the key, so ذ->ز and ظ->ز - which share a registry entry -
    remain two cards, as they should.
    """
    from ..content.coaching import resolve

    buckets: dict[tuple[str, str], list[TypedError]] = {}
    for e in errors:
        buckets.setdefault((resolve(e.code), e.letter), []).append(e)
    return list(buckets.values())


def occurrences(group: list[TypedError]) -> list[dict]:
    """Where each occurrence happened, in reading order.

    Every one is kept. The card shows a count and the distinct words, but the
    ayah needs each individual `at` to mark every affected letter red - which is
    the requirement merging must not break.
    """
    return [{"at": e.at, "word": e.word, "word_index": e.word_index}
            for e in sorted(group, key=lambda e: e.at)]


def distinct_words(group: list[TypedError]) -> list[str]:
    """The words this error touched, deduplicated, in reading order.

    Deduplicated because "4 marta uchradi" over one repeated word should name
    that word once, not four times.
    """
    out: list[str] = []
    for e in sorted(group, key=lambda e: e.at):
        if e.word and e.word not in out:
            out.append(e.word)
    return out
