# -*- coding: utf-8 -*-
"""Render restructured cards exactly as the API would send them.

WHY A TOOL AND NOT A TEST. A test asserts that a field is non-empty; this
prints the sentence a learner reads, in both languages and at both levels, so
the wording can be reviewed by someone who is not going to read present().
Every card below comes off the real path - real phonetizer, real rule
placement, real merge, real template substitution - so a card that renders
here renders in the app.

The scenarios are hand-built TypedErrors rather than recordings, for the reason
in tilawah-model-wont-fit: inference does not fit on this machine. What is
faked is only the model's opinion. Everything downstream of it is live, which
is the seam worth exercising.

    py -3.13 tools/render_samples.py
    py -3.13 tools/render_samples.py --lang ru
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from quran_transcript import Aya, quran_phonetizer  # noqa: E402

from tilawah.engine.moshaf import MOSHAF  # noqa: E402
from tilawah.engine.pipeline import _rules_at, locate, present  # noqa: E402
from tilawah.engine.segments import (unit_char_spans,  # noqa: E402
                                     unit_spans_for_range)
from tilawah.engine.typed_errors import TypedError  # noqa: E402


def units(sura: int, aya: int):
    """(uthmani, flat phonemes, unit char spans) for one whole ayah."""
    uthmani = Aya(sura, aya).get().uthmani
    flat = quran_phonetizer(uthmani, MOSHAF, remove_spaces=True)
    return uthmani, flat.phonemes, unit_char_spans(flat.phonemes)


def find_unit(phonemes: str, spans, char: str, *, min_run: int = 1) -> int:
    """The first unit whose text is `char` repeated at least `min_run` times.

    How a scenario names the sound it is about without hard-coding an index
    that shifts the moment the phonetizer changes.
    """
    for at, (a, b) in enumerate(spans):
        text = phonemes[a:b]
        if text and text[0] == char and len(text) >= min_run:
            return at
    raise LookupError(f"no unit of {char!r}x{min_run} in {phonemes!r}")


# ── the five scenarios ────────────────────────────────────────────────────
# Each is a real ayah, a real position in it, and the error a learner actually
# makes there. The comment on each says what the learner did.
SCENARIOS = [
    # Held the 6-count madd of الٓمٓ for about 2. Every letter correct.
    dict(name="MADD_TOO_SHORT", sura=2, aya=1, char="ا", min_run=6,
         code="MADD_TOO_SHORT", expected_count=6, heard_count=2),
    # Read the tashdid nun of إِنَّ with no nasalisation.
    dict(name="GHUNNA_MISSING", sura=103, aya=2, char="ن", min_run=2,
         code="GHUNNA_MISSING", sifa="ghonna"),
    # Sounded the nun of مِن شَرِّ instead of hiding it.
    dict(name="IKHFA_MISSING", sura=114, aya=4, char="ں",
         code="IKHFA_MISSING"),
    # Read the ص of صِرَٰطَ as a plain س.
    dict(name="MAKHARIJ_SAD_TO_SEEN", sura=1, aya=7, char="ص",
         code="SUB_SAD_SEEN", expected="ص", heard="س"),
    # Dropped the madd alif of ٱلرَّحْمَـٰنِ.
    dict(name="LETTER_DROPPED", sura=1, aya=3, char="ا", min_run=2,
         code="LETTER_DROPPED", expected="ا"),
]


def build(scn: dict) -> tuple[TypedError, str, str]:
    uthmani, phonemes, spans = units(scn["sura"], scn["aya"])
    at = find_unit(phonemes, spans, scn["char"], min_run=scn.get("min_run", 1))

    words = uthmani.split()

    e = TypedError(
        code=scn["code"], at=at,
        letter=scn.get("expected") or scn["char"],
        expected=scn.get("expected", ""), heard=scn.get("heard", ""),
        expected_count=scn.get("expected_count", 0),
        heard_count=scn.get("heard_count", 0),
        sifa=scn.get("sifa", ""),
    )
    # THE REAL locate(), not a hand-rolled word lookup. It does two jobs and
    # the second is easy to forget: it attaches the word, and it resolves QPS
    # NOTATION MARKS back to Arabic letters. ں is the ikhfa noon and ڇ the
    # qalqalah mark - neither is a letter, and a card built without this step
    # prints «ں» where the learner needs to read «ن». A harness that skipped it
    # would show wording the app never produces, which is the one thing a
    # review harness may not do.
    locate(e_list := [e], uthmani, scn["sura"], scn["aya"], 0, len(words))
    return e_list[0], uthmani, phonemes


def render(scn: dict, lang: str) -> None:
    e, uthmani, phonemes = build(scn)
    shown, _silent = present([e], lang, uthmani=uthmani,
                             spans=unit_spans_for_range(
                                 scn["sura"], scn["aya"], 0,
                                 len(uthmani.split())),
                             rules_at=_rules_at(uthmani, phonemes))
    if not shown:
        print(f"  !! {scn['name']}: nothing shown (gated or template error)")
        return

    r = shown[0]
    c = r["content"] or {}
    kind = c.get("card_kind", 0)

    print(f"\n{'─' * 66}")
    print(f"{scn['name']}   [{scn['sura']}:{scn['aya']}]   "
          f"KIND {kind or '— (not yet restructured)'}   lang={lang}")
    print(f"  placed rule: {r.get('rule_code') or '(none)'}"
          f"   rule_name: {r.get('rule_name') or '(none)'}")
    print(f"{'─' * 66}")

    print(f"\n  ┌─ STANDARD {'─' * 50}")
    print(f"  │  {c.get('headline', '')}")
    if c.get("explanation"):
        print(f"  │  {c['explanation']}")
    if c.get("correction") or c.get("fix"):
        print(f"  │  {c.get('correction') or c.get('fix')}")
    if c.get("retry"):
        print(f"  │  🎙  {c['retry']}")
    if kind == 1 and c.get("rule_text"):
        print(f"  │  ❔ {c['rule_text']}")
    print(f"  └{'─' * 61}")

    simple = c.get("simplified")
    if simple:
        print(f"\n  ┌─ 💡 EXPLAIN SIMPLY {'─' * 42}")
        print(f"  │  {simple.get('explanation', '')}")
        if simple.get("correction"):
            print(f"  │  {simple['correction']}")
        if c.get("retry"):
            print(f"  │  🎙  {c['retry']}")
        print(f"  └{'─' * 61}")
    else:
        print("\n  (no simplified level authored — button does not render)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="uz", choices=("uz", "ru"))
    ap.add_argument("--both", action="store_true")
    args = ap.parse_args()

    langs = ("uz", "ru") if args.both else (args.lang,)
    for lang in langs:
        for scn in SCENARIOS:
            try:
                render(scn, lang)
            except Exception as exc:  # noqa: BLE001
                print(f"\n  !! {scn['name']}: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
