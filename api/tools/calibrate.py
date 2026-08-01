# -*- coding: utf-8 -*-
"""Tolerance calibration harness - the gate before any learner sees the app.

You supply recordings you certify as CORRECT. Every check that fires on one of
them is a false positive by construction: no expert labelling, no annotation
queue, no ambiguity about ground truth. That property is what makes this cheap
enough to run after every change.

    py -3.13 tools/calibrate.py

Run it once and it transcribes (slow: ~1-3 s per clip on the laptop) and caches.
Edit config/tolerances.json and run the SAME command again and it re-scores from
the cache in under a second. That is the loop this tool exists to make fast.

    py -3.13 tools/calibrate.py --recompute    force re-transcription
    py -3.13 tools/calibrate.py --suggest      write thresholds that zero the FPs

WHAT IT WILL NOT DO
-------------------
It will not tell you the checks are safe. A zero false-positive rate over eight
clips from one reciter is eight clips from one reciter - see the ground-truth
problem already on record (own ص reads as س on 4/4, so a single reciter cannot
certify their own "correct" set). Read the per-reciter breakdown, not the total.
"""
import argparse
import csv
import hashlib
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tilawah.config import settings  # noqa: E402
from tilawah.engine import tolerances  # noqa: E402
from tilawah.engine.audio import DecodeInfo, check_quality, decode  # noqa: E402
from tilawah.engine.collapse import looks_collapsed  # noqa: E402
from tilawah.engine.ranges import Range, is_legal_range, n_words, reference  # noqa: E402
from tilawah.engine.sifa_compare import (FIELDS, alignment_ratio,  # noqa: E402
                                         compare, reference_groups)
from tilawah.engine.tolerances import eligible_checks  # noqa: E402
from tilawah.engine.typed_errors import typed_diff  # noqa: E402

DIR = ROOT / "calibration"
CACHE = DIR / ".cache"
MANIFEST = DIR / "manifest.csv"


# ─────────────────────────────────────────────────────────── manifest

def read_manifest(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"No manifest at {path}\n"
            f"Create it with a header row:\n"
            f"  path,sura,aya,start_word,num_words,reciter,note\n"
            f"See {DIR / 'README.md'}.")
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for i, raw in enumerate(csv.DictReader(fh), start=2):
            if not (raw.get("path") or "").strip():
                continue
            if (raw.get("path") or "").lstrip().startswith("#"):
                continue
            try:
                sura, aya = int(raw["sura"]), int(raw["aya"])
            except (KeyError, TypeError, ValueError):
                raise SystemExit(f"{path}:{i}: sura and aya are required integers")
            audio = Path((raw["path"] or "").strip())
            if not audio.is_absolute():
                audio = (path.parent / audio).resolve()
            rows.append({
                "line": i, "audio": audio, "sura": sura, "aya": aya,
                "start_word": int(raw.get("start_word") or 0),
                "num_words": int(raw.get("num_words") or 0),
                "reciter": (raw.get("reciter") or "unknown").strip(),
                "note": (raw.get("note") or "").strip(),
            })
    if not rows:
        raise SystemExit(f"{path} has a header but no recordings.")
    return rows


# ─────────────────────────────────────────────────── stage 1: transcribe

def cache_key(row: dict, data: bytes) -> str:
    """Audio bytes + the exact range + the model that produced the answer.

    The model id is in the key because a cached transcription from a different
    checkpoint is not a cheap re-score, it is a wrong one - and the whole point
    of the cache is that step 4 of the loop can be trusted without thinking.
    """
    h = hashlib.sha256()
    h.update(data)
    h.update(f"|{row['sura']}:{row['aya']}:{row['start_word']}:"
             f"{row['num_words']}|{settings.model_id}".encode())
    return h.hexdigest()[:20]


def transcribe_row(row: dict, *, recompute: bool) -> dict:
    """-> cached record: expected/heard phonemes, predicted ṣifāt, quality.

    Everything expensive and nondeterministic-in-cost happens here exactly once.
    Scoring reads the cache, which is why a threshold change re-runs in seconds.
    """
    audio_path: Path = row["audio"]
    if not audio_path.exists():
        return {"outcome": "missing_file", "detail": str(audio_path)}

    data = audio_path.read_bytes()
    key = cache_key(row, data)
    cached = CACHE / f"{key}.json"
    if cached.exists() and not recompute:
        rec = json.loads(cached.read_text(encoding="utf-8"))
        rec["from_cache"] = True
        return rec

    try:
        total = n_words(row["sura"], row["aya"])
    except Exception:
        return {"outcome": "ayah_not_in_catalogue"}

    start, num = row["start_word"], row["num_words"]
    if num <= 0:
        start, num = 0, total
    if not is_legal_range(row["sura"], row["aya"], start, num):
        return {"outcome": "illegal_word_range",
                "detail": f"{start}+{num} of {total} words"}

    info = DecodeInfo()
    try:
        wave = decode(data, info)
    except Exception as exc:
        return {"outcome": "decode_failed", "detail": str(exc)}

    q = check_quality(wave)
    rng = Range(row["sura"], row["aya"], start, num)
    uthmani, phonetized = reference(rng)

    rec = {
        "outcome": "ok" if q.ok else "rejected_by_quality_gate",
        "reason": q.reason, "uthmani": uthmani,
        "expected": phonetized.phonemes,
        "ref_sifat": reference_groups(phonetized.sifat),
        "duration_s": round(q.duration_s, 3), "snr_db": round(q.snr_db, 2),
        "snr_measurable": q.snr_measurable,
        "start_word": start, "num_words": num,
        "model_dtype": settings.model_dtype,
    }

    if q.ok:
        from tilawah.engine.model import transcribe
        t0 = time.perf_counter()
        pred = transcribe(wave, phonetized)
        rec["infer_s"] = round(time.perf_counter() - t0, 2)
        rec["heard"] = pred.phonemes
        rec["pred_sifat"] = pred.sifat
        rec["mean_prob"] = round(pred.mean_prob, 4)
        collapsed, detail = looks_collapsed(pred.phonemes, row["sura"],
                                            row["aya"], phonetized.phonemes)
        if collapsed:
            rec["outcome"] = "rejected_as_collapsed"
            rec["reason"] = detail

    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    rec["from_cache"] = False
    return rec


# ────────────────────────────────────────────────────── stage 2: score

def score_row(row: dict, rec: dict, cfg: dict) -> dict:
    out = {**{k: row[k] for k in ("line", "reciter", "note", "sura", "aya")},
           "file": row["audio"].name, "outcome": rec.get("outcome"),
           "reason": rec.get("reason", ""), "detail": rec.get("detail", "")}
    if rec.get("outcome") != "ok":
        return out

    raw = typed_diff(rec["expected"], rec["heard"])
    kept, dropped = tolerances.apply(raw, rec.get("mean_prob", 0.0), cfg)

    out.update({
        "expected": rec["expected"], "heard": rec["heard"],
        "mean_prob": rec.get("mean_prob", 0.0),
        "duration_s": rec.get("duration_s"), "snr_db": rec.get("snr_db"),
        "eligible": sorted(eligible_checks(rec["expected"])),
        "fires": [{"code": e.code, "at": e.at, "letter": e.letter,
                   "expected": e.expected, "heard": e.heard,
                   "margin": tolerances.margin_of(e),
                   "expected_count": e.expected_count,
                   "heard_count": e.heard_count} for e in kept],
        "within_tolerance": [{"code": e.code, "at": e.at, "letter": e.letter,
                              "margin": v.margin, "threshold": v.threshold,
                              "reason": v.reason} for e, v in dropped],
    })

    ref_g, pred_g = rec.get("ref_sifat") or [], rec.get("pred_sifat") or []
    out["sifa_alignment"] = round(alignment_ratio(ref_g, pred_g), 3)
    out["sifa_diffs"] = [
        {"at": d.at, "letter": d.letter, "field": d.field,
         "expected": d.expected, "heard": d.heard, "prob": d.prob}
        for d in compare(ref_g, pred_g)]
    out["sifa_groups_compared"] = len(ref_g)
    return out


# ────────────────────────────────────────────────────────── reporting

def aggregate(scored: list[dict], cfg: dict) -> dict:
    usable = [s for s in scored if s["outcome"] == "ok"]
    fired = defaultdict(list)          # code -> [margin or None]
    clips_with = defaultdict(set)      # code -> {clip index}
    eligible = defaultdict(int)
    suppressed = defaultdict(list)

    for i, s in enumerate(usable):
        for code in s["eligible"]:
            eligible[code] += 1
        for f in s["fires"]:
            fired[f["code"]].append(f["margin"])
            clips_with[f["code"]].add(i)
        for w in s["within_tolerance"]:
            suppressed[w["code"]].append(w["margin"])

    checks = []
    for code in sorted(set(fired) | set(eligible) | set(suppressed)):
        margins = [m for m in fired[code] if m is not None]
        rule = tolerances.rule_for(code, cfg)
        row = {
            "code": code,
            "kind": rule.get("kind"),
            "threshold": rule.get("min_delta") if rule.get("kind") == "duration" else None,
            "eligible_clips": eligible.get(code, 0),
            "clips_fired": len(clips_with.get(code, ())),
            "total_fires": len(fired.get(code, ())),
            "suppressed_fires": len(suppressed.get(code, ())),
            "fp_rate": (len(clips_with.get(code, ())) / eligible[code]
                        if eligible.get(code) else None),
        }
        if margins:
            row.update({
                "margin_min": min(margins), "margin_max": max(margins),
                "margin_median": statistics.median(margins),
                "margin_hist": {str(int(m)): margins.count(m)
                                for m in sorted(set(margins))},
                # The threshold that would silence every false positive SEEN
                # HERE. Not a safe threshold - a bound from this sample. int,
                # because it is copied straight into a config a human edits and
                # "min_delta": 3.0 there reads like a precision nobody has.
                "would_need": int(max(margins)) + 1,
            })
        elif row["kind"] == "duration":
            row["would_need"] = rule.get("min_delta")
        checks.append(row)
    checks.sort(key=lambda r: (-(r["clips_fired"]), r["code"]))

    sifa = defaultdict(lambda: {"diffs": 0, "clips": set(), "probs": []})
    groups_total = 0
    for i, s in enumerate(usable):
        groups_total += s.get("sifa_groups_compared", 0)
        for d in s.get("sifa_diffs", []):
            f = sifa[d["field"]]
            f["diffs"] += 1
            f["clips"].add(i)
            f["probs"].append(d["prob"])
    sifa_rows = []
    for field in FIELDS:
        f = sifa.get(field)
        if not f:
            sifa_rows.append({"field": field, "diffs": 0, "clips": 0,
                              "per_group_rate": 0.0, "median_prob": None})
            continue
        sifa_rows.append({
            "field": field, "diffs": f["diffs"], "clips": len(f["clips"]),
            "per_group_rate": (f["diffs"] / groups_total) if groups_total else None,
            "median_prob": round(statistics.median(f["probs"]), 3) if f["probs"] else None,
        })

    per_reciter = defaultdict(lambda: {"clips": 0, "clean": 0, "fires": 0})
    for s in usable:
        r = per_reciter[s["reciter"]]
        r["clips"] += 1
        r["fires"] += len(s["fires"])
        r["clean"] += int(not s["fires"])

    return {
        "n_manifest": len(scored),
        "n_usable": len(usable),
        "n_excluded": len(scored) - len(usable),
        "excluded": [{"file": s["file"], "outcome": s["outcome"],
                      "reason": s.get("reason") or s.get("detail", "")}
                     for s in scored if s["outcome"] != "ok"],
        "clips_completely_clean": sum(1 for s in usable if not s["fires"]),
        "checks": checks,
        "sifa_observed": sifa_rows,
        "sifa_groups_compared": groups_total,
        "sifa_alignment_median": (
            round(statistics.median([s["sifa_alignment"] for s in usable]), 3)
            if usable else None),
        "per_reciter": {k: v for k, v in sorted(per_reciter.items())},
    }


def print_report(agg: dict, cfg_path: Path) -> None:
    print()
    print("=" * 78)
    print("TOLERANCE CALIBRATION - every fire below is a FALSE POSITIVE")
    print("=" * 78)
    print(f"thresholds : {cfg_path}")
    print(f"manifest   : {agg['n_manifest']} recordings, {agg['n_usable']} usable, "
          f"{agg['n_excluded']} excluded")
    print(f"clean      : {agg['clips_completely_clean']}/{agg['n_usable']} "
          f"clips fired nothing at the current thresholds")

    if agg["excluded"]:
        print("\nEXCLUDED - these never reached the checks:")
        for e in agg["excluded"]:
            print(f"  {e['file']:<34} {e['outcome']:<26} {e['reason']}")
        print("  ^ a correct recitation rejected here is a false REJECTION,")
        print("    which costs the same trust as a false positive.")

    print(f"\n{'check':<16} {'kind':<9} {'clips':>7} {'elig':>6} {'fires':>6} "
          f"{'supp':>6} {'margins':>16} {'now':>5} {'need':>6}")
    print("-" * 92)
    for c in agg["checks"]:
        if not c["clips_fired"] and not c["suppressed_fires"]:
            continue
        m = ("-" if "margin_min" not in c else
             f"{c['margin_min']:g}/{c['margin_median']:g}/{c['margin_max']:g}")
        print(f"{c['code']:<16} {str(c['kind']):<9} {c['clips_fired']:>7} "
              f"{c['eligible_clips']:>6} {c['total_fires']:>6} "
              f"{c['suppressed_fires']:>6} {m:>16} "
              f"{str(c['threshold'] or '-'):>5} "
              f"{str(c.get('would_need', '-')):>6}")
    silent = [c["code"] for c in agg["checks"]
              if not c["clips_fired"] and not c["suppressed_fires"]]
    if silent:
        print(f"\nfired on nothing: {', '.join(silent)}")
    print("\nmargins are min/median/max, in QPS units (~1 harakah).")
    print("'need' = the min_delta that would silence every FP in THIS sample.")
    print("Discrete checks show '-': a wrong letter has no gradient, so a")
    print("threshold cannot fix it - only a better model or a narrower scope can.")

    print(f"\nṢIFA (observation only - no detector exists; "
          f"{agg['sifa_groups_compared']} groups compared, "
          f"alignment median {agg['sifa_alignment_median']})")
    print(f"{'field':<22} {'diffs':>7} {'clips':>7} {'per-group':>11} {'med prob':>9}")
    print("-" * 60)
    for s in agg["sifa_observed"]:
        rate = "-" if s["per_group_rate"] is None else f"{s['per_group_rate']*100:.1f}%"
        print(f"{s['field']:<22} {s['diffs']:>7} {s['clips']:>7} {rate:>11} "
              f"{str(s['median_prob'] or '-'):>9}")
    print("^ this is the false-positive floor for a ṣifa detector you have not")
    print("  built yet. Build it only if these rates are low.")

    print(f"\n{'reciter':<22} {'clips':>7} {'clean':>7} {'fires':>7}")
    print("-" * 46)
    for name, r in agg["per_reciter"].items():
        print(f"{name:<22} {r['clips']:>7} {r['clean']:>7} {r['fires']:>7}")
    if not agg["per_reciter"]:
        print("\n!! NOTHING WAS SCORED. Every recording was excluded above -")
        print("   fix those before reading anything else as a result.")
    elif len(agg["per_reciter"]) == 1:
        print("\n!! ONE RECITER. A threshold fitted here is fitted to one voice,")
        print("   one microphone and one room. It is a starting point, not a gate.")


def write_markdown(agg: dict, path: Path, cfg_path: Path) -> None:
    L = ["# Tolerance calibration report", "",
         f"- thresholds: `{cfg_path}`",
         f"- recordings: {agg['n_manifest']} ({agg['n_usable']} usable, "
         f"{agg['n_excluded']} excluded)",
         f"- clips firing nothing: **{agg['clips_completely_clean']}/{agg['n_usable']}**",
         "", "Every fire below happened on a recitation certified correct, so "
         "every one is a false positive.", "",
         "| check | kind | clips fired | eligible | fires | suppressed | "
         "margins min/med/max | threshold | would need |",
         "|---|---|---|---|---|---|---|---|---|"]
    for c in agg["checks"]:
        m = ("–" if "margin_min" not in c else
             f"{c['margin_min']:g} / {c['margin_median']:g} / {c['margin_max']:g}")
        L.append(f"| `{c['code']}` | {c['kind']} | {c['clips_fired']} | "
                 f"{c['eligible_clips']} | {c['total_fires']} | "
                 f"{c['suppressed_fires']} | {m} | {c['threshold'] or '–'} | "
                 f"{c.get('would_need', '–')} |")
    L += ["", "## Ṣifa disagreement (observation only)", "",
          f"{agg['sifa_groups_compared']} groups compared; "
          f"median alignment {agg['sifa_alignment_median']}.", "",
          "| field | diffs | clips | per-group rate | median prob |",
          "|---|---|---|---|---|"]
    for s in agg["sifa_observed"]:
        rate = "–" if s["per_group_rate"] is None else f"{s['per_group_rate']*100:.1f}%"
        L.append(f"| `{s['field']}` | {s['diffs']} | {s['clips']} | {rate} | "
                 f"{s['median_prob'] or '–'} |")
    L += ["", "## Per reciter", "", "| reciter | clips | clean | fires |",
          "|---|---|---|---|"]
    for name, r in agg["per_reciter"].items():
        L.append(f"| {name} | {r['clips']} | {r['clean']} | {r['fires']} |")
    if agg["excluded"]:
        L += ["", "## Excluded", "", "| file | outcome | reason |", "|---|---|---|"]
        for e in agg["excluded"]:
            L.append(f"| {e['file']} | {e['outcome']} | {e['reason']} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def write_suggestion(agg: dict, cfg: dict, path: Path) -> None:
    """A tolerances.json that would silence every FP in this sample.

    Deliberately written to a SEPARATE file. Auto-applying it would fit
    thresholds to whatever was recorded last, which is how a calibration tool
    turns into a way of hiding errors.
    """
    out = json.loads(json.dumps(cfg))
    out["_meta"] = {
        "GENERATED": "by tools/calibrate.py --suggest. Review before use.",
        "basis": f"{agg['n_usable']} clips certified correct, "
                 f"{len(agg['per_reciter'])} reciter(s)",
        "warning": "These thresholds silence every false positive IN THIS "
                   "SAMPLE and nothing more. Raising a threshold also hides "
                   "real errors of the same size - a min_delta of 3 on "
                   "MADD_SHORT means a 4-count madd read as 2 goes unmentioned. "
                   "Copy a value across only when you accept that trade.",
        "inherits": out.get("_meta", {}).get("purpose", ""),
    }
    for c in agg["checks"]:
        if c["kind"] != "duration" or "would_need" not in c:
            continue
        out.setdefault("checks", {}).setdefault(c["code"], {})
        out["checks"][c["code"]]["min_delta"] = c["would_need"]
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


# ─────────────────────────────────────────────────────────────── main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--recompute", action="store_true",
                    help="re-transcribe even if cached")
    ap.add_argument("--suggest", action="store_true",
                    help="write calibration/tolerances.suggested.json")
    ap.add_argument("--out", type=Path, default=DIR / "report.json")
    args = ap.parse_args()

    rows = read_manifest(args.manifest)
    cfg = tolerances.load()
    cfg_path = tolerances.config_path()

    print(f"{len(rows)} recordings from {args.manifest}")
    scored, n_new = [], 0
    for row in rows:
        rec = transcribe_row(row, recompute=args.recompute)
        if not rec.get("from_cache") and rec.get("outcome") == "ok":
            n_new += 1
        mark = "." if rec.get("from_cache") else "*"
        print(f"  {mark} {row['audio'].name:<40} {row['sura']}:{row['aya']} "
              f"{rec.get('outcome')}", flush=True)
        scored.append(score_row(row, rec, cfg))
    if n_new:
        print(f"  ({n_new} transcribed, rest from cache)")

    agg = aggregate(scored, cfg)
    print_report(agg, cfg_path)

    DIR.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"summary": agg, "clips": scored},
                                   ensure_ascii=False, indent=1),
                        encoding="utf-8")
    write_markdown(agg, DIR / "report.md", cfg_path)
    print(f"\nwrote {args.out} and {DIR / 'report.md'}")

    if args.suggest:
        sug = DIR / "tolerances.suggested.json"
        write_suggestion(agg, cfg, sug)
        print(f"wrote {sug} - review it, then copy values into {cfg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
