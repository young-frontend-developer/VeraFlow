# -*- coding: utf-8 -*-
"""The daily hadith. One per day, cited, and gated like every other content
file in this project.

── WHY THIS IS NOT A LIST IN A COMPONENT ──────────────────────────────────

Because it is religious text with an attribution attached, and this app has one
rule about that: nothing is put in the Prophet's mouth ﷺ, or anyone else's,
without a named collection and a reference number beside it. That rule needs a
file a qori can read and sign off, not a string array in a TSX file that ships
whenever the frontend does.

So the set lives in hadith.json under the SAME status pattern as the tajweed
registry - every entry is `draft` until reviewed - and `today()` returns None
when nothing has been reviewed and the deployment is production. The card is
then simply not drawn. An unsourced or unchecked hadith is worse than no card.

── SELECTION IS DETERMINISTIC ─────────────────────────────────────────────

By date, not at random. A "daily hadith" that changes when the learner reopens
the app is not a daily anything, it is decoration on a shuffle - and it quietly
teaches that nothing on the screen is stable. Same day, same hadith, every time
the app is opened, on every device.

The rotation walks the whole set before repeating, which is what an ordinal date
index gives for free.
"""
import json
from datetime import date
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).parent / "hadith.json"


@lru_cache(maxsize=1)
def _all() -> list[dict]:
    if not _PATH.exists():
        return []
    return json.loads(_PATH.read_text(encoding="utf-8")).get("hadith", [])


def reviewed() -> list[dict]:
    """Entries a qori has signed off - the only ones production may show."""
    return [h for h in _all() if h.get("status") == "reviewed"]


def available(show_unreviewed: bool) -> list[dict]:
    """What this deployment is allowed to draw from.

    Outside production the drafts are shown, marked as drafts by the client,
    which is how every other piece of content in this app behaves. In
    production, reviewed only - and an empty list is a real answer.
    """
    return _all() if show_unreviewed else reviewed()


def today(lang: str = "uz", *, show_unreviewed: bool = False,
          on: date | None = None) -> dict | None:
    """One hadith for the given day, or None if there is nothing to show.

    None is a real answer and the caller must render nothing rather than
    substitute something - there is no fallback hadith, because a fallback is
    where an unreviewed one would end up.
    """
    pool = available(show_unreviewed)
    if not pool:
        return None
    day = on or date.today()
    entry = pool[day.toordinal() % len(pool)]
    body = entry.get(lang) or entry.get("uz") or ""
    if not body:
        return None
    return {
        "id": entry.get("id", ""),
        "ar": entry.get("ar", ""),
        "text": body,
        # The citation travels as separate fields rather than as one
        # pre-joined string, so the client can format it and a reviewer can
        # see exactly which collection and number is being claimed.
        "collection": entry.get("collection", ""),
        "ref": entry.get("ref", ""),
        "grading": entry.get("grading", ""),
        # The client MUST mark an unreviewed entry, the same as a draft
        # correction card. See the draft chip in Feedback.tsx.
        "draft": entry.get("status") != "reviewed",
    }


def unsourced() -> list[str]:
    """Entries missing a collection or a reference number.

    Should always be empty: the sourcing rule in hadith.json's _meta says an
    entry without a citation does not go in the file. Computed rather than
    trusted, because a hand-edited JSON file is exactly where one slips in.
    """
    return [h.get("id", "?") for h in _all()
            if not (h.get("collection") and h.get("ref"))]
