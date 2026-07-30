# -*- coding: utf-8 -*-
"""
s2b_expert.py - download expert reciter audio as a KNOWN-GOOD control.

The point of the control
------------------------
If your own "correct" takes score a high phoneme distance, there are two very
different explanations and the numbers alone cannot separate them:

  (a) the model is bad / biased against non-Arab learner audio, or
  (b) your recordings or pronunciation are the problem.

Expert recitation settles it. These clips are, by definition, correct, and they
are the exact kind of audio the model was trained on. Run them through the same
s3 -> s4 path as everything else:

  expert scores ~0, your OK takes score high  -> (b), the input is the problem
  expert ALSO scores high                     -> (a) or a pipeline bug, and no
                                                 recording effort will fix it

Several reciters are fetched, not one, so a single odd recording style cannot
masquerade as a verdict.

Audio comes from EveryAyah (per-ayah mp3, 44.1 kHz) and is converted to the
16 kHz mono WAV the rest of the pipeline expects.

Run:  python s2b_expert.py                 # al-Asr 103:1, all reciters
      python s2b_expert.py --sura 112 --aya 1
      python s2b_expert.py --reciters Alafasy_128kbps Husary_128kbps

Then:  python s3_transcribe.py && python s4_score.py

Rows are appended to manifest.csv with error_category "control", which s4
reports separately so the control never contaminates your false-positive rate.
Re-running is safe - existing clips are skipped. NOTE: s1_manifest.py REWRITES
manifest.csv, so if you ever re-run s1, re-run this afterwards to put the
control rows back.
"""
import argparse
import csv
import io
import os
import sys
import urllib.request

import librosa
import numpy as np
import soundfile as sf
from quran_transcript import Aya, MoshafAttributes, quran_phonetizer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SR = 16000
BASE = "https://everyayah.com/data"

# MUST match s1/s3 exactly, or the control is scored against a different target.
MOSHAF = MoshafAttributes(
    rewaya="hafs",
    madd_monfasel_len=4,
    madd_mottasel_len=4,
    madd_mottasel_waqf=4,
    madd_aared_len=4,
)

# Murattal (plain recitation) rather than mujawwad (melodic, heavily extended)
# - mujawwad stretches madd well past the 4-count reference and would score as
# a duration error for reasons that have nothing to do with your recordings.
RECITERS = {
    "alafasy": "Alafasy_128kbps",
    "husary": "Husary_128kbps",
    "minshawy": "Minshawy_Murattal_128kbps",
    "abdulbasit": "Abdul_Basit_Murattal_192kbps",
    "ayyoub": "Muhammad_Ayyoub_128kbps",
}

MANIFEST_FIELDS = ["clip_id", "sura", "aya", "nickname", "uthmani",
                   "expected_phonemes", "error_code", "error_category",
                   "target", "instruction", "has_error"]


def fetch_wav(reciter_dir, sura, aya, timeout=30):
    """Download one ayah and return it as 16 kHz mono float32."""
    url = f"{BASE}/{reciter_dir}/{sura:03d}{aya:03d}.mp3"
    req = urllib.request.Request(url, headers={"User-Agent": "tilawah-spike/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()

    wave, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
    if wave.ndim > 1:
        wave = wave.mean(axis=1)
    if sr != SR:
        wave = librosa.resample(wave, orig_sr=sr, target_sr=SR)
    return np.ascontiguousarray(wave, dtype=np.float32), url


def manifest_row(sura, aya, existing):
    """Reference text for the control.

    Prefer the row s1_manifest.py already wrote for this ayah, so the control is
    scored against a byte-identical reference. Only fall back to recomputing if
    the ayah is not in the manifest at all.
    """
    for r in existing:
        if int(r["sura"]) == sura and int(r["aya"]) == aya:
            return r["nickname"], r["uthmani"], r["expected_phonemes"]
    g = Aya(sura, aya).get()
    ph = quran_phonetizer(g.uthmani, MOSHAF, remove_spaces=True).phonemes
    return f"{sura}:{aya}", g.uthmani, ph


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sura", type=int, default=103)
    ap.add_argument("--aya", type=int, default=1)
    ap.add_argument("--clips-dir", default="clips")
    ap.add_argument("--manifest", default="manifest.csv")
    ap.add_argument("--reciters", nargs="*", default=None,
                    help="EveryAyah directory names; default: all five")
    ap.add_argument("--force", action="store_true",
                    help="re-download clips that already exist")
    args = ap.parse_args()

    if args.reciters:
        chosen = {r.split("_")[0].lower(): r for r in args.reciters}
    else:
        chosen = RECITERS

    os.makedirs(args.clips_dir, exist_ok=True)
    with open(args.manifest, encoding="utf-8-sig") as f:
        existing = list(csv.DictReader(f))
    have = {r["clip_id"] for r in existing}

    nickname, uthmani, expected = manifest_row(args.sura, args.aya, existing)
    print(f"Control for {args.sura}:{args.aya}  ({nickname})")
    print(f"  uthmani : {uthmani}")
    print(f"  expected: {expected}\n")

    new_rows, n_ok = [], 0
    for short, rec_dir in sorted(chosen.items()):
        cid = f"{args.sura:03d}_{args.aya:03d}_ctrl_{short}"
        path = os.path.join(args.clips_dir, cid + ".wav")

        if os.path.exists(path) and not args.force:
            print(f"  {short:12s} already downloaded, skipping")
        else:
            try:
                wave, url = fetch_wav(rec_dir, args.sura, args.aya)
            except Exception as e:
                print(f"  {short:12s} FAILED: {type(e).__name__}: {e}")
                continue
            sf.write(path, wave, SR, subtype="PCM_16")
            rms = float(np.sqrt((wave ** 2).mean()))
            print(f"  {short:12s} {len(wave)/SR:4.2f}s  rms {rms:.4f}  -> {path}")
        n_ok += 1

        if cid not in have:
            new_rows.append({
                "clip_id": cid, "sura": args.sura, "aya": args.aya,
                "nickname": nickname, "uthmani": uthmani,
                "expected_phonemes": expected,
                "error_code": f"CTRL_{short.upper()}",
                "error_category": "control",
                "target": "-",
                "instruction": f"Expert control from EveryAyah ({rec_dir}). Not recorded by you.",
                "has_error": 0,
            })

    if new_rows:
        # Append, never rewrite - the 150-row recording plan stays untouched.
        with open(args.manifest, "a", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=MANIFEST_FIELDS).writerows(new_rows)
        print(f"\nAppended {len(new_rows)} control rows to {args.manifest}")
    else:
        print(f"\n{args.manifest} already has these control rows")

    if not n_ok:
        raise SystemExit("\nNo control audio downloaded. Check your connection.")

    print(f"Control clips ready: {n_ok}")
    print("\nNext:  python s3_transcribe.py   (only the new clips will infer)")
    print("       python s4_score.py")


if __name__ == "__main__":
    main()
