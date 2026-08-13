# -*- coding: utf-8 -*-
"""The retry action. What it asks for, and what it refuses to ask for.

WHAT THIS FILE USED TO PIN, AND WHY IT CHANGED. There was a four-rung ladder -
letter, letter+harakat, word, ayah - and this file asserted its shape in
detail. Two of those rungs could not be scored (there is no target for a bare
letter) and the fourth was a defect: EVERY card ended on a whole-ayah rung, so
a recitation with ten corrections asked for the entire verse ten times, once
per card. A learner who fixed card 2 last performed the whole ayah for it,
having already performed the whole ayah for cards 8, 5 and 1.

So the ladder is now one rung - the affected word - and the ayah is requested
ONCE, by the results screen, after every card is resolved. The tests below pin
that, and several of them are stated as ABSENCES, because the defect was never
one wrong branch: it was one shape applied to everything, and it would come
back the same way.
"""
import pytest

from tilawah.engine import practice, pipeline
from tilawah.engine.typed_errors import TypedError


def focuses(letter="ذ", word="ذَٰلِكَ", word_index=1, code="", expected_count=0):
    return [r["focus"] for r in practice.ladder(
        letter, word, word_index, code=code, expected_count=expected_count)]


# ── one action, never a ladder ────────────────────────────────────────────

@pytest.mark.parametrize("code", [
    "SUB_DHAL_ZAY", "LETTER_DROPPED", "LETTER_ADDED", "MADD_TOO_SHORT",
    "GENERIC_SIFAT_MISMATCH", "QALQALA_DROP", "SOMETHING_NEW", "",
])
def test_one_rung_whatever_the_error(code):
    """THE CENTRAL PROMISE. One card asks for one recording."""
    rungs = practice.ladder("ذ", "ذَٰلِكَ", 1, code=code, expected_count=4)
    assert len(rungs) == 1, [r["focus"] for r in rungs]
    assert rungs[0]["level"] == 1


@pytest.mark.parametrize("code", [
    "SUB_DHAL_ZAY", "LETTER_DROPPED", "LETTER_ADDED", "MADD_TOO_SHORT",
    "MADD_SHORT", "GHUNNA_MISSING", "QALQALA_DROP", "SOMETHING_NEW", "",
])
def test_no_card_ever_asks_for_the_whole_ayah(code):
    """THE REGRESSION GUARD, and the reason this file exists in this shape.

    Stated over every code and every input shape rather than on one example,
    because the bug was structural: `rungs.append(AYAH)` ran unconditionally at
    the end of ladder(), so it applied to all of them at once and would return
    that way. An ayah rung anywhere here means a ten-mistake attempt is back to
    demanding ten full recitations.
    """
    for letter in ("ذ", "ا", "ن", ""):
        for word, wi in [("ذَٰلِكَ", 1), ("قَالَ", 0), ("", -1)]:
            got = [r["focus"] for r in practice.ladder(
                letter, word, wi, code=code, expected_count=4)]
            assert "ayah" not in got, f"{code} {letter!r} {word!r}: {got}"


@pytest.mark.parametrize("code", [
    "SUB_DHAL_ZAY", "LETTER_DROPPED", "MADD_TOO_SHORT", "SOMETHING_NEW", "",
])
def test_no_card_drills_a_bare_letter_or_a_syllable(code):
    """The two rungs the engine could never score.

    They carried `check: "self"` - the learner grading themselves on the first
    thing they touched - and for three of the four old categories they were not
    even the mistake. Gone for every code, not just the ones that were reviewed.
    """
    for letter in ("ذ", "ح", "ا", "ن", ""):
        got = [r["focus"] for r in practice.ladder(
            letter, "ذَٰلِكَ", 1, code=code, expected_count=4)]
        assert "letter" not in got, f"{code} {letter!r}: {got}"
        assert "syllables" not in got, f"{code} {letter!r}: {got}"


# ── what the one rung is ──────────────────────────────────────────────────

def test_the_rung_is_the_learners_own_word():
    """Not an example from a registry. The word they actually misread is the
    word they are about to be re-tested on, and no authored example beats it."""
    rungs = practice.ladder("ص", "ٱلصَّمَدُ", 2)
    assert rungs[0]["items"] == ["ٱلصَّمَدُ"]
    assert rungs[0]["word_index"] == 2


@pytest.mark.parametrize("code,focus", [
    ("LETTER_DROPPED", "word_include"),
    ("LETTER_ADDED", "word_omit"),
    ("MADD_TOO_SHORT", "word_hold"),
    ("SUB_DHAL_ZAY", "word"),
    ("GENERIC_SIFAT_MISMATCH", "word"),
])
def test_the_focus_still_says_what_to_attend_to(code, focus):
    """One action described four ways, not four actions.

    The focus survived the collapse because the instruction genuinely differs -
    sound the letter you skipped / leave out the one you added / hold for the
    count / say it as written - and the client prints a different line for each.
    """
    assert focuses(letter="ا", word="قَالَ", word_index=0, code=code,
                   expected_count=4) == [focus]


def test_the_madd_rung_carries_the_reference_count():
    rungs = practice.ladder("ا", "قَالَ", 0, code="MADD_TOO_SHORT",
                            expected_count=6)
    assert rungs[0]["hold"] == 6
    assert rungs[0]["items"] == ["قَالَ"], "a count on a rung with no word"


def test_a_madd_error_with_no_reference_count_still_records_the_word():
    """The count comes from the reference and nowhere else, but its absence
    costs the COUNTER, not the recording. Falling back to the plain word rung
    keeps the card actionable instead of dropping its only control."""
    assert focuses(letter="ا", word="قَالَ", word_index=0,
                   code="MADD_TOO_SHORT", expected_count=0) == ["word"]


def test_every_word_rung_is_recordable_and_scored():
    """The whole reason the narrow rungs went. What remains, the engine can
    actually judge: a word range of an ayah is exactly what present() scores."""
    for code in ("LETTER_DROPPED", "LETTER_ADDED", "MADD_TOO_SHORT",
                 "SUB_DHAL_ZAY"):
        rung = practice.ladder("ا", "قَالَ", 3, code=code,
                               expected_count=4)[0]
        assert rung["recordable"] is True
        assert rung["check"] == practice.SCORED
        assert rung["word_index"] == 3


def test_an_unplaceable_word_is_shown_but_not_recordable():
    """word_index -1 means the unit could not be placed in a word. The text can
    still be shown; the re-record cannot, because start_word would be a guess
    and a guess silently scores the learner against a different word."""
    rung = practice.ladder("ص", "ٱلصَّمَدُ", -1)[0]
    assert rung["items"] == ["ٱلصَّمَدُ"]
    assert rung["recordable"] is False


def test_no_word_means_no_recorder_at_all():
    """A ṣifa error the engine could not place in a word. An empty ladder
    renders no control, which is correct: there is nothing honest to record
    against, and the ayah button is no longer available as a consolation rung.
    """
    assert practice.ladder("ذ", "", -1) == []
    assert practice.ladder("", "", -1, code="MADD_TOO_SHORT") == []


def test_every_rung_carries_the_full_wire_shape():
    """The client indexes these directly, so a rung missing one is not a
    degraded ladder - it is a crash on the results screen."""
    keys = {"level", "focus", "items", "recordable", "check", "word_index",
            "audio", "audio_source", "hold"}
    for code, count in [("SUB_DHAL_ZAY", 0), ("LETTER_DROPPED", 0),
                        ("LETTER_ADDED", 0), ("MADD_TOO_SHORT", 4)]:
        for rung in practice.ladder("ذ", "ذَٰلِكَ", 1, code=code,
                                    expected_count=count):
            assert set(rung) == keys, f"{code} {rung['focus']}: {set(rung)}"


def test_the_isolated_letter_audio_is_no_longer_wired_in():
    """§C: the recordings stay on disk for a future alphabet reference, and
    stop reaching this flow. The parameter is still accepted so that every
    existing caller keeps working - including ensure_shape() replaying rows
    written before any of this existed."""
    rungs = practice.ladder("ذ", "ذَٰلِكَ", 1, code="SUB_DHAL_ZAY",
                            letter_audio="/audio/dhal_zay.mp3")
    assert len(rungs) == 1
    for rung in rungs:
        assert rung["audio"] == ""
        assert rung["audio_source"] == ""


# ── classification is unchanged ───────────────────────────────────────────

def test_qalqala_drop_is_still_an_articulation_error_despite_the_name():
    """A dropped qalqalah is not a dropped LETTER. The letter was said; the
    bounce at the end of it was not. The category no longer picks a ladder
    shape, but it still picks the focus, so getting it wrong still costs the
    learner the right instruction."""
    assert practice.category("QALQALA_DROP") == "articulation"


def test_an_unclassified_code_defaults_to_articulation():
    assert practice.category("SOMETHING_NEW") == "articulation"
    assert practice.category("") == "articulation"


# ── through the pipeline, with more than one mistake ──────────────────────

def test_every_card_carries_a_recordable_word():
    """Including the ones with no coaching text. That is the property the
    derivation buys, and it is worth asserting end to end."""
    errs = [
        TypedError(code="SUB_DHAL_ZAY", at=2, letter="ذ", expected="ذ",
                   heard="ز", word="ذَٰلِكَ", word_index=1),
        # no registry entry at all
        TypedError(code="GHUNNA_LONG", at=9, letter="ن", expected_count=2,
                   heard_count=6, word="مِنْ", word_index=2),
    ]
    shown, _ = pipeline.present(errs, "uz")
    assert shown
    for card in shown:
        assert card["practice"], f'{card["code"]} has no retry action'
        assert len(card["practice"]) == 1
        assert card["practice"][0]["focus"] != "ayah"


def test_ten_mistakes_ask_for_ten_words_and_zero_ayat():
    """THE REPORTED DEFECT, asserted at the scale it was reported at.

    Ten distinct corrections in one recitation. Before: ten whole-ayah rungs,
    one per card, on top of the ten word rungs. After: ten words, no ayah - the
    single full recitation is the results screen's, once, at the end.
    """
    words = ["ذَٰلِكَ", "ٱلَّذِى", "قَالَ", "مِنْ", "ٱلصَّمَدُ",
             "يَلِدْ", "أَحَدٌ", "كُفُوًا", "ٱلْفَلَقِ", "وَقَبَ"]
    letters = "ذضقنصدحكفب"
    errs = [
        TypedError(code="GENERIC_LETTER_SUBSTITUTED", at=i * 3, letter=ch,
                   expected=ch, heard="س", word=w, word_index=i)
        for i, (ch, w) in enumerate(zip(letters, words))
    ]
    shown, _ = pipeline.present(errs, "uz")
    assert len(shown) == 10, f"expected 10 cards, got {len(shown)}"

    ayah_rungs = [r for card in shown for r in card["practice"]
                  if r["focus"] == "ayah"]
    assert ayah_rungs == [], (
        f"{len(ayah_rungs)} cards still demand the whole ayah")

    for card in shown:
        assert len(card["practice"]) == 1
        assert card["practice"][0]["items"] == [card["words"][0]]


def test_a_merged_card_records_the_word_once():
    """Four occurrences of one letter are ONE thing to learn and one recording
    to make. The action is built from the merged card, so it cannot multiply
    with the occurrences."""
    errs = [
        TypedError(code="SUB_DHAL_ZAY", at=at, letter="ذ", expected="ذ",
                   heard="ز", word=w, word_index=i)
        for at, w, i in [(2, "ذَٰلِكَ", 1), (7, "ٱلَّذِى", 3),
                         (11, "ذَٰلِكَ", 1), (14, "إِذَا", 5)]
    ]
    shown, _ = pipeline.present(errs, "uz")
    assert len(shown) == 1, "four occurrences produced more than one card"
    card = shown[0]
    assert card["count"] == 4
    assert [r["focus"] for r in card["practice"]] == ["word"]
    # ONE word - the first - not all four. Four words on one rung is the wall
    # of text the merge exists to prevent.
    assert card["practice"][0]["items"] == ["ذَٰلِكَ"]
