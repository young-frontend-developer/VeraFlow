# -*- coding: utf-8 -*-
"""The catalogue the Practice picker runs on: 114 suras, 6236 ayat.

No model, no HTTP. These guard the two things that would break the picker
silently rather than loudly - a wrong ayah count truncating a sura, and a
sub-range highlight landing on the wrong letter.
"""
import pytest

from tilawah import content
from tilawah.engine.ranges import is_legal_range
from tilawah.engine.segments import segments_for, segments_for_range


def test_catalogue_is_complete():
    suras = content.suras()
    assert len(suras) == 114
    assert sum(s["n_ayat"] for s in suras) == 6236, "canonical ayah total"
    assert [s["number"] for s in suras] == list(range(1, 115))


def test_every_sura_has_both_transliterations_and_an_arabic_name():
    for s in content.suras():
        assert s["name_ar"] and s["translit"] and s["uz"], s["number"]


@pytest.mark.parametrize("query,expect", [
    ("fatiha", 1),      # bare stem, no article
    ("al-fatiha", 1),   # with the hyphen a learner may or may not type
    ("fotiha", 1),      # Uzbek spelling
    ("ixlos", 112),     # Uzbek only - the Latin form is "Al-Ikhlas"
    ("112", 112),       # by number
    ("ali imran", 3),   # apostrophe dropped, as people type it
    ("الناس", 114),     # Arabic
])
def test_search_finds_the_sura(query, expect):
    """The search field filters on the prefolded `search` key with a plain
    substring test, so this is exactly what the client does."""
    folded = query.lower().replace("'", "").replace("-", "").strip()
    hits = [s["number"] for s in content.suras() if folded in s["search"]]
    assert expect in hits, f"{query!r} found {hits}"


def test_ayah_counts_match_the_library():
    """The counts come from quran_transcript in build_suras.py, never from the
    hand-maintained table - a typo there would silently truncate a sura's ayah
    picker, which is very hard to notice by eye."""
    from quran_transcript import Aya

    cursor = Aya(1, 1)
    for s in content.suras():
        cursor.set(s["number"], 1)
        assert cursor.get().num_ayat_in_sura == s["n_ayat"], s["number"]


# ───────────────────────────────────────────────── ranges the picker offers

@pytest.mark.slow
def test_every_precomputed_segment_is_a_legal_range():
    """Otherwise the learner picks a segment, records a take, and only then gets
    'illegal_word_range' back. Measured: 16366/16366 legal."""
    n = 0
    for sura in range(1, 115):
        aya = 1
        while True:
            segs = content.segments_of(sura, aya)
            if not segs:
                break
            for s in segs:
                assert is_legal_range(sura, aya, s["start_word"],
                                      s["num_words"]), f"{sura}:{aya} {s}"
                n += 1
            aya += 1
    assert n == 16366


@pytest.mark.parametrize("sura,aya", [(2, 255), (1, 7), (36, 1), (78, 1)])
def test_range_segments_tile_their_own_text(sura, aya):
    """The UI renders one text node and measures over these offsets. If they do
    not tile the range exactly, a highlight lands on the wrong letter."""
    for s in content.segments_of(sura, aya):
        segs = segments_for_range(sura, aya, s["start_word"], s["num_words"])
        from tilawah.engine.ranges import Range, uthmani_of
        text = uthmani_of(Range(sura, aya, s["start_word"], s["num_words"]))
        assert "".join(x["text"] for x in segs) == text
        assert segs[0]["start"] == 0 and segs[-1]["end"] == len(text)
        for a, b in zip(segs, segs[1:]):
            assert a["end"] == b["start"]


def test_whole_ayah_range_matches_the_whole_ayah_segments():
    """A range covering the entire ayah must agree with the whole-ayah path -
    two implementations of the same thing is exactly how highlights drift."""
    from tilawah.engine.ranges import n_words

    for sura, aya in [(103, 1), (112, 1), (1, 7)]:
        total = n_words(sura, aya)
        assert segments_for_range(sura, aya, 0, total) == segments_for(sura, aya)


def test_sub_range_units_are_relative_to_the_range():
    """2:255 is eight segments. Every one of them must start its unit numbering
    at 0, because that is what the engine diffs against - reusing the ayah's
    numbering would offset every highlight in every segment but the first."""
    for s in content.segments_of(2, 255):
        segs = segments_for_range(2, 255, s["start_word"], s["num_words"])
        units = [u for x in segs for u in x["units"]]
        assert min(units) == 0, f"segment at w{s['start_word']} does not start at 0"
