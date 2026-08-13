# -*- coding: utf-8 -*-
"""Cards come back in RECITATION ORDER.

A DELIBERATE OVERRIDE of the teaching-tier ordering in engine/teaching.py, not
a merge with it. Cards used to be sorted by what the mistake DID - wrong letter,
then articulation, then ruling, then timing - with severity breaking ties. They
are now sorted by where the mistake happens in the ayah and by nothing else.

The tests are written as they are because a HYBRID is the likely regression, not
a return to pure tier order: someone adds tier back as a tiebreaker or a
secondary key, the order looks positional on most inputs, and it silently stops
being positional exactly when two mistakes of different tiers sit near each
other. So the fixtures below deliberately put the LOWEST-priority tier first in
the ayah and the highest last.
"""
import pytest

from tilawah.engine import pipeline, teaching
from tilawah.engine.typed_errors import TypedError


def err(code: str, at: int, letter: str = "ن", word: str = "مِنْ") -> TypedError:
    return TypedError(code=code, at=at, letter=letter, word=word, word_index=0,
                      expected=letter, heard="س")


def order(errors):
    shown, _ = pipeline.present(errors, "uz")
    return [(e["code"], e["at"]) for e in shown]


def test_cards_come_back_in_position_order():
    got = order([err("SUB_SAD_SEEN", 40, "ص"),
                 err("SUB_DHAL_ZAY", 10, "ذ"),
                 err("SUB_QAF_KAF", 25, "ق")])
    assert [at for _c, at in got] == [10, 25, 40]


def test_timing_first_in_the_ayah_still_comes_first():
    """THE CASE A HYBRID GETS WRONG.

    MADD is teaching tier 4 - the lowest priority - and a substituted letter is
    tier 1. Here the madd is at unit 3 and the letter at unit 30. Under tier
    ordering the letter card came first; under position ordering the madd does.
    Any sort that still consults the tier fails this.
    """
    got = order([err("SUB_SAD_SEEN", 30, "ص"),
                 err("MADD_TOO_SHORT", 3, "ا", "قَالَ")])
    assert [c for c, _at in got] == ["MADD_TOO_SHORT", "SUB_SAD_SEEN"]


def test_severity_does_not_reorder_anything():
    """Severity used to break ties inside a tier. It now breaks nothing.

    Two errors cannot share a unit index, so there are no ties left for it to
    break - which is worth asserting, because leaving severity in the sort key
    would be invisible until two entries of different severity landed close
    together.
    """
    got = order([err("QALQALA_DROP", 7, "د", "يَلِدْ"),
                 err("GENERIC_LETTER_SUBSTITUTED", 2, "ب", "بِرَبِّ")])
    assert [at for _c, at in got] == [2, 7]


def test_reveal_order_follows_the_same_order():
    """The client unlocks cards by `reveal_order`, so it must agree with the
    sort or the learner meets them in a different order than they are listed."""
    shown, _ = pipeline.present(
        [err("SUB_SAD_SEEN", 40, "ص"), err("SUB_DHAL_ZAY", 10, "ذ")], "uz")
    assert [c["reveal_order"] for c in shown] == [0, 1]
    assert [c["at"] for c in shown] == [10, 40]


def test_a_merged_card_sorts_by_its_first_occurrence():
    """One letter wrong in four places is one card, and it belongs where the
    learner first meets it - not where its last occurrence sits."""
    errs = [err("SUB_DHAL_ZAY", at, "ذ") for at in (30, 12, 45)]
    errs.append(err("SUB_SAD_SEEN", 20, "ص"))
    got = order(errs)
    assert [c for c, _at in got] == ["SUB_DHAL_ZAY", "SUB_SAD_SEEN"]
    assert got[0][1] == 12


def test_tiers_are_still_computed_for_the_client():
    """The override changed the SORT, not the tier. `tier` still travels on
    every card, and teaching.tier() is still its source - so a future decision
    to restore tier ordering has everything it needs."""
    shown, _ = pipeline.present([err("SUB_SAD_SEEN", 5, "ص")], "uz")
    card = shown[0]
    assert card["tier"] == teaching.tier(card["kind"])
    assert card["tier"] > 0


@pytest.mark.parametrize("positions", [
    [1, 2, 3], [3, 2, 1], [2, 1, 3], [9, 4, 7], [50, 1, 25],
])
def test_order_is_position_whatever_the_input_order(positions):
    """present() sorts; it does not preserve the caller's order."""
    codes = ["SUB_DHAL_ZAY", "SUB_SAD_SEEN", "SUB_QAF_KAF"]
    letters = ["ذ", "ص", "ق"]
    errs = [err(c, at, ch)
            for c, at, ch in zip(codes, positions, letters)]
    got = order(errs)
    assert [at for _c, at in got] == sorted(positions)
