# -*- coding: utf-8 -*-
"""Word ranges, duration estimation, and segmentation.

Fast by design: these sample the Quran rather than sweep it. The exhaustive
versions live in test_full_quran.py behind the `slow` marker - they take
minutes, and a suite you skip is a suite that stops catching things.
"""
import ast
import json
from pathlib import Path

import pytest
from quran_transcript import Aya
from quran_transcript.utils import PartOfUthmaniWord

from tilawah import content
from tilawah.engine.ranges import (HARD_CAP_SECONDS, RATE_DISPLAY, RATE_GATE,
                                   Range, estimate_seconds, is_legal_cut,
                                   is_legal_range, legal_cuts, n_words,
                                   reference)
from tilawah.engine.segmentation import segment_ayah

API_ROOT = Path(__file__).resolve().parent.parent

# Deliberately mixed: muqatta'at, sajda, first-ayat, the longest ayah, and the
# ayat Phase 0 found with merged uthmani words (5:1, 2:282).
SAMPLE = [(1, 1), (2, 1), (2, 255), (2, 282), (5, 1), (7, 206), (19, 1),
          (36, 1), (55, 1), (103, 1), (108, 1), (112, 1), (114, 1)]


# ───────────────────────────────────────────────────────────── cut points
@pytest.mark.parametrize("sura,aya", SAMPLE)
def test_predicted_cuts_match_the_library(sura, aya):
    """The whole point of legal_cuts: predict PartOfUthmaniWord instead of
    catching it. Probing costs ~60 ms/call, so the UI cannot trial-and-error.

    REGRESSION: a predictor that checks only the `end` boundary - which is all
    the library's source shows - scores 98.79%. Every miss is a range STARTING
    mid-uthmani-word. Both boundaries must be checked.
    """
    n = n_words(sura, aya)
    combos = [(s, w) for s in range(n) for w in range(1, n - s + 1)][:120]
    for start, window in combos:
        predicted = is_legal_range(sura, aya, start, window)
        try:
            Aya(sura, aya).get_by_imlaey_words(start, window)
            actual = True
        except PartOfUthmaniWord:
            actual = False
        assert predicted == actual, (
            f"{sura}:{aya} words[{start}:{start + window}] "
            f"predicted={predicted} actual={actual}")


def test_start_boundary_is_checked_not_just_end():
    """5:1 spells one uthmani word as two imlaey words, so a cut at 1 is
    illegal. Pinned explicitly because checking only `end` passes everything
    else and quietly breaks exactly this."""
    assert not is_legal_cut(5, 1, 1)
    assert not is_legal_range(5, 1, 1, 3)     # starts mid-word
    assert not is_legal_range(5, 1, 0, 1)     # ends mid-word
    assert is_legal_range(5, 1, 0, 2)         # spans the whole word


def test_ayah_ends_are_always_legal():
    for sura, aya in SAMPLE:
        n = n_words(sura, aya)
        assert is_legal_cut(sura, aya, 0)
        assert is_legal_cut(sura, aya, n)
        assert is_legal_range(sura, aya, 0, n)


def test_illegal_ranges_are_rejected_not_raised():
    assert not is_legal_range(103, 1, 0, 5)   # past the end
    assert not is_legal_range(103, 1, -1, 1)
    assert not is_legal_range(103, 1, 0, 0)


# ───────────────────────────────────────────────────────────── duration
def test_duration_estimate_matches_real_reciters():
    """Against Husary and Alafasy, silence-trimmed, from the Phase 0 calibration.
    The display rate is a median, so it must be unbiased across reciters even
    though any single clip can be off."""
    path = API_ROOT.parent / "spike" / "step0-results" / "audit_durations.json"
    if not path.exists():
        pytest.skip("run spike/s8c_duration_calib.py to generate")
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert len(rows) >= 20

    errors = [estimate_seconds(r["n_phonemes"]) - r["duration_s"] for r in rows]
    mean_err = sum(errors) / len(errors)
    assert abs(mean_err) < 2.0, f"display rate is biased by {mean_err:+.2f}s"

    # The gate rate must genuinely bound slow reciters, or segments sized with
    # it will still overrun for the people it exists to protect.
    over = [r for r in rows
            if estimate_seconds(r["n_phonemes"], gate=True) < r["duration_s"]]
    assert len(over) / len(rows) < 0.10, (
        f"gate rate under-estimated {len(over)}/{len(rows)} clips")


def test_gate_rate_is_slower_than_display_rate():
    assert RATE_GATE > RATE_DISPLAY
    assert estimate_seconds(100, gate=True) > estimate_seconds(100)


# ───────────────────────────────────────────────────────── segmentation
@pytest.mark.parametrize("sura,aya", SAMPLE)
def test_segments_tile_the_ayah_losslessly(sura, aya):
    """Concatenating the segments must reproduce the ayah exactly - no word
    dropped, duplicated or reordered."""
    segs = segment_ayah(sura, aya)
    assert segs, f"{sura}:{aya} produced no segments"
    assert segs[0].start_word == 0
    assert segs[-1].start_word + segs[-1].num_words == n_words(sura, aya)
    for a, b in zip(segs, segs[1:]):
        assert a.start_word + a.num_words == b.start_word, "gap or overlap"


@pytest.mark.parametrize("sura,aya", SAMPLE)
def test_segments_never_split_an_uthmani_word(sura, aya):
    """The property PartOfUthmaniWord exists to enforce. If a segment boundary
    is illegal the reference cannot even be built, so this is load-bearing."""
    for seg in segment_ayah(sura, aya):
        assert is_legal_range(sura, aya, seg.start_word, seg.num_words), (
            f"{sura}:{aya} segment w[{seg.start_word}:"
            f"{seg.start_word + seg.num_words}] splits an uthmani word")
        reference(seg.as_range())          # must not raise


@pytest.mark.parametrize("sura,aya", SAMPLE)
def test_every_segment_is_under_the_hard_cap(sura, aya):
    """Measured at the SLOW rate - a segment sized for a fast reciter that
    overruns for a deliberate one is exactly the failure the cap prevents."""
    for seg in segment_ayah(sura, aya):
        assert seg.seconds_gate <= HARD_CAP_SECONDS, (
            f"{sura}:{aya} w[{seg.start_word}:{seg.start_word + seg.num_words}]"
            f" is {seg.seconds_gate:.1f}s at the gate rate")


def test_short_ayah_is_one_whole_segment():
    """Under the cap means no artificial subdivision."""
    segs = segment_ayah(103, 1)
    assert len(segs) == 1
    assert (segs[0].start_word, segs[0].num_words) == (0, n_words(103, 1))


def test_segmentation_is_deterministic():
    a = [(s.start_word, s.num_words, s.n_phonemes) for s in segment_ayah(2, 255)]
    b = [(s.start_word, s.num_words, s.n_phonemes) for s in segment_ayah(2, 255)]
    assert a == b


# ─────────────────────────────────────────────────── bismillah handling
def test_bismillah_uses_the_library_flag_and_reports_the_offset():
    """include_bismillah prepends the basmala INTO the index space, so a range
    of (0, n) returns only the basmala's first word unless the offset is
    applied. aya_imlaey_span_words reports it - never hardcode 4."""
    plain = reference(Range(2, 1, 0, n_words(2, 1)))[0]
    withb = reference(Range(2, 1, 0, n_words(2, 1), include_bismillah=True))[0]
    assert plain == "الٓمٓ"
    assert withb.endswith("الٓمٓ")
    assert "بِسْمِ" in withb and len(withb) > len(plain)


def test_bismillah_rejected_mid_ayah():
    """The basmala precedes an ayah; it does not appear from word 3 onwards."""
    with pytest.raises(ValueError):
        reference(Range(2, 255, 3, 5, include_bismillah=True))


# ──────────────────────────────────────── no hand-built reference strings
def test_no_manual_reference_concatenation():
    """quran_phonetizer must never be handed a string built by concatenation.

    Joining reference texts is reported to crash the model's multi-level
    tokenizer with "Could not infer dtype of NoneType". Phase 0 could not
    reproduce it, which makes it unproven rather than safe - so the codebase
    uses include_bismillah and range extraction, and this keeps it that way.
    """
    offenders = []
    for path in (API_ROOT / "tilawah").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name != "quran_phonetizer" or not node.args:
                continue
            arg = node.args[0]
            built = (
                (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add))
                or isinstance(arg, ast.JoinedStr)
                or (isinstance(arg, ast.Call)
                    and getattr(arg.func, "attr", None) == "join")
            )
            if built:
                offenders.append(f"{path.relative_to(API_ROOT)}:{node.lineno}")
    assert not offenders, (
        "quran_phonetizer called on a hand-built string at: "
        + ", ".join(offenders)
        + ". Use Aya.get_by_imlaey_words(..., include_bismillah=...) instead.")


# ─────────────────────────────────────────────────── precomputed artifact
def test_segment_artifact_is_present_and_consistent():
    """The artifact is committed because packing an ayah costs 0.2-3s and must
    not happen in a request path."""
    meta = content.segments_meta()
    if not meta:
        pytest.skip("run tools/build_segments.py to generate segments.json")
    assert meta["n_ayat"] == 6236
    assert meta["rate_gate_s_per_phoneme"] == RATE_GATE
    assert meta["hard_cap_seconds"] == HARD_CAP_SECONDS
    assert not meta["segments_over_hard_cap"], meta["segments_over_hard_cap"][:5]

    for sura, aya in SAMPLE:
        stored = content.segments_of(sura, aya)
        assert stored, f"{sura}:{aya} missing from artifact"
        live = segment_ayah(sura, aya)
        assert [(s["start_word"], s["num_words"]) for s in stored] == \
               [(s.start_word, s.num_words) for s in live], \
               f"{sura}:{aya} artifact is stale - rebuild it"
