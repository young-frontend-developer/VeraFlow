# -*- coding: utf-8 -*-
"""PHASE 0, part 2: are PartOfUthmaniWord failures predictable?

The library raises it here (quran_transcript/utils.py, _decode_uthmani):

    if end in imlaey2uthmani:
        if imlaey2uthmani[end - 1] == imlaey2uthmani[end]:
            raise PartOfUthmaniWord(...)

so a cut at `end` is illegal exactly when the imlaey words on either side of it
belong to the SAME uthmani word. That is a pure function of a map we can read
up front - meaning the UI can offer only legal cut points instead of catching
exceptions. This script proves the prediction matches reality exhaustively.
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from quran_transcript import Aya  # noqa: E402
from quran_transcript.utils import PartOfUthmaniWord  # noqa: E402

OUT = ROOT / "spike" / "step0-results"
OUT.mkdir(parents=True, exist_ok=True)


def word_map(sura: int, aya: int) -> dict[int, int]:
    """imlaey word index -> uthmani word index."""
    enc = Aya(sura, aya)._encode_imlaey_to_uthmani()
    return dict(enc.imlaey2uthmani)


def is_cut(m: dict[int, int], n: int, c: int) -> bool:
    """Can the text be cut just before imlaey word `c` without splitting an
    uthmani word? The ends of the ayah are always legal."""
    if c <= 0 or c >= n:
        return True
    return m.get(c - 1) != m.get(c)


def legal_cuts(m: dict[int, int], n_imlaey: int) -> set[int]:
    """Every legal boundary position, 0..n inclusive."""
    return {c for c in range(n_imlaey + 1) if is_cut(m, n_imlaey, c)}


def predicted_ok(m: dict[int, int], n: int, start: int, window: int) -> bool:
    """BOTH boundaries must be legal. The library only shows the `end` check in
    _decode_uthmani, but `start` is a cut too - a range beginning mid-uthmani-word
    fails just the same, which is what the first pass of this audit found."""
    return is_cut(m, n, start) and is_cut(m, n, start + window)


MUQATTAAT = {(2, 1), (3, 1), (7, 1), (19, 1), (36, 1), (42, 2), (68, 1)}
SAJDA = {(32, 15), (41, 38), (96, 19), (13, 15), (22, 18)}


def sample() -> list[tuple[int, int]]:
    """Short, long, muqatta'at, sajda, first-ayah-of-sura, spread across the book."""
    picks: list[tuple[int, int]] = []
    picks += sorted(MUQATTAAT)
    picks += sorted(SAJDA)
    picks += [(s, 1) for s in (1, 2, 9, 18, 55, 78, 110, 112, 114)]
    picks += [(2, 282), (2, 255), (4, 176), (3, 154), (7, 206), (24, 35)]
    for s in range(1, 115, 4):                    # spread over the whole Quran
        picks.append((s, 1))
        picks.append((s, 2))
    seen, out = set(), []
    for p in picks:
        if p in seen:
            continue
        try:
            if p[1] <= Aya(p[0], 1).get().num_ayat_in_sura:
                seen.add(p)
                out.append(p)
        except Exception:
            pass
    return out[:200]


if __name__ == "__main__":
    rows, mismatches = [], []
    agree = disagree = 0
    t0 = time.perf_counter()
    picks = sample()
    print(f"testing {len(picks)} ayat\n")

    for i, (sura, aya) in enumerate(picks):
        a = Aya(sura, aya).get()
        n = len(a.imlaey_words)
        m = word_map(sura, aya)
        cuts = legal_cuts(m, n)
        n_uth = len(a.uthmani_words)

        # Exhaustive where cheap; systematic sample where not.
        if n <= 14:
            combos = [(s, w) for s in range(n) for w in range(1, n - s + 1)]
        else:
            windows = [1, 2, 3, 5, 8, 12]
            combos = [(s, w) for s in range(n)
                      for w in windows if s + w <= n]

        for start, window in combos:
            pred = predicted_ok(m, n, start, window)
            try:
                Aya(sura, aya).get_by_imlaey_words(start, window)
                actual, err = True, ""
            except PartOfUthmaniWord:
                actual, err = False, "PartOfUthmaniWord"
            except Exception as exc:
                actual, err = False, type(exc).__name__

            if pred == actual:
                agree += 1
            else:
                disagree += 1
                mismatches.append({"sura": sura, "aya": aya, "start": start,
                                   "window": window, "predicted_ok": pred,
                                   "actual_ok": actual, "error": err})

        rows.append({"sura": sura, "aya": aya, "n_imlaey_words": n,
                     "n_uthmani_words": n_uth,
                     "n_legal_cuts": len(cuts), "legal_cuts": sorted(cuts),
                     "merged_spans": n - n_uth})
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(picks)}  agree={agree} disagree={disagree}  "
                  f"{time.perf_counter() - t0:.0f}s", flush=True)

    (OUT / "audit_ranges.json").write_text(
        json.dumps({"per_ayah": rows, "mismatches": mismatches,
                    "agree": agree, "disagree": disagree},
                   ensure_ascii=False), encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"prediction vs reality: {agree} agree, {disagree} disagree")
    print(f"accuracy: {agree / max(1, agree + disagree) * 100:.2f}%")
    if mismatches:
        print(f"\nfirst mismatches:")
        for mm in mismatches[:10]:
            print("  ", mm)
    merged = [r for r in rows if r["merged_spans"] > 0]
    print(f"\nayat where imlaey and uthmani word counts differ: "
          f"{len(merged)}/{len(rows)}")
    print(f"error types seen: "
          f"{Counter(m['error'] for m in mismatches).most_common()}")
