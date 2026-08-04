# -*- coding: utf-8 -*-
"""How long is each correction card, against the 60-word budget?

A card answers four questions - what happened, where, how do I fix it, what do
I practise - and only the first and third are prose. So the number that matters
is headline + the ONE instruction, and that is the whole card's text.

WHAT CHANGED, AND WHY THE OLD NUMBERS FLATTERED. This used to measure a
"visible" figure against a 70-word budget and report zero entries over, which
was true and misleading: `rule` and `drill` were merely COLLAPSED, not absent,
so the real card ran to 120 words for anyone who tapped. Both are gone from the
card now, and `fix` is narrowed to its first paragraph - see
coaching.instruction() - so measured and shown are finally the same thing.

NOTHING HERE REWRITES ANYTHING. Decision 4 puts authoring in a qori's hands and
shortening an instruction is authoring. This measures, ranks, and hands the
list over.

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

BUDGET = 60


def words(text: str) -> int:
    return len((text or "").split())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="uz", choices=("uz", "ru"))
    ap.add_argument("--all", action="store_true",
                    help="include entries within budget")
    args = ap.parse_args()

    rows = []
    for code, spec in coaching.registry().items():
        block = spec.get(args.lang) or spec.get("uz") or {}
        headline = words(block.get("headline", ""))
        # The instruction as the learner gets it, not as it sits in the file.
        tip = words(coaching.instruction(block.get("fix", "")))
        # What is authored but no longer shown, for context: this is the
        # material a qori still owns and the review tool still displays.
        unshown = words(block.get("rule", "")) + words(block.get("drill", ""))
        rows.append((headline + tip, headline, tip, unshown, code))

    rows.sort(reverse=True)
    over = [r for r in rows if r[0] > BUDGET]

    print(f"registry entries: {len(rows)}   lang: {args.lang}   "
          f"budget: {BUDGET}")
    print(f"over budget: {len(over)}\n")
    print(f"{'card':>5} {'head':>5} {'tip':>5} {'unshown':>8}  code")
    print("-" * 62)
    for card, headline, tip, unshown, code in (rows if args.all else over):
        flag = "  <-- over" if card > BUDGET else ""
        print(f"{card:>5} {headline:>5} {tip:>5} {unshown:>8}  {code}{flag}")

    if not args.all and not over:
        print("  (every card is within budget)")

    print("\ncard    = headline + tip. The ENTIRE text a learner reads.")
    print("tip     = the first paragraph of `fix`, which is all that is shown.")
    print("unshown = rule + drill: still authored, still in the registry, "
          "read by the\n          review tool, and no longer on the card.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
