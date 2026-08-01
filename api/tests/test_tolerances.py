# -*- coding: utf-8 -*-
"""The tolerance gate and the calibration harness's pure half.

No model, no audio. Everything here is deterministic, so the whole file runs in
milliseconds - see test_engine.py for why that matters.
"""
import json

import pytest

from tilawah.engine import tolerances
from tilawah.engine.runlength import GHUNNA_LETTERS, tokenize
from tilawah.engine.typed_errors import TypedError, typed_diff


def cfg(**checks):
    return {"defaults": {"min_delta": 1, "min_mean_prob": 0.0},
            "checks": checks}


# ────────────────────────────────────────────────────────── margins

def test_duration_margin_is_the_count_difference():
    e = TypedError(code="MADD_SHORT", at=0, letter="ا",
                   expected_count=4, heard_count=2)
    assert tolerances.margin_of(e) == 2.0


def test_discrete_checks_have_no_margin():
    """A wrong letter is not 'a bit wrong'. Reporting a margin of 1.0 would
    invite a threshold that cannot mean anything."""
    e = TypedError(code="SUB_SAD_SEEN", at=0, letter="ص",
                   expected="ص", heard="س")
    assert tolerances.margin_of(e) is None


# ──────────────────────────────────────────────────────── the gate

def test_shipped_defaults_change_nothing():
    """REGRESSION GUARD. The committed config must reproduce the pre-tolerance
    behaviour exactly. Guessing thresholds before calibrating would silence real
    errors on the strength of nobody's measurement."""
    errs = typed_diff("اااا", "اا") + typed_diff("عَ", "ءَ")
    kept, dropped = tolerances.apply(errs, mean_prob=0.9)
    assert len(kept) == len(errs) and not dropped


def test_threshold_suppresses_a_smaller_deviation():
    errs = typed_diff("اااا", "ااا")            # off by one count
    kept, dropped = tolerances.apply(
        errs, 0.9, cfg(MADD_SHORT={"kind": "duration", "min_delta": 2}))
    assert not kept and len(dropped) == 1
    _err, verdict = dropped[0]
    assert verdict.margin == 1.0 and verdict.threshold == 2.0


def test_threshold_still_reports_a_larger_deviation():
    """The other half of the same threshold - a tolerance that swallows
    everything is not a tolerance."""
    errs = typed_diff("اااا", "اا")             # off by two
    kept, _dropped = tolerances.apply(
        errs, 0.9, cfg(MADD_SHORT={"kind": "duration", "min_delta": 2}))
    assert [e.code for e in kept] == ["MADD_SHORT"]


def test_no_threshold_can_silence_a_wrong_letter():
    """Discrete checks must not be tunable into silence by a min_delta. If ص is
    read as س, no amount of threshold moves that; only a model or a scope change
    does, and pretending otherwise would hide the limitation."""
    errs = typed_diff("صَ", "سَ")
    kept, dropped = tolerances.apply(
        errs, 0.9, cfg(SUB_SAD_SEEN={"kind": "discrete", "min_delta": 99}))
    assert len(kept) == 1 and not dropped


def test_confidence_floor_gates_the_clip():
    errs = typed_diff("اااا", "اا")
    kept, dropped = tolerances.apply(
        errs, 0.20, cfg(MADD_SHORT={"kind": "duration", "min_delta": 1,
                                    "min_mean_prob": 0.5}))
    assert not kept and "confidence" in dropped[0][1].reason


def test_config_survives_a_windows_bom(tmp_path, monkeypatch):
    """Notepad, VS Code and PowerShell's Out-File all prepend a BOM. The file is
    documented as hand-editable, so a BOM must not break the next run."""
    p = tmp_path / "tolerances.json"
    p.write_text(json.dumps(cfg(MADD_SHORT={"kind": "duration",
                                            "min_delta": 2})),
                 encoding="utf-8-sig")
    monkeypatch.setenv("TILAWAH_TOLERANCES", str(p))
    assert tolerances.rule_for("MADD_SHORT")["min_delta"] == 2


def test_config_reload_picks_up_an_edit(tmp_path, monkeypatch):
    """Step 4 of the documented loop - edit a threshold, re-run the same
    command - is only one command if the file is re-read. A process-lifetime
    cache would silently score the old numbers."""
    p = tmp_path / "tolerances.json"
    p.write_text(json.dumps(cfg(MADD_SHORT={"kind": "duration",
                                            "min_delta": 1})), encoding="utf-8")
    monkeypatch.setenv("TILAWAH_TOLERANCES", str(p))
    errs = typed_diff("اااا", "ااا")
    assert len(tolerances.apply(errs, 0.9)[0]) == 1

    import os
    import time
    p.write_text(json.dumps(cfg(MADD_SHORT={"kind": "duration",
                                            "min_delta": 3})), encoding="utf-8")
    os.utime(p, (time.time() + 1, time.time() + 1))   # beat mtime granularity
    assert tolerances.apply(errs, 0.9)[0] == []


# ─────────────────────────────────────────── the shipped config itself

def test_every_emittable_code_has_a_tolerance_entry():
    """A code the engine can emit but the config does not name would silently
    take the defaults - which is how a check ends up ungoverned."""
    from tilawah.engine.typed_errors import L1_PAIRS

    emittable = set(L1_PAIRS.values()) | {
        "MADD_SHORT", "MADD_LONG", "GHUNNA_SHORT", "GHUNNA_LONG",
        "SHADDA_SHORT", "SHADDA_LONG", "QALQALA_DROP", "DELETION",
        "INSERTION", "SUBSTITUTION"}
    named = set(tolerances.load().get("checks", {}))
    assert not (emittable - named), f"ungoverned: {sorted(emittable - named)}"


def test_duration_codes_are_classified_as_duration():
    for code in tolerances.DURATION_CODES:
        assert tolerances.rule_for(code)["kind"] == "duration"


# ──────────────────────────────────────────────────── runlength fix

@pytest.mark.parametrize("letter", ["ں", "۾"])
def test_ikhfa_and_iqlab_are_ghunnah_not_shadda(letter):
    """REGRESSION. QPS writes the ikhfa noon as ں and the iqlab meem as ۾. They
    were missing from GHUNNA_LETTERS, so a shortened ikhfa ghunnah - one of the
    most common beginner errors there is - came out as SHADDA_SHORT, a code with
    no authored content, and disappeared."""
    assert letter in GHUNNA_LETTERS
    errs = typed_diff(letter * 3, letter)
    assert [e.code for e in errs] == ["GHUNNA_SHORT"]


def test_ikhfa_run_still_tokenizes_as_one_unit():
    assert tokenize("ںںں") == [("ں", 3, "")]


# ────────────────────────────────────────────── harness pure helpers

def test_eligible_checks_exclude_what_cannot_fire():
    """A 0% false-positive rate on a check that was never eligible is no
    evidence at all, so the denominator has to be honest."""
    from tilawah.engine.tolerances import eligible_checks

    # وَلعَصر - has a و, but nothing is held long and there is no nasal.
    plain = eligible_checks("وَلعَصر")
    assert "DELETION" in plain                    # always possible
    assert "MADD_LONG" in plain, "a و can always be over-lengthened"
    assert "MADD_SHORT" not in plain, "nothing here is held long enough to shorten"
    assert "GHUNNA_SHORT" not in plain and "GHUNNA_LONG" not in plain

    assert "MADD_SHORT" in eligible_checks("اااا")
    assert "GHUNNA_SHORT" in eligible_checks("ننننَ")
    # ں is the ikhfa noon - a ghunnah, not a shadda. See the runlength fix.
    assert "GHUNNA_SHORT" in eligible_checks("مِںںں")


def test_sifa_compare_ignores_unaligned_regions():
    """A single inserted phoneme must not report every following letter as a
    ṣifa error - that would drown the real signal in alignment noise."""
    from tilawah.engine.sifa_compare import compare

    ref = [{"phonemes": "بَ", "hams_or_jahr": "jahr"},
           {"phonemes": "تَ", "hams_or_jahr": "hams"}]
    pred = [{"phonemes": "بَ", "hams_or_jahr": "jahr"},
            {"phonemes": "سَ", "hams_or_jahr": "hams"},
            {"phonemes": "تَ", "hams_or_jahr": "hams"}]
    assert compare(ref, pred) == []


def test_sifa_compare_reports_an_aligned_flip():
    from tilawah.engine.sifa_compare import compare

    ref = [{"phonemes": "صَ", "tafkheem_or_taqeeq": "mofakham"}]
    pred = [{"phonemes": "صَ", "tafkheem_or_taqeeq": "moraqaq",
             "probs": {"tafkheem_or_taqeeq": 0.71}}]
    d = compare(ref, pred)
    assert len(d) == 1 and d[0].field == "tafkheem_or_taqeeq"
    assert d[0].expected == "mofakham" and d[0].heard == "moraqaq"
    assert d[0].prob == 0.71
