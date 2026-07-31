# -*- coding: utf-8 -*-
"""Exhaustive sweeps over all 6236 ayat. Minutes, not milliseconds.

Skipped by default so the fast suite stays fast. Run before shipping a change
to ranges.py, segmentation.py, or the moshaf config:

    pytest tests/test_full_quran.py --run-slow -q

test_ranges.py covers the same properties on a sample; these are the versions
that would actually catch a rule that holds for 6235 ayat and fails for one.
"""
import pytest
from quran_transcript import Aya, quran_phonetizer

from tilawah import content
from tilawah.engine.moshaf import MOSHAF
from tilawah.engine.ranges import (HARD_CAP_SECONDS, estimate_seconds,
                                   is_legal_range, n_words)

pytestmark = pytest.mark.slow


def all_ayat():
    for sura in range(1, 115):
        for aya in range(1, Aya(sura, 1).get().num_ayat_in_sura + 1):
            yield sura, aya


def test_every_ayah_phonetizes():
    """Phase 0 measured 6236/6236 with zero exceptions. If this ever goes red,
    a moshaf setting changed - not a rare ayah."""
    failures = []
    for sura, aya in all_ayat():
        try:
            out = quran_phonetizer(Aya(sura, aya).get().uthmani, MOSHAF,
                                   remove_spaces=True)
            assert out.phonemes
        except Exception as exc:
            failures.append(f"{sura}:{aya} {type(exc).__name__}: {exc}")
    assert not failures, f"{len(failures)} ayat failed: {failures[:10]}"


def test_every_stored_segment_is_legal_and_tiles_its_ayah():
    """Reads the committed artifact rather than recomputing - this is what the
    app actually serves, so this is what has to be correct."""
    meta = content.segments_meta()
    if not meta:
        pytest.skip("run tools/build_segments.py first")

    bad_cut, bad_tile, over_cap = [], [], []
    for sura, aya in all_ayat():
        segs = content.segments_of(sura, aya)
        if not segs:
            bad_tile.append(f"{sura}:{aya} has no segments")
            continue
        total = n_words(sura, aya)
        pos = 0
        for s in segs:
            if not is_legal_range(sura, aya, s["start_word"], s["num_words"]):
                bad_cut.append(f"{sura}:{aya} w[{s['start_word']}:"
                               f"{s['start_word'] + s['num_words']}]")
            if s["start_word"] != pos:
                bad_tile.append(f"{sura}:{aya} gap/overlap at {s['start_word']}")
            pos = s["start_word"] + s["num_words"]
            secs = estimate_seconds(s["n_phonemes"], gate=True)
            if secs > HARD_CAP_SECONDS:
                over_cap.append(f"{sura}:{aya} {secs:.1f}s")
        if pos != total:
            bad_tile.append(f"{sura}:{aya} covers {pos}/{total} words")

    assert not bad_cut, f"{len(bad_cut)} segments split an uthmani word: {bad_cut[:10]}"
    assert not bad_tile, f"{len(bad_tile)} tiling faults: {bad_tile[:10]}"
    assert not over_cap, f"{len(over_cap)} segments over the cap: {over_cap[:10]}"


def test_artifact_covers_every_ayah():
    meta = content.segments_meta()
    if not meta:
        pytest.skip("run tools/build_segments.py first")
    missing = [f"{s}:{a}" for s, a in all_ayat() if not content.segments_of(s, a)]
    assert not missing, f"{len(missing)} ayat missing: {missing[:10]}"
