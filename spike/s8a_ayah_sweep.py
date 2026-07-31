# -*- coding: utf-8 -*-
"""PHASE 0, part 1: every ayah through quran_phonetizer. ~15 min, no network."""
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from quran_transcript import Aya, quran_phonetizer  # noqa: E402
from tilawah.engine.moshaf import MOSHAF  # noqa: E402

OUT = ROOT / "spike" / "step0-results"
OUT.mkdir(parents=True, exist_ok=True)

MUQATTAAT = {(2, 1), (3, 1), (7, 1), (10, 1), (11, 1), (12, 1), (13, 1), (14, 1),
             (15, 1), (19, 1), (20, 1), (26, 1), (27, 1), (28, 1), (29, 1),
             (30, 1), (31, 1), (32, 1), (36, 1), (38, 1), (40, 1), (41, 1),
             (42, 1), (42, 2), (43, 1), (44, 1), (45, 1), (46, 1), (50, 1),
             (68, 1)}
SAJDA = {(7, 206), (13, 15), (16, 50), (17, 109), (19, 58), (22, 18), (22, 77),
         (25, 60), (27, 26), (32, 15), (38, 24), (41, 38), (53, 62), (84, 21),
         (96, 19)}

rows = []
t0 = time.perf_counter()
for sura in range(1, 115):
    n_ayat = Aya(sura, 1).get().num_ayat_in_sura
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
            row["trace"] = traceback.format_exc()[-400:]
        rows.append(row)
    print(f"sura {sura:3d} done  ({len(rows)} ayat, "
          f"{time.perf_counter() - t0:.0f}s)", flush=True)

(OUT / "audit_ayat.json").write_text(json.dumps(rows, ensure_ascii=False),
                                     encoding="utf-8")
bad = [r for r in rows if not r.get("ok")]
print(f"\nDONE: {len(rows)} ayat, {len(bad)} failed, "
      f"{time.perf_counter() - t0:.0f}s total")
