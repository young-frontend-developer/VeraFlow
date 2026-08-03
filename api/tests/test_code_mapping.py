# -*- coding: utf-8 -*-
"""The engine's vocabulary must reach the registry's.

This is the test that was missing. The engine emitted MADD_SHORT, GHUNNA_SHORT,
QALQALA_DROP and SUB_SAD_SEEN; the registry held MADD_TOO_SHORT,
GHUNNA_TOO_SHORT, QALQALAH_MISSING and MAKHARIJ_SAD_TO_SEEN. Nothing joined
them, nothing complained, and every one of those errors reached the learner as a
generic fallback card. A lookup miss produced a slightly worse card instead of a
failure, so it was invisible for as long as nobody read the output closely.

These tests turn that class of miss RED.
"""
import pytest

from tilawah.content import coaching
from tilawah.engine import sifat_codes
from tilawah.engine.typed_errors import EMITTED_CODES, L1_PAIRS


def test_registry_actually_loads():
    """v3 was on disk and unread for the whole life of the coaching module."""
    reg = coaching.registry()
    assert len(reg) >= 55, (
        f"only {len(reg)} entries loaded; v3 (39) + v5 (22) should merge to "
        f"roughly 60. A registry file is not being read."
    )
    for code in ("MADD_TOO_SHORT", "MAKHARIJ_SAD_TO_SEEN", "TAFKHEEM_LOST",
                 "QALQALAH_MISSING", "GENERIC_SIFAT_MISMATCH"):
        assert code in reg, f"{code} missing from the merged registry"


def test_every_emitted_code_resolves():
    """No engine code may reach a learner without an entry or an alias.

    Failing here means one of two things, and the fix differs:

      - the code is a synonym of an existing entry  -> add a row to
        coaching.ALIAS
      - the code names an error nobody has written about -> AUTHOR an entry

    What it must never mean is "point it at the closest-looking entry". That
    hands the learner a correction for an error they did not make, which is
    worse than the generic card this test exists to eliminate.
    """
    unresolved = sorted(c for c in EMITTED_CODES if not coaching.has(c))
    assert not unresolved, (
        "engine codes with neither a registry entry nor an alias:\n  "
        + "\n  ".join(f"{c} -> {coaching.resolve(c)}" for c in unresolved)
    )


def test_every_alias_target_exists():
    """An alias pointing at nothing is worse than no alias - it looks handled."""
    dangling = sorted(
        f"{src} -> {dst}" for src, dst in coaching.ALIAS.items()
        if dst not in coaching.registry()
    )
    assert not dangling, "aliases pointing at absent entries:\n  " + \
        "\n  ".join(dangling)


def test_aliases_are_not_self_referential():
    """A code that is its own alias means someone copied a row and forgot."""
    for src, dst in coaching.ALIAS.items():
        assert src != dst, f"{src} aliases to itself"
        assert dst not in coaching.ALIAS, (
            f"{src} -> {dst} -> {coaching.ALIAS[dst]}: alias chains are not "
            f"resolved, so this silently stops one hop short")


@pytest.mark.parametrize("pair,code", sorted(L1_PAIRS.items()))
def test_l1_pairs_resolve_or_fall_back_to_generic(pair, code):
    """An L1 prior with no content must not shadow the generic.

    _substitution_code checks L1_PAIRS first because those carry the
    language-specific coaching that differentiates this product. A prior nobody
    has authored content for is the exception: it must yield to
    GENERIC_LETTER_SUBSTITUTED, which at least describes the confusion.
    """
    from tilawah.engine.typed_errors import _substitution_code

    expected, heard = pair
    got = _substitution_code(expected, heard)
    assert coaching.has(got), (
        f"{expected} -> {heard} produced {got}, which has no registry entry; "
        f"the L1 tier should have yielded to the generic")


# ── substitution signal parsing ───────────────────────────────────────────
# Three shapes the old parser dropped, each costing every entry written in it.

@pytest.mark.parametrize("expected,heard,code", [
    ("ص", "س", "MAKHARIJ_SAD_TO_SEEN"),      # trailing comma after the pair
    ("ب", "م", "MAKHARIJ_BA_TO_MEEM"),       # bidirectional <->
    ("م", "ب", "MAKHARIJ_BA_TO_MEEM"),       # ... in the other direction
    ("ذ", "ز", "MAKHARIJ_INTERDENTAL_TO_ZAY"),   # two pairs in one signal
    ("ظ", "ز", "MAKHARIJ_INTERDENTAL_TO_ZAY"),   # ... the second one
    ("ع", "غ", "MAKHARIJ_AIN_TO_GHAYN"),     # the plain shape, unchanged
])
def test_substitution_pairs_parsed(expected, heard, code):
    assert coaching.substitution_pairs().get((expected, heard)) == code


def test_substitution_pairs_are_single_letters():
    """The old regex captured "س," - a two-character key nothing could match."""
    for (a, b), code in coaching.substitution_pairs().items():
        assert len(a) == 1 and len(b) == 1, f"{code}: bad pair {a!r} -> {b!r}"


# ── ṣifa routing ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("field,letter,exp,heard,code", [
    ("tafkheem_or_taqeeq", "ط", "mofakham", "moraqaq", "TAFKHEEM_LOST"),
    ("tafkheem_or_taqeeq", "ت", "moraqaq", "mofakham", "TAFKHEEM_ADDED"),
    ("hams_or_jahr",       "ت", "hams", "jahr", "HAMS_LOST"),
    ("hams_or_jahr",       "د", "jahr", "hams", "JAHR_LOST"),
    ("shidda_or_rakhawa",  "ط", "shadeed", "rikhw", "SHIDDA_LOST"),
    ("ghonna",             "ن", "maghnoon", "not_maghnoon", "GHUNNA_MISSING"),
    ("qalqla",             "ق", "moqalqal", "not_moqalqal", "QALQALAH_MISSING"),
    # letter-specific rulings that contradict the general one
    ("tafkheem_or_taqeeq", "ر", "mofakham", "moraqaq", "RAA_TAFKHEEM_MISSING"),
    ("tafkheem_or_taqeeq", "ر", "moraqaq", "mofakham", "RAA_TARQIQ_MISSING"),
    ("tafkheem_or_taqeeq", "ل", "moraqaq", "mofakham", "LAM_TAFKHEEM_WRONG"),
])
def test_sifat_routing(field, letter, exp, heard, code):
    assert sifat_codes.code_for(field, letter, exp, heard) == code


@pytest.mark.parametrize("field", ["itbaq", "safeer", "tikraar", "tafashie",
                                   "istitala"])
def test_unauthored_sifat_stay_generic(field):
    """The generic is narrowed, not deleted - these are what it is still for."""
    assert sifat_codes.code_for(field, "ص", "motbaq", "monfateh") == \
        sifat_codes.GENERIC


def test_heavy_degree_difference_is_not_an_error():
    """mofakham vs low_mofakham is a degree, not a direction. No card."""
    assert sifat_codes.code_for(
        "tafkheem_or_taqeeq", "ق", "mofakham", "low_mofakham") is None
    assert sifat_codes.code_for(
        "tafkheem_or_taqeeq", "ق", "low_mofakham", "mofakham") is None


def test_every_routed_sifat_code_has_an_entry():
    """Routing to a code with no content would reintroduce the empty card."""
    cases = [
        ("tafkheem_or_taqeeq", "ط", "mofakham", "moraqaq"),
        ("tafkheem_or_taqeeq", "ت", "moraqaq", "mofakham"),
        ("tafkheem_or_taqeeq", "ر", "mofakham", "moraqaq"),
        ("tafkheem_or_taqeeq", "ر", "moraqaq", "mofakham"),
        ("tafkheem_or_taqeeq", "ل", "moraqaq", "mofakham"),
        ("hams_or_jahr", "ت", "hams", "jahr"),
        ("hams_or_jahr", "د", "jahr", "hams"),
        ("shidda_or_rakhawa", "ط", "shadeed", "rikhw"),
        ("shidda_or_rakhawa", "ط", "shadeed", "between"),
        ("ghonna", "ن", "maghnoon", "not_maghnoon"),
        ("qalqla", "ق", "moqalqal", "not_moqalqal"),
        ("qalqla", "س", "not_moqalqal", "moqalqal"),
    ]
    for field, letter, exp, heard in cases:
        code = sifat_codes.code_for(field, letter, exp, heard)
        assert code and coaching.has(code), \
            f"{field} {exp}->{heard} on {letter} routed to {code}, no entry"


def test_sifat_routing_no_longer_collapses_to_one_code():
    """The behaviour this whole change is about.

    Six different ṣifa faults previously produced six identical cards.
    """
    faults = [
        ("tafkheem_or_taqeeq", "ط", "mofakham", "moraqaq"),
        ("tafkheem_or_taqeeq", "ت", "moraqaq", "mofakham"),
        ("hams_or_jahr", "ت", "hams", "jahr"),
        ("hams_or_jahr", "د", "jahr", "hams"),
        ("ghonna", "ن", "maghnoon", "not_maghnoon"),
        ("qalqla", "ق", "moqalqal", "not_moqalqal"),
    ]
    codes = {sifat_codes.code_for(*f) for f in faults}
    assert len(codes) == 6, f"still collapsing: {codes}"
    assert sifat_codes.GENERIC not in codes


# ── alif is not a consonant ───────────────────────────────────────────────

@pytest.mark.parametrize("expected,heard", [
    ("ء", "ا"),      # hamza "read as" a madd alif - the reported nonsense
    ("ا", "ء"),
    ("ا", "ب"),
    ("ب", "ا"),
])
def test_alif_pairings_are_not_substitutions(expected, heard):
    """Alif has no makhraj. "You read ء as ا" is a category error, not a
    correction, so no code is produced and no card is shown."""
    from tilawah.engine.typed_errors import _substitution_code

    assert _substitution_code(expected, heard) is None


@pytest.mark.parametrize("expected,heard,code", [
    ("و", "ف", "SUB_WAW_V"),                    # waw as a CONSONANT
    ("ف", "و", "MAKHARIJ_WAW_TO_FA"),
    ("ج", "ي", "MAKHARIJ_JEEM_TO_YA"),          # ya as a CONSONANT
    ("ي", "ج", "MAKHARIJ_JEEM_TO_YA"),
])
def test_waw_and_ya_still_fire(expected, heard, code):
    """Only ALIF is suppressed. و and ي are dual-nature - madd letters when
    sakin after a matching haraka, ordinary consonants otherwise - and their
    makharij entries must keep working."""
    from tilawah.engine.typed_errors import _substitution_code

    assert _substitution_code(expected, heard) == code


def test_alif_substitution_produces_no_error():
    """End to end through typed_diff, not just the code lookup."""
    from tilawah.engine.typed_errors import typed_diff

    errs = typed_diff("ءَلَم", "اَلَم")
    assert [e.code for e in errs if "SUBSTITUT" in e.code] == []


# ── learner-facing categories ─────────────────────────────────────────────

@pytest.mark.parametrize("code,group,kind", [
    ("LETTER_ADDED", "haraka", "extra_letter"),
    ("LETTER_DROPPED", "haraka", "missing_letter"),
    ("MAKHARIJ_SAD_TO_SEEN", "makharij", "wrong_letter"),
    ("GENERIC_LETTER_SUBSTITUTED", "fallback", "wrong_letter"),
    ("TAFKHEEM_LOST", "sifat", "pronunciation"),
    ("QALQALAH_MISSING", "sifat", "tajweed"),
    ("QALQALA_DROP", "", "tajweed"),
    ("MADD_TOO_SHORT", "madd", "madd"),
    ("GHUNNA_TOO_SHORT", "ghunna", "ghunna"),
    ("HARAKA_SUBSTITUTED", "haraka", "haraka"),
    # no group at all - must still land on a real title, never on the code
    ("SHADDA_LONG", "", "madd"),
    ("GHUNNA_LONG", "", "ghunna"),
    ("SUB_HA_HEH", "", "wrong_letter"),
])
def test_kind_of(code, group, kind):
    from tilawah.engine import cards

    assert cards.kind_of(code, group) == kind


def test_every_emitted_code_gets_a_real_kind():
    """Including the four with no entry. A card with no title would be the code
    leaking back in through the gap."""
    from tilawah.engine import cards

    for code in EMITTED_CODES:
        k = cards.kind_of(code, "")
        assert k in cards.KINDS, f"{code} -> {k!r}"


# ── practice audio ────────────────────────────────────────────────────────

def test_audio_pair_hidden_when_the_file_is_absent():
    """No file, no URL, so the client renders no button. 13 entries name a
    recording and none of the files exist yet."""
    assert coaching.audio_url("audio/sad_zay.mp3") == ""
    assert coaching.audio_url("") == ""


def test_audio_pair_rejects_paths_that_escape_the_directory():
    assert coaching.audio_url("audio/../../secrets.mp3") == ""
    assert coaching.audio_url("../../etc/passwd") == ""


def test_audio_pair_appears_once_the_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(coaching, "AUDIO_DIR", tmp_path)
    (tmp_path / "sad_zay.mp3").write_bytes(b"\0")
    assert coaching.audio_url("audio/sad_zay.mp3") == "/audio/sad_zay.mp3"


def test_missing_audio_is_reported():
    """The gap has to stay countable, or hiding the button hides the problem."""
    missing = coaching.missing_audio()
    assert len(missing) == 13
    assert any("MAKHARIJ_SAD_TO_ZAY" in m for m in missing)


# ── the card has a word budget ────────────────────────────────────────────

@pytest.mark.parametrize("lang", ["uz", "ru"])
def test_visible_card_text_stays_under_the_budget(lang):
    """Part B caps a card at 70 words. `headline` + `fix` is what a learner
    reads without tapping anything, so that is what the budget governs.

    This is a REGRESSION guard, not a request to shorten rulings: `rule` and
    `drill` sit behind a disclosure and are deliberately longer. It fails if a
    future adapter change starts concatenating fields back into the visible
    slots - which is exactly what it caught the first time, when `fix` carried
    both nima_xato and tuzatish and every card opened with the same sentence
    twice.

    tools/audit_card_length.py prints the full ranking.
    """
    over = []
    for code, spec in coaching.registry().items():
        block = spec.get(lang) or spec.get("uz") or {}
        n = len(block.get("headline", "").split()) + len(block.get("fix", "").split())
        if n > 70:
            over.append(f"{code}: {n} words")
    assert not over, "cards over the 70-word visible budget:\n  " + \
        "\n  ".join(sorted(over))


def test_headline_and_fix_are_not_the_same_sentence():
    """v3's `short` and `nima_xato` say the same thing at two lengths. Carrying
    both put a restatement directly under the headline on every card."""
    for code, spec in coaching.registry().items():
        block = spec.get("uz") or {}
        head, fix = block.get("headline", ""), block.get("fix", "")
        if head and fix:
            assert head.strip() not in fix, f"{code}: headline repeated in fix"


# ── rendering ─────────────────────────────────────────────────────────────

def test_v3_entries_render_all_four_fields():
    """The adapter must fill the shape, not just load the file.

    v3 was authored under different key names. Loading it without mapping them
    would put entries in the registry that render four empty strings - a card
    that looks authored and says nothing.
    """
    fields = {"word": "ٱلصَّمَدُ", "letter": "ص", "expected": "ص",
              "heard": "س", "actual": "س", "expected_count": 2,
              "heard_count": 1, "n_expected": 2, "n_actual": 1}
    for code in ("MAKHARIJ_SAD_TO_SEEN", "MADD_TOO_SHORT", "TAFKHEEM_LOST",
                 "QALQALAH_MISSING"):
        card = coaching.render(code, "uz", fields)
        assert card, f"{code} rendered nothing"
        for key in coaching.FIELDS:
            assert card[key].strip(), f"{code}.{key} rendered empty"


def test_engine_codes_render_through_their_alias():
    """MADD_SHORT must produce MADD_TOO_SHORT's text, in both languages."""
    fields = {"word": "قَالَ", "letter": "ا", "expected": "", "heard": "",
              "actual": "", "expected_count": 2, "heard_count": 1,
              "n_expected": 2, "n_actual": 1}
    for lang in ("uz", "ru"):
        direct = coaching.render("MADD_TOO_SHORT", lang, fields)
        aliased = coaching.render("MADD_SHORT", lang, fields)
        assert aliased == direct, f"MADD_SHORT diverged from its alias in {lang}"
        assert aliased["headline"].strip()
