# -*- coding: utf-8 -*-
"""No QPS notation symbol may ever be named as a letter.

QPS borrows five characters from outside the Arabic alphabet to notate what the
alphabet has no character for: ڇ for qalqalah, ۥ and ۦ for the two madd
lengthenings, ں for the ikhfa noon, ۾ for the iqlab meem. They are transcription
marks. A learner shown one is being asked to recognise, write and pronounce a
symbol that does not exist in the text in front of them.

THE MERGE BUG IS THE HALF NOBODY COULD SEE. Cards group on (code, letter), so
while every qalqalah error carried the same ڇ, every qalqalah mistake in an ayah
collapsed into ONE card regardless of which of ق ط ب ج د it happened on. Two
real mistakes, one card, and nothing in the output to suggest anything was lost.

The regression sample that existed when this was found - 112:3, «لَمْ يَلِدْ وَلَمْ
يُولَدْ» - could not have caught it: both its qalqalahs are on د, so the collapse
was correct by accident. Hence test_two_qalqalahs_on_different_letters below,
which uses ayat chosen precisely because their qalqalah letters differ.
"""
import pytest

from tilawah.engine import cards, pipeline
from tilawah.engine.ranges import Range, n_words, reference
from tilawah.engine.runlength import MARKS, QALQALA_MARK, tokenize
from tilawah.engine.segments import segments_for_range, unit_letters
from tilawah.engine.typed_errors import TypedError, typed_diff


def read(sura: int, aya: int):
    """The reference text and phonemes for a whole ayah."""
    nw = n_words(sura, aya)
    uthmani, ph = reference(Range(sura, aya, 0, nw, False))
    return uthmani, ph, nw


def drop_qalqalahs(phonemes: str) -> str:
    """What the phoneme string looks like when the learner drops every
    qalqalah - the mistake this test is about, made deliberately."""
    return phonemes.replace(QALQALA_MARK, "")


def analyse(sura: int, aya: int, heard: str):
    """The real pipeline path, minus the model: diff, locate, resolve, merge."""
    uthmani, ph, nw = read(sura, aya)
    detected = typed_diff(ph.phonemes, heard)
    pipeline.locate(detected, uthmani, sura, aya, 0, nw)
    return detected, cards.merge(detected)


# ── the case the old sample could not catch ───────────────────────────────

@pytest.mark.parametrize("sura,aya,expected_letters", [
    # ٱلنَّجْمُ ٱلثَّاقِبُ — qalqalah on ج and on ب
    (86, 3, {"ج", "ب"}),
    # وَمَآ أَدْرَىٰكَ مَا ٱلطَّارِقُ — on د and on ق
    (86, 2, {"د", "ق"}),
    # كَلَّا لَا تُطِعْهُ وَٱسْجُدْ وَٱقْتَرِب — three distinct: ب, د and ق
    (96, 19, {"ب", "د", "ق"}),
])
def test_two_qalqalahs_on_different_letters(sura, aya, expected_letters):
    """THE REGRESSION. Distinct letters must produce distinct cards.

    Before the fix every one of these carried letter='ڇ' and merged into a
    single card, so an ayah with three dropped qalqalahs reported one mistake.
    """
    _, ph, _ = read(sura, aya)
    detected, merged = analyse(sura, aya, drop_qalqalahs(ph.phonemes))

    qalqala = [e for e in detected if e.code == "QALQALA_DROP"]
    assert len(qalqala) == len(expected_letters), (
        f"{sura}:{aya} should detect {len(expected_letters)} dropped qalqalahs")
    assert {e.letter for e in qalqala} == expected_letters

    q_cards = [g for g in merged if g[0].code == "QALQALA_DROP"]
    assert len(q_cards) == len(expected_letters), (
        f"{sura}:{aya}: {len(expected_letters)} qalqalah mistakes on different "
        f"letters merged into {len(q_cards)} card(s)")
    assert {g[0].letter for g in q_cards} == expected_letters


def test_repeats_of_the_same_letter_still_merge():
    """The other half of the contract. Resolving the letter must not turn the
    merge off: 112:3 has two qalqalahs and BOTH are on د, so they are one thing
    to learn and must stay one card."""
    _, ph, _ = read(112, 3)
    detected, merged = analyse(112, 3, drop_qalqalahs(ph.phonemes))

    qalqala = [e for e in detected if e.code == "QALQALA_DROP"]
    assert len(qalqala) == 2
    assert {e.letter for e in qalqala} == {"د"}

    q_cards = [g for g in merged if g[0].code == "QALQALA_DROP"]
    assert len(q_cards) == 1, "two mistakes on the SAME letter should be one card"
    assert len(q_cards[0]) == 2, "both occurrences must survive on that card"


# ── the enumeration the brief asked for ───────────────────────────────────

AYAT = [(112, 3), (113, 1), (114, 1), (110, 1), (103, 1), (86, 2), (86, 3),
        (90, 1), (96, 19), (85, 12), (111, 5), (1, 7), (36, 1), (2, 255)]


@pytest.mark.parametrize("mark", sorted(MARKS))
def test_every_internal_symbol_is_named_and_resolvable(mark):
    """Each of the five is a known mark, not a letter, and MARKS is complete
    enough that nothing else is being treated as one."""
    assert len(mark) == 1
    assert mark in MARKS


def test_no_internal_symbol_survives_into_a_located_error():
    """THE ENUMERATION. Every ayah, every single-unit mistake, every field a
    card can print as a letter. Not one may come back a mark.

    Perturbs each ayah at every position three ways - drop the unit, double it,
    substitute a plain letter - which is what generates markers in `letter`,
    `expected` and `heard` respectively.
    """
    offenders = []
    for sura, aya in AYAT:
        uthmani, ph, nw = read(sura, aya)
        exp = ph.phonemes
        for i in range(len(exp)):
            for heard in (exp[:i] + exp[i + 1:],
                          exp[:i] + exp[i] + exp[i:],
                          exp[:i] + "س" + exp[i + 1:]):
                try:
                    detected = typed_diff(exp, heard)
                except Exception:
                    continue
                pipeline.locate(detected, uthmani, sura, aya, 0, nw)
                for e in detected:
                    for field in ("letter", "expected", "heard"):
                        if getattr(e, field) in MARKS:
                            offenders.append(
                                f"{sura}:{aya} {e.code}.{field}="
                                f"{getattr(e, field)!r}")
    assert not offenders, (
        f"{len(offenders)} errors still name a QPS mark as a letter; "
        f"first few: {sorted(set(offenders))[:10]}")


def test_every_marker_unit_resolves_to_a_real_letter():
    """The resolution itself, measured rather than assumed. Every unit whose
    QPS base is a mark must map to a real Arabic letter - including in 2:255,
    where the mushaf writes ۥ and ۦ as superscripts in its own right."""
    unresolved = []
    for sura, aya in AYAT:
        uthmani, ph, nw = read(sura, aya)
        segs = segments_for_range(sura, aya, 0, nw)
        letters = unit_letters(uthmani, segs)
        for i, (base, _count, _marks) in enumerate(tokenize(ph.phonemes)):
            if base not in MARKS:
                continue
            got = letters.get(i, "")
            if not got or got in MARKS:
                unresolved.append(f"{sura}:{aya} unit {i} {base!r} -> {got!r}")
    assert not unresolved, f"unresolved marker units: {unresolved}"


# ── two detectors, one event ──────────────────────────────────────────────

def test_the_two_qalqalah_detectors_produce_one_card():
    """A dropped qalqalah is found TWICE, by two different detectors.

    The phoneme diff reports QALQALA_DROP on the ڇ unit; the ṣifa comparison
    reports QALQALAH_MISSING on the letter itself. Both alias to one registry
    entry, so both render the same headline, the same instruction and the same
    ladder - and keyed on the raw code, the learner saw that card twice.

    Caught by driving a real 112:3 recitation through the API. Neither detector
    is wrong on its own, which is why no unit test found it.
    """
    shared = dict(letter="د", word="يَلِدْ", word_index=0)
    errs = [
        TypedError(code="QALQALAH_MISSING", at=4, sifa="qalqla", **shared),
        TypedError(code="QALQALA_DROP", at=5, **shared),
        TypedError(code="QALQALA_DROP", at=13, **shared),
    ]
    merged = cards.merge(errs)
    assert len(merged) == 1, (
        f"one dropped qalqalah on د produced {len(merged)} cards: "
        f"{[(g[0].code, g[0].letter) for g in merged]}")
    assert len(merged[0]) == 3, "every occurrence must survive the merge"


def test_aliasing_does_not_merge_across_letters():
    """The guard on the above. SUB_DHAL_ZAY (ذ->ز) and SUB_DHA_ZAY (ظ->ز) share
    ONE registry entry, so merging on the resolved code alone would collapse
    two different letters into one card. The letter stays in the key."""
    errs = [
        TypedError(code="SUB_DHAL_ZAY", at=2, letter="ذ", expected="ذ",
                   heard="ز", word="ذَٰلِكَ", word_index=0),
        TypedError(code="SUB_DHA_ZAY", at=7, letter="ظ", expected="ظ",
                   heard="ز", word="ظَلَمَ", word_index=1),
    ]
    merged = cards.merge(errs)
    assert len(merged) == 2
    assert {g[0].letter for g in merged} == {"ذ", "ظ"}


# ── the insertion case ────────────────────────────────────────────────────

def test_an_added_qalqalah_is_not_reported_as_an_added_letter():
    """An inserted ڇ used to come back as LETTER_ADDED carrying ڇ in both
    `letter` and `heard`, producing "you added an extra ڇ".

    It cannot be fixed by resolution the way the reference side is: `heard`
    describes the prediction, so there is no mushaf character to look up, and a
    qalqalah is an echo ON a letter rather than a letter. It is filed as
    QALQALAH_EXCESSIVE instead - a code the registry already has words for.

    THE NAME IS THE REGISTRY'S. This first shipped emitting QALQALA_EXCESSIVE,
    which is not an entry in any registry generation, so it resolved to nothing
    and rendered the unauthored stand-in over content that already existed. The
    spelling is asserted here because that is the only thing that was wrong.
    """
    uthmani, ph, nw = read(113, 1)
    exp = ph.phonemes
    # Add a qalqalah echo where the text has none: after the ل of «قُل».
    heard = exp[:3] + QALQALA_MARK + exp[3:]
    detected = typed_diff(exp, heard)
    pipeline.locate(detected, uthmani, 113, 1, 0, nw)

    assert detected, "no error detected for an inserted qalqalah"
    assert not any(e.code == "LETTER_ADDED" and e.letter in MARKS
                   for e in detected)
    assert any(e.code == "QALQALAH_EXCESSIVE" for e in detected)
    from tilawah.content import coaching
    assert coaching.has("QALQALAH_EXCESSIVE"), (
        "the code the engine emits must be the one the registry is keyed by")
    for e in detected:
        assert e.heard not in MARKS


def test_a_qps_mark_is_never_reported_as_a_letter_substitution():
    """THE INVENTED CARD. The aligner pairs a ڇ against whatever the model put
    in its slot, and the replace branch used to call that a letter confusion.
    _resolve_marks then made it WORSE by turning the ڇ in `expected` into the
    real letter, producing a fluent and completely fabricated correction:

        2:7 «أَبْصَـٰرِهِمْ», the qalqalah on بْ
        -> GENERIC_LETTER_SUBSTITUTED  expected «ب»  heard «ء»
        -> "you read «ب» as «ء»" — about a letter the learner did say

    The true finding is that the qalqalah was not produced. Found by replaying
    a real recitation; no unit test could have caught it, because every layer
    was behaving as written.
    """
    uthmani, ph, nw = read(2, 7)
    exp = ph.phonemes
    # Put a hamza where the qalqalah mark is - what the model actually heard.
    at = exp.index(QALQALA_MARK)
    heard = exp[:at] + "ء" + exp[at + 1:]
    detected = typed_diff(exp, heard)
    pipeline.locate(detected, uthmani, 2, 7, 0, nw)

    subs = [e for e in detected if "SUBSTITUT" in e.code]
    assert not subs, (
        "a QPS mark was reported as a letter substitution: "
        f"{[(e.code, e.letter, e.expected, e.heard) for e in subs]}")
    assert any(e.code == "QALQALA_DROP" for e in detected), (
        "the qalqalah that was not produced must still be reported")


def test_a_voweled_qalqalah_letter_is_one_card_not_two():
    """THE JUDGMENT CALL, decided from the 2:7 capture.

    Reading a sakin qalqalah letter WITH a vowel produces two findings on the
    same letter one unit apart: the vowel that should not be there, and the
    bounce that therefore cannot happen. They are not two mistakes - qalqalah IS
    the release of a letter stopped dead, so giving it a vowel removes the thing
    that would bounce. The missing bounce is a measurement of the same event.

    The vowel error survives, because it is the one whose instruction works;
    the qalqalah occurrence rides along so the ayah still marks that letter.
    """
    shared = dict(letter="ب", word="أَبْصَـٰرِهِمْ", word_index=7)
    errs = [
        TypedError(code="SUKUN_TO_HARAKA", at=29, expected="sukun",
                   heard="fatha", **shared),
        TypedError(code="QALQALA_DROP", at=30, **shared),
    ]
    merged = cards.merge(errs)
    assert len(merged) == 1, (
        f"one voweled qalqalah letter produced {len(merged)} cards: "
        f"{[(g[0].code, g[0].letter) for g in merged]}")
    assert merged[0][0].code == "SUKUN_TO_HARAKA", "the cause must be the card"
    assert len(merged[0]) == 2, "the bounce occurrence must still mark the ayah"


def test_folding_does_not_swallow_an_unrelated_mistake():
    """The guard on the above. The fold is one named pair with a stated
    mechanism, not "errors on the same letter collapse" - which would have
    hidden the ص substitution two units later in the same word."""
    merged = cards.merge([
        TypedError(code="SUKUN_TO_HARAKA", at=29, letter="ب", expected="sukun",
                   heard="fatha", word="أَبْصَـٰرِهِمْ", word_index=7),
        TypedError(code="SUB_SAD_SEEN", at=31, letter="ص", expected="ص",
                   heard="س", word="أَبْصَـٰرِهِمْ", word_index=7),
        # Same letter, but nowhere near the vowel error: a separate mistake.
        TypedError(code="QALQALA_DROP", at=48, letter="ب",
                   word="ٱقْتَرِب", word_index=12),
    ])
    assert len(merged) == 3, (
        f"{[(g[0].code, g[0].letter) for g in merged]}")
