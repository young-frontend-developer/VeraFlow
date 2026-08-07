# -*- coding: utf-8 -*-
"""RULE 13. Walk every card the engine can produce and check it can answer.

    which letter · which occurrence · which rule · which ṣifa · which duration
    which articulation point · which tongue/throat/lip position · where's the
    audio · can they retry now

WHY A SCRIPT AND NOT A REVIEW. There are 64 registry entries across two
languages, and each renders differently depending on which letter the detector
found, whether the ṣifa is known, and whether the word could be located. Reading
them is how the ذ-named card for a ظ mistake survived three passes of manual
review: it is correct in the registry, correct in the renderer, and wrong only
in the combination.

NOT EVERY QUESTION APPLIES TO EVERY CARD, and pretending otherwise would make
the audit noise. A letter substitution has no duration to report; a madd error
has no ṣifa. Each check therefore states its own precondition, and a card is
only asked the questions its own kind raises - the same discipline as
[[tilawah-precondition-narrowing]]: a check that fires everywhere is a check
that measures nothing.

    py -3.13 tools/audit_cards.py            # summary, exit 1 on any failure
    py -3.13 tools/audit_cards.py --verbose  # every card, every answer
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tilawah.content import coaching, sifat                        # noqa: E402
from tilawah.engine import cards, practice                         # noqa: E402
from tilawah.engine.sifat_codes import ROUTED                      # noqa: E402
from tilawah.engine.typed_errors import EMITTED_CODES, TypedError  # noqa: E402

LANGS = ("uz", "ru")

# A plausible detection for each shape of error, so a card is audited with the
# fields it would really carry rather than with a blank namespace.
SAMPLES = {
    "substitution": dict(letter="ص", expected="ص", heard="س",
                         word="ٱلصَّمَدُ", word_index=1, at=3),
    "duration":     dict(letter="ا", expected_count=4, heard_count=2,
                         word="قَالَ", word_index=0, at=2),
    "haraka":       dict(letter="ب", expected="sukun", heard="fatha",
                         word="أَبْصَـٰرِهِمْ", word_index=7, at=29),
    "sifat":        dict(letter="ط", expected="mofakham", heard="moraqaq",
                         sifa="tafkheem_or_taqeeq", word="ٱلطَّارِقُ",
                         word_index=2, at=5),
    "qalqala":      dict(letter="د", sifa="qalqla", word="يَلِدْ",
                         word_index=0, at=4),
}


def shape_of(code: str, group: str) -> str:
    if code.startswith(("MADD_", "SHADDA_", "GHUNNA_")) or group in ("madd",
                                                                    "ghunna"):
        return "duration"
    if code.startswith(("HARAKA_", "SUKUN_")) or group == "haraka":
        return "haraka"
    if "QALQAL" in code:
        return "qalqala"
    if group == "sifat":
        return "sifat"
    return "substitution"


def render(code: str, lang: str, shape: str) -> dict:
    """One card, the way pipeline.present would build it."""
    from tilawah.engine.pipeline import _name_the_sifat
    from tilawah import content

    err = TypedError(code=code, **SAMPLES[shape])
    body = content.render(code, lang, err.dict())
    guide = sifat.guidance(err.sifa, err.letter, lang)
    body = _name_the_sifat(err, body, guide)
    return {
        "err": err,
        "body": body or {},
        "guide": guide or {},
        "kind": cards.kind_of(code, (body or {}).get("group", ""), err.sifa),
        # code and expected_count pick the ladder shape - the audit renders the
        # card "the way pipeline.present would build it", so it has to pass the
        # same two arguments or it would audit a ladder no learner ever sees.
        "practice": practice.ladder(err.letter, err.word, err.word_index,
                                    code=code,
                                    expected_count=err.expected_count,
                                    letter_audio=(body or {}).get(
                                        "audio_pair", "")),
    }


# ── the nine questions ────────────────────────────────────────────────────
# Each returns "" when answered, or the reason it is not. `None` means the
# question does not apply to this card and it is not counted either way.

def q_letter(c) -> str | None:
    if not practice.is_letter(c["err"].letter):
        # ṣifa errors can legitimately carry no single letter. What must never
        # happen is a card claiming one that is not a letter at all.
        return ("names a non-letter as the letter"
                if c["err"].letter else None)
    return ""


def q_occurrence(c) -> str | None:
    """Answered structurally: the span and ordinal are computed in the pipeline
    from the ayah text, which this harness does not have. What is checkable
    here is that the card would have somewhere to put them."""
    return "" if c["err"].word else None


def q_rule(c) -> str:
    name = c["body"].get("label", "") or c["guide"].get("name", "")
    if name:
        return ""
    # The kind title is a real name too, and it is always present - so this
    # only fails if even that is missing.
    return "" if c["kind"] in cards.KINDS else "no rule name and no kind"


def q_sifa(c) -> str | None:
    if not c["err"].sifa:
        return None
    return "" if c["guide"].get("name") else \
        f"ṣifa {c['err'].sifa!r} has no authored name"


def q_duration(c) -> str | None:
    e = c["err"]
    if not (e.expected_count or e.heard_count):
        return None
    return "" if e.expected_count and e.heard_count else \
        "a duration error missing one of its two counts"


def q_articulation(c) -> str | None:
    """Which mouth position, and which tongue/throat/lip position - one
    question, because one sentence answers both."""
    if not c["err"].sifa:
        return None
    return "" if c["guide"].get("how") else \
        f"ṣifa {c['err'].sifa!r} has no physical instruction"


def q_audio(c) -> str:
    """Not "audio exists" - "the card is honest about whether it does".

    Every rung must declare a source it can actually play or none at all. A
    rung claiming audio with no URL is the dead button this project keeps
    refusing to ship.
    """
    for rung in c["practice"]:
        if rung["audio"] and not rung["audio_source"]:
            return f"rung {rung['focus']} has audio with no source"
        if rung["audio_source"] == "letter" and not rung["audio"]:
            return f"rung {rung['focus']} claims letter audio with no file"
    return ""


def q_retry(c) -> str:
    rungs = c["practice"]
    if not rungs:
        return "no practice ladder at all"
    if not any(r["recordable"] for r in rungs):
        return "nothing on the ladder can be recorded"
    for r in rungs:
        if r["recordable"] and r["check"] != practice.SCORED:
            return f"rung {r['focus']} is recordable but not scored"
        if r["check"] == practice.SCORED and not r["recordable"]:
            return f"rung {r['focus']} claims a score it cannot take"
    return ""


def q_no_wrong_letter(c) -> str:
    """The one that keeps being the real defect: text about another letter."""
    letter = c["err"].letter
    for key in ("headline", "fix"):
        if coaching.contradicts_letter(c["err"].code, c["body"].get(key, ""),
                                       letter):
            return f"{key} names a letter other than {letter!r}"
    return ""


def q_no_code_on_screen(c) -> str:
    code = c["err"].code
    for key in ("headline", "fix"):
        if code in c["body"].get(key, ""):
            return f"the raw code appears in {key}"
    if code in c["body"].get("label", ""):
        return "the raw code appears in the rule name"
    return ""


CHECKS = [
    ("which letter", q_letter),
    ("which occurrence", q_occurrence),
    ("which rule", q_rule),
    ("which ṣifa", q_sifa),
    ("which duration", q_duration),
    ("articulation", q_articulation),
    ("where's the audio", q_audio),
    ("can they retry", q_retry),
    ("no wrong letter", q_no_wrong_letter),
    ("no code on screen", q_no_code_on_screen),
]


def audit() -> list[str]:
    """Every failure, as one line each."""
    failures = []
    codes = sorted(set(coaching.registry()) | set(EMITTED_CODES))
    for code in codes:
        group = (coaching.entry(code) or {}).get("group", "")
        shape = shape_of(code, group)
        for lang in LANGS:
            c = render(code, lang, shape)
            for name, check in CHECKS:
                why = check(c)
                if why:
                    failures.append(f"{code}.{lang} [{name}] {why}")
    return failures


def gaps() -> list[str]:
    """Not failures - known, named holes, printed so they stay countable."""
    out = []
    for f in sifat.missing_guidance():
        out.append(f"ṣifa {f}: detected and routed, no guidance authored")
    for f in sifat.undetected():
        out.append(f"ṣifa {f}: guidance authored, no detector compares it")
    for m in coaching.missing_audio():
        out.append(f"audio {m}")
    unrouted = sorted(set(sifat.known()) - set(ROUTED) - set(sifat.undetected()))
    for f in unrouted:
        out.append(f"ṣifa {f}: compared but not routed to any code")
    return out


def main() -> int:
    verbose = "--verbose" in sys.argv
    failures = audit()
    known = gaps()

    n_codes = len(set(coaching.registry()) | set(EMITTED_CODES))
    print(f"audited {n_codes} codes x {len(LANGS)} languages x "
          f"{len(CHECKS)} questions")

    if verbose:
        for code in sorted(set(coaching.registry()) | set(EMITTED_CODES)):
            group = (coaching.entry(code) or {}).get("group", "")
            c = render(code, "uz", shape_of(code, group))
            answers = " ".join(
                "-" if check(c) is None else ("x" if check(c) else "+")
                for _n, check in CHECKS)
            print(f"  {answers}  {code}")

    if known:
        print(f"\nKNOWN GAPS ({len(known)}) - not failures, but not invisible:")
        for g in known:
            print(f"  · {g}")

    if failures:
        print(f"\nINCOMPLETE CARDS ({len(failures)}):")
        for f in failures:
            print(f"  ! {f}")
        return 1

    print("\nevery card answers every question that applies to it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
