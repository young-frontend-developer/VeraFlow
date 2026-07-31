# -*- coding: utf-8 -*-
"""Rank the 34 registry error types by how much of the catalogue they unlock.

Purpose: Rahmatulloh reviews entries by hand, and review time is the scarce
resource. An entry that is structurally possible in 4000 segments buys far more
coverage than one possible in 30, so this ranks them by reach - weighted toward
where beginners actually start.

"Structurally possible" is derived from the REFERENCE phonetic script, not from
any recording: QALQALAH_MISSING can only fire where a qalqalah letter carries
sukun, MAKHARIJ_SAD_TO_SEEN only where ص occurs, and so on. That is the same
computation Phase 2 will bake into the segment artifact; this is its first use.

The four `ahkam` entries are excluded - their detection_signal is marked
TEKSHIRILMAGAN (untested), and ranking something that cannot yet be detected
would put review effort in the wrong place.

Run:  python tools/rank_error_frequency.py
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tilawah import content  # noqa: E402
from tilawah.engine.ranges import Range, reference  # noqa: E402

REGISTRY = ROOT.parent / "tajweed_error_registry_v2.json"
OUT = ROOT.parent / "spike" / "step0-results" / "error_frequency_ranking.json"

# Where a beginner starts: al-Fatiha and Juz Amma.
BEGINNER_SURAS = {1} | set(range(78, 115))

# Letters whose presence makes a substitution error possible, per signal.
SUBSTITUTION_SOURCE = {
    "MAKHARIJ_AIN_TO_HAMZA": "ع", "MAKHARIJ_AIN_TO_HHA": "ع",
    "MAKHARIJ_HAMZA_TO_AIN": "ء", "MAKHARIJ_HA_TO_HHA": "ه",
    "MAKHARIJ_KHA_TO_HHA": "خ", "MAKHARIJ_GHAYN_TO_QAF": "غ",
    "MAKHARIJ_QAF_TO_KAF": "ق", "MAKHARIJ_THA_TO_SEEN": "ث",
    "MAKHARIJ_THAL_TO_ZAY": "ذ", "MAKHARIJ_ZAA_TO_ZAY": "ظ",
    "MAKHARIJ_SAD_TO_SEEN": "ص", "MAKHARIJ_TAA_TO_TA": "ط",
    "MAKHARIJ_DAD_TO_DAL": "ض", "MAKHARIJ_DAD_TO_ZAA": "ض",
}


def sifa_values(sifat, field):
    for s in sifat:
        v = getattr(s, field, None)
        yield getattr(v, "text", v)


def possible_codes(phonemes: str, sifat) -> set[str]:
    """Which error types could fire on this reference at all."""
    found = set()

    for code, letter in SUBSTITUTION_SOURCE.items():
        if letter in phonemes:
            found.add(code)

    tafkheem = set(sifa_values(sifat, "tafkheem_or_taqeeq"))
    if "mofakham" in tafkheem:
        found.add("TAFKHEEM_LOST")
    if "moraqaq" in tafkheem:
        found.add("TAFKHEEM_ADDED")
    # Raa-specific: needs the letter AND the relevant expected sifa.
    for s in sifat:
        group = getattr(s, "phonemes", None) or getattr(s, "phonemes_group", None)
        text = group if isinstance(group, str) else getattr(group, "text", "")
        if "ر" not in (text or ""):
            continue
        val = getattr(s, "tafkheem_or_taqeeq", None)
        val = getattr(val, "text", val)
        if val == "mofakham":
            found.add("RAA_TAFKHEEM_MISSING")
        elif val == "moraqaq":
            found.add("RAA_TARQIQ_MISSING")

    if "moqalqal" in set(sifa_values(sifat, "qalqla")):
        found.update({"QALQALAH_MISSING", "QALQALAH_EXCESSIVE"})

    hams = set(sifa_values(sifat, "hams_or_jahr"))
    if "hams" in hams:
        found.add("HAMS_LOST")
    if "jahr" in hams:
        found.add("JAHR_LOST")
    if "shadeed" in set(sifa_values(sifat, "shidda_or_rakhawa")):
        found.add("SHIDDA_LOST")

    ghonna = set(sifa_values(sifat, "ghonna"))
    if "maghnoon" in ghonna:
        found.update({"GHUNNA_MISSING", "GHUNNA_TOO_SHORT"})
    if "not_maghnoon" in ghonna:
        found.add("GHUNNA_ADDED")

    # QPS repeats a character to encode length, so a run of >=2 identical
    # vowel marks is a madd.
    has_madd = any(phonemes[i] == phonemes[i + 1] for i in range(len(phonemes) - 1))
    if has_madd:
        found.update({"MADD_TOO_SHORT", "MADD_TOO_LONG"})
        # madd muttasil: a madd immediately followed by hamza.
        for i in range(len(phonemes) - 2):
            if phonemes[i] == phonemes[i + 1] and phonemes[i + 2] == "ء":
                found.add("MADD_WAJIB_SHORTENED")
                break
    found.add("MADD_ADDED")    # lengthening can be added anywhere

    return found


def main() -> int:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))["errors"]
    in_scope = {k: v for k, v in reg.items()
                if v.get("detection_confidence") in ("high", "medium")}
    print(f"{len(in_scope)} of {len(reg)} entries in scope "
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
                _, out = reference(Range(sura, aya, s["start_word"], s["num_words"]))
                codes = possible_codes(out.phonemes, out.sifat) & set(in_scope)
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
    for code, entry in in_scope.items():
        rows.append({
            "code": code,
            "group": entry["group"],
            "severity": entry["severity"],
            "detection_confidence": entry["detection_confidence"],
            "beginner_segments": beg_count.get(code, 0),
            "beginner_pct": round(beg_count.get(code, 0) / max(1, n_beg) * 100, 1),
            "all_segments": all_count.get(code, 0),
            "all_pct": round(all_count.get(code, 0) / max(1, n_all) * 100, 1),
        })
    # Review order: reach among beginners first, then reach overall.
    rows.sort(key=lambda r: (-r["beginner_pct"], -r["all_pct"]))
    for i, r in enumerate(rows, 1):
        r["review_order"] = i

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n_segments_total": n_all, "n_segments_beginner": n_beg,
         "beginner_suras": "1 + 78-114", "ranking": rows,
         "segments_per_sura": per_sura_segments},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n{n_all} segments scanned ({n_beg} in beginner suras) in "
          f"{time.perf_counter() - t0:.0f}s\n")
    print(f"{'#':>3} {'code':<26} {'grp':<9} {'conf':<6} "
          f"{'beginner':>10} {'all':>10}")
    print("-" * 72)
    for r in rows:
        print(f"{r['review_order']:>3} {r['code']:<26} {r['group']:<9} "
              f"{r['detection_confidence']:<6} "
              f"{r['beginner_pct']:>9.1f}% {r['all_pct']:>9.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
