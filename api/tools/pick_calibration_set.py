# -*- coding: utf-8 -*-
"""Choose recording segments that actually exercise the gradient checks.

A calibration set is only worth the time it takes to record if every check it is
meant to calibrate can fire on it. Picking ayat by eye gets this wrong: madd and
shadda are everywhere, but a segment with no nasal cannot exercise GHUNNA_*, and
one with no mutbaq letter cannot exercise TAFKHEEM_ADDED. So the set is computed
from the same eligibility functions the harness scores with.

Three constraints, in order:

  1. COVERAGE. Greedy set-cover over the gradient checks, then keep going until
     every check has several independent samples - one sample per check measures
     nothing about variance, and variance is the whole question.
  2. CORRECTNESS IS PLAUSIBLE. Restricted to al-Fatiha and the short mufassal
     suras. The reciter has to certify these as correct, and a passage they know
     cold is far likelier to be genuinely correct than one they are reading for
     the first time. This is the ground-truth problem, handled at selection time.
  3. RECORDABLE. Roughly 2-9 seconds at the display rate. Long enough to settle
     into, short enough to re-take without irritation.

Run:  py -3.13 tools/pick_calibration_set.py [n]
"""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from quran_transcript import Aya, quran_phonetizer  # noqa: E402

from tilawah import content  # noqa: E402
from tilawah.engine.coverage import possible_codes  # noqa: E402
from tilawah.engine.moshaf import MOSHAF  # noqa: E402
from tilawah.engine.ranges import (Range, estimate_seconds,  # noqa: E402
                                   reference)
from tilawah.engine.tolerances import eligible_checks  # noqa: E402

# The gradient checks - the ones a threshold can actually move.
DURATION = ["MADD_SHORT", "MADD_LONG", "GHUNNA_SHORT", "GHUNNA_LONG",
            "SHADDA_SHORT", "SHADDA_LONG"]
# The ṣifa preconditions. No detector reads these yet, but the harness measures
# reference-vs-predicted disagreement wherever they are possible, and that is
# the number that decides whether such a detector is buildable.
#
# HAMS_LOST, SHIDDA_LOST and JAHR_LOST are deliberately absent: their codes were
# removed on 2026-08-07 as a scope decision (lahn khafiy khafiy - see
# engine/sifat_codes.OUT_OF_SCOPE), so possible_codes() no longer returns them
# and selecting clips to cover them would optimise the calibration set for
# checks that cannot fire. calibrate.py still reports the raw hams and shidda
# ṣifa disagreement rate, because that is observation and costs nothing.
SIFA = ["TAFKHEEM_LOST", "TAFKHEEM_ADDED",
        "RAA_TAFKHEEM_MISSING", "RAA_TARQIQ_MISSING",
        "QALQALAH_MISSING", "MADD_WAJIB_SHORTENED", "MADD_ADDED_LEEN"]
TARGETS = DURATION + SIFA

# Short mufassal + al-Fatiha: what a learner is most likely to know by heart.
CANDIDATE_SURAS = [1] + list(range(93, 115))

MIN_S, MAX_S = 2.0, 9.0
WANT_PER_CHECK = 5


def candidates():
    out = []
    for sura in CANDIDATE_SURAS:
        aya = 1
        while True:
            segs = content.segments_of(sura, aya)
            if not segs:
                break
            for s in segs:
                rng = Range(sura, aya, s["start_word"], s["num_words"])
                uthmani, flat = reference(rng)
                secs = estimate_seconds(len(flat.phonemes))
                if not (MIN_S <= secs <= MAX_S):
                    continue
                spaced = quran_phonetizer(uthmani, MOSHAF, remove_spaces=False)
                hits = (eligible_checks(flat.phonemes)
                        | possible_codes(flat.phonemes, flat.sifat,
                                         spaced.phonemes))
                out.append({
                    "sura": sura, "aya": aya,
                    "start_word": s["start_word"], "num_words": s["num_words"],
                    "whole_ayah": s["start_word"] == 0
                    and s["num_words"] >= len(Aya(sura, aya).get().imlaey_words),
                    "seconds": round(secs, 1), "uthmani": uthmani,
                    "hits": hits & set(TARGETS),
                })
            aya += 1
    return out


def pick(pool, n):
    """Greedy: cover what is missing first, then top up the thinnest checks."""
    chosen, have = [], Counter()
    remaining = list(pool)
    while len(chosen) < n and remaining:
        def gain(c):
            uncovered = sum(1 for t in c["hits"] if have[t] == 0)
            thin = sum(1 for t in c["hits"] if 0 < have[t] < WANT_PER_CHECK)
            # Whole ayat first - a learner recites a complete ayah more
            # naturally than a fragment, and unnatural delivery is itself a
            # source of false positives.
            return (uncovered, thin, c["whole_ayah"], -c["seconds"])
        remaining.sort(key=gain, reverse=True)
        best = remaining.pop(0)
        chosen.append(best)
        have.update(best["hits"])
    return chosen, have


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    pool = candidates()
    print(f"{len(pool)} candidate segments in suras "
          f"{CANDIDATE_SURAS[0]}, {CANDIDATE_SURAS[1]}-{CANDIDATE_SURAS[-1]} "
          f"between {MIN_S} and {MAX_S}s\n")

    chosen, have = pick(pool, n)
    chosen.sort(key=lambda c: (c["sura"], c["aya"], c["start_word"]))

    print(f"{'#':>3} {'ref':<12} {'sec':>5}  text")
    print("-" * 78)
    for i, c in enumerate(chosen, 1):
        ref = f"{c['sura']}:{c['aya']}"
        if not c["whole_ayah"]:
            ref += f" w{c['start_word']}+{c['num_words']}"
        print(f"{i:>3} {ref:<12} {c['seconds']:>5}  {c['uthmani']}")

    print(f"\n{'check':<24} {'segments':>9}")
    print("-" * 36)
    for t in TARGETS:
        flag = "" if have[t] >= WANT_PER_CHECK else (
            "  <- THIN" if have[t] else "  <- NOT COVERED")
        print(f"{t:<24} {have[t]:>9}{flag}")

    print("\nmanifest.csv rows:\n")
    print("path,sura,aya,start_word,num_words,reciter,note")
    for i, c in enumerate(chosen, 1):
        sw = "" if c["whole_ayah"] else c["start_word"]
        nw = "" if c["whole_ayah"] else c["num_words"]
        stem = f"{c['sura']:03d}_{c['aya']:03d}"
        if not c["whole_ayah"]:
            stem += f"_w{c['start_word']}"
        for take in (1, 2):
            print(f"clips/{stem}_take{take}.wav,{c['sura']},{c['aya']},"
                  f"{sw},{nw},CHANGE-ME,take {take}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
