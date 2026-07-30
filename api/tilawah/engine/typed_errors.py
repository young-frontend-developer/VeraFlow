# -*- coding: utf-8 -*-
"""Typed error extraction - the spine of the product.

Every downstream feature (lessons, drills, Hifz weighting) consumes the typed
error list, never a score. Ported from spike/s5_typed_errors.py; keep the two in
sync or delete the spike copy once you trust this one.
"""
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher

from .runlength import GHUNNA_LETTERS, MADD_LETTERS, QALQALA_MARK, tokenize

# Uzbek/Russian L1 interference pairs. Decision 6: these priors are the cheap
# differentiator - nobody has built this for these languages.
L1_PAIRS = {
    ("ع", "ء"): "SUB_AYN_HAMZA",
    ("ح", "خ"): "SUB_HA_KHA",
    ("ح", "ه"): "SUB_HA_HEH",
    ("ص", "س"): "SUB_SAD_SEEN",
    ("ط", "ت"): "SUB_TA_PLAIN",
    ("ض", "د"): "SUB_DAD_DAL",
    ("ظ", "ز"): "SUB_DHA_ZAY",
    ("ق", "ك"): "SUB_QAF_KAF",
    ("ذ", "ز"): "SUB_DHAL_ZAY",
    ("ث", "س"): "SUB_THA_SEEN",
    ("و", "ف"): "SUB_WAW_V",
}


@dataclass
class TypedError:
    code: str           # joins to content/rules.json
    at: int             # unit index, for highlighting the ayah
    letter: str
    expected: str = ""
    heard: str = ""
    expected_count: int = 0
    heard_count: int = 0

    def dict(self):
        return asdict(self)


def _duration_code(letter: str, exp_n: int, got_n: int) -> str:
    if letter in MADD_LETTERS:
        base = "MADD"
    elif letter in GHUNNA_LETTERS:
        base = "GHUNNA"
    else:
        base = "SHADDA"
    return f"{base}_{'SHORT' if got_n < exp_n else 'LONG'}"


def _missing(unit, at) -> TypedError:
    if unit[0] == QALQALA_MARK:
        return TypedError(code="QALQALA_DROP", at=at, letter=QALQALA_MARK)
    return TypedError(code="DELETION", at=at, letter=unit[0], expected=unit[0])


def typed_diff(expected: str, predicted: str) -> list[TypedError]:
    exp_u, got_u = tokenize(expected), tokenize(predicted)
    sm = SequenceMatcher(None, [u[0] for u in exp_u], [u[0] for u in got_u])
    out: list[TypedError] = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            # Letters match but the run length may not - the case a raw
            # character diff misreports as a missing letter.
            for k in range(i2 - i1):
                e, g = exp_u[i1 + k], got_u[j1 + k]
                if e[1] != g[1]:
                    out.append(TypedError(
                        code=_duration_code(e[0], e[1], g[1]), at=i1 + k,
                        letter=e[0], expected_count=e[1], heard_count=g[1]))

        elif op == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                e, g = exp_u[i1 + k], got_u[j1 + k]
                code = L1_PAIRS.get((e[0], g[0]), "SUBSTITUTION")
                out.append(TypedError(code=code, at=i1 + k, letter=e[0],
                                      expected=e[0], heard=g[0]))
            for k in range(n, i2 - i1):
                out.append(_missing(exp_u[i1 + k], i1 + k))
            for k in range(n, j2 - j1):
                out.append(TypedError(code="INSERTION", at=i1,
                                      letter=got_u[j1 + k][0],
                                      heard=got_u[j1 + k][0]))

        elif op == "delete":
            for k in range(i1, i2):
                out.append(_missing(exp_u[k], k))

        elif op == "insert":
            for k in range(j1, j2):
                out.append(TypedError(code="INSERTION", at=i1,
                                      letter=got_u[k][0], heard=got_u[k][0]))

    return out
