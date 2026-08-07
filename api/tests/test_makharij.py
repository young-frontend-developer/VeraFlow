# -*- coding: utf-8 -*-
"""The makhraj + ṣifat line: one sentence per letter, on every card that is
about producing one.

THE GAP THIS CLOSES, stated as the case that made it urgent:
GENERIC_LETTER_SUBSTITUTED and GENERIC_SIFAT_MISMATCH catch every confusion
nobody has authored an entry for, which makes them the most-shown cards in the
app, and neither described any letter at all. The learner was told which letter
was wrong and handed a drill, with nothing anywhere on the card saying what the
correct sound IS.
"""
import pytest

from tilawah.content import makharij
from tilawah.engine import cards, pipeline
from tilawah.engine.typed_errors import TypedError

ALPHABET = "ءبتثجحخدذرزسشصضطظعغفقكلمنهوي"


def test_all_28_letters_are_covered():
    """The alphabet is fixed and the table is expected to cover it. Computed
    rather than assumed, because a hand-edited JSON file is exactly where a
    letter goes missing quietly."""
    assert makharij.missing() == []
    assert len(ALPHABET) == 28
    assert len(makharij.known()) == 28


@pytest.mark.parametrize("lang", ["uz", "ru"])
@pytest.mark.parametrize("letter", list(ALPHABET))
def test_every_letter_has_one_sentence_in_both_languages(letter, lang):
    line = makharij.line(letter, lang)
    assert line, f"{letter} has no {lang} sentence"
    # A budget, not a style rule: this sits above the fix inside a card with a
    # word budget, and a paragraph here pushes the correction off the screen.
    assert len(line) < 220, f"{letter} {lang} is too long for a card: {line}"


@pytest.mark.parametrize("value", ["", "fatha", "mofakham", "sh", "ڇ", "ـ"])
def test_a_non_letter_has_no_makhraj(value):
    """`letter` is not always a letter. A haraka error reports a NAME, a ṣifa
    error reports a ṣifa, and QPS notation marks reach cards too. None of them
    come out of a place in the mouth."""
    assert makharij.line(value) == ""


def test_the_line_describes_the_target_not_what_was_heard():
    """THE PROPERTY THAT MATTERS. The card exists to move the learner toward
    the correct sound; describing the one they produced by mistake describes
    the mistake."""
    sad = makharij.line("ص")
    seen = makharij.line("س")
    assert sad != seen
    assert makharij.for_error("ص", "ص") == sad
    # Even when `letter` carries the heard side, `expected` wins.
    assert makharij.for_error("ص", "س") == sad


def test_a_sifa_error_falls_back_to_the_letter():
    """ṣifa errors carry a ṣifa VALUE in `expected` - "mofakham", not a letter -
    and on those the letter IS the target: the learner said the right letter
    and made it wrong."""
    assert makharij.for_error("mofakham", "ط") == makharij.line("ط")


# ── through the pipeline ──────────────────────────────────────────────────

def card_for(err):
    shown, _ = pipeline.present([err], "uz")
    assert shown, f"{err.code} produced no card"
    return shown[0]


@pytest.mark.parametrize("code,letter,expected,heard,sifa", [
    ("GENERIC_LETTER_SUBSTITUTED", "ص", "ص", "س", ""),
    ("GENERIC_SIFAT_MISMATCH", "ط", "mofakham", "moraqaq",
     "tafkheem_or_taqeeq"),
    ("SUB_SAD_SEEN", "ص", "ص", "س", ""),
    ("SUB_QAF_KAF", "ق", "ق", "ك", ""),
    ("TAFKHEEM_LOST", "ط", "mofakham", "moraqaq", "tafkheem_or_taqeeq"),
    ("QALQALA_DROP", "د", "", "", "qalqla"),
])
def test_letter_cards_carry_a_makhraj_line(code, letter, expected, heard,
                                           sifa):
    err = TypedError(code=code, at=3, letter=letter, expected=expected,
                     heard=heard, sifa=sifa, word="ٱلصَّمَدُ", word_index=1)
    card = card_for(err)
    assert card["makhraj"], f"{code} has no makhraj line"
    assert card["makhraj"] == makharij.line(letter)


def test_the_two_generics_are_covered_which_was_the_whole_gap():
    """Named separately from the parametrised case above because these two are
    the reason the table exists: every unlisted confusion lands on one of
    them."""
    for code in ("GENERIC_LETTER_SUBSTITUTED", "GENERIC_SIFAT_MISMATCH"):
        err = TypedError(code=code, at=3, letter="ص", expected="ص", heard="س",
                         word="ٱلصَّمَدُ", word_index=1)
        assert card_for(err)["makhraj"]


@pytest.mark.parametrize("code,letter,count", [
    ("LETTER_DROPPED", "ح", 0),
    ("LETTER_ADDED", "ا", 0),
    ("MADD_SHORT", "ا", 4),
    ("MADD_LONG", "و", 2),
])
def test_non_articulation_cards_carry_no_makhraj_line(code, letter, count):
    """THE SCOPE IS THE ISOLATED-LETTER DRILL'S, and the two must not diverge.
    A learner who SKIPPED a ح can already say ح - being told where it comes
    from answers a question they did not ask - and a madd error is about a
    length, not a place. One rule in both places, so the card and its ladder
    cannot disagree about what kind of mistake this is."""
    err = TypedError(code=code, at=3, letter=letter, expected=letter,
                     expected_count=count, heard_count=1,
                     word="ٱلْفَتْحُ", word_index=1)
    card = card_for(err)
    assert card["makhraj"] == "", f"{code} should carry no makhraj line"


def test_the_makhraj_line_is_not_the_fix_repeated():
    """Two slots answering two different questions. If they were the same
    sentence the card would print it twice under two headings - the exact
    duplication `articulation` already guards against."""
    err = TypedError(code="SUB_SAD_SEEN", at=3, letter="ص", expected="ص",
                     heard="س", word="ٱلصَّمَدُ", word_index=1)
    card = card_for(err)
    body = card["content"] or {}
    assert card["makhraj"].strip() != (body.get("fix") or "").strip()
