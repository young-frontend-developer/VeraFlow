# -*- coding: utf-8 -*-
"""PHASE 0, part 3+4: calibrate phonemes -> seconds, and test Bismillah handling.

QPS encodes duration by repeating characters (madd letters repeat, ghunnah
repeats), so phoneme-string LENGTH should be close to linear in recitation time.
This measures that against real reciters instead of assuming it - the estimate
drives whether a segment fits under MAX_DURATION_S, so a wrong constant means
either rejecting valid recitations or accepting ones that time out.
"""
import io
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from quran_transcript import Aya, quran_phonetizer  # noqa: E402
from tilawah.engine.moshaf import MOSHAF  # noqa: E402

OUT = ROOT / "spike" / "step0-results"
CACHE = ROOT / "spike" / ".cache_mp3"
CACHE.mkdir(parents=True, exist_ok=True)

RECITERS = {
    "Husary": "Husary_128kbps",
    "Alafasy": "Alafasy_128kbps",
}


def fetch(reciter_dir: str, sura: int, aya: int) -> bytes | None:
    name = f"{sura:03d}{aya:03d}.mp3"
    path = CACHE / f"{reciter_dir}_{name}"
    if path.exists():
        return path.read_bytes()
    url = f"https://everyayah.com/data/{reciter_dir}/{name}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read()
        path.write_bytes(data)
        return data
    except Exception as exc:
        print(f"  fetch failed {url}: {exc}")
        return None


def duration_of(data: bytes) -> float | None:
    try:
        w, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
        if w.ndim > 1:
            w = w.mean(axis=1)
        # everyayah files carry a little head/tail padding; trim it so we measure
        # recitation, not the encoder's silence.
        n = 512
        m = len(w) // n * n
        if m < n:
            return len(w) / sr
        e = np.sqrt((w[:m].reshape(-1, n) ** 2).mean(axis=1))
        live = np.where(e > e.max() * 0.02)[0]
        if len(live) == 0:
            return len(w) / sr
        return float((live[-1] + 1 - live[0]) * n / sr)
    except Exception as exc:
        print(f"  decode failed: {exc}")
        return None


def pick_targets(n=30) -> list[tuple[int, int]]:
    """Spread across the phoneme-count distribution using the part-1 audit."""
    rows = json.loads((OUT / "audit_ayat.json").read_text(encoding="utf-8"))
    ok = sorted([r for r in rows if r.get("ok")], key=lambda r: r["n_phonemes"])
    step = len(ok) // n
    return [(r["sura"], r["aya"]) for r in ok[::step]][:n]


def calibrate():
    targets = pick_targets(30)
    rows = []
    print(f"calibrating on {len(targets)} ayat x {len(RECITERS)} reciters")
    for sura, aya in targets:
        try:
            uth = Aya(sura, aya).get().uthmani
            n_ph = len(quran_phonetizer(uth, MOSHAF, remove_spaces=True).phonemes)
        except Exception as exc:
            print(f"  {sura}:{aya} phonetize failed: {exc}")
            continue
        for label, d in RECITERS.items():
            data = fetch(d, sura, aya)
            if not data:
                continue
            dur = duration_of(data)
            if dur:
                rows.append({"sura": sura, "aya": aya, "reciter": label,
                             "n_phonemes": n_ph, "duration_s": round(dur, 2)})
        print(f"  {sura:3d}:{aya:<4} phonemes={n_ph:5d}  "
              + "  ".join(f"{r['reciter']}={r['duration_s']}s"
                          for r in rows if r["sura"] == sura and r["aya"] == aya),
              flush=True)
    return rows


def fit(rows):
    x = np.array([r["n_phonemes"] for r in rows], dtype=float)
    y = np.array([r["duration_s"] for r in rows], dtype=float)
    # through the origin: zero phonemes is zero seconds
    k = float((x * y).sum() / (x * x).sum())
    pred = k * x
    resid = y - pred
    print(f"\nseconds = {k:.4f} x n_phonemes")
    print(f"  n={len(rows)}  R^2={1 - (resid ** 2).sum() / ((y - y.mean()) ** 2).sum():.4f}")
    print(f"  mean abs error {np.abs(resid).mean():.2f}s   max {np.abs(resid).max():.2f}s")
    print(f"  ratio spread: p05={np.percentile(y / x, 5):.4f} "
          f"p50={np.percentile(y / x, 50):.4f} p95={np.percentile(y / x, 95):.4f}")
    return k


def bismillah_check():
    print(f"\n{'=' * 64}\nBISMILLAH HANDLING\n{'=' * 64}")
    results = {"flag_ok": 0, "flag_fail": 0, "concat_ok": 0, "concat_fail": 0,
               "failures": []}
    for sura in range(1, 115):
        a = Aya(sura, 1).get()
        n = len(a.imlaey_words)
        try:
            seg = Aya(sura, 1).get_by_imlaey_words(0, n, include_bismillah=True)
            quran_phonetizer(seg.uthmani, MOSHAF, remove_spaces=True)
            results["flag_ok"] += 1
        except Exception as exc:
            results["flag_fail"] += 1
            results["failures"].append(
                {"sura": sura, "mode": "include_bismillah",
                 "error": f"{type(exc).__name__}: {str(exc)[:120]}"})
        if a.bismillah_uthmani:
            try:
                joined = a.bismillah_uthmani + " " + a.uthmani
                quran_phonetizer(joined, MOSHAF, remove_spaces=True)
                results["concat_ok"] += 1
            except Exception as exc:
                results["concat_fail"] += 1
                results["failures"].append(
                    {"sura": sura, "mode": "concat",
                     "error": f"{type(exc).__name__}: {str(exc)[:120]}"})
    print(f"include_bismillah=True : {results['flag_ok']} ok, "
          f"{results['flag_fail']} failed")
    print(f"naive string concat    : {results['concat_ok']} ok, "
          f"{results['concat_fail']} failed")
    for f in results["failures"][:8]:
        print("  ", f)
    return results


if __name__ == "__main__":
    rows = calibrate()
    (OUT / "audit_durations.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    k = fit(rows) if rows else None

    bism = bismillah_check()
    (OUT / "audit_bismillah.json").write_text(
        json.dumps(bism, ensure_ascii=False, indent=1), encoding="utf-8")

    if k:
        full = json.loads((OUT / "audit_ayat.json").read_text(encoding="utf-8"))
        ok = [r for r in full if r.get("ok")]
        secs = np.array([k * r["n_phonemes"] for r in ok])
        print(f"\n{'=' * 64}\nESTIMATED DURATION OF ALL {len(ok)} AYAT\n{'=' * 64}")
        for cap in (10, 15, 20, 25, 30, 40, 60):
            over = int((secs > cap).sum())
            print(f"  > {cap:3d}s : {over:5d} ayat ({over / len(ok) * 100:5.2f}%)")
        for p in (50, 75, 90, 95, 99, 100):
            print(f"  p{p:<3d}  : {np.percentile(secs, p):6.1f}s")
