# -*- coding: utf-8 -*-
"""What happens at the top end, where whole-ayah practice meets the hardware.

Measured on this stack, 8 GB, float32 CPU:

    audio    wall    xRT   outcome
     13 s     18 s   1.4x  ok
     52 s    522 s  10.0x  ok, 3 errors on an expert recitation
    129 s      -      -    RuntimeError: tried to allocate 9401241600 bytes

The failure is quadratic, not gradual: wav2vec2-BERT's relative-position
attention builds a [frames, frames, 64] float32 tensor at 47 frames/s. So there
is a hard ceiling, `settings.max_audio_seconds` exists to stay under it, and an
OOM that slips past it must still not reach the learner as a 500 — they have
already waited minutes by then.
"""
import pytest

from tilawah.config import Settings, settings
from tilawah.engine import audio, pipeline

FPS = 47.0          # model frames per second of audio
BYTES_PER_PAIR = 256  # [frames, frames, 64] float32


def positional_bytes(seconds: float) -> float:
    return (FPS * seconds) ** 2 * BYTES_PER_PAIR


def test_the_formula_matches_the_observed_failure():
    """Pins the arithmetic the ceiling is derived from. If a model or
    transformers upgrade changes the shape, this is the tripwire."""
    assert positional_bytes(128.8) == pytest.approx(9_401_241_600, rel=0.01)


def test_the_default_ceiling_stays_inside_a_sane_budget():
    """90 s asks for ~4.6 GB for that one tensor. Above ~6 GB an 8 GB box is
    gone, and the model itself already holds 2.4 GB."""
    need = positional_bytes(Settings().max_audio_seconds)
    assert need < 6e9, f"{Settings().max_audio_seconds}s needs {need/1e9:.1f} GB"


def test_the_measured_good_case_is_under_the_ceiling():
    """52 s ran successfully, so the ceiling must not have been set below it —
    that would reject something known to work."""
    assert Settings().max_audio_seconds >= 52


def test_the_measured_failure_is_over_the_ceiling():
    assert Settings().max_audio_seconds < 128.8


def test_the_audio_gate_uses_the_configured_ceiling():
    """audio.MAX_DURATION_S is what actually rejects a long upload; if it drifts
    from the setting, the setting is decorative."""
    assert audio.MAX_DURATION_S == settings.max_audio_seconds


# ─────────────────────────────────────── an OOM is a retry, not a 500

@pytest.mark.parametrize("message", [
    "[enforce fail at alloc_cpu.cpp:117] data. DefaultCPUAllocator: not "
    "enough memory: you tried to allocate 9401241600 bytes.",
    "CUDA out of memory. Tried to allocate 9.40 GiB",
    "cannot allocate memory",
])
def test_allocation_failures_are_recognised(message):
    assert pipeline._is_allocation_failure(RuntimeError(message))


def test_memory_error_is_recognised():
    assert pipeline._is_allocation_failure(MemoryError())


@pytest.mark.parametrize("message", [
    "shape mismatch: expected 3 dims, got 2",
    "Expected all tensors to be on the same device",
    "index out of range in self",
])
def test_real_bugs_are_not_swallowed_as_length_problems(message):
    """The narrow match is the point. Reporting a genuine crash to the learner
    as 'your ayah was too long' would hide breakage behind a plausible excuse
    and send them off to split an ayah that was never the problem."""
    assert not pipeline._is_allocation_failure(RuntimeError(message))


def test_oom_becomes_a_named_retry(monkeypatch):
    """End to end through analyze(): the learner gets a retry with a reason
    that names the real cause, not a 500 after a multi-minute wait."""
    import numpy as np

    monkeypatch.setattr(pipeline, "decode",
                        lambda data, info: np.zeros(16000 * 5, dtype="float32"))
    monkeypatch.setattr(
        pipeline, "check_quality",
        lambda wave: audio.Quality(True, reason="", duration_s=5.0, snr_db=20.0),
    )

    def boom(wave, phonetized):
        raise RuntimeError("DefaultCPUAllocator: not enough memory: you tried "
                           "to allocate 9401241600 bytes.")

    monkeypatch.setattr(pipeline, "transcribe", boom)
    monkeypatch.setattr(pipeline, "capture", lambda *a, **k: None)

    fb = pipeline.analyze(b"x", 2, 282, "uz")
    assert fb.status == "retry_recording"
    assert fb.reason == "too_long_for_engine"


def test_a_real_bug_still_raises(monkeypatch):
    import numpy as np

    monkeypatch.setattr(pipeline, "decode",
                        lambda data, info: np.zeros(16000 * 5, dtype="float32"))
    monkeypatch.setattr(
        pipeline, "check_quality",
        lambda wave: audio.Quality(True, reason="", duration_s=5.0, snr_db=20.0),
    )
    monkeypatch.setattr(pipeline, "capture", lambda *a, **k: None)

    def boom(wave, phonetized):
        raise RuntimeError("shape mismatch somewhere real")

    monkeypatch.setattr(pipeline, "transcribe", boom)
    with pytest.raises(RuntimeError, match="shape mismatch"):
        pipeline.analyze(b"x", 112, 1, "uz")
