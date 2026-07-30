# -*- coding: utf-8 -*-
"""
s4_score.py - turn results.json into the decision-gate numbers.

Two independent detection channels, because they catch different things:

  PHONEME channel - edit distance between expected and predicted phoneme
                    strings. Catches substitutions, madd duration (madd length
                    is literally visible as repeated vowel chars), and
                    skipped/repeated words.

  SIFA channel    - per-phoneme articulation attributes. Catches errors where
                    the letter is RIGHT but the manner is wrong: tafkheem loss,
                    missing ghunnah, missing qalqalah. The phoneme string can be
                    identical for these, so the phoneme channel is blind to them.

Reporting recall per category through the wrong channel would badly misread the
model, which is why they are kept separate.

  CONTROL clips   - expert reciter audio from s2b_expert.py. Known-good by
                    definition, so it separates "the model is bad" from "the
                    input is bad". Held out of the false-positive rate: it is a
                    reference point, not a sample of your recordings.

WARNING - the SIFA channel is not trustworthy yet. Predicted and expected sifat
frequently have different lengths (the run-length decoding boundary is not
aligned), and sifa_mismatches is only computed when the lengths happen to match.
Every sifa number below is computed on that biased subset. Do not act on it.

Run:  python s4_score.py
      python s4_score.py --results results_aisha.json
      python s4_score.py --no-detail          # skip the per-clip phoneme dump
"""
import argparse
import csv
import json
import sys
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from Levenshtein import distance as _lev
except ImportError:  # pragma: no cover - Levenshtein ships with quran-transcript
    def _lev(a, b):
        if a == b:
            return 0
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]

SIFA_FIELDS = [
    "hams_or_jahr", "shidda_or_rakhawa", "tafkheem_or_taqeeq", "itbaq",
    "safeer", "qalqla", "tikraar", "tafashie", "istitala", "ghonna",
]

# Which channel is the RIGHT one to judge each error category by.
CHANNEL_FOR = {
    "substitution": "phoneme",
    "duration": "phoneme",
    "structural": "phoneme",
    "sifa": "sifa",
}


def sifa_mismatches(exp, pred):
    """Field-level mismatch count. None if lengths differ (structural change)."""
    if len(exp) != len(pred):
        return None, len(pred) - len(exp)
    n = 0
    for e, p in zip(exp, pred):
        for f in SIFA_FIELDS:
            ev, pv = e.get(f), p.get(f)
            if ev is not None and pv is not None and ev != pv:
                n += 1
    return n, 0


def pct(n, d):
    return f"{100.0 * n / d:5.1f}%" if d else "    -"


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def dump_clips(title, clips, note=""):
    """Expected vs predicted, one clip per block.

    Arabic is RTL, so stacked lines line up readably in a terminal where
    side-by-side columns would not.
    """
    if not clips:
        return
    print(f"\n    {title}")
    if note:
        print(f"    {note}")
    for s in sorted(clips, key=lambda c: c["ph_dist"]):
        mp = s["mean_prob"]
        print(f"\n      {s['clip_id']:24s} dist {s['ph_dist']:3d}   conf {mp}")
        print(f"        expected : {s['expected_phonemes']}")
        print(f"        predicted: {s['predicted_phonemes']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results.json")
    ap.add_argument("--out", default="scored.csv")
    ap.add_argument("--no-detail", action="store_true",
                    help="skip the per-clip expected/predicted phoneme dump")
    args = ap.parse_args()

    with open(args.results, encoding="utf-8") as f:
        blob = json.load(f)
    res = blob["results"]
    if not res:
        raise SystemExit("results.json has no results")

    scored = []
    for r in res:
        exp, pred = r["expected_phonemes"], r["predicted_phonemes"]
        d = _lev(exp, pred)
        sm, len_delta = sifa_mismatches(r["expected_sifat"], r["predicted_sifat"])
        scored.append({
            **{k: r[k] for k in ("clip_id", "nickname", "error_code",
                                 "error_category", "has_error", "duration_s")},
            "expected_phonemes": exp,
            "predicted_phonemes": pred,
            "ph_dist": d,
            "ph_dist_norm": round(d / max(len(exp), 1), 3),
            "sifa_mismatches": sm if sm is not None else "",
            "sifa_len_delta": len_delta,
            "mean_prob": round(r["probs"]["mean"], 3) if r.get("probs") else "",
        })

    # Controls are known-good expert audio, NOT a sample of your recording
    # setup. Leaving them in `ok` would flatter the false-positive rate.
    ctrl = [s for s in scored if s["error_category"] == "control"]
    ok = [s for s in scored if s["has_error"] == 0 and s["error_category"] != "control"]
    err = [s for s in scored if s["has_error"] == 1]

    print("=" * 74)
    print(f"  TILAWAH SPIKE RESULTS   ({len(ok)} correct / {len(err)} error"
          f" / {len(ctrl)} control clips)")
    print(f"  model: {blob.get('model')}   dtype: {blob.get('dtype')}")
    print("=" * 74)

    if not ok:
        print("\n  !! No correct-recitation clips. You cannot compute precision.")
        print("     Record the OK takes before trusting any recall number.")

    # ----------------------------------------------------------------- control
    print("\n[0] EXPERT CONTROL  (known-good audio, not your recordings)")
    ok_med = median([s["ph_dist"] for s in ok])
    if not ctrl:
        print("    None. Run:  python s2b_expert.py")
        print("    Without it you cannot tell a bad model from bad input.")
    else:
        cd = sorted(s["ph_dist"] for s in ctrl)
        c_exact = sum(1 for x in cd if x == 0)
        c_med = median(cd)
        print(f"    reciters              : {len(ctrl)}")
        print(f"    phoneme edit distance : min {cd[0]}  median {c_med}  max {cd[-1]}")
        print(f"    exact matches         : {c_exact}/{len(ctrl)}  ({pct(c_exact, len(ctrl))})")
        if ok:
            print(f"    your correct takes    : median {ok_med}   (compare above)")

        print()
        if c_med <= 1 and ok_med is not None and ok_med > max(2, 2 * c_med + 1):
            print("    >> The model transcribes expert audio near-perfectly but not your")
            print("       correct takes. The bottleneck is the INPUT - recording quality,")
            print("       or pronunciation, or both - NOT model bias against learners.")
            print("       Fix the input before drawing any conclusion from [2] and [4].")
        elif c_med <= 1:
            print("    >> Control is clean and your correct takes are close to it.")
            print("       The pipeline is sound; read [2] and [4] at face value.")
        else:
            print("    >> The control ALSO scores badly. Expert audio is exactly what this")
            print("       model was trained on, so this is a PIPELINE BUG, not recording")
            print("       quality - check the moshaf settings match across s1/s2b/s3, and")
            print("       that the reference text is the one you think it is.")
            print("       No amount of re-recording will move these numbers.")

    # ---------------------------------------------------------------- baseline
    print("\n[1] BASELINE NOISE ON CORRECT RECITATION")
    print("    How much the model disagrees with a reference it should match.")
    if ok:
        ds = sorted(s["ph_dist"] for s in ok)
        exact = sum(1 for x in ds if x == 0)
        med = median(ds)
        print(f"    phoneme edit distance : min {ds[0]}  median {med}  max {ds[-1]}")
        print(f"    exact matches         : {exact}/{len(ok)}  ({pct(exact, len(ok))})")
        print(f"    all distances         : {ds}")

        # A clean split means two different things are happening, and averaging
        # across them describes neither.
        if len(ds) >= 4:
            gaps = [(ds[i + 1] - ds[i], i) for i in range(len(ds) - 1)]
            gap, at = max(gaps)
            if gap >= 4 and ds[-1] >= 3 * max(ds[0], 1):
                lo, hi = ds[:at + 1], ds[at + 1:]
                print(f"\n    !! BIMODAL: {len(lo)} clip(s) at {lo}, {len(hi)} at {hi}.")
                print("       These are two different failure modes. A median over both")
                print("       is meaningless - read the per-clip dump in [1b] instead.")

        sms = [s["sifa_mismatches"] for s in ok if s["sifa_mismatches"] != ""]
        nlen = sum(1 for s in ok if s["sifa_len_delta"] != 0)
        if sms:
            sms = sorted(sms)
            print(f"\n    sifa mismatches       : min {sms[0]}  median {median(sms)}  max {sms[-1]}")
        print(f"    sifa length mismatch  : {nlen}/{len(ok)} clips")
        if nlen:
            print(f"    !! sifa channel UNTRUSTWORTHY - lengths differ on {nlen}/{len(ok)}")
            print(f"       correct clips, so the mismatch count above is computed on the")
            print(f"       {len(sms)} clip(s) that happened to align. Known unfixed bug;")
            print("       do not use sifa recall to make the ship/no-ship call.")

    # -------------------------------------------------- per-clip phoneme dump
    if not args.no_detail:
        print("\n[1b] WHAT THE MODEL ACTUALLY HEARD")
        dump_clips("CONTROL (expert reciters)", ctrl)
        dump_clips("YOUR CORRECT TAKES", ok,
                   note="conf is the model's own mean phoneme probability.")

    # ------------------------------------------------------- threshold sweep
    print("\n[2] OPERATING POINT SWEEP  (the key table)")
    print("    Flag a clip when phoneme distance > k. Does any k separate")
    print("    correct recitation from real errors?\n")
    print("      k   FP rate (correct clips)   Recall (phoneme-detectable errors)")
    print("    " + "-" * 64)

    ph_err = [s for s in err if CHANNEL_FOR.get(s["error_category"]) == "phoneme"]
    best = None
    for k in range(0, 7):
        fp = sum(1 for s in ok if s["ph_dist"] > k)
        tp = sum(1 for s in ph_err if s["ph_dist"] > k)
        fpr = fp / len(ok) if ok else 0
        rec = tp / len(ph_err) if ph_err else 0
        mark = ""
        if ok and ph_err and fpr <= 0.20 and rec >= 0.50:
            mark = "  <- viable"
            if best is None:
                best = k
        print(f"      {k}   {pct(fp, len(ok))}  ({fp}/{len(ok)})"
              f"          {pct(tp, len(ph_err))}  ({tp}/{len(ph_err)}){mark}")

    # -------------------------------------------------------- recall by type
    print("\n[3] RECALL BY ERROR TYPE")
    k_ph = best if best is not None else 0
    print(f"    phoneme-channel errors flagged at k={k_ph}; sifa-channel at >0 mismatches\n")
    print(f"    {'error_code':18s} {'chan':8s} {'n':>3s}  {'recall':>7s}")
    print("    " + "-" * 44)

    by_code = defaultdict(list)
    for s in err:
        by_code[s["error_code"]].append(s)

    cat_tally = defaultdict(lambda: [0, 0])
    for code in sorted(by_code, key=lambda c: (CHANNEL_FOR.get(by_code[c][0]["error_category"], "z"), c)):
        group = by_code[code]
        chan = CHANNEL_FOR.get(group[0]["error_category"], "phoneme")
        if chan == "phoneme":
            hit = sum(1 for s in group if s["ph_dist"] > k_ph)
        else:
            hit = sum(1 for s in group
                      if (s["sifa_mismatches"] != "" and s["sifa_mismatches"] > 0)
                      or s["sifa_len_delta"] != 0)
        print(f"    {code:18s} {chan:8s} {len(group):3d}  {pct(hit, len(group)):>7s}")
        cat = group[0]["error_category"]
        cat_tally[cat][0] += hit
        cat_tally[cat][1] += len(group)

    print("\n    By category:")
    for cat, (hit, tot) in sorted(cat_tally.items()):
        star = "  (sifa channel - untrustworthy, see [1])" if cat == "sifa" else ""
        print(f"    {cat:18s} {tot:3d}  {pct(hit, tot):>7s}{star}")

    # ---------------------------------------------------------------- verdict
    print("\n[4] VERDICT")
    if ctrl and median([s["ph_dist"] for s in ctrl]) <= 1 and ok and \
            ok_med is not None and ok_med > max(2, 2 * median([s["ph_dist"] for s in ctrl]) + 1):
        print("    READ [0] FIRST. The expert control transcribes cleanly, so the")
        print("    numbers below are measuring your recordings, not the model.")
        print("    Any RED/AMBER call here is premature until the input is fixed.\n")
    if not ok or not err:
        print("    Need both correct and error clips to judge. Record more.")
    else:
        fp_at = sum(1 for s in ok if s["ph_dist"] > k_ph) / len(ok)
        tp_at = sum(1 for s in ph_err if s["ph_dist"] > k_ph) / len(ph_err) if ph_err else 0
        flagged_ok = sum(1 for s in ok if s["ph_dist"] > k_ph)
        flagged_err = sum(1 for s in ph_err if s["ph_dist"] > k_ph)
        prec = flagged_err / (flagged_err + flagged_ok) if (flagged_err + flagged_ok) else 0

        print(f"    at k={k_ph}:  false-positive rate {fp_at*100:.0f}%"
              f"   recall {tp_at*100:.0f}%   clip-level precision {prec*100:.0f}%\n")

        if fp_at < 0.20 and tp_at > 0.50:
            print("    GREEN - the architecture holds.")
            print("    Proceed to full system design. Scope v1 to the error types")
            print("    above ~60% recall and ship only those.")
        elif fp_at <= 0.40:
            print("    AMBER - usable signal, not yet trustworthy.")
            print("    Add a confidence gate on phonemes.probs (see mean_prob in")
            print("    scored.csv) and only surface errors above a threshold. Re-score.")
        else:
            print("    RED - the model flags correct recitation too often.")
            print("    Do NOT build error-reporting UI on this. Switch to the fallback")
            print("    in docs/tajweed-engine-derisking.md: 8-12 binary classifiers")
            print("    on frozen embeddings, trained on your own learner data.")

        if tp_at < 0.30:
            print("\n    Also: recall is very low. That is Risk 1 (expert-data bias)")
            print("    showing up - the model is snapping learner audio onto correct")
            print("    phonemes. The fallback applies regardless of FP rate.")

    fields = list(scored[0].keys())
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(scored)
    print(f"\n    Per-clip detail: {args.out}")
    print("    Sort by ph_dist and read the worst correct clips first - that is")
    print("    where you learn what the model is actually confusing.")


if __name__ == "__main__":
    main()
