# -*- coding: utf-8 -*-
"""
s5_typed_errors.py - Layer 4 prototype: turn raw insert/delete diffs into TYPED errors.

WHY THIS EXISTS
---------------
The HF Spaces run diff_match_patch straight over the phoneme string, so every
finding collapses to "missing letter" / "extra letter". That loses the two things
a learner actually needs:

  - A substitution (ع read as ء) is reported as delete+insert at the same spot.
  - A ghunnah or madd held too short is ALSO reported as "missing letter",
    because QPS encodes duration as repeated characters (نننن = 4 counts).
    Those are completely different mistakes with the same raw signature.

The fix is run-length decoding BEFORE diffing. Collapse repeated base letters
into (letter, count) units, then diff the unit sequence:

    count differs on a matched unit  -> DURATION error (madd / ghunnah / shadda)
    letter differs at same position  -> SUBSTITUTION  (with articulatory detail)
    whole unit missing / extra       -> genuine deletion / insertion

Run:  python s5_typed_errors.py --demo          # reproduce the al-Kawthar case
      python s5_typed_errors.py                 # annotate results.json -> typed.csv
"""
import argparse
import csv
import json
import sys
import unicodedata
from difflib import SequenceMatcher

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# QPS special markers, confirmed against quran_transcript output
QALQALA_MARK = "ڇ"                      # ڇ  appended to a qalqalah letter
MADD_LETTERS = set("اۥۦوي")   # ا  ۥ  ۦ  و  ي
GHUNNA_LETTERS = set("نم")                    # ن  م

# Uzbek/Russian L1 interference pairs -> (label, what to tell the learner)
L1_PAIRS = {
    ("ع", "ء"): ("SUB_AYN_HAMZA", "ayn read as hamza - throat not engaged"),
    ("ح", "خ"): ("SUB_HA_KHA", "haa read as khaa (Russian х)"),
    ("ح", "ه"): ("SUB_HA_HEH", "haa read as heh - too far forward"),
    ("ص", "س"): ("SUB_SAD_SEEN", "saad read as plain seen - emphasis lost"),
    ("ط", "ت"): ("SUB_TA_PLAIN", "taa marbuta emphasis lost (Russian т)"),
    ("ض", "د"): ("SUB_DAD_DAL", "daad read as plain daal"),
    ("ظ", "ز"): ("SUB_DHA_ZAY", "dhaa read as zay"),
    ("ق", "ك"): ("SUB_QAF_KAF", "qaaf read as kaaf (Russian к)"),
    ("ذ", "ز"): ("SUB_DHAL_ZAY", "dhaal read as zay (Russian з)"),
    ("ث", "س"): ("SUB_THA_SEEN", "thaa read as seen (Russian с)"),
    ("و", "ف"): ("SUB_WAW_V", "waw read as v (Russian в)"),
}


def tokenize(ph):
    """
    Phoneme string -> list of run units.

    A unit is (base_letter, count, marks). Consecutive identical base letters
    merge into one unit ONLY while no diacritic has been attached yet - that is
    what makes نننن one 4-count run but ءَء two separate hamzas.
    """
    units = []
    for ch in ph:
        if unicodedata.combining(ch):          # fatha, kasra, shadda, sukun...
            if units:
                units[-1][2] += ch
            continue
        if units and units[-1][0] == ch and not units[-1][2]:
            units[-1][1] += 1                  # same letter, still open -> longer run
        else:
            units.append([ch, 1, ""])
    return [(b, c, m) for b, c, m in units]


def _duration_kind(letter, exp_n, got_n):
    if letter in MADD_LETTERS:
        base = "MADD"
        unit = "counts"
    elif letter in GHUNNA_LETTERS:
        base = "GHUNNA"
        unit = "counts"
    else:
        base = "SHADDA"
        unit = "length"
    direction = "SHORT" if got_n < exp_n else "LONG"
    return f"{base}_{direction}", f"held {got_n} {unit}, expected {exp_n}"


def typed_diff(expected, predicted):
    """Compare two QPS strings and return a list of typed error dicts."""
    exp_u, got_u = tokenize(expected), tokenize(predicted)
    sm = SequenceMatcher(None, [u[0] for u in exp_u], [u[0] for u in got_u])
    errors = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            # letters match - but the RUN LENGTH may not. This is the case the
            # raw diff reports as "missing letter" and gets wrong.
            for k in range(i2 - i1):
                e, g = exp_u[i1 + k], got_u[j1 + k]
                if e[1] != g[1]:
                    kind, detail = _duration_kind(e[0], e[1], g[1])
                    errors.append({"type": kind, "at": i1 + k, "letter": e[0],
                                   "detail": detail})

        elif op == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                e, g = exp_u[i1 + k], got_u[j1 + k]
                lbl, why = L1_PAIRS.get(
                    (e[0], g[0]),
                    ("SUBSTITUTION", f"read {e[0]} as {g[0]}"))
                errors.append({"type": lbl, "at": i1 + k, "letter": e[0],
                               "detail": f"{why} ({e[0]} -> {g[0]})"})
            for k in range(n, i2 - i1):          # leftover expected = dropped
                e = exp_u[i1 + k]
                errors.append(_missing(e, i1 + k))
            for k in range(n, j2 - j1):          # leftover heard = added
                g = got_u[j1 + k]
                errors.append({"type": "INSERTION", "at": i1, "letter": g[0],
                               "detail": f"extra {g[0]} not in the text"})

        elif op == "delete":
            for k in range(i1, i2):
                errors.append(_missing(exp_u[k], k))

        elif op == "insert":
            for k in range(j1, j2):
                errors.append({"type": "INSERTION", "at": i1, "letter": got_u[k][0],
                               "detail": f"extra {got_u[k][0]} not in the text"})

    return errors


def _missing(unit, at):
    """A dropped ڇ is a missing qalqalah, not a missing letter."""
    if unit[0] == QALQALA_MARK:
        return {"type": "QALQALA_DROP", "at": at, "letter": QALQALA_MARK,
                "detail": "no bounce on the sukoon letter"}
    return {"type": "DELETION", "at": at, "letter": unit[0],
            "detail": f"{unit[0]} not pronounced"}


# --------------------------------------------------------------------------- demo
def demo():
    from quran_transcript import Aya, MoshafAttributes, quran_phonetizer

    moshaf = MoshafAttributes(rewaya="hafs", madd_monfasel_len=4,
                              madd_mottasel_len=4, madd_mottasel_waqf=4,
                              madd_aared_len=4)
    expected = quran_phonetizer(Aya(108, 1).get().uthmani, moshaf,
                                remove_spaces=True).phonemes

    # Reproduce exactly the errors the Space reported on the al-Kawthar clip.
    predicted = expected
    predicted = predicted.replace("نننن", "نن")  # ghunnah 4->2
    predicted = predicted.replace("عط", "ءت")              # ayn->hamza, taa->plain
    predicted = predicted.replace("ث", "س")                          # thaa->seen
    predicted = predicted.replace("كَل", "كَهل")  # extra heh

    print("=" * 72)
    print("  LAYER 4 DEMO - al-Kawthar 108:1, the Step 0 error set")
    print("=" * 72)
    print(f"\n  expected : {expected}")
    print(f"  heard    : {predicted}\n")

    raw = SequenceMatcher(None, expected, predicted)
    n_raw = sum(1 for op, *_ in raw.get_opcodes() if op != "equal")
    print(f"  Raw character diff (what the Space does): {n_raw} untyped edit regions")
    print("  -> all of it renders as حرف ناقص / حرف زائد\n")

    errs = typed_diff(expected, predicted)
    print(f"  Run-length typed diff: {len(errs)} TYPED errors\n")
    for e in errs:
        print(f"    {e['type']:16s} at unit {e['at']:2d}   {e['detail']}")
    print()


# --------------------------------------------------------------------- batch mode
def batch(results_path, out_path):
    with open(results_path, encoding="utf-8") as f:
        res = json.load(f)["results"]

    rows = []
    for r in res:
        errs = typed_diff(r["expected_phonemes"], r["predicted_phonemes"])
        rows.append({
            "clip_id": r["clip_id"],
            "induced": r["error_code"],
            "has_error": r["has_error"],
            "n_typed": len(errs),
            "types": ";".join(sorted({e["type"] for e in errs})),
            "detail": " | ".join(e["detail"] for e in errs[:4]),
        })

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    hit = sum(1 for r in rows
              if r["has_error"] and r["induced"] in r["types"].split(";"))
    tot = sum(1 for r in rows if r["has_error"])
    print(f"Wrote {out_path}: {len(rows)} clips")
    print(f"Induced error type recovered EXACTLY: {hit}/{tot}")
    print("(this is the metric that matters - not just 'something was flagged',")
    print(" but 'the right error type was named')")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--results", default="results.json")
    ap.add_argument("--out", default="typed.csv")
    a = ap.parse_args()
    demo() if a.demo else batch(a.results, a.out)
