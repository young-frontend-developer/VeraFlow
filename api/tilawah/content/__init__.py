# -*- coding: utf-8 -*-
"""Scholar-authored content. Loaded once at import, never written at runtime.

Decision 4 lives here: every learner-facing sentence about tajweed comes out of
these JSON files. An LLM may later translate or soften the encouragement line,
but it must never author a rule, a correction, or a reason.
"""
import json
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent
LANGS = ("uz", "ru")


@lru_cache(maxsize=1)
def rules() -> dict:
    data = json.loads((_DIR / "rules.json").read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


@lru_cache(maxsize=1)
def ayat() -> list[dict]:
    return json.loads((_DIR / "ayat.json").read_text(encoding="utf-8"))["ayat"]


@lru_cache(maxsize=1)
def ayat_index() -> dict[tuple[int, int], dict]:
    return {(a["sura"], a["aya"]): a for a in ayat()}


@lru_cache(maxsize=1)
def _segments_file() -> dict:
    """Precomputed practice segments for the whole Quran.

    Built by tools/build_segments.py and committed - packing an ayah costs
    0.2-3 s, which must not happen in a request.
    """
    path = _DIR / "segments.json"
    if not path.exists():
        return {"_meta": {}, "segments": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def segments_meta() -> dict:
    return _segments_file().get("_meta", {})


@lru_cache(maxsize=4096)
def segments_of(sura: int, aya: int) -> list[dict]:
    """[{start_word, num_words, n_phonemes}] covering the ayah in order."""
    raw = _segments_file().get("segments", {}).get(f"{sura}:{aya}")
    if not raw:
        return []
    return [{"start_word": s, "num_words": n, "n_phonemes": p}
            for s, n, p in raw]


DEV_OVERRIDE = "DEV-OVERRIDE"


def status_of(code: str) -> str:
    """ship | teacher | collect. Unknown codes are never shown."""
    return rules().get(code, {}).get("status", "collect")


def dev_overrides() -> list[str]:
    """Codes marked reviewed WITHOUT a qori actually reviewing them.

    These exist so the app can be demonstrated end to end before content review
    is done. They are not fit to launch. Three things surface them: this
    function, a startup WARNING banner, and a test that fails on purpose.
    """
    return sorted(
        code
        for code, rule in rules().items()
        if str(rule.get("reviewed_by", "")).startswith(DEV_OVERRIDE)
    )


def render(code: str, lang: str, fields: dict) -> dict | None:
    """Error code -> localised strings with {placeholders} filled.

    Returns None when the code has no authored content, which is a bug worth
    surfacing rather than papering over - see unauthored_codes().
    """
    rule = rules().get(code)
    if not rule:
        return None
    block = rule.get(lang) or rule.get("uz")
    safe = {k: ("" if v is None else v) for k, v in fields.items()}
    out = {}
    for key in ("rule", "you_did", "fix", "drill"):
        text = block.get(key, "")
        try:
            out[key] = text.format(**safe)
        except (KeyError, IndexError):
            out[key] = text
    out["severity"] = rule.get("severity", "medium")
    out["reviewed"] = bool(rule.get("reviewed", False))
    return out


def unauthored_codes(codes) -> list[str]:
    """Codes the engine can emit that nobody has written content for."""
    return sorted({c for c in codes if c not in rules()})
