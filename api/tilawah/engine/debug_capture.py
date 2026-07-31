# -*- coding: utf-8 -*-
"""Measurements for every attempt; audio ONLY when it was actually consented to.

Two separate things live here, and the distinction is the whole point:

  METRICS - duration, peak, RMS, SNR, decode path, predicted phonemes. Logged
  for every attempt, always. Contains no audio and identifies no one.

  AUDIO - the raw upload and the decoded 16 kHz wav. This is someone's voice
  reciting the Quran. It is written only when BOTH are true:
      * the operator enabled collection at all  (TILAWAH_COLLECT_AUDIO=1)
      * that specific learner ticked the audio box (User.audio_consented)
  Either one false means nothing is written. Default for both is off.

  TILAWAH_DEBUG_AUDIO=1 bypasses consent entirely for local debugging. main.py
  refuses to boot with it set unless TILAWAH_ENV=dev, so it cannot reach a box
  real people can talk to.

Files are named with the device id so revoking consent can find and delete them
(see db.delete_user). Deletion that misses the audio is not deletion.
"""
import json
import logging
import re
import time
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf

from ..config import settings

log = logging.getLogger(__name__)

DIR = Path(settings.debug_dir) if settings.debug_dir else (
    Path(__file__).resolve().parent.parent.parent / "debug_audio")

_EXT = {"webm/matroska": "webm", "ogg": "ogg", "wav": "wav", "flac": "flac",
        "mp3": "mp3"}
_SAFE = re.compile(r"[^A-Za-z0-9_-]")


def _ext(sniff: str) -> str:
    for key, ext in _EXT.items():
        if sniff.startswith(key):
            return ext
    return "bin"


def _tag(device_id: str) -> str:
    """Filesystem-safe device id, kept intact enough to delete by."""
    return _SAFE.sub("", device_id or "anon")[:36] or "anon"


def may_store_audio(audio_consented: bool) -> bool:
    if settings.debug_audio:
        return True                      # operator diagnostic mode, dev only
    return bool(settings.collect_audio and audio_consented)


def log_line(tag: str, info: dict, meas: dict, extra: dict | None = None) -> str:
    """One dense human-readable line. This is what you read in the uvicorn log."""
    parts = [
        f"[{tag}]",
        f"{info.get('sniff', '?')}",
        f"{info.get('bytes', 0)}B",
        f"via={info.get('decode_path', '?')}",
        f"src={info.get('src_sr', 0)}Hz/{info.get('src_channels', 0)}ch",
        f"dur={meas.get('duration_s', 0):.2f}s",
        f"peak={meas.get('peak', 0):.4f}",
        f"rms={meas.get('rms', 0):.5f}",
        f"speech={meas.get('speech_db', 0):.1f}dB",
        f"noise={meas.get('noise_db', 0):.1f}dB",
        f"snr={meas.get('snr_db', 0):.1f}dB",
        f"snr_ok={meas.get('snr_measurable', False)}",
        f"clip={meas.get('clipped_pct', 0):.2f}%",
    ]
    for k, v in (extra or {}).items():
        parts.append(f"{k}={v}")
    return " ".join(parts)


def capture(raw: bytes, wave: "np.ndarray | None", sura: int, aya: int,
            info: dict, meas: dict, extra: dict | None = None, *,
            device_id: str = "", audio_consented: bool = False) -> str | None:
    """Log the metrics; persist the audio only if consent allows. Returns the
    file stem when audio was written, else None."""
    log.info(log_line(f"{sura:03d}:{aya:03d}", info, meas, extra))

    if not may_store_audio(audio_consented):
        return None

    try:
        DIR.mkdir(parents=True, exist_ok=True)
        stem = (f"{time.strftime('%Y%m%d-%H%M%S')}-{sura:03d}_{aya:03d}"
                f"-{_tag(device_id)}-{uuid.uuid4().hex[:6]}")
        base = DIR / stem

        (base.with_suffix(f".raw.{_ext(info.get('sniff', ''))}")).write_bytes(raw)
        if wave is not None and len(wave):
            sf.write(base.with_suffix(".16k.wav"), wave, 16000, subtype="PCM_16")
        base.with_suffix(".json").write_text(
            json.dumps({"sura": sura, "aya": aya, "device_id": device_id,
                        "decode": info, "measurements": meas, **(extra or {})},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
        return stem
    except Exception as exc:  # diagnostics must never break the request
        log.warning("audio capture failed: %s", exc)
        return None


def purge_user(device_id: str) -> int:
    """Delete every stored artefact for one device. Called on consent revocation."""
    if not DIR.exists():
        return 0
    tag = _tag(device_id)
    removed = 0
    for path in DIR.glob(f"*-{tag}-*"):
        try:
            path.unlink()
            removed += 1
        except OSError as exc:
            log.warning("could not delete %s: %s", path, exc)
    if removed:
        log.info("purged %d stored audio file(s) for device %s", removed, tag)
    return removed
