# -*- coding: utf-8 -*-
"""Rank the in-scope registry error types by how much of the catalogue they unlock.

Purpose: Rahmatulloh reviews entries by hand, and review time is the scarce
resource. An entry that is structurally possible in 4000 segments buys far more
coverage than one possible in 30, so this ranks them by reach - weighted toward
where beginners actually start.

"Structurally possible" is derived from the REFERENCE phonetic script, not from
any recording: QALQALAH_MISSING can only fire where a qalqalah letter carries
sukun, MAKHARIJ_SAD_TO_SEEN only where ص occurs, and so on.

WHERE THE PRECONDITIONS LIVE
----------------------------
engine/coverage.py, and nowhere else. This tool used to carry its own copy, and
the copy went stale the moment the preconditions were narrowed: the ranking kept
reporting TAFKHEEM_ADDED, JAHR_LOST, GHUNNA_ADDED and MADD_ADDED at 100.0% and
put them in the top four review slots long after coverage.py had stopped
agreeing. Ranking review effort by numbers the engine no longer computes is
worse than not ranking it, so there is one implementation now.

The four `ahkam` entries are excluded - their detection_signal is marked
TEKSHIRILMAGAN (untested), and ranking something that cannot yet be detected
would put review effort in the wrong place.

Run:  py -3.13 tools/rank_error_frequency.py
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from quran_transcript import Aya, quran_phonetizer  # noqa: E402

from tilawah import content  # noqa: E402
from tilawah.engine.coverage import (UNIVERSAL, in_scope,  # noqa: E402
                                     possible_codes, registry)
from tilawah.engine.moshaf import MOSHAF  # noqa: E402
from tilawah.engine.ranges import Range, reference  # noqa: E402

OUT = ROOT.parent / "spike" / "step0-results" / "error_frequency_ranking.json"

# Where a beginner starts: al-Fatiha and Juz Amma.
BEGINNER_SURAS = {1} | set(range(78, 115))


def codes_for(rng: Range) -> set[str]:
    """Preconditions for one segment, with the word boundaries intact.

    reference() flattens spaces out, but MADD_WAJIB_SHORTENED is defined as a
    madd letter followed by hamza WITHIN A WORD - so the spaced string has to be
    generated too, or muttasil and munfasil become indistinguishable.
    """
    uthmani, flat = reference(rng)
    spaced = quran_phonetizer(uthmani, MOSHAF, remove_spaces=False)
    return possible_codes(flat.phonemes, flat.sifat, spaced.phonemes)


def main() -> int:
    # The registry and the scope rule both come from engine/coverage.py. This
    # tool used to load and filter the JSON itself, which meant it kept ranking
    # v2 after the engine had moved to v3 - the same staleness that had it
    # reporting 100% preconditions long after they were narrowed.
    reg, scoped = registry(), in_scope()
    print(f"{len(scoped)} of {len(reg)} entries in scope "
          f"(high+medium; ahkam/low excluded)\n")

    meta = content.segments_meta()
    if not meta:
        print("segments.json missing - run tools/build_segments.py first")
        return 1

    all_count, beg_count = Counter(), Counter()
    n_all = n_beg = 0
    per_sura_segments = {}
    t0 = time.perf_counter()

    for sura in range(1, 115):
        segs_in_sura = 0
        aya = 1
        while True:
            segs = content.segments_of(sura, aya)
            if not segs:
                break
            segs_in_sura += len(segs)
            for s in segs:
                codes = codes_for(
                    Range(sura, aya, s["start_word"], s["num_words"]))
                codes &= set(scoped)
                n_all += 1
                all_count.update(codes)
                if sura in BEGINNER_SURAS:
                    n_beg += 1
                    beg_count.update(codes)
            aya += 1
        per_sura_segments[sura] = segs_in_sura
        if sura % 10 == 0:
            print(f"  ...sura {sura} ({n_all} segments, "
                  f"{time.perf_counter() - t0:.0f}s)", flush=True)

    rows = []
    for code, entry in scoped.items():
        rows.append({
            "code": code,
            "group": entry["group"],
            "severity": entry["severity"],
            "detection_confidence": entry["detection_confidence"],
            "universal": code in UNIVERSAL,
            "beginner_segments": beg_count.get(code, 0),
            "beginner_pct": round(beg_count.get(code, 0) / max(1, n_beg) * 100, 1),
            "all_segments": all_count.get(code, 0),
            "all_pct": round(all_count.get(code, 0) / max(1, n_all) * 100, 1),
        })
    # Review order: reach among beginners first, then reach overall - but a
    # UNIVERSAL code sorts LAST regardless of reach. Reach is a proxy for "how
    # much does reviewing this unlock", and that proxy breaks exactly where the
    # precondition stops discriminating: MADD_ADDED is possible in 100% of
    # segments, which is why it topped this list, and it is possible in 100% of
    # segments precisely because it distinguishes nothing. coverage() already
    # refuses to score it; ranking it first would send the scarcest resource in
    # the project - Rahmatulloh's review time - to the one entry that cannot
    # improve a single segment's coverage.
    rows.sort(key=lambda r: (r["universal"], -r["beginner_pct"], -r["all_pct"]))
    for i, r in enumerate(rows, 1):
        r["review_order"] = i

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n_segments_total": n_all, "n_segments_beginner": n_beg,
         "beginner_suras": "1 + 78-114",
         "preconditions": "engine/coverage.py (narrowed - see its docstring)",
         "universal_codes": sorted(UNIVERSAL), "ranking": rows,
         "segments_per_sura": per_sura_segments},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n{n_all} segments scanned ({n_beg} in beginner suras) in "
          f"{time.perf_counter() - t0:.0f}s\n")
    print(f"{'#':>3} {'code':<26} {'grp':<9} {'conf':<6} "
          f"{'beginner':>10} {'all':>10}  note")
    print("-" * 82)
    for r in rows:
        note = "UNIVERSAL - cannot improve coverage" if r["universal"] else (
            "~universal, but genuinely so" if r["all_pct"] > 95 else "")
        print(f"{r['review_order']:>3} {r['code']:<26} {r['group']:<9} "
              f"{r['detection_confidence']:<6} "
              f"{r['beginner_pct']:>9.1f}% {r['all_pct']:>9.1f}%  {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
