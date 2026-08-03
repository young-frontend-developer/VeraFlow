# -*- coding: utf-8 -*-
"""How long is each coaching card, against the 70-word budget?

Part B caps a card at 70 words. The registries were authored earlier, as a
tajweed reference rather than as interactive cards, so some entries are well
over. NOTHING HERE REWRITES THEM - decision 4 puts authoring in a qori's hands,
and shortening a ruling is authoring. This measures, ranks, and hands the list
over.

VISIBLE is what the learner reads without tapping anything: the headline and
the fix. That is the number the budget is really about - `rule` and `drill` sit
behind a disclosure and are meant to be longer.

    py -3.13 tools/audit_card_length.py            uz, over-budget only
    py -3.13 tools/audit_card_length.py --all      every entry
    py -3.13 tools/audit_card_length.py --lang ru
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from tilawah.content import coaching  # noqa: E402

BUDGET = 70


def words(text: str) -> int:
    return len((text or "").split())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="uz", choices=("uz", "ru"))
    ap.add_argument("--all", action="store_true", help="include entries within budget")
    args = ap.parse_args()

    rows = []
    for code, spec in coaching.registry().items():
        block = spec.get(args.lang) or spec.get("uz") or {}
        visible = words(block.get("headline", "")) + words(block.get("fix", ""))
        total = visible + words(block.get("rule", "")) + words(block.get("drill", ""))
        rows.append((visible, total, code))

    rows.sort(reverse=True)
    over = [r for r in rows if r[0] > BUDGET]

    print(f"registry entries: {len(rows)}   lang: {args.lang}   budget: {BUDGET}")
    print(f"over budget on VISIBLE text: {len(over)}\n")
    print(f"{'visible':>7} {'total':>6}  code")
    print("-" * 58)
    for visible, total, code in (rows if args.all else over):
        flag = "  <-- over" if visible > BUDGET else ""
        print(f"{visible:>7} {total:>6}  {code}{flag}")

    if not args.all and not over:
        print("  (every entry is within budget on visible text)")

    print(f"\nvisible = headline + fix, what shows without tapping")
    print(f"total   = + rule + drill, both collapsed behind a disclosure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
