# -*- coding: utf-8 -*-
"""
s3_transcribe.py - run the Muaalem model over every recorded clip.

CLOSE CHROME FIRST. The model is 2.42 GB in float32 and you have 7.7 GB of RAM.

Run:  python s3_transcribe.py
      python s3_transcribe.py --dtype bfloat16     # if you hit MemoryError
      python s3_transcribe.py --clips-dir clips_aisha --out results_aisha.json
      python s3_transcribe.py --limit 3            # smoke test before the full run
      python s3_transcribe.py --refresh            # ignore cache, re-run the model

Writes results.json. First run downloads the model (~2.42 GB, one time).

Every clip's model output is cached to .cache_transcribe/ the moment it is
produced, keyed by a hash of (audio bytes, model, dtype, reference phonemes).
Re-running only infers clips whose cache is missing or stale, and the model is
not even loaded if every clip hits. So reshaping the JSON, fixing a scoring
bug, or adding a field costs seconds, not a re-run.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time

import numpy as np
import soundfile as sf
import torch
from quran_transcript import MoshafAttributes, quran_phonetizer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SR = 16000
MODEL_ID = "obadx/muaalem-model-v3_2"

# MUST match s1_manifest.py exactly, or every clip will look wrong.
MOSHAF = MoshafAttributes(
    rewaya="hafs",
    madd_monfasel_len=4,
    madd_mottasel_len=4,
    madd_mottasel_waqf=4,
    madd_aared_len=4,
)

SIFA_FIELDS = [
    "hams_or_jahr", "shidda_or_rakhawa", "tafkheem_or_taqeeq", "itbaq",
    "safeer", "qalqla", "tikraar", "tafashie", "istitala", "ghonna",
]

# Bump when the on-disk shape of a cached clip changes, so old caches are
# ignored instead of silently feeding s4_score a stale layout.
CACHE_VERSION = "2"


def _seq_to_list(x):
    """torch tensor / numpy array / sequence -> plain list of float or int.

    torch.bfloat16 has no numpy equivalent, so go through torch's own .float()
    rather than np.asarray - otherwise --dtype bfloat16 silently loses probs.
    """
    if x is None:
        return None
    if isinstance(x, torch.Tensor):
        x = x.detach().cpu().reshape(-1)
        return x.float().tolist() if x.is_floating_point() else x.long().tolist()
    return np.asarray(x, dtype=float).reshape(-1).tolist()


def sifa_to_dict(s):
    """Serialize one sifa object to plain types. Handles BOTH schemas.

    Reference side (quran_transcript.SifaOutput): group under `phonemes`, and
    each attribute is already a plain str, e.g. "jahr".

    Predicted side (quran_muaalem.Sifa): group under `phonemes_group`, and each
    attribute is a SingleUnit(text, prob, idx) or None - which is what blew up
    json.dump.

    Both collapse to the same label-string keys so s4_score can compare them
    field by field. The model's per-field confidence is not thrown away; it is
    kept alongside under "probs" / "ids", which s4_score ignores because it
    only ever iterates SIFA_FIELDS.
    """
    group = getattr(s, "phonemes", None)
    if group is None:
        group = getattr(s, "phonemes_group", None)
    d = {"phonemes": group if isinstance(group, str) else _label(group)}

    probs, ids = {}, {}
    for f in SIFA_FIELDS:
        v = getattr(s, f, None)
        if v is None or isinstance(v, str):
            d[f] = v                      # reference side, or absent field
            continue
        d[f] = _label(v)                  # SingleUnit -> "jahr"
        p = getattr(v, "prob", None)
        if p is not None:
            probs[f] = round(float(p), 4)
        i = getattr(v, "idx", None)
        if i is not None:
            ids[f] = int(i)
    if probs:
        d["probs"] = probs
    if ids:
        d["ids"] = ids
    return d


def _label(u):
    """SingleUnit/Unit -> its .text label; str passes through; None stays None."""
    if u is None:
        return None
    if hasattr(u, "text"):
        return u.text
    return str(u)


def extract_phonemes(unit):
    """phonemes may be a Unit object (.text) or already a string."""
    return _label(unit)


def extract_probs(unit):
    vals = _seq_to_list(getattr(unit, "probs", None))
    if not vals:
        return None
    return {"mean": float(sum(vals) / len(vals)), "min": float(min(vals)),
            "values": [round(float(x), 4) for x in vals]}


def _json_fallback(o):
    """Last-resort encoder so a schema change degrades instead of crashing.

    Everything above should already have produced plain types; if the library
    ever returns something new, we still get a usable file plus a loud warning
    rather than losing a completed run at the write step.
    """
    for conv in (_seq_to_list, lambda x: dict(vars(x))):
        try:
            v = conv(o)
            if v is not None:
                print(f"  ! serialized {type(o).__name__} via fallback - check sifa_to_dict")
                return v
        except Exception:
            pass
    print(f"  ! stringified {type(o).__name__} - check sifa_to_dict")
    return str(o)


def write_json(path, payload):
    """Serialize fully, THEN touch the file - a crash can't truncate the old one."""
    text = json.dumps(payload, ensure_ascii=False, indent=1, default=_json_fallback)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def fingerprint(wav_path, ref_phonemes, dtype_name):
    """Identity of one inference. Changes if the audio, model, dtype, reference
    text or output format changes - anything else re-uses the cache."""
    h = hashlib.sha256()
    with open(wav_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    for part in (ref_phonemes, MODEL_ID, dtype_name, CACHE_VERSION):
        h.update(b"\0")
        h.update(str(part).encode("utf-8"))
    return h.hexdigest()[:16]


def cache_load(cache_dir, cid, fp):
    path = os.path.join(cache_dir, f"{cid}.{fp}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None       # corrupt entry - just re-infer


def cache_store(cache_dir, cid, fp, payload):
    os.makedirs(cache_dir, exist_ok=True)
    write_json(os.path.join(cache_dir, f"{cid}.{fp}.json"), payload)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips-dir", default="clips")
    ap.add_argument("--manifest", default="manifest.csv")
    ap.add_argument("--out", default="results.json")
    ap.add_argument("--dtype", default="float32", choices=["float32", "bfloat16"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--cache-dir", default=".cache_transcribe")
    ap.add_argument("--refresh", action="store_true",
                    help="ignore cached transcriptions and re-run the model")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    rows = [r for r in rows
            if os.path.exists(os.path.join(args.clips_dir, r["clip_id"] + ".wav"))]
    if not rows:
        raise SystemExit(f"No clips found in {args.clips_dir}/ - run s2_record.py first")
    if args.limit:
        rows = rows[: args.limit]

    print(f"Clips to process: {len(rows)}")
    print(f"dtype: {args.dtype}   device: cpu")
    print(f"cache: {args.cache_dir}" + ("  (--refresh: ignoring)" if args.refresh else ""))

    # Loaded on first cache miss only - an all-hits run never pays the 2.42 GB.
    holder = {}

    def get_model():
        if "m" not in holder:
            print(f"\nLoading {MODEL_ID} (first run downloads ~2.42 GB)...")
            from quran_muaalem import Muaalem  # late import keeps --help fast

            dtype = torch.float32 if args.dtype == "float32" else torch.bfloat16
            t0 = time.time()
            try:
                holder["m"] = Muaalem(model_name_or_path=MODEL_ID, device="cpu",
                                      dtype=dtype)
            except MemoryError:
                raise SystemExit(
                    "\nOut of memory loading the model.\n"
                    "  1. Close Chrome and every other app, then retry.\n"
                    "  2. Still failing?  python s3_transcribe.py --dtype bfloat16\n"
                    "  3. Last resort: run this on Google Colab's free T4 (needs ~1.5 GB VRAM)."
                )
            print(f"Model loaded in {time.time() - t0:.0f}s\n")
        return holder["m"]

    results, failures = [], []
    n_cached = 0

    for i, r in enumerate(rows, 1):
        cid = r["clip_id"]
        path = os.path.join(args.clips_dir, cid + ".wav")
        try:
            wave, sr = sf.read(path, dtype="float32", always_2d=False)
            if wave.ndim > 1:
                wave = wave.mean(axis=1)
            if sr != SR:
                raise RuntimeError(f"clip is {sr} Hz, expected {SR} - re-record it")

            ref = quran_phonetizer(r["uthmani"], MOSHAF, remove_spaces=True)

            fp = fingerprint(path, ref.phonemes, args.dtype)
            cached = None if args.refresh else cache_load(args.cache_dir, cid, fp)

            if cached is not None:
                pred_ph = cached["predicted_phonemes"]
                pred_sifat = cached["predicted_sifat"]
                probs = cached["probs"]
                elapsed = cached["infer_s"]
                n_cached += 1
                source = "cached"
            else:
                first_infer = "m" not in holder
                muaalem = get_model()

                t1 = time.time()
                outs = muaalem([wave], [ref], sampling_rate=SR)
                elapsed = round(time.time() - t1, 2)
                o = outs[0]

                pred_ph = extract_phonemes(o.phonemes)
                pred_sifat = [sifa_to_dict(s) for s in (getattr(o, "sifat", None) or [])]
                probs = extract_probs(o.phonemes)

                # Written before anything else can fail, so a crash downstream
                # never costs this inference again.
                cache_store(args.cache_dir, cid, fp, {
                    "clip_id": cid, "model": MODEL_ID, "dtype": args.dtype,
                    "predicted_phonemes": pred_ph,
                    "predicted_sifat": pred_sifat,
                    "probs": probs,
                    "infer_s": elapsed,
                })
                source = "        "

                if first_infer:
                    print(f"  First clip OK: {elapsed:.1f}s for {len(wave)/SR:.1f}s of audio")
                    print(f"  Estimated total: ~{elapsed * len(rows) / 60:.0f} min\n")
                    print(f"  expected : {ref.phonemes}")
                    print(f"  predicted: {pred_ph}\n")

            results.append({
                "clip_id": cid,
                "sura": int(r["sura"]), "aya": int(r["aya"]),
                "nickname": r["nickname"],
                "error_code": r["error_code"],
                "error_category": r["error_category"],
                "target": r["target"],
                "has_error": int(r["has_error"]),
                "duration_s": round(len(wave) / SR, 2),
                "infer_s": elapsed,
                "expected_phonemes": ref.phonemes,
                "predicted_phonemes": pred_ph,
                "expected_sifat": [sifa_to_dict(s) for s in ref.sifat],
                "predicted_sifat": pred_sifat,
                "probs": probs,
            })

            flag = "" if pred_ph == ref.phonemes else "  <- differs"
            print(f"  [{i:3d}/{len(rows)}] {cid}  {r['error_code']:16s} "
                  f"{elapsed:5.1f}s {source}{flag}")

        except MemoryError:
            raise SystemExit("\nOut of memory mid-run. Retry with --dtype bfloat16.")
        except Exception as e:
            print(f"  [{i:3d}/{len(rows)}] {cid}  FAILED: {type(e).__name__}: {e}")
            failures.append({"clip_id": cid, "error": f"{type(e).__name__}: {e}"})
            if i == 1:
                print(
                    "\nThe very first clip failed, which usually means the library API\n"
                    "differs from what this script expects. Send me this traceback and\n"
                    "I'll correct the call. Full traceback:\n"
                )
                import traceback
                traceback.print_exc()
                raise SystemExit(1)

    write_json(args.out, {"model": MODEL_ID, "dtype": args.dtype,
                          "clips_dir": args.clips_dir,
                          "results": results, "failures": failures})

    print(f"\nWrote {args.out}: {len(results)} clips ({len(failures)} failed)")
    print(f"Reused from cache: {n_cached}/{len(rows)}"
          f"   (delete {args.cache_dir}/ or pass --refresh to force re-inference)")
    if results:
        avg = sum(x["infer_s"] for x in results) / len(results)
        print(f"Average inference: {avg:.1f}s per clip")
    print("\nNext:  python s4_score.py")


if __name__ == "__main__":
    main()
