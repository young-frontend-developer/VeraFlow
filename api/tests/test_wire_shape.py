# -*- coding: utf-8 -*-
"""The shape of an error on the wire is a contract. Pin it.

WHY THIS FILE EXISTS. `words` was added to the rendered error for card merging.
The client indexes it directly — `error.words.map(...)` — and when a payload
arrived without it, React threw inside the card, unmounted the tree, and the
learner got a WHITE SCREEN after waiting minutes for inference. Nothing failed
in CI, because nothing asserted what the client is entitled to receive.

Two things produce error dicts and both are covered here:

  present()            fresh analysis — must emit the full shape
  cards.ensure_shape() replay of an attempt PERSISTED BEFORE these fields
                       existed, which is a permanent source of half-shaped
                       records living in SQLite

The client is deliberately NOT defensive about these keys. A `?? []` at every
use site turns a contract violation into a card that silently renders wrong,
which is harder to find than a crash and worse than either. The contract is
enforced here instead.
"""
import json

import pytest

from tilawah.api.schemas import AttemptOut
from tilawah.engine import cards, pipeline
from tilawah.engine.typed_errors import TypedError


def sample() -> list[TypedError]:
    return [
        TypedError(code="SUB_SAD_SEEN", at=2, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
        TypedError(code="SUB_SAD_SEEN", at=5, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
        # no registry entry — the unauthored path must carry the shape too
        TypedError(code="GHUNNA_LONG", at=9, letter="ن", expected_count=2,
                   heard_count=5, word="مِنْ", word_index=2),
        # a ṣifa error, which reaches present() by a different route
        TypedError(code="TAFKHEEM_LOST", at=11, letter="ط", expected="mofakham",
                   heard="moraqaq", sifa="tafkheem_or_taqeeq", word="طٰهٰ",
                   word_index=3),
    ]


def test_present_emits_exactly_the_wire_keys():
    """Exact set, both directions.

    Missing key  -> the client throws on it.
    Extra key    -> something is being sent that nothing documents, and the
                    next person to read cards.WIRE_KEYS will be wrong.
    """
    shown, _ = pipeline.present(sample(), "uz")
    assert shown, "fixture produced no cards; the test would assert nothing"
    for card in shown:
        assert set(card.keys()) == set(cards.WIRE_KEYS), (
            f'{card["code"]}: '
            f'missing={sorted(set(cards.WIRE_KEYS) - set(card))} '
            f'unexpected={sorted(set(card) - set(cards.WIRE_KEYS))}'
        )


@pytest.mark.parametrize("key,kind", [
    ("words", list),
    ("occurrences", list),
    ("count", int),
    ("kind", str),
    ("word_index", int),
])
def test_merge_fields_have_the_right_type(key, kind):
    """The client calls .map on two of these and prints the others. A null
    where a list belongs is the exact crash this file was written after."""
    shown, _ = pipeline.present(sample(), "uz")
    for card in shown:
        assert isinstance(card[key], kind), \
            f'{card["code"]}.{key} is {type(card[key]).__name__}'


def test_occurrences_are_never_empty():
    """A card with no occurrences marks no letter in the ayah — the error would
    be described and then be unfindable."""
    shown, _ = pipeline.present(sample(), "uz")
    for card in shown:
        assert card["occurrences"], f'{card["code"]} has no occurrences'
        for occ in card["occurrences"]:
            assert set(occ) == {"at", "word", "word_index"}


def test_count_matches_occurrences():
    shown, _ = pipeline.present(sample(), "uz")
    for card in shown:
        assert card["count"] == len(card["occurrences"])


def test_shape_survives_the_response_model():
    """FastAPI's response_model is where a field silently disappears.

    `AttemptOut.errors` is a bare `list`, so pydantic passes the dicts through
    untouched — but that is a property worth asserting rather than assuming,
    because typing it more strictly later would start filtering keys and the
    only symptom would be a white screen.
    """
    shown, _ = pipeline.present(sample(), "uz")
    out = AttemptOut(id=1, sura=112, aya=2, status="ok", clean=False,
                     analysable=True, errors=shown)
    wire = json.loads(out.model_dump_json())
    assert wire["errors"], "errors were dropped entirely by the response model"
    for card in wire["errors"]:
        assert set(card.keys()) == set(cards.WIRE_KEYS)


# ── legacy rows ───────────────────────────────────────────────────────────

def test_ensure_shape_repairs_a_pre_merge_record():
    """Exactly what a row written before merging looks like in SQLite."""
    legacy = {
        "code": "SUB_SAD_SEEN", "at": 4, "letter": "ص",
        "expected": "ص", "heard": "س", "expected_count": 0, "heard_count": 0,
        "word": "ٱلصَّمَدُ", "status": "collect", "draft": True,
        "needs_teacher": False,
        "content": {"headline": "x", "fix": "", "rule": "", "drill": "",
                    "severity": "high", "group": "makharij"},
    }
    fixed = cards.ensure_shape(legacy)
    assert set(fixed.keys()) == set(cards.WIRE_KEYS)
    # Rebuilt from what the row actually knew, not blanked.
    assert fixed["kind"] == "wrong_letter"
    assert fixed["count"] == 1
    assert fixed["words"] == ["ٱلصَّمَدُ"]
    assert fixed["occurrences"] == [
        {"at": 4, "word": "ٱلصَّمَدُ", "word_index": -1}]


def test_ensure_shape_survives_an_almost_empty_record():
    """Belt and braces: even a row with only a code must not produce a payload
    the client throws on."""
    fixed = cards.ensure_shape({"code": "LETTER_ADDED"})
    assert set(fixed.keys()) == set(cards.WIRE_KEYS)
    assert fixed["kind"] == "extra_letter"
    assert isinstance(fixed["words"], list)
    assert fixed["count"] == len(fixed["occurrences"]) == 1


def test_ensure_shape_leaves_a_current_record_alone():
    """It repairs; it must not overwrite. A merged card that already knows it
    happened five times must still say five."""
    shown, _ = pipeline.present(sample(), "uz")
    merged = next(c for c in shown if c["count"] == 2)
    assert cards.ensure_shape(merged) == merged
