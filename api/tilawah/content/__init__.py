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
def suras() -> list[dict]:
    """All 114, for the picker. Built by tools/build_suras.py.

    Names and ayah counts come from quran_transcript, not from the file's own
    table - see that tool. This is the whole catalogue, not the curated subset
    in ayat.json, which is a shortlist of worked examples and nothing more.
    """
    path = _DIR / "suras.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["suras"]


@lru_cache(maxsize=1)
def sura_index() -> dict[int, dict]:
    return {s["number"]: s for s in suras()}


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


@lru_cache(maxsize=1)
def _translations_file() -> dict:
    """Uzbek and Russian translations for all 6236 ayat.

    Built by tools/build_translations.py and committed, for the same reason as
    segments.json: the verse-by-verse reader shows one under every ayah, and
    fetching that live would put a third party between a learner and the text.
    """
    path = _DIR / "translations.json"
    if not path.exists():
        return {"_meta": {}, "translations": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def translations_meta() -> dict:
    return _translations_file().get("_meta", {})


def translation_of(sura: int, aya: int, lang: str) -> str:
    """One ayah's translation, or "" if the artifact is missing.

    Falls back to the other language rather than to nothing: a Russian reader
    looking at a blank space learns less than one reading the Uzbek.
    """
    entry = _translations_file().get("translations", {}).get(f"{sura}:{aya}")
    if not entry:
        return ""
    return entry.get(lang) or entry.get("uz") or ""


@lru_cache(maxsize=1)
def _reciters_file() -> dict:
    """everyayah reciters, each probed at four ayat by tools/build_reciters.py.

    Probed rather than listed: the host has partial mirrors, and a folder that
    404s on 2:282 is exactly the "playback dies on long suras" bug.
    """
    path = _DIR / "reciters.json"
    if not path.exists():
        return {"default": "", "reciters": [], "_meta": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def reciters() -> list[dict]:
    return _reciters_file().get("reciters", [])


def default_reciter() -> str:
    return _reciters_file().get("default", "")


def reciter_base_url() -> str:
    return _reciters_file().get("_meta", {}).get("base_url", "")


def is_known_reciter(rid: str) -> bool:
    return any(r["id"] == rid for r in reciters())


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


def substitution_context(fields: dict) -> dict:
    """One namespace both authoring generations can be written against.

    The coaching registries use {word} {letter} {expected} {actual}
    {n_expected} {n_actual}; rules.json was written earlier against {heard}
    {expected_count} {heard_count}. Rather than rewrite either set of authored
    text, both names are provided and point at the same values.
    """
    safe = {k: ("" if v is None else v) for k, v in fields.items()}
    safe.setdefault("word", "")
    safe["actual"] = safe.get("heard", "")
    safe["n_expected"] = safe.get("expected_count", "")
    safe["n_actual"] = safe.get("heard_count", "")
    return safe


def render(code: str, lang: str, fields: dict) -> dict | None:
    """Error code -> the coaching card, or None if nothing is authored for it.

    Prefers the v4/v5 coaching registries (headline / fix / rule / drill) and
    falls back to the older rules.json shape, which is mapped onto the same
    four fields so the client only ever handles one card:

        headline <- you_did   "what we heard", the closest thing rules.json has
        fix      <- fix
        rule     <- ""        rules.json's `rule` is a LABEL, not an
                              explanation, so it travels as `label` instead of
                              being promoted into a field it does not fill
        drill    <- drill

    Nothing is invented in that mapping; a field with no source stays empty and
    the UI omits its section.
    """
    from .coaching import render as render_coaching

    safe = substitution_context(fields)

    card = render_coaching(code, lang, safe)
    if card is not None:
        return card

    rule = rules().get(code)
    if not rule:
        return None
    block = rule.get(lang) or rule.get("uz")

    from .coaching import _fill

    out = {
        "headline": _fill(block.get("you_did", ""), safe, code=code,
                          key="you_did"),
        "fix": _fill(block.get("fix", ""), safe, code=code, key="fix"),
        "rule": "",
        "drill": _fill(block.get("drill", ""), safe, code=code, key="drill"),
        "label": block.get("rule", ""),
        "severity": rule.get("severity", "medium"),
        "reviewed": bool(rule.get("reviewed", False)),
        "unauthored": False,
    }
    return out


def unauthored_codes(codes) -> list[str]:
    """Codes the engine can emit that nobody has written content for."""
    return sorted({c for c in codes if c not in rules()})
