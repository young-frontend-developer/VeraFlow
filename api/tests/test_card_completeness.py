# -*- coding: utf-8 -*-
"""RULE 13 as a failing test rather than as a checklist somebody remembers.

tools/audit_cards.py renders every code the engine can emit, in both languages,
and asks each card the nine questions a correction has to answer. This file is
what makes it run on every commit.

WHY IT IS NOT JUST THE SCRIPT. The defect this whole audit exists for - a card
whose authored text names a letter the learner never said - was present in the
registry for the life of the file and survived being read by a person more than
once. It is correct in the registry, correct in the renderer, and wrong only in
the combination, which is exactly the class of thing manual review does not
catch and a loop over the cross product does.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import audit_cards  # noqa: E402


def test_every_card_answers_every_question_that_applies_to_it():
    failures = audit_cards.audit()
    assert not failures, (
        f"{len(failures)} incomplete cards:\n  "
        + "\n  ".join(failures[:40]))


@pytest.mark.parametrize("lang", ["uz", "ru"])
def test_every_routed_sifa_has_a_name_and_an_instruction(lang):
    """RULES 3 AND 4. A ṣifa the detector can report and nobody has written
    guidance for falls straight back to "the letter's ṣifa did not come out
    right" - the sentence those rules ban, and the one that was the most-shown
    correction in the app."""
    from tilawah.content import sifat
    from tilawah.engine.sifat_codes import ROUTED

    missing = []
    for field in sorted(ROUTED):
        guide = sifat.guidance(field, "", lang)
        if not guide:
            missing.append(field)
    assert not missing, (
        f"routed ṣifāt with no authored guidance in {lang}: {missing}")


def test_the_generic_sifat_sentence_is_gone_wherever_a_sifa_is_known():
    """The lint RULE 4 asks for, stated as behaviour rather than as a string
    search: when the detector knows which property flipped, the card must be
    about that property."""
    from tilawah import content
    from tilawah.content import sifat
    from tilawah.engine.pipeline import _name_the_sifat
    from tilawah.engine.typed_errors import TypedError
    from tilawah.engine.sifat_codes import ROUTED

    for field in sorted(ROUTED):
        e = TypedError(code="GENERIC_SIFAT_MISMATCH", at=3, letter="ط",
                       expected="mofakham", heard="moraqaq", sifa=field,
                       word="ٱلطَّارِقُ", word_index=2)
        body = _name_the_sifat(
            e, content.render(e.code, "uz", e.dict()),
            sifat.guidance(field, e.letter, "uz"))
        guide = sifat.guidance(field, e.letter, "uz")
        assert body["headline"] == guide["wrong"], (
            f"{field}: the generic headline survived")
        assert body["fix"] == guide["how"], (
            f"{field}: the generic instruction survived")
        # And the banned sentence itself, so a rephrasing cannot slip past.
        assert "sifati to'g'ri chiqmadi" not in body["headline"]


def test_known_gaps_are_named_rather_than_silent():
    """The audit's other half. A gap nobody can count becomes permanent - see
    coaching.missing_audio(), which exists for the same reason."""
    gaps = audit_cards.gaps()
    assert gaps, "the gap report went empty, which means it stopped looking"
    # The 13 unrecorded letter-pair files are the largest single gap and the
    # one with a name attached: it is a recording task for a qori, not an
    # engineering one.
    assert sum(1 for g in gaps if g.startswith("audio ")) == 13
