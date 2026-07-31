# -*- coding: utf-8 -*-
"""Upload -> 16 kHz mono float32, plus the recording-quality gate.

The gate exists because low-quality audio does not degrade gracefully: the model
snaps to huruf muqatta'at (alif-lam-meem, kaf-ha-ya-ain-sad) at 0.92-0.97
confidence. That is confident, fluent nonsense, and tajweed corrections derived
from it would be worse than shipping nothing.

WHAT CHANGED AND WHY (2026-07-31)
---------------------------------
The previous gate computed p90/p10 of frame energy and called it SNR. It is not
SNR - it is a measure of how much SILENCE the clip contains. Measured:

  * padding a clip with a copy of ITS OWN noise floor moved it 33.2 -> 67.2 dB
    with the noise physically unchanged;
  * trimming leading/trailing silence dropped all five expert reciters - the
    clips the 35 dB threshold was calibrated on - to 26-31 dB, i.e. FAIL.

So the old threshold encoded "this clip has generous lead-in silence". Files
downloaded from everyayah.com do. A browser recording, where the learner taps
record, recites, and taps stop, does not - which is why every browser take was
rejected while the same recitation passed from a WAV.

The correlation that made the old gate look calibrated was duration: the three
lowest-scoring clips were simply the three shortest (1.12 s, 1.48 s, 1.61 s),
and short truncated takes are what actually trigger the muqatta'at collapse.

This module now measures the noise floor honestly - and the honest finding is
that IT IS NOT ALWAYS MEASURABLE. If a clip contains no silence there is no room
tone to measure, and no statistic recovers it: a clip with no silence and a clip
recorded in a noisy room both produce a middling number, indistinguishably. A
"more correct" estimator does not fix this; it swings harder, because it tracks
the real floor when one exists and quiet speech when one does not.

The consequences, both deliberate:

  * nothing gates on noise any more. The measurement is logged and returned on
    every attempt, but the only blocking checks are duration and near-silence.
    The failure worth blocking - the muqatta'at collapse - is now detected from
    the model's own output in engine/collapse.py, where it separates cleanly on
    all 13 clips measured, instead of being proxied through an audio statistic
    that never predicted it.
  * recorder.ts banks ~250 ms of room tone before the UI goes live, so the
    figure is a real measurement rather than a coin flip. Given that lead-in it
    is stable to ~1.6 dB; without it, treat snr_db as advisory only.
"""
import io
import logging
import shutil
import subprocess
from dataclasses import dataclass, field

import numpy as np
import soundfile as sf

log = logging.getLogger(__name__)

SR = 16000
MIN_DURATION_S = 0.6
MAX_DURATION_S = 30.0

# Applied only when the noise floor is actually measurable (see Quality.snr_measurable).
# Deliberately well below the old 35 dB: that number was a silence-fraction
# threshold in disguise and never described noise. Re-derive this from real
# browser takes once attempt logging has collected them.
MIN_SNR_DB = 12.0

# Noise floor is estimated from the quietest contiguous window of this length.
# Must fit comfortably inside the lead-in recorder.ts banks (SETTLE_MS = 300 ms),
# or the window straddles the start of the recitation and reads ~8 dB high.
NOISE_WIN_S = 0.15
# If the speech level sits less than this above the quietest window, the clip has
# no measurable silence and the SNR figure is meaningless - report, never reject.
SNR_MEASURABLE_MARGIN_DB = 6.0


@dataclass
class Quality:
    ok: bool
    snr_db: float
    duration_s: float
    reason: str = ""
    # Diagnostics. Logged on every upload and returned to the caller so real
    # numbers from real devices are visible instead of inferred.
    snr_measurable: bool = True
    speech_db: float = 0.0
    noise_db: float = 0.0
    peak: float = 0.0
    rms: float = 0.0
    clipped_pct: float = 0.0


@dataclass
class DecodeInfo:
    """Everything about the bytes that arrived, before any resampling."""
    path: str = ""              # "libsndfile" | "ffmpeg"
    container: str = ""
    subtype: str = ""
    src_sr: int = 0
    src_channels: int = 0
    n_bytes: int = 0
    sniff: str = ""             # container guessed from magic bytes

    def as_dict(self) -> dict:
        return {"decode_path": self.path, "container": self.container,
                "subtype": self.subtype, "src_sr": self.src_sr,
                "src_channels": self.src_channels, "bytes": self.n_bytes,
                "sniff": self.sniff}


def sniff_container(data: bytes) -> str:
    """Identify the container from magic bytes, for logging and error messages."""
    if data[:4] == b"\x1aE\xdf\xa3":
        return "webm/matroska"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:4] == b"fLaC":
        return "flac"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    if data[4:8] == b"ftyp":
        return f"mp4/{data[8:12].decode('ascii', 'replace')}"
    return f"unknown({data[:4].hex()})"


def decode(data: bytes, info: DecodeInfo | None = None) -> np.ndarray:
    """Any browser audio blob -> 16 kHz mono float32.

    libsndfile 1.2.2 reads wav/flac/mp3/ogg-opus but NOT WebM, which is what
    Chrome's MediaRecorder produces. ffmpeg is the fallback for that.
    """
    info = info if info is not None else DecodeInfo()
    info.n_bytes = len(data)
    info.sniff = sniff_container(data)

    sf_error = None
    try:
        with sf.SoundFile(io.BytesIO(data)) as f:
            info.container, info.subtype = f.format, f.subtype
            info.src_sr, info.src_channels = f.samplerate, f.channels
        wave, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
        if wave.ndim > 1:
            wave = wave.mean(axis=1)
        info.path = "libsndfile"
        if sr == SR:
            return np.ascontiguousarray(wave, dtype=np.float32)
        import librosa
        return np.ascontiguousarray(
            librosa.resample(wave, orig_sr=sr, target_sr=SR), dtype=np.float32)
    except Exception as exc:
        sf_error = exc

    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            f"Cannot decode {info.sniff} ({len(data)} bytes): libsndfile refused it "
            f"({type(sf_error).__name__}: {sf_error}) and ffmpeg is not on PATH. "
            f"libsndfile cannot read WebM at all. Either install ffmpeg or have the "
            f"client send WAV (web/src/lib/recorder.ts does the latter)."
        )
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
         "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
        input=data, capture_output=True,
    )
    if p.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed on {info.sniff}: "
            f"{p.stderr.decode('utf-8', 'replace')[:300]}")
    info.path = "ffmpeg"
    info.container = info.sniff
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def _frame_db(wave: np.ndarray, n: int = 512, hop: int = 256) -> np.ndarray:
    if len(wave) < n:
        return np.array([])
    idx = np.arange(0, len(wave) - n + 1, hop)
    frames = np.stack([wave[i:i + n] for i in idx])
    rms = np.sqrt((frames ** 2).mean(axis=1)) + 1e-12
    return 20 * np.log10(rms)


def measure(wave: np.ndarray) -> dict:
    """Signal statistics. Pure measurement - no policy, no thresholds."""
    dur = len(wave) / SR
    if len(wave) == 0:
        return {"duration_s": 0.0, "peak": 0.0, "rms": 0.0, "clipped_pct": 0.0,
                "speech_db": 0.0, "noise_db": 0.0, "snr_db": 0.0,
                "snr_measurable": False}

    peak = float(np.abs(wave).max())
    rms = float(np.sqrt((wave ** 2).mean()))
    clipped = float((np.abs(wave) >= 0.999).mean() * 100.0)

    db = _frame_db(wave)
    if len(db) < 8:
        return {"duration_s": dur, "peak": peak, "rms": rms,
                "clipped_pct": clipped, "speech_db": 0.0, "noise_db": 0.0,
                "snr_db": 0.0, "snr_measurable": False}

    # Speech level: median of frames within 25 dB of the loudest. Robust to how
    # long the learner recited and to leading/trailing silence.
    top = float(np.percentile(db, 95))
    active = db[db > (top - 25.0)]
    speech_db = float(np.median(active)) if len(active) >= 3 else top

    # Noise floor: quietest contiguous NOISE_WIN_S window. Contiguity matters -
    # a percentile over scattered frames lands on inter-syllable dips, which are
    # speech, not room tone.
    win = max(1, int(NOISE_WIN_S * SR / 256))
    if len(db) >= win:
        kernel = np.ones(win) / win
        smoothed = np.convolve(db, kernel, mode="valid")
        noise_db = float(smoothed.min())
    else:
        noise_db = float(db.min())

    snr = speech_db - noise_db
    return {"duration_s": dur, "peak": peak, "rms": rms, "clipped_pct": clipped,
            "speech_db": speech_db, "noise_db": noise_db, "snr_db": snr,
            "snr_measurable": snr >= SNR_MEASURABLE_MARGIN_DB}


def check_quality(wave: np.ndarray) -> Quality:
    m = measure(wave)
    dur = m["duration_s"]
    common = dict(snr_db=m["snr_db"], duration_s=dur,
                  snr_measurable=m["snr_measurable"], speech_db=m["speech_db"],
                  noise_db=m["noise_db"], peak=m["peak"], rms=m["rms"],
                  clipped_pct=m["clipped_pct"])

    if dur < MIN_DURATION_S:
        return Quality(False, reason="too_short", **common)
    if dur > MAX_DURATION_S:
        return Quality(False, reason="too_long", **common)
    if m["peak"] < 0.005:
        # Essentially nothing arrived: muted mic, wrong input device, or a
        # permission prompt the learner never answered.
        return Quality(False, reason="too_quiet", **common)

    # NOISE IS MEASURED BUT NOT GATED ON. Deliberate, and worth the paragraph:
    #
    # A clip with no silence gives a middling SNR because the quietest window is
    # quiet speech. A genuinely noisy clip WITH silence also gives a middling
    # SNR. Those two cases are not separable from this statistic alone, so any
    # threshold here rejects honest tight recordings at the same rate it catches
    # noisy ones. The old gate resolved that ambiguity by accident and always in
    # the wrong direction - it rejected every browser take.
    #
    # The failure actually worth blocking is the muqatta'at collapse, and that is
    # now detected directly from the model output (see engine/collapse.py) rather
    # than proxied through an audio statistic that does not predict it.
    #
    # snr_db is still computed, logged and returned on every attempt. Re-derive a
    # threshold here only once those logs contain real browser takes with known
    # good/bad labels - not before.
    return Quality(True, **common)
