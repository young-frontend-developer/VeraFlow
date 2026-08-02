# -*- coding: utf-8 -*-
"""Engine tests that run WITHOUT loading the 2.42 GB model.

Everything except transcribe() is deterministic, so nearly all of the engine is
testable in milliseconds. Keep it that way - if a test needs the model, it
belongs in a separate slow suite.

Run:  pytest -q
"""
import numpy as np
import pytest

from tilawah import content
from tilawah.content import coaching
from tilawah.engine.audio import MIN_SNR_DB, SR, check_quality
from tilawah.engine.runlength import tokenize
from tilawah.engine.target import target_for
from tilawah.engine.typed_errors import typed_diff


def test_runlength_merges_only_before_diacritics():
    # نننن is one 4-count ghunnah run...
    assert tokenize("نننن") == [("ن", 4, "")]
    # ...but a diacritic closes the unit, so ءَء stays two hamzas.
    assert len(tokenize("ءَء")) == 2


def test_duration_error_is_not_a_missing_letter():
    errs = typed_diff("نننن", "نن")
    assert [e.code for e in errs] == ["GHUNNA_SHORT"]
    assert (errs[0].expected_count, errs[0].heard_count) == (4, 2)


def test_l1_substitution_is_named():
    errs = typed_diff("عَ", "ءَ")
    assert errs[0].code == "SUB_AYN_HAMZA"


def test_identical_input_is_clean():
    t = target_for(103, 1)
    assert typed_diff(t.phonemes, t.phonemes) == []


def test_target_is_deterministic():
    assert target_for(103, 1).phonemes == target_for(103, 1).phonemes
    assert target_for(103, 1).uthmani


def _speech_like(seconds=2.0, amp=0.3, lead_silence_s=0.0):
    t = np.linspace(0, seconds, int(SR * seconds), dtype=np.float32)
    env = (np.sin(2 * np.pi * 3 * t) > 0).astype(np.float32)   # bursts and silence
    wave = (np.sin(2 * np.pi * 200 * t) * env * amp).astype(np.float32)
    if lead_silence_s:
        pad = np.zeros(int(SR * lead_silence_s), dtype=np.float32)
        wave = np.concatenate([pad, wave])
    return wave


def test_quality_gate_rejects_short():
    assert check_quality(np.zeros(int(SR * 0.2), dtype=np.float32)).reason == "too_short"


def test_quality_gate_rejects_silence():
    """A muted mic or an unanswered permission prompt, not a recitation."""
    q = check_quality(np.zeros(SR * 2, dtype=np.float32))
    assert not q.ok and q.reason == "too_quiet"


def test_quality_gate_accepts_speech_like_signal():
    q = check_quality(_speech_like())
    assert q.ok and q.snr_db > MIN_SNR_DB


def test_snr_is_stable_once_room_tone_is_present():
    """The noise floor is only estimable when the clip CONTAINS some. Given a
    lead-in of room tone - which recorder.ts guarantees via SETTLE_MS - the
    figure must not drift as more of it is added. Measured on the real clips:
    1.6 dB mean drift between a 250 ms and a 1000 ms lead-in.

    Note the limitation this test encodes: with NO silence anywhere in the clip
    the number is not meaningful, which is exactly why nothing gates on it."""
    from tilawah.engine.audio import measure

    floor = 0.002
    rng = np.random.default_rng(0)
    tone = lambda n: rng.normal(0, floor, n).astype(np.float32)  # noqa: E731
    body = _speech_like(seconds=1.5) + tone(int(SR * 1.5))
    short = np.concatenate([tone(int(SR * 0.25)), body])
    long_ = np.concatenate([tone(int(SR * 1.0)), body])
    drift = abs(measure(long_)["snr_db"] - measure(short)["snr_db"])
    assert drift < 6.0, f"SNR moved {drift:.1f} dB on identical audio"


def test_tight_recording_is_not_rejected():
    """REGRESSION. The old gate computed p90/p10 of frame energy and called it
    SNR, but it was measuring how much SILENCE the clip contained: padding a
    clip with a copy of its own noise floor moved it 33 -> 67 dB, and trimming
    silence pushed all five expert reciters below the 35 dB reject threshold.

    Browser takes have almost no lead-in, so every one of them was rejected as
    "too_noisy" while the same recitation passed from a .wav. A learner who taps
    record, recites, and taps stop must get through."""
    q = check_quality(_speech_like(seconds=1.5, lead_silence_s=0.0))
    assert q.ok, f"rejected a clean tight take as {q.reason}"


# ------------------------------------------------------------------- collapse
def test_collapse_detects_muqattaat_on_ordinary_ayah():
    """The real failure mode: unusable audio makes the model emit huruf
    muqatta'at fluently at 0.94-0.97 confidence rather than reporting doubt.
    These four strings are actual predictions from the spike clips."""
    from tilawah.engine.collapse import looks_collapsed

    target = target_for(103, 1).phonemes
    for heard in ("ءَلِفلَااممرَاا", "ءَلِفلَااااممممِۦۦ",
                  "كَفهَايَااعِقَدڇ", "ءَلِفلَمرَ"):
        collapsed, detail = looks_collapsed(heard, 103, 1, target)
        assert collapsed, f"missed collapse {heard}: {detail}"


def test_collapse_passes_real_recitations():
    """Good takes of 103:1, including the learner's sad-as-seen substitution,
    must never be mistaken for a collapse."""
    from tilawah.engine.collapse import looks_collapsed

    target = target_for(103, 1).phonemes
    for heard in ("وَلعَصر", "وَلعَسر", "وَلءَسر", "وَلءَصر", "وَلءَسَر"):
        collapsed, detail = looks_collapsed(heard, 103, 1, target)
        assert not collapsed, f"false collapse on {heard}: {detail}"


def test_collapse_allows_ayat_that_really_are_muqattaat():
    """Reciting 2:1 correctly is alif-lam-meem. Never flag it."""
    from tilawah.engine.collapse import looks_collapsed

    collapsed, _ = looks_collapsed("ءَلِفلَاامم", 2, 1, "ءَلِفلَاامم")
    assert not collapsed


@pytest.mark.parametrize("code", ["SUB_AYN_HAMZA", "MADD_SHORT", "DELETION"])
def test_every_shipped_code_has_both_languages(code):
    """A legacy rules.json entry maps onto the coaching card as headline / fix
    / drill. `rule` stays empty on purpose: rules.json's `rule` is a LABEL, not
    an explanation, so it travels as `label` rather than being promoted into a
    field it does not fill."""
    for lang in content.LANGS:
        body = content.render(code, lang,
                              {"expected_count": 4, "heard_count": 2,
                               "letter": "ع", "expected": "ع", "heard": "ء",
                               "word": "عَلَيْهِمْ"})
        assert body
        assert all(body[k] for k in ("headline", "fix", "drill", "label"))


def test_templates_have_no_unfilled_placeholders():
    """Every authored template, both registries, both languages.

    render() now RAISES on an unfilled placeholder rather than returning the
    raw text, so this asserts twice over: the call must not raise, and nothing
    that comes back may contain a brace.
    """
    fields = {"expected_count": 4, "heard_count": 2, "letter": "ع",
              "expected": "ع", "heard": "ء", "code": "X", "at": 0,
              "word": "عَلَيْهِمْ"}
    codes = set(content.rules()) | set(coaching.registry())
    for code in codes:
        for lang in content.LANGS:
            body = content.render(code, lang, fields)
            assert body, code
            for key in ("headline", "fix", "rule", "drill"):
                assert "{" not in body[key], f"{code}.{lang}.{key} left a placeholder"
                assert "}" not in body[key], f"{code}.{lang}.{key} left a placeholder"


def test_shipped_content_is_marked_reviewed():
    """Nothing reaches a learner unless it is marked reviewed. This is the real
    invariant and it should always pass."""
    unreviewed = [
        code
        for code, rule in content.rules().items()
        if rule.get("status") == "ship" and not rule.get("reviewed")
    ]
    assert not unreviewed, f"shipped but not marked reviewed: {unreviewed}"


def test_no_dev_overrides_remain():
    """DEV ONLY TRIPWIRE - THIS TEST FAILS ON PURPOSE.

    Some rules are flipped to reviewed=true so the app can be demonstrated
    before a qori has reviewed the content. That is fine on a laptop and not
    fine anywhere else, so this stays red until the override is removed. It is
    the one failure the suite is allowed to have; anything else going red is a
    real regression.

    To make it pass: in tilawah/content/rules.json, either set reviewed=false
    and drop the reviewed_by key, or replace reviewed_by with the name of the
    qori who actually signed the strings off.
    """
    overrides = content.dev_overrides()
    assert not overrides, (
        "DEV OVERRIDE STILL ACTIVE - do not launch. "
        f"These corrections are shown to learners with no qori review: {overrides}. "
        "See rules.json -> _meta.DEV_OVERRIDE for how to re-gate."
    )


# ---------------------------------------------------------------- segmentation
def test_segments_are_lossless_and_tile_the_ayah():
    """The UI renders these spans over the real text. If they do not tile it
    exactly, a highlight lands on the wrong letter - or a letter disappears."""
    from tilawah.engine.segments import segments_for

    for a in content.ayat():
        segs = segments_for(a["sura"], a["aya"])
        uthmani = target_for(a["sura"], a["aya"]).uthmani
        assert "".join(s["text"] for s in segs) == uthmani, a["slug"]
        assert segs[0]["start"] == 0 and segs[-1]["end"] == len(uthmani), a["slug"]
        for x, y in zip(segs, segs[1:]):
            assert x["end"] == y["start"], a["slug"]


def test_every_error_unit_maps_to_exactly_one_segment():
    """An error at any unit must be pointable at. Uncovered units would leave a
    correction with nothing to highlight."""
    from tilawah.engine.runlength import tokenize
    from tilawah.engine.segments import segments_for, unit_to_segment

    for a in content.ayat():
        n_units = len(tokenize(target_for(a["sura"], a["aya"]).phonemes))
        owners = [u for s in segments_for(a["sura"], a["aya"]) for u in s["units"]]
        assert sorted(owners) == list(range(n_units)), a["slug"]
        for u in range(n_units):
            assert unit_to_segment(a["sura"], a["aya"], u) is not None


def test_segments_match_runlength_units():
    """unit_char_spans mirrors tokenize by hand; keep them in step."""
    from tilawah.engine.runlength import tokenize
    from tilawah.engine.segments import unit_char_spans

    for a in content.ayat():
        ph = target_for(a["sura"], a["aya"]).phonemes
        spans = unit_char_spans(ph)
        units = tokenize(ph)
        assert len(spans) == len(units), a["slug"]
        for (start, end), (base, count, _marks) in zip(spans, units):
            chunk = ph[start:end]
            assert chunk[0] == base
            assert chunk.count(base) == count
