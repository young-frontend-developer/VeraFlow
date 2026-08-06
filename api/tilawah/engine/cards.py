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
# A doubled consonant held for the wrong length. NOT madd - madd is the
# lengthening of a vowel on ا و ي, and shadda is the holding of a consonant.
# They are different rulings with different corrections, and SHADDA_* used to
# fall through kind_of()'s `startswith` into MADD, so a learner who under-held
# the ّ in «إِيَّاكَ» was shown a madd card. See RULE 1.
SHADDA = "shadda"

KINDS = (EXTRA, MISSING, WRONG, PRONUNCIATION, TAJWEED, MADD, GHUNNA, HARAKA,
         SHADDA)

# ── ṣifa -> kind ──────────────────────────────────────────────────────────
# RULE 1, ENFORCED AT THE ROUTING LAYER. When the ṣifa comparison is the
# detector, it says WHICH property flipped, and that property decides what kind
# of card this is - not the registry `group`, which for an unrouted ṣifa is
# `fallback` and means only "nobody wrote an entry".
#
# The failure this fixes: a ghunna held on a letter that should carry none, or
# any ghunna disagreement other than the one GHUNNA_MISSING covers, resolved to
# GENERIC_SIFAT_MISMATCH -> group `fallback` -> "Talaffuz". A nasalisation error
# titled "pronunciation" is precisely the mad/ghunna-vs-ṣifat confusion.
_BY_SIFA = {
    "ghonna": GHUNNA,
    "qalqla": TAJWEED,
    "tafkheem_or_taqeeq": PRONUNCIATION,
    "hams_or_jahr": PRONUNCIATION,
    "shidda_or_rakhawa": PRONUNCIATION,
    "itbaq": PRONUNCIATION,
}

# Explicit overrides, checked before the group fallback. These are the codes
# whose registry group does not describe what the learner experienced:
# LETTER_ADDED is filed under `haraka` in v5 but is not a vowel error, and the
# qalqalah entries are filed under `sifat` but read as a tajweed ruling.
_BY_CODE = {
    "LETTER_ADDED": EXTRA,
    "LETTER_DROPPED": MISSING,
    # Filed under group `fallback`, which says where the entry came from and
    # nothing about what the learner did.
    "GENERIC_LETTER_SUBSTITUTED": WRONG,
    # GENERIC_SIFAT_MISMATCH IS DELIBERATELY ABSENT. It used to sit here mapped
    # to PRONUNCIATION, and _BY_CODE is consulted first - so an unrouted ghunna
    # or qalqalah fault was titled "Talaffuz" even though the detector had said
    # which property flipped. That is the RULE 1 confusion, hard-coded. It now
    # falls through to _BY_SIFA, and only to `fallback` -> PRONUNCIATION when
    # there is genuinely no ṣifa to route on.
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


def kind_of(code: str, group: str = "", sifa: str = "") -> str:
    """The learner-facing category for one code.

    `sifa` is the ṣifa property that disagreed, for errors that came from the
    ṣifa comparison. It OUTRANKS the registry group, because a group of
    `fallback` describes the state of the content and not the error - see
    _BY_SIFA. It does not outrank an explicit per-code override, which is a
    decision about a specific entry.
    """
    if code in _BY_CODE:
        return _BY_CODE[code]
    if sifa in _BY_SIFA:
        return _BY_SIFA[sifa]
    if group in _BY_GROUP:
        return _BY_GROUP[group]
    if code.startswith("MADD_"):
        return MADD
    # Length on a doubled consonant, not on a madd letter. Its own kind - see
    # SHADDA above.
    if code.startswith("SHADDA_"):
        return SHADDA
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
    # RULE 12's fixed card shape. `rule_name` fills the "which rule" slot,
    # `sifa_name` the "which ṣifa", `articulation` the "which mouth position" -
    # the three questions a card could not previously answer at all.
    "rule_name", "sifa_name", "articulation",
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
    # RULE 12's three newest slots. A legacy row predates all of them, and they
    # are left EMPTY rather than reconstructed: `rule_name` and `articulation`
    # are authored text, and inventing either for an old attempt would put words
    # on a card that no qori wrote and no detector supported.
    for key in ("rule_name", "sifa_name", "articulation"):
        out.setdefault(key, "")

    body = out.get("content") or {}
    if not out.get("kind"):
        out["kind"] = kind_of(out["code"], body.get("group", ""),
                              out.get("sifa", ""))

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
    return _fold_consequences(buckets)


# ── one mistake that the engine necessarily reports twice ─────────────────
# A sakin qalqalah letter read WITH a vowel produces two findings, and they are
# not two mistakes:
#
#     2:7  «أَبْصَـٰرِهِمْ»,  بْ read as بَ
#       unit 29  SUKUN_TO_HARAKA  on ب   the vowel that should not be there
#       unit 30  QALQALA_DROP     on ب   the bounce that therefore cannot happen
#
# The second is not an independent error a learner can fix. Qalqalah IS the
# release of a letter stopped dead; give the letter a vowel and there is nothing
# to release, so the missing bounce is a MEASUREMENT OF THE SAME EVENT. Two
# cards would ask the learner to correct a consequence separately from its
# cause, and the correction for the consequence - "let it bounce" - is not even
# actionable while the vowel is still there.
#
# SO THE EFFECT IS FOLDED INTO THE CAUSE, not merged with it. The surviving card
# is the vowel error, which is the one with an instruction that works; the
# qalqalah occurrence joins its `occurrences` so the ayah still marks that letter
# and tapping it still lands on a card that explains it.
#
# DELIBERATELY NARROW. This is one named pair with a stated mechanism, not a
# general "errors on the same letter collapse" rule - which would have hidden
# the SUB_SAD_SEEN on ص two units later, an unrelated mistake in the same word.
# Adjacency is required for the same reason: two qalqalah letters elsewhere in
# the ayah are not caused by this vowel.
_CAUSE = "SUKUN_TO_HARAKA"
_EFFECT = frozenset({"QALQALAH_MISSING"})     # resolved codes
# The ṣifa detector reports a missing qalqalah on the LETTER's unit and the
# phoneme diff reports it on the MARK's unit, one later. Both are the same
# letter's bounce.
_ADJACENT = 1


def _fold_consequences(
    buckets: dict[tuple[str, str], list[TypedError]],
) -> list[list[TypedError]]:
    causes = {letter: group for (code, letter), group in buckets.items()
              if code == _CAUSE}
    if not causes:
        return list(buckets.values())

    out: list[list[TypedError]] = []
    for (code, letter), group in buckets.items():
        cause = causes.get(letter)
        if cause is not None and code in _EFFECT:
            near_ids = {id(e) for e in group
                        if any(abs(e.at - c.at) <= _ADJACENT for c in cause)}
            cause.extend(e for e in group if id(e) in near_ids)
            # An occurrence too far from any vowel error is a separate mistake
            # on the same letter and keeps its own card. Partitioned by
            # IDENTITY: TypedError is a dataclass, so two occurrences that
            # happen to carry the same values compare equal and `not in` would
            # discard a real one.
            rest = [e for e in group if id(e) not in near_ids]
            if rest:
                out.append(rest)
            continue
        out.append(group)
    return out


def occurrences(group: list[TypedError], spans: dict[int, tuple[int, int]] |
                None = None, uthmani: str = "") -> list[dict]:
    """Where each occurrence happened, in reading order.

    Every one is kept. The card shows a count and the distinct words, but the
    ayah needs each individual `at` to mark every affected letter red - which is
    the requirement merging must not break.

    `span` is the Uthmani character range to paint, narrowed to the SOUND rather
    than the letter-group it sits in (RULE 2), and `ordinal`/`of` say which
    instance of the letter within its word this is (RULE 10). Both are omitted
    rather than guessed when the caller has no text to derive them from - the
    history endpoint replays rows written before either existed.
    """
    out = []
    for e in sorted(group, key=lambda x: x.at):
        one = {"at": e.at, "word": e.word, "word_index": e.word_index}
        span = (spans or {}).get(e.at)
        if span:
            one["span"] = [span[0], span[1]]
            if uthmani:
                from .segments import occurrence_ordinal
                ordinal, total = occurrence_ordinal(uthmani, span, e.letter)
                one["ordinal"], one["of"] = ordinal, total
        out.append(one)
    return out


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
