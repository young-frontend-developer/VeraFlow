# -*- coding: utf-8 -*-
"""The coaching registries, the harakat detector, and the fallback principle.

The property that ties these together: once the engine has located an error,
the learner is told WHERE it was — always. Before this, an error whose code had
no registry entry fell through to "Toʻliq baholay olmadik", which is the
sentence reserved for the model returning nothing at all. A gap in the registry
was being reported as a failure of the model.
"""
import pytest

from tilawah import content
from tilawah.content import coaching
from tilawah.content.coaching import UnfilledTemplate
from tilawah.engine.ranges import Range, n_words, reference
from tilawah.engine.segments import segments_for_range, unit_words
from tilawah.engine.target import _phonetized
from tilawah.engine.typed_errors import HARAKAT, typed_diff

SHIP_FIRST = ("GENERIC_LETTER_SUBSTITUTED", "GENERIC_SIFAT_MISMATCH",
              "HARAKA_SUBSTITUTED")
NEW_FROM_DIFF = ("HARAKA_TO_SUKUN", "SUKUN_TO_HARAKA", "LETTER_DROPPED",
                 "LETTER_ADDED")

FIELDS = {"expected_count": 4, "heard_count": 2, "letter": "ع",
          "expected": "ع", "heard": "ء", "code": "X", "at": 0,
          "word": "عَلَيْهِمْ"}


# ── the registries ───────────────────────────────────────────────────────

def test_v5_is_loaded():
    assert len(coaching.registry()) >= 22


def test_v4_is_still_missing():
    """DOCUMENTS A GAP, and fails the day it closes so the note gets removed.

    tajweed_registry_v4_coaching.json was specified but is not in the repo.
    Until it lands, every pre-existing code keeps its old rules.json wording
    and renders through the legacy mapping in content.render.
    """
    missing = coaching.missing_sources()
    assert missing == ["tajweed_registry_v4_coaching.json"], (
        f"expected only v4 to be missing, got {missing} — if v4 has landed, "
        f"delete this test and check the merged text renders")


@pytest.mark.parametrize("code", SHIP_FIRST + NEW_FROM_DIFF)
def test_the_wired_codes_are_all_authored(code):
    assert coaching.has(code), f"{code} is wired in the engine but has no entry"


@pytest.mark.parametrize("code", SHIP_FIRST + NEW_FROM_DIFF)
def test_the_wired_codes_render_in_both_languages(code):
    for lang in ("uz", "ru"):
        body = content.render(code, lang, FIELDS)
        assert body and body["headline"], f"{code}.{lang} has no headline"
        assert body["fix"], f"{code}.{lang} has no fix"


def test_everything_stays_draft():
    """All entries are status='draft'; the review gate is unchanged."""
    for code in coaching.registry():
        body = content.render(code, "uz", FIELDS)
        assert body["reviewed"] is False, f"{code} claims to be reviewed"


# ── templates never leak a brace ─────────────────────────────────────────

def test_a_missing_field_raises_rather_than_printing_a_brace():
    """The old behaviour was to catch the KeyError and return the raw template,
    so a learner saw «{word}» — «{expected}». That is the failure this refuses.
    """
    with pytest.raises(UnfilledTemplate):
        content.render("HARAKA_SUBSTITUTED", "uz",
                       {"code": "X", "at": 0, "letter": "ب"})


def test_a_stray_brace_in_the_source_is_caught_too():
    """format_map only raises for placeholders it recognises. A malformed one
    survives substitution, so the output is checked as well as the input."""
    with pytest.raises(UnfilledTemplate):
        coaching._fill("«{word}» and {not closed", {"word": "x"},
                       code="T", key="headline")


def test_both_naming_generations_substitute():
    """v4/v5 write {actual} and {n_expected}; rules.json wrote {heard} and
    {expected_count}. Both have to fill from one detection result."""
    ctx = content.substitution_context(
        {"heard": "ء", "expected_count": 4, "heard_count": 2})
    assert ctx["actual"] == "ء"
    assert ctx["n_expected"] == 4 and ctx["n_actual"] == 2


# ── harakat: the category that had no detector ───────────────────────────

def phonemes(sura: int, aya: int) -> str:
    return _phonetized(sura, aya).phonemes


def only(codes, want):
    return [c for c in codes if c == want]


def test_the_reference_carries_exactly_three_vowels():
    """The detector's premise. If QPS ever emits sukun or tanween in the mark
    slot, the sukun pair below silently changes meaning."""
    seen = set()
    for s, a in ((1, 1), (1, 7), (2, 255), (114, 1)):
        for ch in phonemes(s, a):
            if ch in "ًٌٍَُِّْ":
                seen.add(ch)
    assert seen == HARAKAT


def test_fatha_for_kasra_is_detected():
    """The exact failure reported from a real take: بَ where بِ was expected."""
    ref = phonemes(1, 7)
    errs = typed_diff(ref, ref.replace("هِم", "هَم", 1))
    codes = [e.code for e in errs]
    assert only(codes, "HARAKA_SUBSTITUTED"), codes
    e = next(e for e in errs if e.code == "HARAKA_SUBSTITUTED")
    assert e.expected == "kasra" and e.heard == "fatha"


def test_haraka_names_not_raw_marks_reach_the_headline():
    """"«ب» ni kasra bilan" reads; "«ب» ni ِ bilan" does not."""
    ref = phonemes(1, 7)
    e = next(x for x in typed_diff(ref, ref.replace("هِم", "هَم", 1))
             if x.code == "HARAKA_SUBSTITUTED")
    e.word = "عَلَيْهِمْ"
    headline = content.render(e.code, "uz", e.dict())["headline"]
    assert "kasra" in headline and "fatha" in headline
    assert "ِ" not in headline.replace("عَلَيْهِمْ", "")


def test_haraka_to_sukun_is_detected():
    ref = phonemes(1, 7)
    codes = [e.code for e in typed_diff(ref, ref.replace("صِ", "ص", 1))]
    assert only(codes, "HARAKA_TO_SUKUN"), codes


def test_sukun_to_haraka_is_detected():
    ref = phonemes(1, 7)
    codes = [e.code for e in typed_diff(ref, ref.replace("نعَ", "نَعَ", 1))]
    assert only(codes, "SUKUN_TO_HARAKA"), codes


def test_a_correct_reading_reports_no_haraka_error():
    """The other half: comparing the reference with itself must be silent, or
    the detector fires on every correct recitation."""
    for s, a in ((1, 1), (1, 7), (2, 255), (112, 1), (114, 1)):
        assert typed_diff(phonemes(s, a), phonemes(s, a)) == []


def test_length_and_vowel_are_separate_errors():
    """A letter can be held for the right count and still carry the wrong
    vowel; conflating them would hide one behind the other."""
    ref = phonemes(1, 7)
    errs = typed_diff(ref, ref.replace("ذِۦۦ", "ذَۦ", 1))
    codes = {e.code for e in errs}
    assert "HARAKA_SUBSTITUTED" in codes
    assert any(c.startswith("MADD") for c in codes), codes


# ── the fallback principle ───────────────────────────────────────────────

def test_an_unlisted_substitution_falls_back_to_the_generic():
    ref = phonemes(1, 7)
    errs = typed_diff(ref, ref.replace("ص", "ك", 1))
    assert errs[0].code == "GENERIC_LETTER_SUBSTITUTED"
    assert errs[0].expected == "ص" and errs[0].heard == "ك"


def test_a_listed_pair_still_wins_over_the_generic():
    """ص -> س is an L1 interference pair with its own reviewed content. The
    generic is a floor, not a replacement for what is already specific."""
    ref = phonemes(1, 7)
    errs = typed_diff(ref, ref.replace("ص", "س", 1))
    assert errs[0].code == "SUB_SAD_SEEN"


def test_registry_pairs_are_read_from_the_signal_not_the_name():
    """MAKHARIJ_INTERDENTAL_TO_ZAY has a category, not a letter, in its name.
    Parsing names would produce nonsense pairs; the detection_signal states
    the substitution explicitly."""
    pairs = coaching.substitution_pairs()
    assert pairs.get(("ع", "غ")) == "MAKHARIJ_AIN_TO_GHAYN"
    assert all(len(a) == 1 and len(b) == 1 for a, b in pairs)


def test_dropped_and_added_letters_use_the_new_codes():
    ref = phonemes(1, 7)
    assert typed_diff(ref, ref.replace("صِ", "", 1))[0].code == "LETTER_DROPPED"
    assert any(e.code == "LETTER_ADDED"
               for e in typed_diff(ref, ref.replace("صِ", "صِب", 1)))


def test_every_code_the_differ_can_emit_is_authored():
    """The point of the generics. Any code reaching a learner with no entry in
    either registry renders as a bare location — acceptable as a floor, but it
    should not happen for anything the differ routinely produces."""
    ref = phonemes(1, 7)
    produced = set()
    for bad in (ref.replace("هِم", "هَم", 1), ref.replace("صِ", "ص", 1),
                ref.replace("نعَ", "نَعَ", 1), ref.replace("ص", "ك", 1),
                ref.replace("صِ", "", 1), ref.replace("صِ", "صِب", 1)):
        produced.update(e.code for e in typed_diff(ref, bad))
    unauthored = [c for c in produced
                  if not coaching.has(c) and c not in content.rules()]
    assert not unauthored, unauthored


# ── the word, always ─────────────────────────────────────────────────────

def test_every_unit_maps_to_a_word():
    """A headline opens with the word. If the map has holes, render() raises on
    the empty {word} rather than showing a brace — correct, but the learner
    loses the card, so the map must be total."""
    for sura, aya in ((1, 7), (2, 255), (112, 1), (114, 1)):
        total = n_words(sura, aya)
        uthmani, out = reference(Range(sura, aya, 0, total))
        segs = segments_for_range(sura, aya, 0, total)
        words = unit_words(uthmani, segs)
        n_units = len({u for s in segs for u in s["units"]})
        assert len(words) == n_units, f"{sura}:{aya} mapped {len(words)}/{n_units}"
        assert all(w.strip() for w in words.values())


def test_the_word_is_the_one_containing_the_error():
    ref = phonemes(1, 7)
    total = n_words(1, 7)
    uthmani, _ = reference(Range(1, 7, 0, total))
    words = unit_words(uthmani, segments_for_range(1, 7, 0, total))
    e = typed_diff(ref, ref.replace("ص", "ك", 1))[0]
    assert words[e.at] == uthmani.split()[0]
