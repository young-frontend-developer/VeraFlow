# -*- coding: utf-8 -*-
"""Where the CORRECT letter comes from, and what it is like. One sentence.

THE GAP THIS CLOSES. A card could tell a learner they read ص as س, and how to
fix it, without ever telling them what ص actually is - where in the mouth it
lives or what quality it carries. For an authored pair that was survivable,
because the fix instruction usually smuggled the makhraj in. For the two
GENERIC entries it was not: GENERIC_LETTER_SUBSTITUTED and
GENERIC_SIFAT_MISMATCH catch every confusion nobody has written an entry for -
which makes them the most-shown cards in the app - and neither said one word
about where any letter comes from. The learner was told which letter was wrong
and given a drill, with no description of the target sound anywhere on the card.

KEYED BY LETTER, WHICH IS WHY IT SCALES. 28 letters against far more error
pairs: authoring the makhraj into each pair would restate one sentence dozens of
times, let the copies drift, and still leave the generics empty. One table means
every card about a letter gets one for free, including codes with no coaching
text at all - the same property the practice ladder has, for the same reason.

ALWAYS THE TARGET LETTER, NEVER THE HEARD ONE. The card exists to move the
learner toward the correct sound; describing the one they produced by mistake
describes the mistake. `expected` is preferred over `letter` because on a
substitution `letter` can be either side depending on which detector fired,
while `expected` is by definition the reference's.

NOTHING HERE IS SELECTED AT RUNTIME OR GENERATED PER CARD. This module reads
makharij.json and looks a letter up. Every sentence in that file is written
down, marked UNREVIEWED, and travels under the same draft gate as the rest of
the content - see its _meta, including the provenance warning about the book.
"""
import json
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).parent / "makharij.json"

# The Arabic letter block. Anything else - a haraka NAME like "fatha", a ṣifa
# value, a QPS notation mark, an empty string - has no makhraj and must not be
# looked up as though it did. Same single-character test the practice ladder
# uses before it puts a value in an Arabic chip.
_FIRST, _LAST = "ء", "ي"
_TATWEEL = "ـ"


@lru_cache(maxsize=1)
def _data() -> dict:
    if not _PATH.exists():
        return {}
    return json.loads(_PATH.read_text(encoding="utf-8")).get("letters", {})


def known() -> list[str]:
    """Every letter this file has a sentence for."""
    return sorted(_data())


def is_letter(value: str) -> bool:
    return (len(value) == 1 and _FIRST <= value <= _LAST
            and value != _TATWEEL)


def line(letter: str, lang: str = "uz") -> str:
    """The makhraj + ṣifat sentence for one letter, or "" if there is none.

    "" is a real answer and callers must render nothing rather than a fallback:
    an invented sentence about where a letter comes from is exactly the content
    Decision 4 reserves for a qori. Falls back to Uzbek across languages, never
    to prose of its own.
    """
    if not is_letter(letter):
        return ""
    block = _data().get(letter) or {}
    return str(block.get(lang) or block.get("uz") or "").strip()


def for_error(expected: str, letter: str, lang: str = "uz") -> str:
    """The sentence for the letter a card is trying to teach.

    `expected` wins wherever it is a real letter, because it is the reference's
    own value and therefore always the target. `letter` is the fallback: ṣifa
    errors carry the letter with no `expected` letter beside it (their
    `expected` holds a ṣifa VALUE like "mofakham", which is_letter refuses), and
    on those the letter IS the target - the learner said the right letter and
    made it wrong.
    """
    return line(expected, lang) or line(letter, lang)


def missing() -> list[str]:
    """Letters with no sentence written, so the gap stays countable.

    The alphabet is fixed at 28 and the file is expected to cover all of it, so
    this should be empty. It is computed rather than assumed because a
    hand-edited JSON file is exactly where a letter goes missing quietly.
    """
    alphabet = "ءبتثجحخدذرزسشصضطظعغفقكلمنهوي"
    return [ch for ch in alphabet if not line(ch)]
