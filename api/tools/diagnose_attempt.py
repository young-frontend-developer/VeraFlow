# -*- coding: utf-8 -*-
"""Where did the errors go? Raw detection -> merged cards -> what was shown.

THE QUESTION THIS ANSWERS. "I made three mistakes and the app showed me one."
That has three completely different causes and they need completely different
fixes:

    raw is 1        the model did not hear two of them   -> DETECTION
    raw 3, merged 1 distinct errors collapsed together   -> MERGE
    merged 3, shown 1  the content gate withheld two     -> REVIEW GATE

Guessing between them wastes days. Every attempt captured with
TILAWAH_DEBUG_AUDIO=1 stores the expected and heard phoneme strings, which is
enough to REPLAY the whole decision chain here - no model, no GPU, no waiting.

    py -3.13 tools/diagnose_attempt.py              the newest capture
    py -3.13 tools/diagnose_attempt.py --all        every capture
    py -3.13 tools/diagnose_attempt.py FILE.json
"""
import argparse
import collections
import glob
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from tilawah.config import settings          # noqa: E402
from tilawah.engine import cards, pipeline    # noqa: E402
from tilawah.engine.runlength import MARKS    # noqa: E402
from tilawah.engine.ranges import Range, n_words, reference  # noqa: E402
from tilawah.engine.typed_errors import typed_diff           # noqa: E402

DEBUG_DIR = Path(__file__).resolve().parents[1] / "debug_audio"


def diagnose(path: Path) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    sura, aya = d.get("sura"), d.get("aya")
    expected, heard = d.get("expected"), d.get("heard")

    print("=" * 78)
    print(f"{path.name}   {sura}:{aya}   outcome={d.get('outcome')}")

    if d.get("outcome") != "ok" or not expected:
        # A rejected recording never reached detection at all, which is its own
        # answer: nothing was lost downstream because nothing got that far.
        print(f"  not analysed — {d.get('reason') or d.get('detail') or '?'}")
        return

    print(f"  expected : {expected}")
    print(f"  heard    : {heard}")
    print(f"  mean_prob: {d.get('mean_prob')}")

    if expected == heard:
        print("\n  RAW 0 — the model heard exactly the reference. Nothing to "
              "merge and nothing to show.")
        return

    raw = typed_diff(expected, heard)
    # Locate and resolve against the real mushaf, exactly as analyze() does.
    uthmani, _ = reference(Range(sura, aya, 0, n_words(sura, aya), False))
    pipeline.locate(raw, uthmani, sura, aya, 0, n_words(sura, aya))

    merged = cards.merge(raw)
    shown, silent = pipeline.present(raw, "uz")

    print()
    print(f"  RAW {len(raw):2d}  ->  MERGED {len(merged):2d}  ->  "
          f"SHOWN {len(shown):2d}   (withheld {len(silent)})")
    print()
    print("  raw errors:")
    for e in sorted(raw, key=lambda e: e.at):
        mark = "  <-- QPS MARK LEAKED" if e.letter in MARKS else ""
        print(f"     at {e.at:3d}  {e.code:26s} letter={e.letter!r} "
              f"word={e.word!r}{mark}")

    print("\n  cards after merge:")
    for g in merged:
        where = ", ".join(sorted({e.word for e in g if e.word}))
        print(f"     {g[0].code:26s} letter={g[0].letter!r}  "
              f"x{len(g):<2d} {where}")

    if silent:
        print("\n  WITHHELD by the content gate:")
        for s in silent:
            print(f"     {s['code']:26s} status={s['status']}")

    # The verdict, stated rather than left to be inferred.
    print("\n  verdict:")
    collapsed = len(raw) - len(merged)
    if collapsed:
        by_key = collections.Counter((e.code, e.letter) for e in raw)
        repeats = {k: n for k, n in by_key.items() if n > 1}
        print(f"     {collapsed} occurrence(s) merged into an existing card, "
              f"all on the same (code, letter): {repeats}")
        print("     That is intended — repeats of ONE mistake are one card.")
    if silent:
        print(f"     {len(silent)} card(s) withheld: unreviewed content and "
              f"env={settings.env}.")
    if not collapsed and not silent:
        print("     Nothing was lost between detection and display. If fewer "
              "mistakes appeared than you made,")
        print("     the model did not hear them — that is a DETECTION "
              "question, not a display one.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="a capture .json (default: newest)")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.file:
        paths = [Path(args.file)]
    else:
        found = sorted(glob.glob(str(DEBUG_DIR / "*.json")),
                       key=os.path.getmtime, reverse=True)
        if not found:
            print(f"No captures in {DEBUG_DIR}.")
            print("Set TILAWAH_DEBUG_AUDIO=1 in api/.env, restart the API, "
                  "and recite once.")
            return 1
        paths = [Path(p) for p in (found if args.all else found[:1])]

    for p in paths:
        diagnose(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
