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
        f"only {len(reg)} entries loaded; v3 (36) + v5 (22) + v6 (4) should "
        f"merge to roughly 60. A registry file is not being read."
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


# ── the lahn khafiy khafiy scope decision (2026-08-07) ────────────────────
#
# hams/jahr and shidda/rakhawa are not corrected by this app. The removal has to
# hold at three separate layers, and each one has failed independently before:
# an entry can come back into the registry, a branch can come back into the
# router, and a field dropped from ROUTED lands in the GENERIC fallback - which
# would show the learner "the ṣifa did not come out right" for exactly the
# errors we decided not to report. So all three are pinned, not just the last.

OUT_OF_SCOPE_VALUES = {
    "hams_or_jahr": ["hams", "jahr"],
    "shidda_or_rakhawa": ["shadeed", "rikhw", "between"],
}


@pytest.mark.parametrize("field,values", sorted(OUT_OF_SCOPE_VALUES.items()))
def test_out_of_scope_sifat_never_produce_an_error(field, values):
    """EVERY direction, on letters where the ṣifa genuinely applies.

    Not a spot check: the whole cross product, because the previous shape of
    this routing had a specific branch per direction plus a fallthrough, and a
    partial restore would leave one of them live.
    """
    letters = ["ت", "د", "ط", "ك", "ء", "س", "ص", "ب", "ن"]
    for letter in letters:
        for expected in values:
            for heard in values:
                assert sifat_codes.code_for(field, letter, expected,
                                            heard) is None, (
                    f"{field} {expected}->{heard} on {letter} produced a code; "
                    f"this ṣifa is out of scope and must yield nothing at all")


@pytest.mark.parametrize("field", sorted(OUT_OF_SCOPE_VALUES))
def test_out_of_scope_sifat_do_not_fall_into_the_generic(field):
    """The failure mode of a half-removal, stated on its own.

    Deleting these from ROUTED without OUT_OF_SCOPE would route them to
    GENERIC_SIFAT_MISMATCH, which is worse than leaving them on: the learner
    gets a card with no property named for an error we do not believe in.
    """
    assert field in sifat_codes.OUT_OF_SCOPE
    assert field not in sifat_codes.ROUTED
    # An unrecognised value must not slip past the scope gate into the fallback.
    assert sifat_codes.code_for(field, "ت", "whatever", "something_else") is None


@pytest.mark.parametrize("code", ["HAMS_LOST", "JAHR_LOST", "SHIDDA_LOST"])
def test_out_of_scope_codes_are_gone_from_every_registry(code):
    """The entry side. Regenerating v3 from the amendments must keep them out,
    and no later generation may quietly re-add one."""
    from tilawah.engine import coverage

    assert code not in coaching.registry(), (
        f"{code} is back in the merged coaching registry")
    assert code not in coverage.registry(), (
        f"{code} is back in the detection registry")
    assert code not in coverage.in_scope()


@pytest.mark.parametrize("code", ["HAMS_LOST", "JAHR_LOST", "SHIDDA_LOST"])
def test_out_of_scope_codes_have_no_precondition(code):
    """The coverage side. A precondition that survives the entry keeps the code
    in `relevant`, which drags every segment's coverage score down against a
    check that can never fire, and puts it back in the review ranking."""
    from tilawah.engine import coverage

    src = coverage.possible_codes.__doc__ or ""
    assert code not in src
    # Behavioural, not textual: over a sample chosen to hit sakin hams, sakin
    # jahr obstruents and sakin shadeed, the code must never appear.
    from quran_transcript import Aya, quran_phonetizer

    from tilawah.engine.moshaf import MOSHAF

    for sura, aya in [(1, 7), (112, 1), (112, 4), (103, 1), (108, 1)]:
        uth = Aya(sura, aya).get().uthmani
        flat = quran_phonetizer(uth, MOSHAF, remove_spaces=True)
        spaced = quran_phonetizer(uth, MOSHAF, remove_spaces=False)
        assert code not in coverage.possible_codes(
            flat.phonemes, flat.sifat, spaced.phonemes), f"{sura}:{aya}"


# ── RULE 5: never invent tajweed that cannot exist ────────────────────────

@pytest.mark.parametrize("letter", ["ا", "ى", "و", "ي"])
@pytest.mark.parametrize("exp,heard", [("mofakham", "moraqaq"),
                                        ("moraqaq", "mofakham")])
def test_a_madd_letter_has_no_heaviness_of_its_own(letter, exp, heard):
    """"The alif became heavy" is not a correction, it is a category error: ا
    has no tafkheem ruling, it takes the weight of the consonant before it. The
    pipeline re-anchors these onto that consonant; anything still carrying a
    madd letter by the time it reaches here had no consonant to move to, and
    gets no card at all."""
    assert sifat_codes.code_for("tafkheem_or_taqeeq", letter, exp, heard) is None


@pytest.mark.parametrize("letter", ["ه", "س", "ل", "ر", "ن"])
def test_qalqalah_is_only_ever_about_the_five_qalqalah_letters(letter):
    """A qalqalah reported on a letter outside «قطب جد» is the model guessing a
    value for a field that does not apply. Correcting it would teach a ruling
    that does not exist."""
    assert sifat_codes.code_for("qalqla", letter, "moqalqal",
                                "not_moqalqal") is None


@pytest.mark.parametrize("letter", ["ب", "س", "ك", "ر"])
def test_ghunna_is_only_ever_about_the_nasal_letters(letter):
    """Nothing outside ن and م has a nasal to hold."""
    assert sifat_codes.code_for("ghonna", letter, "maghnoon",
                                "not_maghnoon") is None


def test_the_possible_cases_still_fire():
    """The guard must refuse impossibilities WITHOUT costing recall on the real
    thing - a heavy ت and a soft ق are both ordinary, correctable mistakes."""
    assert sifat_codes.code_for(
        "tafkheem_or_taqeeq", "ت", "moraqaq", "mofakham") == "TAFKHEEM_ADDED"
    assert sifat_codes.code_for(
        "qalqla", "د", "moqalqal", "not_moqalqal") == "QALQALAH_MISSING"
    assert sifat_codes.code_for(
        "ghonna", "م", "maghnoon", "not_maghnoon") == "GHUNNA_MISSING"


def test_heaviness_on_a_madd_letter_is_reanchored_to_its_consonant():
    """The observation is real - something DID come out light - so the error is
    moved onto the letter it is actually about rather than thrown away."""
    from tilawah.engine.pipeline import _reanchor_tafkheem

    # «طَا»: groups are [ط, ا] and the heaviness belongs to the ط.
    keys = ["ط", "ا"]
    assert _reanchor_tafkheem("tafkheem_or_taqeeq", 1, "ا", keys) == (0, "ط")
    # No consonant in front of it: nothing to re-anchor to, left alone so
    # code_for can refuse it.
    assert _reanchor_tafkheem("tafkheem_or_taqeeq", 0, "ا", ["ا"]) == (0, "ا")
    # A different ṣifa is never moved.
    assert _reanchor_tafkheem("hams_or_jahr", 1, "ا", keys) == (1, "ا")


def test_heavy_degree_difference_is_not_an_error():
    """mofakham vs low_mofakham is a degree, not a direction. No card."""
    assert sifat_codes.code_for(
        "tafkheem_or_taqeeq", "ق", "mofakham", "low_mofakham") is None
    assert sifat_codes.code_for(
        "tafkheem_or_taqeeq", "ق", "low_mofakham", "mofakham") is None


# The shidda equivalent of the test above - rikhw vs between being a difference
# of degree rather than a direction - is now subsumed by
# test_out_of_scope_sifat_never_produce_an_error, which asserts the stronger
# thing: NO shidda_or_rakhawa pair produces a code, degree or direction. The
# original finding is preserved in the amendments file's restore note, because
# a restore that reinstates the shadeed branch without the rikhw/between drop
# would reintroduce a false positive that was measured, not theorised: 4 of the
# 16 ṣifa disagreements on a real 2:7 recitation were that pair, and every one
# produced a card reading "the ṣifa did not come out right".


def test_every_routed_sifat_code_has_an_entry():
    """Routing to a code with no content would reintroduce the empty card."""
    cases = [
        ("tafkheem_or_taqeeq", "ط", "mofakham", "moraqaq"),
        ("tafkheem_or_taqeeq", "ت", "moraqaq", "mofakham"),
        ("tafkheem_or_taqeeq", "ر", "mofakham", "moraqaq"),
        ("tafkheem_or_taqeeq", "ر", "moraqaq", "mofakham"),
        ("tafkheem_or_taqeeq", "ل", "moraqaq", "mofakham"),
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

    Six different ṣifa faults previously produced six identical cards. Two of
    the six were hams/jahr and are now out of scope entirely, so the surviving
    faults are these - each still has to reach its own code. The count is
    derived from the list rather than written as a literal, so removing another
    check for scope does not turn this into a red test about a decision that
    was made deliberately.
    """
    faults = [
        ("tafkheem_or_taqeeq", "ط", "mofakham", "moraqaq"),
        ("tafkheem_or_taqeeq", "ت", "moraqaq", "mofakham"),
        ("tafkheem_or_taqeeq", "ر", "mofakham", "moraqaq"),
        ("ghonna", "ن", "maghnoon", "not_maghnoon"),
        ("qalqla", "ق", "moqalqal", "not_moqalqal"),
        ("qalqla", "س", "not_moqalqal", "moqalqal"),
    ]
    codes = {sifat_codes.code_for(*f) for f in faults}
    assert len(codes) == len(faults), f"still collapsing: {codes}"
    assert sifat_codes.GENERIC not in codes
    assert None not in codes


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
    ("SHADDA_LONG", "", "shadda"),
    ("GHUNNA_LONG", "", "ghunna"),
    ("SUB_HA_HEH", "", "wrong_letter"),
])
def test_kind_of(code, group, kind):
    from tilawah.engine import cards

    assert cards.kind_of(code, group) == kind


# ── RULE 1: duration and nasalisation are never "pronunciation" ───────────

@pytest.mark.parametrize("sifa,kind", [
    ("ghonna", "ghunna"),
    ("qalqla", "tajweed"),
    ("tafkheem_or_taqeeq", "pronunciation"),
    # hams_or_jahr was the fourth case here. It is out of scope now, so no
    # TypedError can carry it and there is no kind for it to resolve to.
    ("itbaq", "pronunciation"),
])
def test_the_sifa_decides_the_kind_not_the_fallback_group(sifa, kind):
    """A ṣifa disagreement nobody authored an entry for resolves to
    GENERIC_SIFAT_MISMATCH, whose registry group is `fallback` - which says
    where the entry came from and NOTHING about what the learner did. Routing on
    it titled every unrouted ghunna fault "Talaffuz", which is exactly the
    mad/ghunna-versus-ṣifat confusion RULE 1 forbids.

    The detector knew which property flipped the whole time; the card just was
    not asking.
    """
    from tilawah.engine import cards

    assert cards.kind_of("GENERIC_SIFAT_MISMATCH", "fallback", sifa) == kind


def test_shadda_length_is_not_a_madd_card():
    """RULE 1, the other direction. Madd is the lengthening of a vowel on ا و ي;
    shadda is the holding of a doubled CONSONANT. SHADDA_* fell through
    kind_of's `startswith` into `madd`, so under-holding the ّ in «إِيَّاكَ» was
    titled as a madd error and pointed the learner at the wrong ruling."""
    from tilawah.engine import cards

    assert cards.kind_of("SHADDA_SHORT", "") == cards.SHADDA
    assert cards.kind_of("SHADDA_LONG", "") == cards.SHADDA
    assert cards.SHADDA != cards.MADD


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

def test_v3_entries_are_adapted_into_all_four_fields():
    """The adapter must fill the shape, not just load the file.

    v3 was authored under different key names. Loading it without mapping them
    would put entries in the registry that carry four empty strings - an entry
    that looks authored and says nothing.

    Asserted on the REGISTRY, not on the rendered card. render() emits only
    CARD_FIELDS now, because `rule` and `drill` are authored but not shown to a
    learner; checking the adapter through the card would therefore stop
    checking two of the four fields it exists to map, and a broken v3 adapter
    would go unnoticed in exactly the fields nobody is looking at.
    """
    for code in ("MAKHARIJ_SAD_TO_SEEN", "MADD_TOO_SHORT", "TAFKHEEM_LOST",
                 "QALQALAH_MISSING"):
        block = coaching.entry(code)["uz"]
        for key in coaching.FIELDS:
            assert block.get(key, "").strip(), f"{code}.{key} adapted empty"


def test_the_card_carries_only_the_card_fields():
    """`rule` and `drill` must not travel to the client at all.

    Not merely unrendered - absent. A field that arrives and is ignored is a
    field the next person to touch the card will render "because it is there",
    and the whole point of dropping them is that a correction card is not a
    tajweed lesson.
    """
    fields = {"word": "ٱلصَّمَدُ", "expected": "ص", "heard": "س",
              "actual": "س", "expected_count": 2, "heard_count": 1,
              "n_expected": 2, "n_actual": 1}
    # `letter` is per-code on purpose. QALQALAH_MISSING's instruction is built
    # around د, and rendering it for a ص would correctly suppress the fix -
    # see test_a_worked_example_about_another_letter_is_not_shown. Asking it
    # about the letter it was written for keeps this test about the SHAPE of
    # the card rather than about the suppression rule.
    for code, letter in [("MAKHARIJ_SAD_TO_SEEN", "ص"),
                         ("MADD_TOO_SHORT", "ا"),
                         ("TAFKHEEM_LOST", "ط"),
                         ("QALQALAH_MISSING", "د")]:
        card = coaching.render(code, "uz", {**fields, "letter": letter})
        assert card, f"{code} rendered nothing"
        for key in coaching.CARD_FIELDS:
            assert card[key].strip(), f"{code}.{key} rendered empty"
        assert "rule" not in card, f"{code} still ships the ruling"
        assert "drill" not in card, f"{code} still ships the prose drill"


def test_the_fix_is_one_instruction_not_a_paragraph_of_commentary():
    """The learner's `fix` slot holds the correction and nothing after it.

    Every multi-part `fix` in the registries is written as paragraphs split by
    a blank line: the correction first, then commentary. Two codes put a
    fallback apology in that second paragraph - "we have not written this yet,
    ask your teacher" - and those two are the codes that fire most often, so
    the app's most-seen card carried a fallback message inside the slot the
    learner reads for the answer.
    """
    fields = {"word": "ٱلصَّمَدُ", "letter": "ص", "expected": "ص",
              "heard": "س", "actual": "س", "expected_count": 2,
              "heard_count": 1, "n_expected": 2, "n_actual": 1}
    for code, spec in coaching.registry().items():
        for lang in ("uz", "ru"):
            authored = (spec.get(lang) or {}).get("fix", "")
            if "\n\n" not in authored:
                continue
            card = coaching.render(code, lang, fields)
            assert "\n\n" not in card["fix"], (
                f"{code}.{lang}: the fix slot still carries commentary after "
                f"the instruction")


def test_a_worked_example_about_another_letter_is_not_shown():
    """QALQALAH_MISSING covers ق ط ب ج د but its instruction is written around
    «أَحَدْ» and «د». A learner who softened the ق in «وَٱقْتَرِب» must not be told
    to practise د - especially now, with a practice ladder correctly showing ق
    directly beneath it.

    The د case is the control: when the worked example IS the detected letter,
    the instruction is exactly right and must survive.
    """
    base = {"word": "وَٱقْتَرِب", "expected": "", "heard": "", "actual": "",
            "expected_count": 0, "heard_count": 0, "n_expected": "",
            "n_actual": ""}
    # Engine code, not registry code - the alias is part of what is tested.
    kept = coaching.render("QALQALA_DROP", "uz", {**base, "letter": "د"})
    assert kept["fix"].strip(), "the د example must survive for a د mistake"

    for letter in ("ق", "ط", "ب", "ج"):
        card = coaching.render("QALQALA_DROP", "uz", {**base, "letter": letter})
        assert card["fix"] == "", (
            f"a {letter} qalqalah is still answered with the د drill: "
            f"{card['fix'][:70]!r}")
        # Suppressing the instruction must not gut the card: what happened and
        # where still stand, and the ladder is built from the real letter.
        assert card["headline"].strip()


def test_letter_specific_suppression_does_not_touch_other_entries():
    """The curated list is narrow BECAUSE the obvious general rule over-fires.

    MADD_WAJIB_SHORTENED names ء as the CONDITION of the ruling and
    IQLAB_MISSING names م as the target sound; neither is a worked example
    about the wrong letter, and blanking either would lose a correct
    instruction.
    """
    base = {"word": "جَآءَ", "expected": "", "heard": "", "actual": "",
            "expected_count": 4, "heard_count": 2, "n_expected": 4,
            "n_actual": 2}
    for code, letter in [("MADD_WAJIB_SHORTENED", "ا"), ("IQLAB_MISSING", "ن"),
                         ("IKHFA_MISSING", "ن"), ("IDGHAM_MISSING", "ن"),
                         ("MADD_ADDED", "و")]:
        card = coaching.render(code, "uz", {**base, "letter": letter})
        assert card and card["fix"].strip(), f"{code} lost its instruction"


def test_no_fallback_apology_reaches_a_learner():
    """The two generics are the most-fired codes in the app. Neither may tell
    the learner we have not written their correction yet: the card exists to
    answer four questions, and "ask someone else" answers none of them."""
    fields = {"word": "ٱلصَّمَدُ", "letter": "ص", "expected": "ص",
              "heard": "س", "actual": "س", "expected_count": 2,
              "heard_count": 1, "n_expected": 2, "n_actual": 1}
    # Phrases the registries use for "this is not authored yet", in both
    # languages. Matched on the AUTHORED text, so this test fails loudly if
    # someone rephrases the apology rather than silently passing.
    apologies = ("tayyorlanmagan", "не подготовлено", "не готово")
    for code in ("GENERIC_LETTER_SUBSTITUTED", "GENERIC_SIFAT_MISMATCH"):
        for lang in ("uz", "ru"):
            card = coaching.render(code, lang, fields)
            shown = f'{card["headline"]} {card["fix"]}'.lower()
            for phrase in apologies:
                assert phrase not in shown, (
                    f"{code}.{lang} shows a fallback apology: {shown!r}")


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
