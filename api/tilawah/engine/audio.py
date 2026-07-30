# -*- coding: utf-8 -*-
"""Upload -> 16 kHz mono float32, plus the recording-quality gate.

The quality gate is the single most valuable thing the spike produced. Low-SNR
audio does not degrade gracefully: the model snaps to huruf muqatta'at (alif-lam-
meem, kaf-ha-ya-ain-sad) at 0.87-0.96 confidence. That is confident, fluent
nonsense, and shipping tajweed corrections derived from it would be worse than
shipping nothing. Reject the take and ask for another BEFORE inference.

Threshold from measurement: clean takes and all five expert reciters landed at
38.8-45.5 dB; every muqatta'at collapse was at or below 33.4 dB.
"""
import io
import shutil
import subprocess
from dataclasses import dataclass

import numpy as np
import soundfile as sf

SR = 16000
MIN_SNR_DB = 35.0
MIN_DURATION_S = 0.6
MAX_DURATION_S = 30.0


@dataclass
class Quality:
    ok: bool
    snr_db: float
    duration_s: float
    reason: str = ""


def decode(data: bytes) -> np.ndarray:
    """Any browser audio blob -> 16 kHz mono float32.

    Tries libsndfile first (wav/flac/mp3), falls back to ffmpeg for webm/opus,
    which is what MediaRecorder produces on Chrome and Android.
    """
    try:
        wave, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
        if wave.ndim > 1:
            wave = wave.mean(axis=1)
        if sr == SR:
            return np.ascontiguousarray(wave, dtype=np.float32)
        import librosa
        return np.ascontiguousarray(
            librosa.resample(wave, orig_sr=sr, target_sr=SR), dtype=np.float32)
    except Exception:
        pass

    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "Could not decode audio and ffmpeg is not installed. "
            "apt-get install ffmpeg (see api/Dockerfile)."
        )
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
         "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
        input=data, capture_output=True,
    )
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {p.stderr.decode('utf-8', 'replace')[:300]}")
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def check_quality(wave: np.ndarray) -> Quality:
    dur = len(wave) / SR
    if dur < MIN_DURATION_S:
        return Quality(False, 0.0, dur, "too_short")
    if dur > MAX_DURATION_S:
        return Quality(False, 0.0, dur, "too_long")

    n = 512
    m = len(wave) // n * n
    frames = wave[:m].reshape(-1, n)
    e = np.sqrt((frames ** 2).mean(axis=1)) + 1e-12
    snr = float(20 * np.log10(np.percentile(e, 90) / np.percentile(e, 10)))

    if snr < MIN_SNR_DB:
        return Quality(False, snr, dur, "too_noisy")
    return Quality(True, snr, dur)
