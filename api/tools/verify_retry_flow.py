# -*- coding: utf-8 -*-
"""Multi-mistake capture: what does each card ask the learner to record?

THE QUESTION. A recitation with ten corrections used to ask for the whole ayah
ten times - once per card - because practice.ladder() appended an AYAH rung to
every card it built. This walks a real ten-mistake attempt through the real
present() path and prints what each card actually asks for.

WHAT IS REAL HERE AND WHAT IS NOT, stated plainly because it decides how much
this proves. The model does not fit on this machine (2.42 GB against 8 GB of
RAM), so the TRANSCRIPTION is not run: the errors below are constructed as
typed_diff would have emitted them. Everything after that point is live - the
merge, the ranking, the content gate, the template substitution and the ladder
construction are the same code the API runs. That is the locate()/present()
seam, and it is where this defect lived.

    py -3.13 tools/verify_retry_flow.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from quran_transcript import Aya  # noqa: E402

from tilawah.engine.pipeline import present  # noqa: E402
from tilawah.engine.typed_errors import TypedError  # noqa: E402

# Al-Falaq, five ayat, read badly in ten places. Real words from a real sura,
# each error placed on a letter that word actually contains.
SURA = 113
MISTAKES = [
    (1, 0, "ق", "GENERIC_LETTER_SUBSTITUTED", "ك"),
    (1, 2, "ب", "QALQALA_DROP", ""),
    (1, 3, "ف", "GENERIC_LETTER_SUBSTITUTED", "ث"),
    (2, 1, "ش", "GENERIC_LETTER_SUBSTITUTED", "س"),
    (2, 3, "خ", "GENERIC_LETTER_SUBSTITUTED", "ح"),
    (3, 2, "غ", "GENERIC_LETTER_SUBSTITUTED", "ق"),
    (3, 3, "ذ", "SUB_DHAL_ZAY", "ز"),
    (4, 2, "ث", "SUB_THA_SEEN", "س"),
    # Two mistakes in ONE word, which is realistic and worth including: the
    # merge keys on (code, letter), so these must stay two cards.
    (5, 2, "ح", "SUB_HA_KHA", "خ"),
    (5, 2, "د", "LETTER_DROPPED", ""),
]


def check_fixtures() -> None:
    """Every mistake must sit on a letter its word actually contains.

    A verification tool whose fixtures are wrong proves nothing about the thing
    it claims to verify. Three of these were wrong on the first run - خ placed
    on «مَا», ذ on «غَاسِقٍ», ح on «شَرِّ» - and the headline result did not change,
    which is exactly why it needs asserting rather than eyeballing: the ladder
    shape does not depend on the letter, so a bad fixture is invisible in the
    output it produces.
    """
    bad = []
    for aya, widx, letter, _code, _heard in MISTAKES:
        words = Aya(SURA, aya).get().uthmani.split()
        word = words[widx] if widx < len(words) else ""
        if letter not in word:
            bad.append(f"{SURA}:{aya} word {widx} «{word}» has no {letter}")
    if bad:
        print("  ✗ BAD FIXTURES:")
        for line in bad:
            print(f"      {line}")
        sys.exit(1)


def build():
    """Ten errors across five ayat, located in real words."""
    out = []
    for i, (aya, widx, letter, code, heard) in enumerate(MISTAKES):
        words = Aya(SURA, aya).get().uthmani.split()
        word = words[widx] if widx < len(words) else ""
        out.append((aya, TypedError(
            code=code, at=i * 4 + 1, letter=letter,
            expected=letter if heard else "", heard=heard,
            word=word, word_index=widx)))
    return out


def main() -> None:
    check_fixtures()
    errors = build()
    print(f"\nAttempt: sura {SURA}, {len(errors)} mistakes across "
          f"{len({a for a, _ in errors})} ayat\n")

    by_aya: dict[int, list[TypedError]] = {}
    for aya, e in errors:
        by_aya.setdefault(aya, []).append(e)

    total_cards = 0
    ayah_demands = 0
    word_demands = 0

    for aya in sorted(by_aya):
        uthmani = Aya(SURA, aya).get().uthmani
        shown, _ = present(by_aya[aya], "uz", uthmani=uthmani)
        print(f"  ── {SURA}:{aya}  «{uthmani}»")
        for card in shown:
            total_cards += 1
            rungs = card["practice"]
            asks = [f"{r['focus']}:{''.join(r['items']) or '(ayah)'}"
                    for r in rungs]
            ayah_demands += sum(1 for r in rungs if r["focus"] == "ayah")
            word_demands += sum(1 for r in rungs if r["focus"] != "ayah")
            print(f"       {card['kind']:<14} {len(rungs)} action(s): "
                  f"{', '.join(asks) or '(none)'}")
        print()

    print("  " + "─" * 60)
    print(f"  cards shown ............... {total_cards}")
    print(f"  word recordings asked ..... {word_demands}")
    print(f"  FULL-AYAH recordings asked  {ayah_demands}")
    print("  " + "─" * 60)

    if ayah_demands:
        print(f"\n  ✗ FAIL: {ayah_demands} card(s) still demand the whole ayah.")
        sys.exit(1)

    print("\n  ✓ No card demands the whole ayah.")
    print("    The single full recitation is the results screen's, gated on")
    print("    every card being resolved — see Feedback.tsx, `open.length`.")


if __name__ == "__main__":
    main()
