# -*- coding: utf-8 -*-
"""Does the duration estimate actually predict how long a learner waits?

Two different quantities are easy to conflate:

    estimate_seconds()  -> how long the RECITATION takes
    inference wall time -> how long the learner waits after tapping stop

They are related by the realtime factor of the box (~1.4x on 2 vCPU with
float32). The 12 s segment target was chosen so that product lands near 17 s,
so if either the estimate or the factor drifts, the practice loop gets slower
than intended and nobody notices until it feels bad.

Loads the 2.42 GB model, so it is opt-in:

    pytest tests/test_inference_budget.py --run-slow -q
"""
import time

import numpy as np
import pytest

from tilawah.config import settings
from tilawah.engine.model import transcribe
from tilawah.engine.ranges import (HARD_CAP_SECONDS, TARGET_SECONDS,
                                   estimate_seconds)
from tilawah.engine.target import _phonetized

pytestmark = pytest.mark.slow

SR = 16000


def test_dtype_is_float32_not_bfloat16():
    """bfloat16 has no native CPU path here - torch emulates it, measured at
    19.68 s vs 1.33 s for identical output. It halves memory and multiplies
    latency by 15, which is the wrong trade when RAM is EUR 4/month."""
    assert settings.model_dtype == "float32", (
        f"model_dtype is {settings.model_dtype!r}; bfloat16 is ~15x slower on "
        "this CPU for identical output")


@pytest.mark.parametrize("seconds", [2.0, 6.0, 12.0])
def test_inference_tracks_audio_length_within_budget(seconds):
    """Wall time must stay proportional to clip length and inside the budget the
    segment cap was sized against."""
    rng = np.random.default_rng(0)
    wave = (rng.normal(0, 0.02, int(SR * seconds))).astype(np.float32)
    ph = _phonetized(103, 1)

    transcribe(wave, ph)                       # warm up: first call pays load
    t0 = time.perf_counter()
    transcribe(wave, ph)
    elapsed = time.perf_counter() - t0

    factor = elapsed / seconds
    assert factor < 4.0, (
        f"{seconds}s clip took {elapsed:.1f}s ({factor:.1f}x realtime) - the "
        f"12s segment target assumes ~1.4x on 2 vCPU")


def test_segment_cap_keeps_the_wait_tolerable():
    """A segment at the hard cap must not blow the practice loop apart. This is
    arithmetic over the constants, so it fails the moment someone raises the cap
    without thinking about what it costs the learner."""
    assert TARGET_SECONDS <= 15.0
    assert HARD_CAP_SECONDS <= 20.0
    worst_wait = HARD_CAP_SECONDS * 1.4       # measured factor on 2 vCPU
    assert worst_wait < 30.0, (
        f"a capped segment would make the learner wait {worst_wait:.0f}s")


def test_estimate_is_in_the_same_units_as_reality():
    """Sanity bound between the two quantities: a 12 s target must not imply a
    sub-second or multi-minute recitation."""
    phonemes_for_target = TARGET_SECONDS / 0.2319
    assert 40 < phonemes_for_target < 80
    assert 10.0 < estimate_seconds(int(phonemes_for_target), gate=True) < 14.0
