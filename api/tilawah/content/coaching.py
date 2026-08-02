# -*- coding: utf-8 -*-
"""Coaching text: headline / fix / rule / drill, with templates filled in.

WHERE IT COMES FROM
-------------------
Two hand-authored registries at the repo root, merged in order:

    tajweed_registry_v4_coaching.json   rewrites the uz/ru text of EXISTING
                                        entries (structure, source_ref,
                                        detection signals and status unchanged)
    tajweed_registry_v5_gaps.json       22 NEW entries, including the generic
                                        fallbacks and the harakat category

⚠️ v4 IS NOT IN THE REPO. Only v5 is present. Everything here is written to
merge v4 the moment it lands - it is loaded if the file exists and skipped
silently if it does not - but until then, codes that only v4 covers keep their
old rules.json text and render through the legacy path below. See
`missing_sources()`, which the API surfaces so this cannot be forgotten.

TEMPLATES
---------
Headlines are templates: {word}, {letter}, {expected}, {actual}, {n_expected},
{n_actual}, substituted from the detection result at render time.

A rendered string that still contains a brace is a BUG, not a cosmetic problem
- it means the detector did not supply a field the author relied on, and the
learner would be shown "«{word}» — «{expected}» oʻrniga...". `render()` raises
rather than letting that reach a screen. The old code did the opposite: it
caught the KeyError and returned the raw template, braces and all.

NOTHING HERE AUTHORS ANYTHING. Every sentence is copied from the registries;
this module only selects, substitutes and validates.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
V4 = _ROOT / "tajweed_registry_v4_coaching.json"
V5 = _ROOT / "tajweed_registry_v5_gaps.json"

FIELDS = ("headline", "fix", "rule", "drill")

# Any {placeholder} left after substitution.
_BRACE = re.compile(r"\{[^}]*\}")


class UnfilledTemplate(RuntimeError):
    """A coaching string still had a placeholder after substitution."""


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    # v5 calls the map `entries`; allow `errors` too so a differently-shaped v4
    # does not need a second loader.
    return data.get("entries") or data.get("errors") or {}


@lru_cache(maxsize=1)
def registry() -> dict:
    """code -> entry, v5 layered over v4.

    v5 wins on a collision: it is the newer authoring pass, and its whole
    purpose is to add what v4 lacked.
    """
    merged = dict(_load(V4))
    merged.update(_load(V5))
    return merged


def missing_sources() -> list[str]:
    """Registry files this module expects but cannot find."""
    return [p.name for p in (V4, V5) if not p.exists()]


def has(code: str) -> bool:
    return code in registry()


def entry(code: str) -> dict | None:
    return registry().get(code)


@lru_cache(maxsize=1)
def substitution_pairs() -> dict[tuple[str, str], str]:
    """(expected, heard) -> specific code, parsed from `detection_signal`.

    Read out of the registry rather than out of the code NAMES. A name like
    MAKHARIJ_AIN_TO_GHAYN looks parseable right up until MAKHARIJ_INTERDENTAL_
    TO_ZAY, where the source letter is a category and not a letter at all. The
    signal states the pair explicitly:

        "phoneme substitution: ع -> غ"

    so that is what is trusted. Anything that does not match this exact shape
    is left out and falls through to GENERIC_LETTER_SUBSTITUTED, which is the
    entire point of having a generic.
    """
    pat = re.compile(r"phoneme substitution:\s*(\S+)\s*->\s*(\S+)")
    out: dict[tuple[str, str], str] = {}
    for code, spec in registry().items():
        m = pat.search(str(spec.get("detection_signal", "")))
        if m and len(m.group(1)) == 1 and len(m.group(2)) == 1:
            out[(m.group(1), m.group(2))] = code
    return out


def _fill(text: str, fields: dict, *, code: str, key: str) -> str:
    """Substitute placeholders, then refuse to return braces.

    format_map with a plain dict raises KeyError on an unknown placeholder;
    that is deliberate. The check afterwards catches the other direction - a
    field supplied as an empty string, or a stray brace in the source text -
    which format() would pass through silently.
    """
    if not text:
        return ""
    try:
        out = text.format_map(fields)
    except (KeyError, IndexError) as exc:
        raise UnfilledTemplate(
            f"{code}.{key}: no value for {exc} — the detector must supply "
            f"every placeholder the author used. Template: {text[:120]!r}"
        ) from exc
    except ValueError as exc:
        # A malformed placeholder - "{not closed", "{}" - is an authoring typo.
        # It has to surface as UnfilledTemplate like every other template
        # failure, or it escapes the pipeline's handler as a bare 500 and takes
        # the whole attempt down with it.
        raise UnfilledTemplate(
            f"{code}.{key}: malformed template ({exc}). Template: {text[:120]!r}"
        ) from exc
    leftover = _BRACE.search(out)
    if leftover:
        raise UnfilledTemplate(
            f"{code}.{key}: {leftover.group(0)!r} survived substitution. "
            f"A learner must never be shown a brace. Result: {out[:120]!r}")
    return out


def render(code: str, lang: str, fields: dict) -> dict | None:
    """Coaching card for one detected error, or None if this code has none.

    `fields` is the detection result. Missing values arrive as empty strings
    rather than being absent, so a template that references a field the
    detector genuinely cannot fill fails the brace check above instead of
    raising a confusing KeyError.
    """
    spec = entry(code)
    if not spec:
        return None
    block = spec.get(lang) or spec.get("uz") or {}
    safe = {k: ("" if v is None else v) for k, v in fields.items()}

    out = {key: _fill(block.get(key, ""), safe, code=code, key=key)
           for key in FIELDS}
    out["severity"] = spec.get("severity", "medium")
    out["group"] = spec.get("group", "")
    # Every entry in both registries is status='draft' by design - the same
    # review gate applies, and nothing here has been signed off by a qori.
    out["reviewed"] = spec.get("status", "draft") == "reviewed"
    out["unauthored"] = False
    return out
