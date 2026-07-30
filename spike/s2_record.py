# -*- coding: utf-8 -*-
"""
s2_record.py - guided recorder. Walks you through manifest.csv one clip at a time.

Resumable: already-recorded clips are skipped, so quit whenever you like.

Run:  python s2_record.py
      python s2_record.py --clips-dir clips_aisha     # a second speaker
      python s2_record.py --only 103                  # just surah 103
      python s2_record.py --redo 103_001_t04          # re-record one clip
"""
import argparse
import csv
import os
import queue
import sys

import numpy as np
import sounddevice as sd
import soundfile as sf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SR = 16000  # the model's required sample rate - do not change


def record_until_enter():
    """Capture from the default mic until the user presses Enter."""
    q = queue.Queue()

    def cb(indata, frames, time_info, status):
        if status:
            print(f"   (audio warning: {status})", file=sys.stderr)
        q.put(indata.copy())

    with sd.InputStream(samplerate=SR, channels=1, dtype="float32", callback=cb):
        input()

    chunks = []
    while not q.empty():
        chunks.append(q.get())
    if not chunks:
        return None
    return np.concatenate(chunks, axis=0).reshape(-1)


def describe(audio):
    """Quick quality read so bad takes are caught now, not at scoring time."""
    dur = len(audio) / SR
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    notes = []
    if dur < 0.7:
        notes.append("TOO SHORT - did it capture?")
    if peak > 0.98:
        notes.append("CLIPPING - move back from the mic")
    elif peak < 0.03:
        notes.append("VERY QUIET - move closer or raise mic gain")
    return dur, peak, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips-dir", default="clips")
    ap.add_argument("--manifest", default="manifest.csv")
    ap.add_argument("--only", default=None, help="only this surah number")
    ap.add_argument("--redo", default=None, help="re-record a single clip_id")
    args = ap.parse_args()

    if not os.path.exists(args.manifest):
        raise SystemExit(f"{args.manifest} not found - run:  python s1_manifest.py")

    os.makedirs(args.clips_dir, exist_ok=True)
    with open(args.manifest, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if args.only:
        rows = [r for r in rows if r["sura"] == str(int(args.only))]
    if args.redo:
        rows = [r for r in rows if r["clip_id"] == args.redo]
        if not rows:
            raise SystemExit(f"clip_id {args.redo} not in manifest")
        p = os.path.join(args.clips_dir, args.redo + ".wav")
        if os.path.exists(p):
            os.remove(p)

    todo = [r for r in rows
            if not os.path.exists(os.path.join(args.clips_dir, r["clip_id"] + ".wav"))]

    print("=" * 70)
    print(f"  Saving to: {os.path.abspath(args.clips_dir)}")
    print(f"  {len(rows) - len(todo)} of {len(rows)} already recorded - {len(todo)} to go")
    print("=" * 70)
    print("""
  Keep these constant for every clip:
    - quiet room, same mic, ~25 cm away, slightly off-axis
    - murattal pace (slow and measured), normal recitation voice
    - stop cleanly at the end of the ayah (qalqalah and madd 'aarid
      only appear when you stop)

  ONE error per clip. Everything else correct. Don't exaggerate the
  error - make it the way a real learner would slip.
""")
    if not todo:
        print("  Nothing left to record. Next:  python s3_transcribe.py")
        return
    input("  Press Enter to begin...")

    done = 0
    for i, r in enumerate(todo, 1):
        path = os.path.join(args.clips_dir, r["clip_id"] + ".wav")

        while True:
            print("\n" + "=" * 70)
            print(f"  Clip {i}/{len(todo)}   [{r['clip_id']}]")
            print(f"  {r['nickname']}  ({r['sura']}:{r['aya']})")
            print("=" * 70)
            print(f"\n  {r['uthmani']}\n")
            print(f"  expected phonemes: {r['expected_phonemes']}")
            print()
            if r["has_error"] == "0":
                print("  >>> RECITE CORRECTLY <<<")
                print(f"  {r['instruction']}")
            else:
                print(f"  >>> INDUCE ERROR: {r['error_code']} <<<")
                print(f"  {r['instruction']}")
            print("\n  Press Enter to START recording...", end="")
            input()
            print("  * RECORDING - recite now, then press Enter to STOP...", end="")
            audio = record_until_enter()

            if audio is None or not len(audio):
                print("  Nothing captured. Retrying.")
                continue

            dur, peak, notes = describe(audio)
            print(f"  Captured {dur:.1f}s, peak {peak:.2f}")
            for n in notes:
                print(f"  !! {n}")

            choice = input("  [Enter]=keep  r=redo  s=skip  q=quit : ").strip().lower()
            if choice == "r":
                continue
            if choice == "s":
                print("  Skipped.")
                break
            if choice == "q":
                print(f"\n  Stopped. {done} clips recorded this session.")
                print("  Re-run any time to resume where you left off.")
                return
            sf.write(path, audio, SR, subtype="PCM_16")
            print(f"  Saved {path}")
            done += 1
            break

    print(f"\n  Done - {done} clips recorded this session.")
    remaining = [r for r in rows
                 if not os.path.exists(os.path.join(args.clips_dir, r["clip_id"] + ".wav"))]
    if remaining:
        print(f"  {len(remaining)} still missing (skipped). Re-run to fill them in.")
    else:
        print("  All clips present. Next:  python s3_transcribe.py")


if __name__ == "__main__":
    main()
