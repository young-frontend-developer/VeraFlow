# -*- coding: utf-8 -*-
"""The rule detector, pinned against worked examples from the printed books.

WHY THIS FILE EXISTS. engine/rule_presence.py carried its validation in its
docstring: every precondition was written against QPS output that had been
printed and read by hand, and nothing in CI held it to that. It was the one
engine module with no test at all. That was survivable while its only consumer
was a decorative badge strip; it stopped being survivable the moment a card
headline started saying "Mad lozim qilinmadi" on the strength of it. A wrong
badge is a wrong pill. A wrong rule name is the app telling a learner they
broke a rule that was never there.

The nine worked examples are the ones the module's own docstring reasons from,
plus the two shapes that break a naive implementation.
"""
import pytest

from tilawah.engine.rule_presence import (
    badges,
    rules_by_char,
    rules_by_unit,
    rules_present,
)
from tilawah.engine.segments import unit_char_spans

quran_transcript = pytest.importorskip("quran_transcript")


def phonetize(sura: int, aya: int):
    """(flat, spaced, uthmani) for one ayah, through the shipped moshaf."""
    from quran_transcript import Aya, quran_phonetizer

    from tilawah.engine.moshaf import MOSHAF

    uthmani = Aya(sura, aya).get().uthmani
    flat = quran_phonetizer(uthmani, MOSHAF, remove_spaces=True)
    spaced = quran_phonetizer(uthmani, MOSHAF, remove_spaces=False)
    return flat, spaced, uthmani


# ── the nine worked examples ──────────────────────────────────────────────
# (sura, aya, the rule that must be found, placeable, why this ayah is it)
#
# `placeable` is not a convenience flag - it is the finding. Eight of the nine
# are detected by a precondition that names a character, so a card may name the
# rule. 2:2's idgham is detected ONLY by the token-count proxy documented in
# rules_present: fewer tokens came back than there were words, so an
# assimilation happened SOMEWHERE. That is a true statement about the ayah and
# an unusable one for a card, and the split is recorded here rather than
# smoothed over - see test_the_idgham_proxy_is_deliberately_unplaced.
WORKED = [
    (2, 1, "RULE_MADD_LOZIM", True,
     "الٓمٓ — muqatta'at, phonetizes to two six-counts"),
    (1, 7, "RULE_MADD_LOZIM", True,
     "ٱلضَّآلِّينَ — madd letter followed by a shadda"),
    (1, 7, "RULE_MADD_TABIIY", True,
     "صِرَٰطَ — a plain two-count with no hamza behind it"),
    (114, 1, "RULE_IKHFO_GHUNNA", True,
     "ٱلنَّاسِ — a shadda'd nasal, held"),
    (113, 2, "RULE_IKHFO_GHUNNA", True,
     "مِن شَرِّ — the ikhfa noon, which QPS gives its own character"),
    (112, 1, "RULE_QALQALA", True,
     "أَحَدٌ in pause — the qalqalah mark ڇ"),
    (1, 7, "RULE_IDGHOM", True,
     "ٱلَّذِينَ — the sun-letter laam, a token opening on a doubled consonant"),
    (1, 7, "RULE_TAFXIM", True,
     "غَيْرِ / ٱلْمَغْضُوبِ — istila letters"),
    (2, 2, "RULE_IDGHOM", False,
     "هُدًى لِّلْمُتَّقِينَ — assimilation found only by the token-count proxy"),
]

_IDS = [f"{s}:{a}-{c}" for s, a, c, _p, _w in WORKED]


@pytest.mark.parametrize("sura,aya,code,placeable,why", WORKED, ids=_IDS)
def test_worked_example_is_found(sura, aya, code, placeable, why):
    """Each book example still produces the rule it is an example of."""
    flat, spaced, uthmani = phonetize(sura, aya)
    found = rules_present(flat.phonemes, flat.sifat, spaced.phonemes,
                          n_words=len(uthmani.split()))
    assert code in found, f"{why}: {code} not in {found}"


@pytest.mark.parametrize("sura,aya,code,placeable,why", WORKED, ids=_IDS)
def test_worked_example_is_placed(sura, aya, code, placeable, why):
    """...and rules_by_char can say WHERE, not merely that it is somewhere.

    This is the property the card headline depends on. A rule that
    rules_present() finds but rules_by_char() cannot place is a rule no card
    may name - so `placeable` is asserted in BOTH directions. An example that
    starts being placeable is as much a change worth noticing as one that stops.
    """
    _flat, spaced, _uthmani = phonetize(sura, aya)
    placed = rules_by_char(spaced.phonemes)
    got = any(code in codes for codes in placed.values())
    assert got is placeable, (
        f"{why}: placeable={placeable} but rules_by_char {'did' if got else 'did not'} place it")


def test_the_idgham_proxy_is_deliberately_unplaced():
    """2:2 names an idgham the cards must stay silent about.

    Found by test_worked_example_is_placed failing on an example this file
    originally asserted was placeable. It is not a detector bug: rules_present
    reaches 2:2's idgham through branch (c), the token-count proxy, which its
    own comment describes as unable to say which letter assimilated. A position
    cannot be recovered from it, so no card may headline "Idg'om qilinmadi"
    here - it falls back to a kind-only headline instead. Pinned so that
    limitation stays deliberate rather than becoming a surprise.
    """
    flat, spaced, uthmani = phonetize(2, 2)
    strip = rules_present(flat.phonemes, flat.sifat, spaced.phonemes,
                          n_words=len(uthmani.split()))
    assert "RULE_IDGHOM" in strip

    placed = rules_by_char(spaced.phonemes)
    everywhere = set().union(*placed.values()) if placed else set()
    assert "RULE_IDGHOM" not in everywhere


# ── the invariant the whole join rests on ─────────────────────────────────
PROBES = [(2, 1), (1, 7), (114, 1), (112, 1), (2, 2), (2, 7), (113, 1),
          (1, 1), (36, 1), (2, 255)]


@pytest.mark.parametrize("sura,aya", PROBES, ids=[f"{s}:{a}" for s, a in PROBES])
def test_flat_is_spaced_without_spaces(sura, aya):
    """The coordinate bridge rules_by_char is built on.

    Rules are detected on the spaced string and errors are located against the
    flat one. If the phonetizer ever changes anything but the spaces between
    the two modes, every rule position silently shifts and cards start naming
    the rule next door. That failure would be invisible in the output - a
    plausible rule name on the wrong sound - so it is pinned here.
    """
    flat, spaced, _ = phonetize(sura, aya)
    assert flat.phonemes == "".join(spaced.phonemes.split())


@pytest.mark.parametrize("sura,aya", PROBES, ids=[f"{s}:{a}" for s, a in PROBES])
def test_placed_rules_agree_with_the_badge_strip(sura, aya):
    """Everything rules_by_char places is something rules_present found.

    One direction only, and deliberately. rules_present carries the idgham
    token-count PROXY, which cannot name a position and so is not carried into
    rules_by_char - see that function's comment. So the placed set is a SUBSET,
    never a superset: the cards may know less than the strip, but they must
    never claim a rule the strip does not agree is present.
    """
    flat, spaced, uthmani = phonetize(sura, aya)
    strip = set(rules_present(flat.phonemes, flat.sifat, spaced.phonemes,
                              n_words=len(uthmani.split())))
    placed = set().union(*rules_by_char(spaced.phonemes).values()) \
        if rules_by_char(spaced.phonemes) else set()
    assert placed <= strip, f"placed but not present: {placed - strip}"


def test_muqattaat_places_lozim_despite_the_token_split():
    """2:1 is the case a token-indexed implementation gets wrong.

    الٓمٓ is ONE Uthmani word and TWO phoneme tokens. The madd lozim lives in the
    second token, so a map keyed on token index would report the rule at word 1
    of a one-word ayah. Keyed on character offset, it lands on real units.
    """
    flat, spaced, _ = phonetize(2, 1)
    at_unit = rules_by_unit(spaced.phonemes, unit_char_spans(flat.phonemes))
    lozim = [at for at, codes in at_unit.items()
             if "RULE_MADD_LOZIM" in codes]
    assert lozim, "no unit carries the madd lozim"
    assert max(lozim) < len(unit_char_spans(flat.phonemes))


def test_a_clean_ayah_places_nothing_it_cannot_justify():
    """rules_by_unit returns only units it genuinely found a rule on.

    An empty answer is a correct answer. The card path reads a MISSING key as
    "no rule name available" and falls back to a kind-only headline, which is
    the behaviour §12 asks for - so a permissive default here would quietly
    turn "we don't know" into a claim.
    """
    flat, spaced, _ = phonetize(1, 1)
    spans = unit_char_spans(flat.phonemes)
    at_unit = rules_by_unit(spaced.phonemes, spans)
    assert set(at_unit) <= set(range(len(spans)))
    for codes in at_unit.values():
        assert codes and all(c in badges() for c in codes)
