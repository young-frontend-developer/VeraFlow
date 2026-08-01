# -*- coding: utf-8 -*-
"""Fold tajweed_registry_v3_patch.json into the v2 registry -> v3.

The patch is sourced from «Тажвид қоидалари» (Ziyovuddin Rahim, Odilxon qori
Yunusxon o'g'li; Tashkent Islamic University, 2011; ISBN 978-9943-390-26-3),
reviewed by Abdulaziz Mansur, approved under Committee on Religious Affairs
recommendation 1204 of 17 June 2011.

Three things happen here, in this order:

  A. global_terminology is applied to every uz block. These are CORRECTIONS from
     the source, not stylistic preferences - heavy letters are yo'g'on, not
     qalin, and the technical pair is iste'lo/istifola, not mufaxxam/moraqaq.
  B. new_entries are added; rewritten_entries REPLACE their v2 counterparts
     wholesale rather than being merged field-by-field.
  C. nothing changes status. Every entry stays draft; the review gate is
     untouched by this script and must stay that way.
  D. tajweed_registry_v3_amendments.json applies structural surgery decided
     after the merge - deletions, merges and splits. Kept in its own file so
     neither the v2 base nor the sourced patch is rewritten to record a later
     decision. It performs NO content authoring; entries needing new text are
     left bodyless and flagged, so render() returns None and they stay silent.

Why a script and not a hand-edit: the terminology pass touches ~30 entries in
two alphabets, and the only way anyone can check it later is to re-run it and
diff. It writes a report of exactly which strings changed.

    py -3.13 tools/apply_v3_patch.py            # writes v3 + a report
    py -3.13 tools/apply_v3_patch.py --dry-run  # report only
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
V2 = REPO / "tajweed_error_registry_v2.json"
PATCH = REPO / "tajweed_registry_v3_patch.json"
AMEND = REPO / "tajweed_registry_v3_amendments.json"
V3 = REPO / "tajweed_error_registry_v3.json"
REPORT = REPO / "docs" / "registry-v3-merge-report.md"


def build_pattern(mapping: dict[str, str]) -> re.Pattern:
    """One alternation, longest key first, so no substitution is re-scanned.

    Applying the map key by key would let an earlier replacement's OUTPUT match a
    later key - "nun sokin" -> "sukunli «nuvn»" and then "nun harfi" hunting
    through the result. A single pass over the original string cannot do that.

    Matching is stem-anchored, not whole-word: Uzbek is agglutinative and the
    corrections are stems. "qalinligi" must become "yo'g'onligi", so the pattern
    anchors the START of the word and lets any suffix ride along untouched.
    """
    keys = sorted((k for k in mapping if not k.startswith("_")),
                  key=len, reverse=True)
    return re.compile(r"(?<![\w'’])(" + "|".join(re.escape(k) for k in keys) + ")",
                      re.IGNORECASE)


def apply_terms(text: str, mapping: dict[str, str], seen: Counter) -> str:
    """One left-to-right pass, case of the first letter preserved."""
    if not isinstance(text, str) or not text:
        return text

    lookup = {k.lower(): v for k, v in mapping.items() if not k.startswith("_")}

    def sub(m: re.Match) -> str:
        src = m.group(1)
        dst = lookup[src.lower()]
        # Entry names are sentence-initial - "Qalin harfni ingichka o'qish" -
        # and lower-casing the first letter of a title is a visible regression.
        if src[:1].isupper():
            dst = dst[:1].upper() + dst[1:]
        seen[f"{src} -> {dst}"] += 1
        return dst

    return build_pattern(mapping).sub(sub, text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    v2 = json.loads(V2.read_text(encoding="utf-8"))
    patch = json.loads(PATCH.read_text(encoding="utf-8"))
    meta = patch["_meta"]
    terms = meta["global_terminology"]
    errors = json.loads(json.dumps(v2["errors"]))     # deep copy

    # ── A. terminology across every uz block ──────────────────────────────
    seen: Counter = Counter()
    touched_entries = set()
    for code, entry in errors.items():
        uz = entry.get("uz")
        if not isinstance(uz, dict):
            continue
        for field, value in list(uz.items()):
            new = apply_terms(value, terms, seen)
            if new != value:
                uz[field] = new
                touched_entries.add(code)

    # ── B. merge ──────────────────────────────────────────────────────────
    new_entries = patch.get("new_entries", {})
    rewrites = patch.get("rewritten_entries", {})

    collisions = sorted(set(new_entries) & set(errors))
    missing_rewrite_targets = sorted(set(rewrites) - set(errors))

    for code, entry in new_entries.items():
        errors[code] = entry
    for code, entry in rewrites.items():
        errors[code] = entry          # wholesale replacement, per the patch

    # ── D. structural amendments ──────────────────────────────────────────
    amend = json.loads(AMEND.read_text(encoding="utf-8")) if AMEND.exists() else {}
    deleted, merged, split = [], [], []

    for code, spec in (amend.get("merges") or {}).items():
        sources = [c for c in spec.get("replaces", []) if c in errors]
        if not sources:
            continue
        carry = spec.get("carried_content_from") or sources[0]
        entry = json.loads(json.dumps(errors[carry]))
        entry.update(spec.get("entry_overrides") or {})
        for key in ("content_status", "content_todo"):
            if spec.get(key):
                entry[key] = spec[key]
        entry["merged_from"] = sources
        errors[code] = entry
        merged.append((code, sources, spec.get("content_status", "")))

    for parent, spec in (amend.get("splits") or {}).items():
        for code, sub in (spec.get("into") or {}).items():
            if sub.get("keeps_existing_content"):
                if code in errors:
                    errors[code].update(sub.get("entry_overrides") or {})
                    split.append((code, "kept + overridden"))
                continue
            # A brand-new entry with NO uz/ru body. That is the point: an
            # unauthored code renders to None and pipeline.analyze() files it
            # under silent_errors, which is exactly right until a qori writes it.
            errors[code] = dict(sub.get("entry") or {})
            split.append((code, sub.get("content_status", "new")))

    for code, spec in (amend.get("delete") or {}).items():
        if code in errors:
            del errors[code]
            deleted.append((code, (spec or {}).get("reason", "")))

    # ── C. the safety gate is not this script's to move ───────────────────
    bad_status = sorted(c for c, e in errors.items() if e.get("status") != "draft")
    bodyless = sorted(c for c, e in errors.items()
                      if not (e.get("uz") or {}).get("name"))

    out = {
        "_meta": {
            **v2.get("_meta", {}),
            "version": "3.0",
            "total_errors": len(errors),
            "derived_from": [V2.name, PATCH.name, AMEND.name],
            "source": meta["source"],
            "detection_notes": meta["detection_notes"],
            "regenerate_with": "py -3.13 api/tools/apply_v3_patch.py",
            "DO_NOT_HAND_EDIT": (
                "Edit tajweed_registry_v3_patch.json or the v2 base and re-run "
                "the script. A hand edit here is invisible to the merge report "
                "and will be silently overwritten on the next run."),
        },
        "errors": dict(sorted(errors.items())),
    }

    lines = [
        "# Registry v3 merge report", "",
        f"- base: `{V2.name}` ({len(v2['errors'])} entries)",
        f"- patch: `{PATCH.name}`",
        f"- result: `{V3.name}` ({len(errors)} entries)",
        f"- source: {meta['source']['title']} — {meta['source']['authors']}, "
        f"{meta['source']['publisher']}, ISBN {meta['source']['isbn']}", "",
        "## A. Terminology corrections applied to uz blocks", "",
        f"{sum(seen.values())} substitutions across {len(touched_entries)} entries.",
        "", "| replacement | count |", "|---|---|",
    ]
    for k, n in sorted(seen.items(), key=lambda kv: -kv[1]):
        lines.append(f"| `{k}` | {n} |")
    unused = [k for k in terms
              if not k.startswith("_")
              and not any(k in s.split(" -> ")[0] for s in seen)]
    lines += ["", f"Map keys that matched nothing: "
                  f"{', '.join(f'`{u}`' for u in unused) or 'none'}.",
              "These are still correct to carry - they guard future entries.", ""]
    lines += ["## B. Entries", "",
              f"- added ({len(new_entries)}): "
              + ", ".join(f"`{c}`" for c in sorted(new_entries)),
              f"- rewritten ({len(rewrites)}): "
              + ", ".join(f"`{c}`" for c in sorted(rewrites)), ""]
    if collisions:
        lines.append(f"⚠️ new_entries that already existed in v2 and were "
                     f"overwritten: {collisions}")
    if missing_rewrite_targets:
        lines.append(f"⚠️ rewrites with no v2 counterpart (added instead): "
                     f"{missing_rewrite_targets}")
    lines += ["", "## D. Structural amendments", ""]
    if deleted:
        lines += ["**Deleted**", ""]
        for code, reason in deleted:
            lines.append(f"- `{code}` — {reason}")
        lines.append("")
    if merged:
        lines += ["**Merged**", ""]
        for code, sources, cs in merged:
            lines.append(f"- `{code}` ← {', '.join(f'`{s}`' for s in sources)}"
                         + (f" — **{cs}**" if cs else ""))
        lines.append("")
    if split:
        lines += ["**Split**", ""]
        for code, note in split:
            lines.append(f"- `{code}` — {note}")
        lines.append("")
    if not (deleted or merged or split):
        lines += ["None.", ""]

    lines += ["", "## C. Safety gate", "",
              "Every entry status is `draft`." if not bad_status else
              f"⚠️ NOT ALL DRAFT: {bad_status}", ""]
    if bodyless:
        lines += [
            f"**{len(bodyless)} entries have no authored uz body**: "
            + ", ".join(f"`{c}`" for c in bodyless) + ".", "",
            "This is deliberate, not an omission. Decision 4 forbids an LLM "
            "authoring a tajweed rule, so a split or merge that needs new text "
            "leaves it unwritten. `content.render()` returns None for these and "
            "`pipeline.analyze()` files them under `silent_errors`.", ""]
    lines += ["Nothing here is shown to a learner. `content/rules.json` is the "
              "learner-facing file and this merge does not touch it.", ""]
    report = "\n".join(lines)

    print(report)
    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    V3.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                  encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"\nwrote {V3}\nwrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
