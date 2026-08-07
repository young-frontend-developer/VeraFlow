# -*- coding: utf-8 -*-
"""What to teach FIRST, and what to refuse to teach at all.

Two policies live here, and they are separate decisions that happen to run in
the same pass.

── 1. ONE THING AT A TIME, IN THE RIGHT ORDER ─────────────────────────────

A learner who reads one ayah and gets eight cards has not been taught eight
things; they have been handed a defect report and left to triage it. Worse, the
list was ordered by the registry's `severity` field, which is a property of the
ENTRY - how bad this class of mistake is in general - and not of what this
learner should fix next.

So cards are ranked into four TIERS, and the tier is about what the mistake DID:

    1  the wrong letter came out       a letter missing, added or swapped
    2  the right letter, made wrong    articulation and ṣifa
    3  a ruling was not applied        ahkam - qalqalah, ghunnah, idgham
    4  the timing was off              madd, shadda and duration generally

The order is not arbitrary and it is not severity by another name. It is the
order the errors DEPEND on each other in. Getting the madd length right on a
word whose letter is wrong teaches the learner to hold a wrong sound for the
correct count. Fix what the mouth produced, then how it produced it, then which
ruling applies to it, then how long it lasts - each step is only meaningful once
the one before it is true.

Severity still breaks ties WITHIN a tier, so nothing that ranking knew is lost.

── 2. A CONTRADICTION IS NOT A CARD ───────────────────────────────────────

Two detectors can land on the same unit and say incompatible things: one that
the letter was dropped, another that it was mispronounced. Both cannot be true -
a letter that was never said cannot also have come out wrong - so at least one
is a measurement artifact, and there is no way to tell which from here.

Showing the more confident one is guessing with extra steps, and the cost is
asymmetric: a learner told to fix a mistake they did not make will "correct" a
sound that was already right. Showing both is worse - two cards about one letter
that disagree with each other, which reads as the app being broken and is in
fact the app being honest badly.

So both are withheld and the conflict is LOGGED, with enough on it to diagnose:
the position, the codes, and what each claimed was heard. That is a detection
bug to fix upstream, and it belongs in a queue rather than on a card.

⚠️ THE THRESHOLD IS DELIBERATELY NARROW. Only pairs where BOTH entries are
detection_confidence 'high' are treated as conflicts, because that is the case
where neither can be dismissed. Where one side is medium the disagreement is
much more likely to be the weaker detector being wrong, and suppressing a good
card because a weak detector disagreed with it would silence real corrections.
That asymmetry is a judgement, and it is the number to revisit first if this
starts hiding things it should not.
"""
import logging

from ..content import coaching
from .typed_errors import TypedError

log = logging.getLogger("tilawah.teaching")

# ── tiers ─────────────────────────────────────────────────────────────────
# Keyed on `kind` - the learner-facing category cards.kind_of() already
# computes - rather than on the code. Keying on the code would need a row per
# entry and would go stale the moment one was added; `kind` is exactly the
# "what did this do to the recitation" axis the tiers are about.
LETTER, ARTICULATION, RULING, TIMING = 1, 2, 3, 4
LAST = 9

BY_KIND = {
    # TIER 1 - the wrong sound came out of the mouth. Classically lahn jaliy:
    # it can change the word, and everything else is built on top of it.
    "missing_letter": LETTER,
    "extra_letter": LETTER,
    "wrong_letter": LETTER,
    # HARAKA IS TIER 1, and this is the one placement that is a judgement
    # rather than a reading of the brief. A vowel is not a letter, so "missing,
    # extra or substituted letter" does not literally cover it - but
    # أَنْعَمْتَ against أَنْعَمْتُ is "You bestowed" against "I bestowed", which is
    # a changed meaning, which is the property that puts tier 1 first. Filing it
    # under articulation would rank a meaning-changing error below a ṣifa one.
    "haraka": LETTER,
    # TIER 2 - the right letter, produced wrong. The mouth is in the wrong
    # place or the wrong shape.
    "pronunciation": ARTICULATION,
    # TIER 3 - the letter and its quality are right; a RULING that applies to it
    # was not applied. qalqalah and ghunnah are rulings about position, not
    # about how the letter is formed.
    "tajweed": RULING,
    "ghunna": RULING,
    # TIER 4 - everything was right except how long it lasted.
    "madd": TIMING,
    "shadda": TIMING,
}


def tier(kind: str) -> int:
    """Which tier a card belongs to. Unknown kinds sort LAST.

    Not tier 4: an unclassified card is not "a timing error", it is a card
    nobody has placed, and putting it ahead of a real timing error would be an
    ordering claim nothing supports. LAST keeps it visible but never first.
    """
    return BY_KIND.get(kind, LAST)


# ── conflicts ─────────────────────────────────────────────────────────────
# Kinds that make a claim about WHAT THE MOUTH PRODUCED at a position. Two of
# these at one unit are talking about the same event, so they can contradict.
# A timing card at the same unit is not a contradiction - a letter can be both
# wrong and held too long - so timing is deliberately absent.
_CLAIMS_PRODUCTION = {"missing_letter", "extra_letter", "wrong_letter",
                      "haraka", "pronunciation"}


# Detectors that are a DIRECT COMPARISON of the reference against the
# hypothesis - the phoneme aligner in typed_diff. A dropped unit, an added one
# or a swapped vowel is read off a string diff, not inferred from a probability
# distribution over ṣifāt, which makes these the strongest signals the engine
# produces. They are named here because THE REGISTRY DOES NOT RATE THEM: the v5
# gap entries were authored without a `detection_confidence` field at all, so
# asking the registry about LETTER_DROPPED answers None.
#
# ⚠️ That missing field is a real gap and this set is a stand-in for it, not a
# fix. Reading it as "high" is defensible - a string diff is not a guess - but
# it is a claim made here rather than in the registry where the other
# confidences live. The clean version is a detection_confidence on every v5
# entry, which needs the person who authored them.
_ALIGNER_CODES = frozenset({
    "LETTER_DROPPED", "LETTER_ADDED",
    "HARAKA_SUBSTITUTED", "HARAKA_TO_SUKUN", "SUKUN_TO_HARAKA",
    "GENERIC_LETTER_SUBSTITUTED",
})


def _is_high_confidence(code: str) -> bool:
    """Whether this detector is credible enough for a disagreement to be a
    genuine standoff rather than one detector simply being wrong.

    Resolved through the alias table first, because the engine and the registry
    speak different vocabularies - SUB_SAD_SEEN carries MAKHARIJ_SAD_TO_SEEN's
    confidence, and looking up the engine name would silently answer False for
    every L1 pair and disable conflict detection exactly where it matters.

    An UNRATED entry falls back to whether the code is an aligner detector. It
    does not fall back to True: an unrated ṣifa code stays out of the conflict
    gate, which is the safe direction - it can still produce its card, and the
    gate only ever withholds.
    """
    entry = coaching.entry(code) or {}
    rated = entry.get("detection_confidence")
    if rated:
        return rated == "high"
    return code in _ALIGNER_CODES


def _contradict(a: TypedError, b: TypedError, kind_of) -> str:
    """Why these two cannot both be true, or "" if they can.

    Returns the reason rather than a bool so the log line says what was decided
    and not merely that something was.
    """
    ka, kb = kind_of(a), kind_of(b)
    if ka not in _CLAIMS_PRODUCTION or kb not in _CLAIMS_PRODUCTION:
        return ""

    # A letter that was never said cannot also have been mispronounced. This is
    # the pairing that actually shows up: the aligner drops a unit and the ṣifa
    # comparison reports on the same index.
    absent = {"missing_letter", "extra_letter"}
    if (ka in absent) != (kb in absent):
        return f"{ka} and {kb} at one unit: it cannot be both absent and wrong"

    # Two claims about what was heard, disagreeing. "You said س" and "you said
    # ز" about one sound is a contradiction on its face.
    if a.heard and b.heard and a.heard != b.heard:
        return f"heard {a.heard!r} and {b.heard!r} claimed for one unit"

    return ""


def conflicts(raw: list[TypedError], kind_of) -> tuple[set[int], list[dict]]:
    """Unit positions to withhold entirely, and a log record for each.

    `kind_of` maps one TypedError to its card kind. Injected rather than
    imported so this module does not need the registry body that
    cards.kind_of() wants, and so a test can drive it directly.

    ONLY THE CONFLICTING UNIT IS WITHHELD, not the whole attempt. Everything
    detected elsewhere in the ayah is unaffected - the contradiction is local to
    one position and so is the refusal.
    """
    by_at: dict[int, list[TypedError]] = {}
    for e in raw:
        by_at.setdefault(e.at, []).append(e)

    bad: set[int] = set()
    records: list[dict] = []
    for at, group in sorted(by_at.items()):
        if len(group) < 2:
            continue
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a.code == b.code:
                    continue
                reason = _contradict(a, b, kind_of)
                if not reason:
                    continue
                if not (_is_high_confidence(a.code)
                        and _is_high_confidence(b.code)):
                    # One side is not credible enough for this to be a genuine
                    # standoff. Left alone rather than suppressed - see the
                    # threshold note in the module docstring.
                    continue
                bad.add(at)
                records.append({"at": at, "codes": sorted({a.code, b.code}),
                                "reason": reason,
                                "letter": a.letter or b.letter,
                                "word": a.word or b.word})
                log.warning("CONFLICT at unit %s: %s (%s)", at,
                            sorted({a.code, b.code}), reason)
                break
            if at in bad:
                break
    return bad, records
