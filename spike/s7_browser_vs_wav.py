# -*- coding: utf-8 -*-
"""Run a browser recording and a spike .wav through the SAME pipeline, stage by
stage, and print where they diverge.

    python s7_browser_vs_wav.py                       # synthetic browser shape
    python s7_browser_vs_wav.py path/to/recording.wav # a real browser upload
                                                      # (api/debug_audio/*.raw.wav)

Every stage prints the numbers it computed, so a divergence is attributable to a
stage rather than guessed at.
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from tilawah.engine.audio import DecodeInfo, check_quality, decode  # noqa: E402
from tilawah.engine.collapse import looks_collapsed  # noqa: E402
from tilawah import content  # noqa: E402
from tilawah.engine.target import _phonetized, target_for  # noqa: E402
from tilawah.engine.typed_errors import typed_diff  # noqa: E402

SR = 16000
SURA, AYA = 103, 1
REF = ROOT / "spike" / "clips" / "103_001_t01.wav"


def as_browser_wav(path: Path) -> bytes:
    """Re-shape a clip into exactly what web/src/lib/recorder.ts now uploads:
    16 kHz mono PCM-16 WAV, with ~300 ms of room tone banked in front."""
    w, sr = sf.read(path, dtype="float32", always_2d=False)
    if w.ndim > 1:
        w = w.mean(axis=1)
    if sr != SR:
        import librosa
        w = librosa.resample(w, orig_sr=sr, target_sr=SR)
    # Lead-in taken from the clip's own quietest frame, so the noise floor is
    # this room's, not an invented one.
    n = 512
    frames = w[: len(w) // n * n].reshape(-1, n)
    tone = frames[int(np.argmin(np.sqrt((frames ** 2).mean(axis=1))))]
    lead = np.tile(tone, int(0.30 * SR / n) + 1)[: int(0.30 * SR)]
    import io
    buf = io.BytesIO()
    sf.write(buf, np.concatenate([lead, w]), SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def stage_report(label: str, raw: bytes) -> dict:
    print(f"\n{'=' * 74}\n{label}\n{'=' * 74}")
    out = {}

    # 1. decode -------------------------------------------------------------
    info = DecodeInfo()
    try:
        wave = decode(raw, info)
    except Exception as exc:
        print(f"  1 decode          FAILED: {exc}")
        return {"failed": "decode"}
    d = info.as_dict()
    print(f"  1 decode          {d['sniff']} {d['bytes']}B via {d['decode_path']}"
          f"  src={d['src_sr']}Hz/{d['src_channels']}ch"
          f" -> {SR}Hz/1ch  {len(wave)} samples")
    out["decode"] = d

    # 2. quality gate -------------------------------------------------------
    q = check_quality(wave)
    print(f"  2 quality         dur={q.duration_s:.2f}s peak={q.peak:.4f} "
          f"rms={q.rms:.5f} clip={q.clipped_pct:.2f}%")
    print(f"                    speech={q.speech_db:.1f}dB noise={q.noise_db:.1f}dB "
          f"snr={q.snr_db:.1f}dB measurable={q.snr_measurable}")
    print(f"                    -> {'PASS' if q.ok else 'REJECT: ' + q.reason}")
    out["quality"] = q
    if not q.ok:
        return out

    # 3. transcribe ---------------------------------------------------------
    from tilawah.engine.model import transcribe
    target = target_for(SURA, AYA)
    pred = transcribe(wave, _phonetized(SURA, AYA))
    print(f"  3 transcribe      expected  {target.phonemes}")
    print(f"                    heard     {pred.phonemes}")
    print(f"                    mean_prob {pred.mean_prob:.4f}")
    out["expected"], out["heard"] = target.phonemes, pred.phonemes

    # 4. collapse check -----------------------------------------------------
    collapsed, detail = looks_collapsed(pred.phonemes, SURA, AYA, target.phonemes)
    print(f"  4 collapse        {'COLLAPSED' if collapsed else 'ok'}  ({detail})")
    out["collapsed"] = collapsed
    if collapsed:
        return out

    # 5. typed errors -------------------------------------------------------
    raw_errs = typed_diff(target.phonemes, pred.phonemes)
    print(f"  5 typed errors    {len(raw_errs)} detected: "
          f"{[e.code for e in raw_errs] or '(none)'}")
    out["errors"] = [e.code for e in raw_errs]

    # 6. content gate -------------------------------------------------------
    shown, silent = [], []
    for e in raw_errs:
        body = content.render(e.code, "uz", e.dict())
        st = content.status_of(e.code)
        (shown if (st != "collect" and body and body.get("reviewed")) else silent
         ).append(e.code)
    print(f"  6 content gate    shown={shown or '(none)'}  suppressed={silent or '(none)'}")
    verdict = ("ALL CLEAR" if not raw_errs
               else f"CORRECTION: {shown}" if shown
               else "'could not fully assess' (all suppressed as unreviewed)")
    print(f"  7 learner sees    {verdict}")
    out["shown"], out["silent"] = shown, silent
    return out


if __name__ == "__main__":
    print(f"reference clip : {REF.name}")
    results = {}
    results["wav"] = stage_report(
        f"A. {REF.name} -- exactly as the spike feeds it", REF.read_bytes())
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        results["browser"] = stage_report(f"B. REAL browser upload: {p.name}",
                                          p.read_bytes())
    else:
        results["browser"] = stage_report(
            "B. same audio in browser upload shape (16k mono PCM-16 + 300ms lead-in)",
            as_browser_wav(REF))

    a, b = results["wav"], results["browser"]
    print(f"\n{'=' * 74}\nDIVERGENCE\n{'=' * 74}")
    for stage, key in [("decode", "decode"), ("gate pass", "quality"),
                       ("heard phonemes", "heard"), ("collapse", "collapsed"),
                       ("typed errors", "errors"), ("shown to learner", "shown")]:
        va, vb = a.get(key), b.get(key)
        if key == "quality":
            va = None if va is None else (va.ok, va.reason)
            vb = None if vb is None else (vb.ok, vb.reason)
        if key == "decode":
            va = None if va is None else f"{va['sniff']} via {va['decode_path']}"
            vb = None if vb is None else f"{vb['sniff']} via {vb['decode_path']}"
        same = "same" if va == vb else "DIFFERS"
        print(f"  {stage:<18} {same:<8} wav={va}  browser={vb}")
