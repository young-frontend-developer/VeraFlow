# -*- coding: utf-8 -*-
"""Measure what every precondition actually restricts, loose vs tightened.

A precondition true in 100% of segments is not a check, it is a decoration: it
inflates coverage uniformly and licenses a detector to fire in contexts nobody
validated. This prints both versions side by side so the narrowing is evidence
rather than assertion - and names the ones that could not be narrowed.

Run:  python tools/audit_preconditions.py [n_suras]
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

V2_PATH = ROOT.parent / "tajweed_error_registry_v2.json"

from quran_transcript import Aya, quran_phonetizer  # noqa: E402

from tilawah import content  # noqa: E402
from tilawah.engine.coverage import (HARAKAT, MADD_LETTERS, THROAT, UNIVERSAL,
                                     _has_run, _sifa_groups, in_scope,
                                     possible_codes)
from tilawah.engine.moshaf import MOSHAF  # noqa: E402
from tilawah.engine.ranges import Range  # noqa: E402


def loose_codes(phonemes: str, sifat) -> set[str]:
    """The ORIGINAL preconditions, before tightening - for comparison only."""
    groups = _sifa_groups(sifat)
    found = set()
    from tilawah.engine.coverage import SUBSTITUTION_SOURCE
    for code, letters in SUBSTITUTION_SOURCE.items():
        # `letters` may be a PAIR now (وف, ذظ) - a plain `in` would be a
        # substring test and would silently match almost nothing, which showed
        # up as a nonsensical "narrowing" from 1.0% to 78.2%.
        if any(ch in phonemes for ch in letters):
            found.add(code)
    tafkheem = [f["tafkheem_or_taqeeq"] for _, f in groups]
    if "mofakham" in tafkheem:
        found.add("TAFKHEEM_LOST")
    if "moraqaq" in tafkheem:
        found.add("TAFKHEEM_ADDED")            # loose: any light letter
    for text, f in groups:
        if "ر" in text:
            if f["tafkheem_or_taqeeq"] == "mofakham":
                found.add("RAA_TAFKHEEM_MISSING")
            elif f["tafkheem_or_taqeeq"] == "moraqaq":
                found.add("RAA_TARQIQ_MISSING")
    if any(f["qalqla"] == "moqalqal" for _, f in groups):
        found.update({"QALQALAH_MISSING", "QALQALAH_EXCESSIVE"})
    # The loose HAMS_LOST / JAHR_LOST / SHIDDA_LOST stand-ins were here. Their
    # codes were deleted from the registry on 2026-08-07 as a scope decision, so
    # in_scope() would filter them out of this comparison anyway and the rows
    # would print as empty. The narrowings they measured are recorded in
    # engine/coverage.py's docstring, which is where the evidence belongs.
    if any(f["ghonna"] == "maghnoon" for _, f in groups):
        found.update({"GHUNNA_MISSING", "GHUNNA_TOO_SHORT"})
    if any(f["ghonna"] == "not_maghnoon" for _, f in groups):
        found.add("GHUNNA_ADDED")              # loose: any non-nasal phoneme
    if _has_run(phonemes, MADD_LETTERS | HARAKAT):
        found.update({"MADD_TOO_SHORT", "MADD_TOO_LONG"})
        for i in range(len(phonemes) - 2):
            if phonemes[i] == phonemes[i + 1] and phonemes[i + 2] == "ء":
                found.add("MADD_WAJIB_SHORTENED")
                break
    found.add("MADD_ADDED")
    return found & set(in_scope())


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 114
    loose, tight = Counter(), Counter()
    n = 0
    for sura in range(1, limit + 1):
        aya = 1
        while True:
            segs = content.segments_of(sura, aya)
            if not segs:
                break
            for s in segs:
                seg_range = Range(sura, aya, s["start_word"], s["num_words"])
                uth = Aya(sura, aya).get_by_imlaey_words(
                    s["start_word"], s["num_words"]).uthmani
                flat = quran_phonetizer(uth, MOSHAF, remove_spaces=True)
                spaced = quran_phonetizer(uth, MOSHAF, remove_spaces=False)
                loose.update(loose_codes(flat.phonemes, flat.sifat))
                tight.update(possible_codes(flat.phonemes, flat.sifat,
                                            spaced.phonemes))
                n += 1
            aya += 1
        if sura % 10 == 0:
            print(f"  ...sura {sura} ({n} segments)", flush=True)

    print(f"\n{n} segments\n")
    print(f"{'code':<30} {'loose':>8} {'tight':>8} {'change':>9}  note")
    print("-" * 82)
    # Entries introduced by the v3 patch have no v2 precondition to compare
    # against, so a "change" column for them would be measuring this tool's own
    # loose stand-in, not a real narrowing.
    v2_codes = set(json.loads(V2_PATH.read_text(encoding="utf-8"))["errors"]) \
        if V2_PATH.exists() else set(in_scope())

    rows = sorted(in_scope(), key=lambda c: -tight.get(c, 0))
    for code in rows:
        lo = loose.get(code, 0) / n * 100
        ti = tight.get(code, 0) / n * 100
        if code not in v2_codes:
            print(f"{code:<30} {'-':>7}  {ti:7.1f}% {'-':>9}  NEW in v3")
            continue
        note = ""
        if code in UNIVERSAL:
            note = "UNIVERSAL - could not be narrowed"
        elif abs(ti - lo) > 1:
            note = "narrowed"
        elif ti > 99:
            note = "still ~universal"
        print(f"{code:<30} {lo:7.1f}% {ti:7.1f}% {ti - lo:+8.1f}%  {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
