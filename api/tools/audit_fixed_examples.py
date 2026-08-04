# -*- coding: utf-8 -*-
"""Which authored cards name a letter the learner may not have got wrong?

THE DEFECT. A qalqalah card fired on ق shows "«أَحَدْ» oxiridagi «د» ni ayting" -
an instruction about د, because د is the example the entry was written around.
Qalqalah applies to five letters, hams to ten, tafkheem to seven; one worked
example cannot serve all of them, and the learner is told to practise a letter
they did not say.

WHY IT IS A CONTENT PROBLEM AND NOT A CODE ONE. The letter is baked into the
authored sentence, not passed into a {placeholder}. Nothing here can rewrite
those sentences - decision 4 puts every learner-facing sentence about tajweed in
a qori's hands, and swapping the letter in a worked example silently changes the
example's makhraj claim. So this MEASURES and hands the list over.

WHAT IS ALREADY SAFE. `rule` and `drill` no longer reach a learner at all, so a
fixed example buried in either of those is not a live defect; the practice
ladder is derived from the detected letter and is always correct. What remains
live is `headline` and `fix`, which are the two fields a card prints.

    py -3.13 tools/audit_fixed_examples.py
    py -3.13 tools/audit_fixed_examples.py --lang ru
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from tilawah.content import coaching  # noqa: E402

# The families where one code covers MANY letters. An entry whose code names a
# specific confusion (MAKHARIJ_SAD_TO_SEEN) is entitled to talk about ص and س -
# that IS the error. The problem is only where the code is letter-generic.
FAMILIES = {
    "QALQALAH": "ق ط ب ج د",
    "QALQALA": "ق ط ب ج د",
    "HAMS": "ف ح ث ه ش خ ص س ك ت",
    "JAHR": "the 19 voiced letters",
    "SHIDDA": "أ ج د ق ط ب ك ت",
    "TAFKHEEM": "خ ص ض ط ظ غ ق",
    "TARQIQ": "every thin letter",
    "MADD": "ا و ي",
    "GHUNNA": "ن م",
    "IKHFA": "the 15 ikhfa letters",
    "IZHAR": "the 6 izhar letters",
    "IDGHAM": "the 6 idgham letters",
    "IQLAB": "ن before ب",
    "LETTER_": "any letter",
    "HARAKA": "any letter",
    "SUKUN": "any letter",
    "GENERIC": "any letter",
}

_ARABIC = re.compile(r"[ء-ي]")
# A run of Arabic script - a quoted word or letter inside the sentence.
_RUN = re.compile(r"[ء-ٰٟۖ-ۭ]+")


def family_of(code: str) -> tuple[str, str] | None:
    for prefix, letters in FAMILIES.items():
        if code.startswith(prefix):
            return prefix, letters
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="uz", choices=("uz", "ru"))
    args = ap.parse_args()

    rows = []
    for code, spec in sorted(coaching.registry().items()):
        fam = family_of(code)
        if not fam:
            continue                       # letter-specific entry: exempt
        block = spec.get(args.lang) or spec.get("uz") or {}
        for field in coaching.CARD_FIELDS:
            text = block.get(field, "")
            if field == "fix":
                text = coaching.instruction(text)
            if not text:
                continue
            # A {placeholder} means the author DID parameterise it - fine.
            runs = [r for r in _RUN.findall(text)
                    if _ARABIC.search(r)]
            if not runs:
                continue
            rows.append((code, fam[1], field, runs, text))

    print(f"lang: {args.lang}")
    print(f"letter-generic entries naming specific Arabic script "
          f"in a SHOWN field: {len(rows)}\n")
    for code, applies, field, runs, text in rows:
        print(f"  {code}.{field}")
        print(f"     applies to : {applies}")
        print(f"     names      : {' '.join(runs)}")
        print(f"     text       : {text[:110]}")
        print()

    if not rows:
        print("  (no shown field of a letter-generic entry names a fixed example)")
    print("These need per-letter authoring by a qori, or rewriting to use the")
    print("{letter} placeholder the detector already supplies. Nothing here")
    print("may be rewritten automatically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
