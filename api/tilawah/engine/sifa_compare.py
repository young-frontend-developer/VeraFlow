# -*- coding: utf-8 -*-
"""Reference ṣifāt vs predicted ṣifāt. OBSERVATION ONLY - never shown to anyone.

typed_diff compares phoneme STRINGS. It never reads the ṣifa level the model also
predicts, which means tafkheem, hams, shidda and jahr have no detector today even
though the registry lists error codes for all four.

Before building one, there is a number worth having: on recitation a qualified
reciter certifies as CORRECT, how often does the predicted ṣifa disagree with the
reference anyway? That rate is the floor on the false-positive rate of any ṣifa
detector built on this model. If it is high, the detector is not buildable at
this operating point and no amount of threshold tuning fixes it - which is worth
discovering from a config file rather than from a learner.

So this module measures disagreement and stops there. It emits no TypedError, is
imported by nothing in the request path, and tools/calibrate.py is its only
caller.
"""
from dataclasses import dataclass
from difflib import SequenceMatcher

HARAKAT = set("َُِ")
MARKS = HARAKAT | {"ڇ", "ْ", "ّ"}

FIELDS = ("tafkheem_or_taqeeq", "hams_or_jahr", "shidda_or_rakhawa",
          "ghonna", "qalqla", "itbaq")


@dataclass
class SifaDiff:
    at: int                # index into the reference group list
    letter: str
    field: str
    expected: str
    heard: str
    prob: float            # model confidence in the value it predicted


def _base(text: str) -> str:
    for ch in text or "":
        if ch not in MARKS:
            return ch
    return ""


def reference_groups(sifat) -> list[dict]:
    """quran_phonetizer ṣifāt -> plain dicts, same shape as the predicted side."""
    out = []
    for s in sifat:
        g = getattr(s, "phonemes", None) or getattr(s, "phonemes_group", None)
        text = g if isinstance(g, str) else getattr(g, "text", "")
        d = {"phonemes": text or ""}
        for f in FIELDS:
            v = getattr(s, f, None)
            d[f] = getattr(v, "text", v)
        out.append(d)
    return out


def compare(ref_groups: list[dict], pred_groups: list[dict]) -> list[SifaDiff]:
    """Aligned ṣifa disagreements.

    Alignment is over base letters, not positions: the model may emit a different
    number of groups than the reference, and comparing group i to group i after a
    single insertion would report every following letter as wrong. Only groups the
    aligner matched as EQUAL are compared - anything inside a replace/insert/delete
    block is a phoneme-level difference, which is typed_diff's job to report, not
    this module's.
    """
    ref_keys = [_base(g["phonemes"]) for g in ref_groups]
    pred_keys = [_base(g.get("phonemes") or "") for g in pred_groups]
    sm = SequenceMatcher(None, ref_keys, pred_keys)

    out: list[SifaDiff] = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            continue
        for k in range(i2 - i1):
            r, p = ref_groups[i1 + k], pred_groups[j1 + k]
            probs = p.get("probs") or {}
            for f in FIELDS:
                exp, got = r.get(f), p.get(f)
                if exp is None or got is None or exp == got:
                    continue
                out.append(SifaDiff(
                    at=i1 + k, letter=ref_keys[i1 + k], field=f,
                    expected=str(exp), heard=str(got),
                    prob=float(probs.get(f) or 0.0)))
    return out


def alignment_ratio(ref_groups: list[dict], pred_groups: list[dict]) -> float:
    """Fraction of reference groups the aligner could match at all.

    Reported alongside the diffs because a low ratio means the ṣifa numbers rest
    on very little: they only cover the letters that lined up.
    """
    if not ref_groups:
        return 0.0
    ref_keys = [_base(g["phonemes"]) for g in ref_groups]
    pred_keys = [_base(g.get("phonemes") or "") for g in pred_groups]
    sm = SequenceMatcher(None, ref_keys, pred_keys)
    matched = sum(size for _, _, size in sm.get_matching_blocks())
    return matched / len(ref_keys)
