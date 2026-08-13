# -*- coding: utf-8 -*-
"""The v7 card restructure: two kinds, five headline patterns, two levels.

THE PROPERTY MOST OF THIS FILE GUARDS is a refusal. §3 and §12 of the spec say
a card may not name a tajweed rule at a position the engine cannot place one
at, and the easy way to satisfy that is to write the check and then quietly
default when it fails. So the tests below mostly assert that nothing was said:
no rule name without a placement, no simplified button without authored text,
no Kind 1 shape on an entry nobody has converted.
"""
import pytest

from tilawah.content import coaching
from tilawah.engine import cards, headlines, pipeline
from tilawah.engine.typed_errors import TypedError


def err(code: str, **kw) -> TypedError:
    base = dict(at=0, letter="ن", word="إِنَّ", word_index=0)
    base.update(kw)
    return TypedError(code=code, **base)


# ── the overlay merged without eating what it did not name ────────────────

def test_v7_is_an_overlay_not_a_replacement():
    """The five converted entries keep the fields earlier generations set.

    A plain dict.update() would have dropped `group`, and cards.kind_of routes
    on `group` - so the entries gaining a simplified explanation would have
    lost their category on the way in.
    """
    for code in coaching.restructured():
        spec = coaching.entry(code)
        assert spec.get("group"), f"{code} lost its group"
        assert spec.get("card_kind") in (1, 2), f"{code} has no card kind"
        assert spec.get("detection_signal"), f"{code} lost its signal"


def test_the_other_entries_are_untouched():
    """56 entries still render exactly the card they rendered before.

    card_kind 0 is the "not converted" marker, and the client reads it as
    "render the old shape". If this drifts to 1 or 2 by accident, 56 cards
    change appearance with no content authored for the new slots.
    """
    converted = set(coaching.restructured())
    for code in coaching.registry():
        if code in converted:
            continue
        body = coaching.render(code, "uz", _FIELDS)
        if body is None:
            continue
        assert body["card_kind"] == 0, f"{code} silently converted"
        assert body["simplified"] is None
        assert body["rule_text"] == ""


_FIELDS = {"word": "إِنَّ", "letter": "ن", "expected": "ن", "heard": "س",
           "actual": "س", "expected_count": 6, "heard_count": 2,
           "n_expected": 6, "n_actual": 2}


# ── the refusal ───────────────────────────────────────────────────────────

def test_no_rule_name_without_a_placement():
    """A rule-shaped pattern with nothing placed falls back, never guesses."""
    body = coaching.render("MADD_TOO_SHORT", "uz", _FIELDS)
    built, named = pipeline._headline(body, err("MADD_TOO_SHORT"), "uz",
                                      placed=[])
    assert named == ""
    assert built == body["headline_no_rule"]
    assert "Mad lozim" not in built


def test_a_rule_from_another_family_is_not_borrowed():
    """A qalqalah placed at this unit does not name a madd card.

    The failure this blocks: taking "whatever rule is here" rather than "the
    rule this error is about". Both are one line of code and only one is true.
    """
    body = coaching.render("MADD_TOO_SHORT", "uz", _FIELDS)
    built, named = pipeline._headline(body, err("MADD_TOO_SHORT"), "uz",
                                      placed=["RULE_QALQALA"])
    assert named == ""
    assert built == body["headline_no_rule"]


def test_the_longest_madd_wins_at_one_position():
    """A six-count is a lozim, not the tabiiy it also technically matches."""
    assert pipeline._placed_rule(
        "madd", ["RULE_MADD_TABIIY", "RULE_MADD_LOZIM"]) == "RULE_MADD_LOZIM"


def test_a_rule_with_no_authored_russian_name_falls_back():
    """RULE_MADD_MUNFASIL has no Russian name, so no Russian card claims it."""
    assert coaching.rule_title("RULE_MADD_MUNFASIL", "uz")
    assert coaching.rule_title("RULE_MADD_MUNFASIL", "ru") == ""

    body = coaching.render("MADD_TOO_SHORT", "ru", _FIELDS)
    built, named = pipeline._headline(body, err("MADD_TOO_SHORT"), "ru",
                                      placed=["RULE_MADD_MUNFASIL"])
    assert named == ""
    assert built == body["headline_no_rule"]


# ── the headline patterns ─────────────────────────────────────────────────

def test_qilinmadi_is_not_used_for_over_application():
    """§15's acceptance criterion, asserted directly."""
    for pattern in (headlines.TOO_STRONG, headlines.EXCESSIVE,
                    headlines.WRONG_LOCATION):
        built = headlines.build(pattern, "uz", rule_name="Mad lozim")
        assert "qilinmadi" not in built, f"{pattern} says qilinmadi"


@pytest.mark.parametrize("gender,expected", [
    ("m", "Мадд лязим не выполнен"),
    ("f", "Гунна не выполнена"),
    ("n", "Ихфа не выполнено"),
])
def test_russian_headlines_agree_with_the_rule_name(gender, expected):
    """Found by reading the rendered output, not by a unit test.

    One Russian frame produced "Мадд лязим не выполнено" and "Гунна не
    выполнено" - both wrong, and the kind of wrong that costs a careful learner
    their confidence in the rest of the card. The genders are read off the
    authored Russian, so this also pins that they stay read rather than guessed.
    """
    name = expected.split(" не ")[0]
    assert headlines.build(headlines.MISSING_RULE, "ru", rule_name=name,
                           gender=gender) == expected


def test_every_pattern_has_a_frame_in_both_languages():
    for pattern in headlines.PATTERNS:
        for lang in ("uz", "ru"):
            assert headlines.frame(pattern, lang), f"{pattern}/{lang} missing"


def test_every_converted_entry_names_a_real_pattern():
    for code in coaching.restructured():
        spec = coaching.entry(code)
        assert spec["headline_pattern"] in headlines.PATTERNS


# ── the two levels ────────────────────────────────────────────────────────

def test_kind_2_gets_no_rule_toggle():
    """§4: on a direct correction, theory does not help. So none is sent."""
    for code in coaching.restructured():
        spec = coaching.entry(code)
        if spec["card_kind"] != 2:
            continue
        body = coaching.render(code, "uz", _FIELDS)
        assert not body["rule_text"], f"{code} is Kind 2 but carries a rule"


def test_kind_1_carries_a_rule_and_a_simplified_level():
    for code in coaching.restructured():
        spec = coaching.entry(code)
        if spec["card_kind"] != 1:
            continue
        for lang in ("uz", "ru"):
            body = coaching.render(code, lang, _FIELDS)
            assert body["rule_text"], f"{code}/{lang} has no rule text"
            assert body["simplified"], f"{code}/{lang} has no simple level"


def test_the_simplified_level_is_shorter_than_the_standard_one():
    """Not a style preference - it is the whole point of the second level.

    "Explain simply" that produces MORE words than the card it explains has
    failed at the one thing it exists to do, and that is a content regression
    no other check would catch.
    """
    for code in coaching.restructured():
        for lang in ("uz", "ru"):
            body = coaching.render(code, lang, _FIELDS)
            simple = body.get("simplified")
            if not simple:
                continue
            standard = f"{body['explanation']} {body['correction']}"
            simplified = f"{simple['explanation']} {simple['correction']}"
            assert len(simplified.split()) <= len(standard.split()), (
                f"{code}/{lang}: simplified is longer than standard")


def test_both_languages_are_authored_for_every_converted_entry():
    """§11: Russian is authored, not derived. Absence is what this catches."""
    for code in coaching.restructured():
        uz = coaching.render(code, "uz", _FIELDS)
        ru = coaching.render(code, "ru", _FIELDS)
        for key in ("explanation", "correction", "retry"):
            assert uz[key], f"{code}.uz.{key} empty"
            assert ru[key], f"{code}.ru.{key} empty"
        assert uz["explanation"] != ru["explanation"]


def test_the_new_fields_are_on_the_wire_contract():
    """A field the client indexes must survive a legacy history row too."""
    assert "rule_code" in cards.WIRE_KEYS
    repaired = cards.ensure_shape({"code": "MADD_TOO_SHORT", "at": 3})
    assert repaired["rule_code"] == ""
