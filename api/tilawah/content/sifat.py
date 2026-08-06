# -*- coding: utf-8 -*-
"""Which ṣifa went wrong, named, with the physical instruction for fixing it.

WHAT THIS REPLACES
------------------
"Harfning sifati to'g'ri chiqmadi." — "the letter's ṣifa did not come out
right." That sentence was the single most-shown correction in the app, and it
answers none of the questions a card exists to answer. It does not say WHICH
property was wrong, and it does not say what to do with your tongue, throat or
lips to fix it. A learner reading it knows only that something about the letter
was off, which they already knew from hearing themselves.

The detector knew the answer the whole time. The model reports the ṣifa field
that disagreed — `ghonna`, `qalqla`, `tafkheem_or_taqeeq` — and the pipeline has
carried it on `TypedError.sifa` since ṣifa routing was built. It was simply
never asked for on the way to the card.

KEYED BY ṢIFA, NOT BY ERROR CODE, which is why this is a separate file from the
registries. One property can be wrong under several codes (TAFKHEEM_LOST,
TAFKHEEM_ADDED, RAA_TAFKHEEM_MISSING and LAM_TAFKHEEM_WRONG are all
tafkheem_or_taqeeq) and one code can be about a property no entry exists for.
Keying on the model's own field name means a card gets its named ṣifa and its
articulation instruction whether or not a specific entry was ever authored.

LETTER OVERRIDES BEAT THE GENERAL RULE, because for a handful of letters the
general rule is wrong rather than merely vague. Heaviness follows the vowel on
ر and only on ر; ghunna is lips-closed on م and tongue-to-gum-ridge on ن;
ه fails by being tightened into ح. Handing a learner the general sentence in
those cases is handing them the wrong instruction, so the specific one wins.

NOTHING HERE IS SELECTED AT RANDOM OR GENERATED AT RUNTIME. This module reads
sifat_guidance.json and looks things up. Every sentence in that file is authored
and marked unreviewed, and travels under the same draft gate as everything else.
"""
import json
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).parent / "sifat_guidance.json"

# What a card needs about a ṣifa. `wrong` exists because RULE 3 bans the
# sentence the generic entry would otherwise supply — it is the what-happened
# slot, phrased without claiming a direction, since the codes that reach the
# generic are exactly the ones whose direction was not routed.
FIELDS = ("name", "wrong", "how")


@lru_cache(maxsize=1)
def _data() -> dict:
    if not _PATH.exists():
        return {"sifat": {}, "letters": {}}
    return json.loads(_PATH.read_text(encoding="utf-8"))


def known() -> list[str]:
    """Every ṣifa field this file has words for."""
    return sorted(_data().get("sifat", {}))


def detected() -> list[str]:
    """The ṣifāt an actual detector compares today.

    The rest are authored ahead of a detector on purpose, so that adding one is
    a routing change rather than a content project. Reported rather than assumed
    so the difference stays countable — see tools/audit_cards.py.
    """
    return sorted(f for f, spec in _data().get("sifat", {}).items()
                  if spec.get("detected"))


def undetected() -> list[str]:
    return sorted(set(known()) - set(detected()))


def _block(spec: dict | None, lang: str) -> dict | None:
    """One language's block, falling back to Uzbek rather than to nothing."""
    if not spec:
        return None
    block = spec.get(lang) or spec.get("uz")
    if not block:
        return None
    out = {k: str(block.get(k, "")).strip() for k in FIELDS}
    # A half-filled entry is worse than none: it would put a named ṣifa on the
    # card with no instruction under it, which reads as though the instruction
    # failed to load.
    return out if all(out.values()) else None


def guidance(sifa: str, letter: str, lang: str) -> dict | None:
    """{name, how} for one ṣifa on one letter, or None if nothing is authored.

    None is a real answer and the caller must handle it: it means this ṣifa has
    no words yet, and the card should say nothing about it rather than fall back
    to the generic sentence this module exists to delete.
    """
    if not sifa:
        return None
    data = _data()
    specific = (data.get("letters", {}).get(letter) or {}).get(sifa)
    return _block(specific, lang) or _block(data.get("sifat", {}).get(sifa), lang)


def missing_guidance() -> list[str]:
    """Ṣifāt a detector can report that nobody has written guidance for.

    The gap that matters, and the one that used to be invisible: a routed ṣifa
    with no entry here falls straight back to the generic sentence.
    """
    from ..engine.sifat_codes import ROUTED

    return sorted(f for f in ROUTED if not guidance(f, "", "uz"))
