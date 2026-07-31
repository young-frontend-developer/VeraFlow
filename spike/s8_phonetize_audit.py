# -*- coding: utf-8 -*-
"""PHASE 0 AUDIT - does the whole Quran survive the phonetizer, and which word
ranges break?

Builds nothing. Writes two JSON reports into spike/step0-results/ :

    audit_ayat.json    one row per ayah, 6236 rows
    audit_ranges.json  one row per (sura, aya, start, window) tried

Run: python s8_phonetize_audit.py
"""
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from quran_transcript import Aya, quran_phonetizer  # noqa: E402
from quran_transcript.utils import PartOfUthmaniWord  # noqa: E402

from tilawah.engine.moshaf import MOSHAF  # noqa: E402

OUT = ROOT / "spike" / "step0-results"
OUT.mkdir(parents=True, exist_ok=True)

# Ayat that are huruf muqatta'at.
MUQATTAAT = {(2, 1), (3, 1), (7, 1), (10, 1), (11, 1), (12, 1), (13, 1), (14, 1),
             (15, 1), (19, 1), (20, 1), (26, 1), (27, 1), (28, 1), (29, 1),
             (30, 1), (31, 1), (32, 1), (36, 1), (38, 1), (40, 1), (41, 1),
             (42, 1), (42, 2), (43, 1), (44, 1), (45, 1), (46, 1), (50, 1),
             (68, 1)}

# The 15 sajdat at-tilawah (Hafs).
SAJDA = {(7, 206), (13, 15), (16, 50), (17, 109), (19, 58), (22, 18), (22, 77),
         (25, 60), (27, 26), (32, 15), (38, 24), (41, 38), (53, 62), (84, 21),
         (96, 19)}


def sweep_ayat() -> list[dict]:
    rows = []
    t0 = time.perf_counter()
    sura = 1
    while True:
        try:
            n_ayat = Aya(sura, 1).get().num_ayat_in_sura
        except Exception:
            break
        for aya in range(1, n_ayat + 1):
            row = {"sura": sura, "aya": aya}
            try:
                a = Aya(sura, aya).get()
                row["n_uthmani_words"] = len(a.uthmani_words)
                row["n_imlaey_words"] = len(a.imlaey_words)
                row["has_bismillah"] = bool(a.bismillah_uthmani)
                row["muqattaat"] = (sura, aya) in MUQATTAAT
                row["sajda"] = (sura, aya) in SAJDA

                out = quran_phonetizer(a.uthmani, MOSHAF, remove_spaces=True)
                row["ok"] = True
                row["n_phonemes"] = len(out.phonemes)
                row["n_sifat"] = len(out.sifat)
            except Exception as exc:
                row["ok"] = False
                row["error"] = type(exc).__name__
                row["message"] = str(exc)[:300]
                row["trace"] = traceback.format_exc()[-500:]
            rows.append(row)
        if sura % 20 == 0:
            print(f"  ...sura {sura} ({len(rows)} ayat, "
                  f"{time.perf_counter() - t0:.0f}s)", flush=True)
        sura += 1
        if sura > 114:
            break
    print(f"  swept {len(rows)} ayat in {time.perf_counter() - t0:.0f}s")
    return rows


def pick_sample(rows: list[dict], n: int = 200) -> list[tuple[int, int]]:
    """Span short / long / muqatta'at / sajda / bismillah deliberately."""
    ok = [r for r in rows if r.get("ok")]
    by_len = sorted(ok, key=lambda r: r["n_imlaey_words"])
    picked: list[tuple[int, int]] = []
    seen = set()

    def add(rs):
        for r in rs:
            key = (r["sura"], r["aya"])
            if key not in seen:
                seen.add(key)
                picked.append(key)

    add([r for r in ok if r["muqattaat"]])
    add([r for r in ok if r["sajda"]])
    add([r for r in ok if r["has_bismillah"]][:25])
    add(by_len[:25])                      # shortest
    add(by_len[-25:])                     # longest
    step = max(1, len(by_len) // (n - len(picked) + 1))
    add(by_len[::step])
    return picked[:n]


def sweep_ranges(sample: list[tuple[int, int]]) -> list[dict]:
    rows = []
    t0 = time.perf_counter()
    for i, (sura, aya) in enumerate(sample):
        a = Aya(sura, aya).get()
        n_words = len(a.imlaey_words)
        for start in range(n_words):
            for window in range(1, n_words - start + 1):
                row = {"sura": sura, "aya": aya, "start": start,
                       "window": window, "n_imlaey_words": n_words}
                try:
                    seg = Aya(sura, aya).get_by_imlaey_words(start, window)
                    row["uthmani"] = seg.uthmani
                    out = quran_phonetizer(seg.uthmani, MOSHAF, remove_spaces=True)
                    row["ok"] = True
                    row["n_phonemes"] = len(out.phonemes)
                except PartOfUthmaniWord as exc:
                    row["ok"] = False
                    row["error"] = "PartOfUthmaniWord"
                    row["message"] = str(exc)[:200]
                except Exception as exc:
                    row["ok"] = False
                    row["error"] = type(exc).__name__
                    row["message"] = str(exc)[:200]
                rows.append(row)
        if (i + 1) % 25 == 0:
            print(f"  ...{i + 1}/{len(sample)} ayat, {len(rows)} ranges, "
                  f"{time.perf_counter() - t0:.0f}s", flush=True)
    print(f"  swept {len(rows)} ranges in {time.perf_counter() - t0:.0f}s")
    return rows


def sweep_bismillah(sample_suras=range(2, 115)) -> list[dict]:
    """Does include_bismillah=True work, or must it be string-concatenated?
    (Concatenating reference texts is the thing that crashed the tokenizer.)"""
    rows = []
    for sura in sample_suras:
        a = Aya(sura, 1).get()
        n = len(a.imlaey_words)
        row = {"sura": sura, "has_bismillah_field": bool(a.bismillah_uthmani)}
        try:
            seg = Aya(sura, 1).get_by_imlaey_words(0, n, include_bismillah=True)
            out = quran_phonetizer(seg.uthmani, MOSHAF, remove_spaces=True)
            row["include_flag_ok"] = True
            row["n_phonemes_with"] = len(out.phonemes)
        except Exception as exc:
            row["include_flag_ok"] = False
            row["include_flag_error"] = f"{type(exc).__name__}: {str(exc)[:150]}"
        # The naive approach, for comparison - this is the known-fragile path.
        try:
            if a.bismillah_uthmani:
                joined = a.bismillah_uthmani + " " + a.uthmani
                out = quran_phonetizer(joined, MOSHAF, remove_spaces=True)
                row["concat_ok"] = True
                row["n_phonemes_concat"] = len(out.phonemes)
        except Exception as exc:
            row["concat_ok"] = False
            row["concat_error"] = f"{type(exc).__name__}: {str(exc)[:150]}"
        rows.append(row)
    return rows


if __name__ == "__main__":
    print("[1/3] sweeping all ayat through quran_phonetizer...")
    ayat = sweep_ayat()
    (OUT / "audit_ayat.json").write_text(
        json.dumps(ayat, ensure_ascii=False), encoding="utf-8")
    bad = [r for r in ayat if not r.get("ok")]
    print(f"      {len(ayat)} ayat, {len(bad)} FAILED")
    if bad:
        print("      error types:", Counter(r["error"] for r in bad).most_common())

    print("\n[2/3] sweeping word ranges on a 200-ayah sample...")
    sample = pick_sample(ayat, 200)
    ranges = sweep_ranges(sample)
    (OUT / "audit_ranges.json").write_text(
        json.dumps(ranges, ensure_ascii=False), encoding="utf-8")
    rbad = [r for r in ranges if not r.get("ok")]
    print(f"      {len(ranges)} ranges, {len(rbad)} FAILED")
    if rbad:
        print("      error types:", Counter(r["error"] for r in rbad).most_common())

    print("\n[3/3] bismillah handling...")
    bism = sweep_bismillah()
    (OUT / "audit_bismillah.json").write_text(
        json.dumps(bism, ensure_ascii=False), encoding="utf-8")
    print(f"      include_bismillah ok: "
          f"{sum(1 for r in bism if r.get('include_flag_ok'))}/{len(bism)}")
    print(f"      naive concat ok:      "
          f"{sum(1 for r in bism if r.get('concat_ok'))}/{len(bism)}")

    print("\ndone -> spike/step0-results/audit_*.json")
