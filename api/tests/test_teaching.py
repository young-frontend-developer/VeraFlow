# -*- coding: utf-8 -*-
"""Teaching order, the reveal chain, and the refusal to guess between
contradictions.

Three properties, all of which the app got wrong by doing the obvious thing:

  ORDER    ranking by the registry's `severity` field ranked by how bad a CLASS
           of mistake is in general, not by what this learner should fix next,
           so a madd card could sit above the substituted letter it was
           measuring the length of.

  REVEAL   every card was rendered at once. Eight cards is not eight lessons.

  CONFLICT two detectors landing on one unit with incompatible claims produced
           two cards that disagreed with each other, in front of a beginner.
"""
import pytest

from tilawah.engine import cards, pipeline, teaching
from tilawah.engine.typed_errors import TypedError


def kinds_of(errs):
    shown, _ = pipeline.present(errs, "uz")
    return [c["kind"] for c in shown]


# ── the four tiers ────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind,expected", [
    ("missing_letter", teaching.LETTER),
    ("extra_letter", teaching.LETTER),
    ("wrong_letter", teaching.LETTER),
    ("haraka", teaching.LETTER),
    ("pronunciation", teaching.ARTICULATION),
    ("tajweed", teaching.RULING),
    ("ghunna", teaching.RULING),
    ("madd", teaching.TIMING),
    ("shadda", teaching.TIMING),
])
def test_each_kind_lands_in_its_tier(kind, expected):
    assert teaching.tier(kind) == expected


def test_an_unplaced_kind_sorts_last_not_fourth():
    """LAST, not TIMING. An unclassified card is not "a timing error", it is a
    card nobody has placed, and ranking it ahead of a real timing error would be
    an ordering claim nothing supports."""
    assert teaching.tier("something_new") == teaching.LAST
    assert teaching.tier("") == teaching.LAST
    assert teaching.LAST > teaching.TIMING


def test_the_wrong_letter_outranks_its_own_length():
    """THE ORDERING BUG, stated as the case that produced it. A learner whose ص
    came out as س in a word they also over-held must be told about the letter
    first: fixing the length first teaches them to hold a wrong sound for the
    correct count."""
    errs = [
        TypedError(code="MADD_LONG", at=9, letter="ا", expected_count=2,
                   heard_count=5, word="ٱلصَّمَدُ", word_index=1),
        TypedError(code="SUB_SAD_SEEN", at=3, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
    ]
    assert kinds_of(errs) == ["wrong_letter", "madd"]
    # ...and the reverse input order must not change it.
    assert kinds_of(list(reversed(errs))) == ["wrong_letter", "madd"]


def test_the_full_four_tier_order():
    errs = [
        TypedError(code="MADD_LONG", at=20, letter="ا", expected_count=2,
                   heard_count=5, word="قَالَ", word_index=4),
        TypedError(code="QALQALA_DROP", at=15, letter="د", sifa="qalqla",
                   word="يَلِدْ", word_index=3),
        TypedError(code="TAFKHEEM_LOST", at=10, letter="ط",
                   expected="mofakham", heard="moraqaq",
                   sifa="tafkheem_or_taqeeq", word="ٱلطَّارِقُ", word_index=2),
        TypedError(code="LETTER_DROPPED", at=5, letter="ح", expected="ح",
                   word="ٱلْفَتْحُ", word_index=1),
    ]
    shown, _ = pipeline.present(errs, "uz")
    assert [c["tier"] for c in shown] == [1, 2, 3, 4]
    assert [c["kind"] for c in shown] == [
        "missing_letter", "pronunciation", "tajweed", "madd"]


def test_severity_still_breaks_ties_inside_a_tier():
    """The tier outranks severity; it does not replace it. Two cards in the
    same tier keep the order severity gave them, so nothing the old ranking
    knew is lost."""
    errs = [
        TypedError(code="SUB_SAD_SEEN", at=30, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=5),
        TypedError(code="SUB_QAF_KAF", at=2, letter="ق", expected="ق",
                   heard="ك", word="قُلْ", word_index=0),
    ]
    shown, _ = pipeline.present(errs, "uz")
    assert {c["tier"] for c in shown} == {teaching.LETTER}
    # Same tier and same severity, so position decides - the earlier one leads.
    assert [c["at"] for c in shown] == [2, 30]


# ── the reveal chain ──────────────────────────────────────────────────────

def test_reveal_order_is_dense_and_starts_at_zero():
    """The client opens card 0 and unlocks forward. A gap or a missing 0 would
    leave the learner looking at a locked list with nothing open."""
    errs = [
        TypedError(code="SUB_SAD_SEEN", at=3, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
        TypedError(code="TAFKHEEM_LOST", at=10, letter="ط",
                   expected="mofakham", heard="moraqaq",
                   sifa="tafkheem_or_taqeeq", word="ٱلطَّارِقُ", word_index=2),
        TypedError(code="MADD_LONG", at=20, letter="ا", expected_count=2,
                   heard_count=5, word="قَالَ", word_index=4),
    ]
    shown, _ = pipeline.present(errs, "uz")
    assert [c["reveal_order"] for c in shown] == list(range(len(shown)))


def test_reveal_order_counts_only_cards_that_will_be_shown(monkeypatch):
    """Numbered AFTER the content gate. Numbering before it would promise
    "hali 3 ta bor" and then reveal one, which is a worse lie than saying
    nothing - the count exists so the learner can trust the rest is there."""
    errs = [
        TypedError(code="SUB_SAD_SEEN", at=3, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
        TypedError(code="SUB_QAF_KAF", at=8, letter="ق", expected="ق",
                   heard="ك", word="قُلْ", word_index=0),
    ]
    shown, silent = pipeline.present(errs, "uz")
    assert [c["reveal_order"] for c in shown] == list(range(len(shown)))
    # Whatever the gate withheld carries no promise of being revealed.
    for s in silent:
        assert not s.get("reveal_order")


# ── contradictions ────────────────────────────────────────────────────────

def kind_of(e):
    return cards.kind_of(e.code, "", e.sifa)


def test_absent_and_mispronounced_at_one_unit_is_a_conflict():
    """A letter that was never said cannot also have come out wrong. Both
    detectors are high-confidence, so there is no basis for preferring one."""
    a = TypedError(code="LETTER_DROPPED", at=7, letter="ص", expected="ص",
                   word="ٱلصَّمَدُ", word_index=1)
    b = TypedError(code="SUB_SAD_SEEN", at=7, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1)
    bad, records = teaching.conflicts([a, b], kind_of)
    assert bad == {7}
    assert records and records[0]["at"] == 7
    assert sorted(records[0]["codes"]) == ["LETTER_DROPPED", "SUB_SAD_SEEN"]
    assert records[0]["reason"]


def test_two_different_heard_values_at_one_unit_is_a_conflict():
    """"You said س" and "you said ك" about one sound cannot both be true."""
    a = TypedError(code="SUB_SAD_SEEN", at=4, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1)
    b = TypedError(code="SUB_QAF_KAF", at=4, letter="ق", expected="ق",
                   heard="ك", word="ٱلصَّمَدُ", word_index=1)
    bad, _ = teaching.conflicts([a, b], kind_of)
    assert bad == {4}


def test_a_conflicting_unit_shows_neither_card():
    """The whole point. Not "show the more confident one" - that is guessing
    with extra steps, and it makes the learner correct a sound that may have
    been right."""
    errs = [
        TypedError(code="LETTER_DROPPED", at=7, letter="ص", expected="ص",
                   word="ٱلصَّمَدُ", word_index=1),
        TypedError(code="SUB_SAD_SEEN", at=7, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
    ]
    shown, silent = pipeline.present(errs, "uz")
    assert shown == []
    assert {s["status"] for s in silent} == {"conflict"}
    assert len(silent) == 2, "both sides must be withheld, not just one"


def test_a_conflict_does_not_silence_the_rest_of_the_ayah():
    """The contradiction is local to one position and so is the refusal."""
    errs = [
        TypedError(code="LETTER_DROPPED", at=7, letter="ص", expected="ص",
                   word="ٱلصَّمَدُ", word_index=1),
        TypedError(code="SUB_SAD_SEEN", at=7, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
        TypedError(code="SUB_QAF_KAF", at=19, letter="ق", expected="ق",
                   heard="ك", word="قُلْ", word_index=0),
    ]
    shown, silent = pipeline.present(errs, "uz")
    assert [c["at"] for c in shown] == [19]
    assert len([s for s in silent if s["status"] == "conflict"]) == 2


def test_timing_beside_a_letter_error_is_not_a_conflict():
    """A letter can be both wrong AND held too long - those are two true
    statements about one unit, not a contradiction. Suppressing them would
    delete real corrections wholesale."""
    errs = [
        TypedError(code="SUB_SAD_SEEN", at=6, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
        TypedError(code="MADD_LONG", at=6, letter="ا", expected_count=2,
                   heard_count=5, word="ٱلصَّمَدُ", word_index=1),
    ]
    bad, records = teaching.conflicts(errs, kind_of)
    assert bad == set() and records == []


def test_a_medium_confidence_disagreement_is_not_a_conflict():
    """THE NARROW THRESHOLD, pinned. Only two HIGH-confidence detectors
    disagreeing is a standoff. Where one side is weaker the disagreement is
    likelier to be that detector being wrong, and suppressing a good card
    because a weak one objected would silence real corrections.

    QALQALAH_EXCESSIVE is detection_confidence 'medium' in the registry, so
    this pair must survive even though the claims are incompatible.
    """
    from tilawah.content import coaching
    assert (coaching.entry("QALQALAH_EXCESSIVE") or {}).get(
        "detection_confidence") == "medium", "fixture assumption broke"

    errs = [
        TypedError(code="LETTER_DROPPED", at=11, letter="د", expected="د",
                   word="يَلِدْ", word_index=0),
        TypedError(code="QALQALAH_EXCESSIVE", at=11, letter="د", sifa="qalqla",
                   heard="moqalqal", word="يَلِدْ", word_index=0),
    ]
    bad, _ = teaching.conflicts(errs, kind_of)
    assert bad == set()


def test_one_error_at_a_unit_is_never_a_conflict():
    errs = [TypedError(code="SUB_SAD_SEEN", at=3, letter="ص", expected="ص",
                       heard="س", word="ٱلصَّمَدُ", word_index=1)]
    assert teaching.conflicts(errs, kind_of) == (set(), [])


def test_the_same_code_twice_at_one_unit_is_never_a_conflict():
    """Two occurrences of one finding is what the merge is for, not a
    disagreement."""
    errs = [
        TypedError(code="SUB_SAD_SEEN", at=3, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
        TypedError(code="SUB_SAD_SEEN", at=3, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
    ]
    assert teaching.conflicts(errs, kind_of) == (set(), [])
