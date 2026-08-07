# -*- coding: utf-8 -*-
"""The practice ladder. What it promises, and what it refuses to promise.

The ladder replaced two things that were not practice: a paragraph describing
an exercise, and a button that re-recorded the whole word. Its value is that
every rung is DERIVED - so it exists for codes nobody has authored a word of
coaching for - and that it never offers a control the engine cannot honour.

Both of those are properties worth pinning. The first because the temptation
under deadline is to hand-pick example words per letter, which reintroduces the
authoring dependency the design exists to avoid; the second because a record
button on a rung the engine cannot score is a control that lies, and it would
fail silently rather than loudly.
"""
import pytest

from tilawah.engine import practice
from tilawah.engine.typed_errors import TypedError
from tilawah.engine import pipeline


def focuses(letter="ذ", word="ذَٰلِكَ", word_index=1, code="", expected_count=0):
    return [r["focus"] for r in practice.ladder(
        letter, word, word_index, code=code, expected_count=expected_count)]


def test_the_full_ladder_goes_narrow_to_wide():
    """The whole point of the ARTICULATION shape: the learner meets the sound
    alone before meeting it inside anything."""
    assert focuses(code="SUB_DHAL_ZAY") == [
        "letter", "syllables", "word", "ayah"]


def test_syllables_are_the_letter_under_each_haraka():
    rungs = practice.ladder("ذ", "ذَٰلِكَ", 1)
    syll = next(r for r in rungs if r["focus"] == "syllables")
    assert syll["items"] == ["ذَ", "ذُ", "ذِ"]


def test_the_word_rung_is_the_learners_own_word():
    """Not an example from a registry. The word they actually misread is the
    word they are about to be re-tested on, and no authored example beats it."""
    rungs = practice.ladder("ص", "ٱلصَّمَدُ", 2)
    word = next(r for r in rungs if r["focus"] == "word")
    assert word["items"] == ["ٱلصَّمَدُ"]
    assert word["word_index"] == 2


# ── what the ladder refuses ───────────────────────────────────────────────

def test_letter_and_syllable_rungs_are_not_recordable():
    """THE PROMISE THAT MUST NOT BREAK. The engine scores audio against a
    target built from a word range of an ayah; it has no target for a bare
    letter. A record button there could never do what it says, and a control
    that lies is worse than no control - the same doctrine as audio_url()
    refusing to send a path for a file that is not on disk."""
    for rung in practice.ladder("ذ", "ذَٰلِكَ", 1):
        if rung["focus"] in ("letter", "syllables"):
            assert rung["recordable"] is False, rung["focus"]
        else:
            assert rung["recordable"] is True, rung["focus"]


def test_an_unplaceable_word_is_shown_but_not_recordable():
    """word_index -1 means the unit could not be placed in a word. The text can
    still be shown; the re-record cannot, because start_word would be a guess
    and a guess silently scores the learner against a different word."""
    rungs = practice.ladder("ص", "ٱلصَّمَدُ", -1)
    word = next(r for r in rungs if r["focus"] == "word")
    assert word["items"] == ["ٱلصَّمَدُ"]
    assert word["recordable"] is False


@pytest.mark.parametrize("letter", ["ا", "و", "ي"])
def test_madd_letters_skip_the_syllable_rung(letter):
    """ا و ي carry the lengthening BECAUSE they are unvowelled. Showing "اَ" as
    something to practise asks for a sound the letter does not make in that
    role.

    This is about the LETTER, not the error: a madd letter can carry an
    articulation error too - a و read as ف - and that card still opens on the
    bare letter. The duration ladder is a separate question, below.
    """
    assert focuses(letter=letter, code="SUB_WAW_V") == [
        "letter", "word", "ayah"]


@pytest.mark.parametrize("value", ["", "fatha", "mofakham", "sh"])
def test_a_non_letter_starts_the_ladder_at_the_word(value):
    """`letter` is not always a letter. A haraka error reports a NAME, a ṣifa
    error reports a ṣifa, and a duration error may report nothing. None of
    those can be set in an Arabic chip or said aloud on their own."""
    assert focuses(letter=value, code="GENERIC_SIFAT_MISMATCH") == [
        "word", "ayah"]


# ── the ladder branches on the error, not on the letter ───────────────────
#
# THE BUG THIS FIXES. Every card opened on "the letter, bare" regardless of what
# went wrong, and for three of the four categories that rung teaches nothing:
# the letter was not mispronounced (it was skipped), or it should not have been
# said at all, or the thing that was wrong was a duration a bare letter does not
# have. See the module docstring in engine/practice.py.

@pytest.mark.parametrize("code,opening", [
    ("LETTER_DROPPED", "word_include"),
    ("LETTER_ADDED", "word_omit"),
])
def test_structural_errors_open_on_the_word_not_the_letter(code, opening):
    assert focuses(code=code) == [opening, "word", "ayah"]


@pytest.mark.parametrize("code", ["LETTER_DROPPED", "LETTER_ADDED"])
def test_an_omission_or_insertion_never_drills_the_letter_alone(code):
    """THE REGRESSION GUARD. Stated as an absence over every input shape,
    because the defect was not one wrong branch - it was one ladder applied to
    everything, and it would come back the same way.

    The letter here is a perfectly good Arabic letter with a perfectly good
    isolated drill available. That is the point: the drill is available and
    still wrong, because the learner's mouth was never the problem.
    """
    for letter in ("ذ", "ح", "ا", "ن", ""):
        for word, wi in [("ذَٰلِكَ", 1), ("قَالَ", 0), ("", -1)]:
            rungs = practice.ladder(letter, word, wi, code=code)
            got = [r["focus"] for r in rungs]
            assert "letter" not in got, f"{code} {letter!r} {word!r}: {got}"
            assert "syllables" not in got, f"{code} {letter!r} {word!r}: {got}"


@pytest.mark.parametrize("code", [
    "MADD_TOO_SHORT", "MADD_TOO_LONG", "MADD_WAJIB_SHORTENED",
    "MADD_ADDED_LEEN", "MADD_ADDED",
    # The engine-side vocabulary reaches ladder() too - present() passes e.code,
    # which is what typed_diff emitted, not the resolved registry name.
    "MADD_SHORT", "MADD_LONG",
])
def test_madd_opens_on_the_word_with_a_count(code):
    """A bare letter has no duration. The first rung is the word, held for the
    count the reference calls for."""
    rungs = practice.ladder("ا", "قَالَ", 0, code=code, expected_count=4)
    assert [r["focus"] for r in rungs] == ["word_hold", "word", "ayah"]
    hold = rungs[0]
    assert hold["items"] == ["قَالَ"], "the hold rung must carry the WORD"
    assert hold["hold"] == 4


@pytest.mark.parametrize("code", [
    "MADD_TOO_SHORT", "MADD_TOO_LONG", "MADD_WAJIB_SHORTENED",
    "MADD_ADDED_LEEN", "MADD_SHORT", "MADD_LONG",
])
def test_a_madd_rung_is_never_a_bare_letter_without_the_word(code):
    """THE REGRESSION GUARD for the duration ladder. Two things must hold at
    once, and only asserting the first would miss the case that matters: no rung
    is the bare letter, AND the rung carrying the count is the word."""
    for letter in ("ا", "و", "ي", "ن", ""):
        rungs = practice.ladder(letter, "قَالَ", 0, code=code,
                                expected_count=6)
        for r in rungs:
            assert r["focus"] not in ("letter", "syllables"), r["focus"]
            if r["hold"]:
                assert r["items"] == ["قَالَ"], (
                    f"{code} {letter!r}: a count on a rung with no word")


def test_a_madd_error_with_no_reference_count_omits_the_hold_rung():
    """The count comes from the reference and nowhere else. Where the reference
    did not supply one there is no number to count to, so the rung is dropped
    rather than shown counting to zero - the same doctrine as a play button for
    a file that is not on disk."""
    assert focuses(letter="ا", word="قَالَ", word_index=0,
                   code="MADD_TOO_SHORT", expected_count=0) == ["word", "ayah"]


def test_qalqala_drop_is_an_articulation_error_despite_the_name():
    """A dropped qalqalah is not a dropped LETTER. The letter was said; the
    bounce at the end of it was not, and the bounce is an articulation. A
    prefix rule on "dropped" would have put this on the omission ladder and
    taken away the drill that actually helps."""
    assert practice.category("QALQALA_DROP") == "articulation"
    assert focuses(letter="د", word="يَلِدْ", word_index=0,
                   code="QALQALA_DROP")[0] == "letter"


def test_an_unclassified_code_keeps_the_ladder_it_always_had():
    """Articulation is the default on purpose: a code nobody has classified
    keeps exactly the shape it has always had rather than silently losing
    rungs."""
    assert practice.category("SOMETHING_NEW") == "articulation"
    assert practice.category("") == "articulation"
    assert focuses(code="SOMETHING_NEW") == [
        "letter", "syllables", "word", "ayah"]


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


def test_the_slow_word_rungs_record_the_same_range_as_the_normal_one():
    """They are the same word. A slow first pass that could not be recorded
    would make rung 1 unscorable on three of the four ladders."""
    for code, count in [("LETTER_DROPPED", 0), ("LETTER_ADDED", 0),
                        ("MADD_TOO_SHORT", 4)]:
        rungs = practice.ladder("ا", "قَالَ", 3, code=code,
                                expected_count=count)
        word_rungs = [r for r in rungs if r["focus"] in practice.WORD_FOCUSES]
        assert len(word_rungs) == 2
        for r in word_rungs:
            assert r["recordable"] is True
            assert r["check"] == practice.SCORED
            assert r["word_index"] == 3


def test_levels_are_gapless_after_a_rung_is_skipped():
    """A ladder numbered 1, 3, 4 reads as though a rung failed to load. `focus`
    identifies a rung; `level` is only its position."""
    for letter in ("ذ", "ا", ""):
        rungs = practice.ladder(letter, "قَالَ", 0)
        assert [r["level"] for r in rungs] == list(range(1, len(rungs) + 1))


def test_the_ayah_rung_is_always_last_and_always_there():
    """It is the way back to the test, and the point of the whole ladder."""
    for letter, word, wi in [("ذ", "ذَٰلِكَ", 1), ("", "", -1), ("ا", "قَالَ", 0)]:
        rungs = practice.ladder(letter, word, wi)
        assert rungs[-1]["focus"] == "ayah"
        assert rungs[-1]["recordable"] is True


def test_the_worst_case_is_still_a_usable_ladder():
    """Nothing known but the error itself: no letter, no word. The learner is
    still handed the ayah rather than an empty section."""
    assert focuses(letter="", word="", word_index=-1) == ["ayah"]


# ── through the pipeline ──────────────────────────────────────────────────

def test_every_card_carries_a_ladder():
    """Including the ones with no coaching text. That is the property the
    derivation buys, and it is worth asserting end to end rather than only on
    the generator."""
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
        assert card["practice"], f'{card["code"]} has no practice ladder'
        assert card["practice"][-1]["focus"] == "ayah"


def test_a_merged_card_drills_the_letter_once():
    """Four occurrences of one letter are ONE thing to learn and one ladder to
    climb. The ladder is built from the merged card, so it cannot multiply with
    the occurrences."""
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
    assert [r["focus"] for r in card["practice"]] == [
        "letter", "syllables", "word", "ayah"]
    # The word rung names ONE word - the first - not all four. Four words on
    # one rung is the wall of text the merge exists to prevent.
    word = next(r for r in card["practice"] if r["focus"] == "word")
    assert word["items"] == ["ذَٰلِكَ"]
