# -*- coding: utf-8 -*-
"""How far off is far enough to mention? One answer, read from config.

The problem this exists for: two takes of the same ayah by the same person, both
correct, do not produce the same phoneme string. A madd held 4 counts in one take
reads as 5 in the other, and typed_diff dutifully reports MADD_LONG on a correct
recitation. Under decision 5 (precision over recall) that is the expensive kind
of wrong - telling a sincere reciter they erred when they did not.

So every gradient check gets a tolerance: a deviation smaller than the threshold
is measured, recorded, and NOT shown. The thresholds live in config/tolerances.json
because they are empirical facts about a microphone, a model and a reciter, not
decisions about the code - and because tuning them must not require a deploy.

Nothing here invents a number. The shipped defaults reproduce the previous
behaviour exactly (min_delta = 1, i.e. any deviation fires); tools/calibrate.py
is what turns certified-correct recordings into the real thresholds.
"""
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .runlength import GHUNNA_LETTERS, MADD_LETTERS, tokenize
from .typed_errors import TypedError

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "tolerances.json"

# Codes whose severity is a matter of degree. Everything else is binary: the
# letter is either the right letter or it is not.
DURATION_CODES = frozenset({
    "MADD_SHORT", "MADD_LONG", "GHUNNA_SHORT", "GHUNNA_LONG",
    "SHADDA_SHORT", "SHADDA_LONG",
})


@dataclass(frozen=True)
class Verdict:
    """Why one error was kept or dropped. The harness reports these verbatim."""
    code: str
    keep: bool
    margin: float | None       # None = discrete check, no gradient to report
    threshold: float | None
    reason: str                # "" when kept


def config_path() -> Path:
    return Path(os.getenv("TILAWAH_TOLERANCES") or DEFAULT_PATH)


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> dict:
    # utf-8-sig, not utf-8: this file is meant to be hand-edited, on Windows,
    # and Notepad, VS Code's default save and PowerShell's `Out-File -Encoding
    # utf8` all write a BOM. Reading it as plain utf-8 turns a threshold edit
    # into a JSONDecodeError on the next run, which is a miserable way to
    # discover your calibration loop is broken.
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load() -> dict:
    """Config, re-read whenever the file changes.

    mtime is part of the cache key on purpose: editing a threshold and re-running
    the harness in the same process must pick the new value up, or step 4 of the
    documented loop silently scores the old numbers.
    """
    p = config_path()
    if not p.exists():
        return {"defaults": {"min_delta": 1, "min_mean_prob": 0.0}, "checks": {}}
    return _load(str(p), p.stat().st_mtime)


def rule_for(code: str, cfg: dict | None = None) -> dict:
    cfg = cfg if cfg is not None else load()
    base = dict(cfg.get("defaults") or {})
    base.setdefault("kind", "duration" if code in DURATION_CODES else "discrete")
    base.update(cfg.get("checks", {}).get(code) or {})
    return base


def margin_of(err: TypedError) -> float | None:
    """How far off this attempt was, in the check's own units.

    Duration -> whole QPS units, one unit being roughly one harakah. Discrete
    checks have no gradient, so they report None rather than a fake 1.0.
    """
    if err.code not in DURATION_CODES:
        return None
    return float(abs(err.heard_count - err.expected_count))


def judge(err: TypedError, mean_prob: float = 0.0,
          cfg: dict | None = None) -> Verdict:
    rule = rule_for(err.code, cfg)
    margin = margin_of(err)

    floor = float(rule.get("min_mean_prob") or 0.0)
    if floor > 0.0 and mean_prob < floor:
        return Verdict(err.code, False, margin, floor,
                       f"clip confidence {mean_prob:.3f} < {floor:.3f}")

    if margin is not None:
        need = float(rule.get("min_delta") or 1)
        if margin < need:
            return Verdict(err.code, False, margin, need,
                           f"off by {margin:g}, tolerance is {need:g}")
        return Verdict(err.code, True, margin, need, "")

    return Verdict(err.code, True, None, None, "")


def eligible_checks(expected: str) -> set[str]:
    """Which checks this reference could structurally have fired.

    The denominator of every false-positive rate the harness reports. Without it
    a check that was never eligible on any clip scores a flawless 0%, and a
    check with no opportunity to be wrong looks identical to one that was right.

    Lives here rather than in tools/calibrate.py so it is importable without
    dragging in soundfile and torch - the harness needs them, the tests do not.
    """
    units = tokenize(expected)
    out = {"DELETION", "INSERTION", "SUBSTITUTION", "QALQALA_DROP"}
    out.update(c for c in load().get("checks", {}) if c.startswith("SUB_"))

    # SHORT and LONG are not eligible in the same places, and collapsing them
    # would quietly inflate the SHORT denominators. _SHORT needs the reference to
    # already hold a run - you cannot recite a 1-count letter shorter than once,
    # that is a DELETION - while _LONG only needs the letter to be there at all.
    # The classes partition by letter exactly as _duration_code chooses its base:
    # madd letter, then nasal, then everything else.
    def klass(b: str) -> str:
        if b in MADD_LETTERS:
            return "MADD"
        return "GHUNNA" if b in GHUNNA_LETTERS else "SHADDA"

    for base, count, _marks in units:
        k = klass(base)
        out.add(f"{k}_LONG")
        if count > 1:
            out.add(f"{k}_SHORT")
    return out


def apply(errors: list[TypedError], mean_prob: float = 0.0,
          cfg: dict | None = None
          ) -> tuple[list[TypedError], list[tuple[TypedError, Verdict]]]:
    """-> (errors worth reporting, errors dropped as within-tolerance).

    The dropped ones are returned rather than discarded: an attempt that was
    flagged and then silenced is not the same thing as a clean one, and
    pipeline.analyze() must not praise it as perfect.
    """
    cfg = cfg if cfg is not None else load()
    kept, dropped = [], []
    for e in errors:
        v = judge(e, mean_prob, cfg)
        (kept if v.keep else dropped).append(e if v.keep else (e, v))
    return kept, dropped
