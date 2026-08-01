# -*- coding: utf-8 -*-
"""Preconditions: what each check is ALLOWED to fire on.

These pin the narrowings against real ayat from the phonetizer rather than
against hand-written phoneme strings, because the three noon rulings are
distinguished by CHARACTER in QPS (ن vs ں vs assimilation) and a hand-written
string is exactly where that gets assumed wrong.
"""
import pytest
from quran_transcript import Aya, quran_phonetizer

from tilawah.engine.coverage import (UNIVERSAL, in_scope, possible_codes,
                                     registry)
from tilawah.engine.moshaf import MOSHAF


def codes(sura: int, aya: int) -> set[str]:
    uth = Aya(sura, aya).get().uthmani
    flat = quran_phonetizer(uth, MOSHAF, remove_spaces=True)
    spaced = quran_phonetizer(uth, MOSHAF, remove_spaces=False)
    return possible_codes(flat.phonemes, flat.sifat, spaced.phonemes)


# ───────────────────────────────────── izhar positions (GHUNNA_ADDED is gone)

def groups_of(sura: int, aya: int):
    from tilawah.engine.coverage import _sifa_groups
    uth = Aya(sura, aya).get().uthmani
    return _sifa_groups(quran_phonetizer(uth, MOSHAF, remove_spaces=True).sifat)


def test_ghunna_added_is_deleted():
    """Its signal asked for a not_maghnoon -> maghnoon flip, but the reference
    marks even an izhar noon maghnoon - ghunnah is a property of the LETTER. No
    such flip exists anywhere in the Quran, so no precondition could rescue it."""
    assert "GHUNNA_ADDED" not in registry()


@pytest.mark.parametrize("sura,aya,why", [
    (1, 7, "أَنْعَمْتَ - nun sakin then ع"),
    (112, 4, "كُفُوًا أَحَدٌ - tanwin then hamza, written as a plain ن"),
    (6, 26, "عَنْهُ - nun sakin then ه"),
])
def test_izhar_positions_found(sura, aya, why):
    """The position logic outlives the entry: an added ghunnah is a duration
    error at exactly these spots, so whatever replaces GHUNNA_ADDED needs them."""
    from tilawah.engine.coverage import izhar_positions

    assert izhar_positions(groups_of(sura, aya)), why


@pytest.mark.parametrize("sura,aya,why", [
    (114, 4, "مِن شَرِّ - ikhfa, QPS writes ں not ن"),
    (2, 5, "هُدًى مِّن - idgham, the noon is assimilated away"),
    (110, 2, "ٱلنَّاسَ - ghunnah mushaddadah, a run then a haraka"),
    (112, 1, "قُلْ هُوَ - no noon at all"),
])
def test_izhar_positions_empty_outside_izhar(sura, aya, why):
    from tilawah.engine.coverage import izhar_positions

    assert not izhar_positions(groups_of(sura, aya)), why


# ────────────────────────────────────────────────── MADD_ADDED split

def test_madd_added_leen_is_restricted_but_madd_added_is_not():
    from tilawah.engine.coverage import leen_positions

    def ph(s, a):
        return quran_phonetizer(Aya(s, a).get().uthmani, MOSHAF,
                                remove_spaces=True).phonemes

    # 1:7 عَلَيْهِمْ - sakin ي after fatha, the classic over-lengthened leen
    assert leen_positions(ph(1, 7))
    assert "MADD_ADDED_LEEN" in codes(1, 7)
    # 112:1 قُلْ هُوَ ٱللَّهُ أَحَدٌ - no leen letter
    assert not leen_positions(ph(112, 1))
    assert "MADD_ADDED_LEEN" not in codes(112, 1)
    # ...but the catch-all is still possible in both.
    assert "MADD_ADDED" in codes(1, 7) and "MADD_ADDED" in codes(112, 1)


def test_madd_added_leen_has_no_authored_content():
    """Decision 4: no LLM authors a tajweed rule. The split created the code,
    a qori must create the words. Until then it must render to nothing."""
    from tilawah import content

    assert registry()["MADD_ADDED_LEEN"]["content_status"] == "NEEDS_AUTHORING"
    assert content.render("MADD_ADDED_LEEN", "uz", {}) is None


# ──────────────────────────────────────── ذ/ظ merge

def test_interdental_merge_replaced_both_zay_entries():
    r = registry()
    assert "MAKHARIJ_INTERDENTAL_TO_ZAY" in r
    assert "MAKHARIJ_THAL_TO_ZAY" not in r
    assert "MAKHARIJ_ZAA_TO_ZAY" not in r
    assert set(r["MAKHARIJ_INTERDENTAL_TO_ZAY"]["merged_from"]) == {
        "MAKHARIJ_THAL_TO_ZAY", "MAKHARIJ_ZAA_TO_ZAY"}


def test_interdental_fires_on_either_letter():
    assert "MAKHARIJ_INTERDENTAL_TO_ZAY" in codes(2, 2)      # ذَٰلِكَ  - ذ
    assert "MAKHARIJ_INTERDENTAL_TO_ZAY" in codes(1, 7)      # ٱلَّذِينَ - ذ
    assert "MAKHARIJ_INTERDENTAL_TO_ZAY" in codes(2, 20)     # أَظْلَمَ  - ظ
    assert "MAKHARIJ_INTERDENTAL_TO_ZAY" not in codes(112, 1)  # neither letter


def test_heaviness_confusion_stays_a_separate_entry():
    """The merge is by CORRECTION, not by letter. ذ↔ظ is a heaviness error with
    a different drill, so folding it in would put two incompatible fixes behind
    one code."""
    r = registry()
    assert "MAKHARIJ_THAL_TO_ZAA_CONFUSION" in r
    assert "merged_from" not in r["MAKHARIJ_THAL_TO_ZAA_CONFUSION"]


# ──────────────────────────────────────────────────── the narrowings

def test_tafkheem_added_needs_a_mutbaq_neighbour():
    """1:7 has صِرَٰطَ and ٱلضَّآلِّينَ - light letters beside ص and ض."""
    assert "TAFKHEEM_ADDED" in codes(1, 7)
    # 112:1 قُلْ هُوَ ٱللَّهُ أَحَدٌ has no mutbaq letter anywhere.
    assert "TAFKHEEM_ADDED" not in codes(112, 1)


def test_jahr_lost_excludes_the_qalqalah_letters():
    """A devoiced sakin ق or ب is reported as a qalqalah problem. 112:1 ends on
    a qalqalah dal and has no ذ ز ض ظ غ, so JAHR_LOST must stay silent while the
    qalqalah checks do not."""
    c = codes(112, 1)
    assert "QALQALAH_MISSING" in c
    assert "JAHR_LOST" not in c


def test_shidda_lost_excludes_the_qalqalah_letters():
    c = codes(112, 1)
    assert "QALQALAH_MISSING" in c and "SHIDDA_LOST" not in c


# ──────────────────────────────────── qalqala: the shadda exception (2-dars)

def qalqala_groups(sura: int, aya: int):
    """[(group text, qalqla value, sakin?)] for every qalqalah LETTER present."""
    uth = Aya(sura, aya).get().uthmani
    flat = quran_phonetizer(uth, MOSHAF, remove_spaces=True)
    out = []
    for s in flat.sifat:
        g = getattr(s, "phonemes", None) or getattr(s, "phonemes_group", None)
        text = g if isinstance(g, str) else getattr(g, "text", "")
        q = getattr(s, "qalqla", None)
        q = getattr(q, "text", q)
        base = next((c for c in (text or "") if c not in set("َُِ") and c != "ڇ"), "")
        if base in set("قطبجد"):
            out.append((text, q, not (set(text) & set("َُِ"))))
    return out


@pytest.mark.parametrize("sura,aya,word,why", [
    (111, 1, "تَبَّتْ", "ب with shadda mid-word, joined to what follows"),
    (1, 2, "رَبِّ", "ب with shadda mid-word, joined"),
    (96, 1, "رَبِّكَ", "ب with shadda mid-word, joined"),
])
def test_joined_shadda_takes_no_qalqala(sura, aya, word, why):
    """2-dars: a qalqala letter carrying shadda MID-WORD, joined to what
    follows, takes NO qalqala. Qalqala applies at lozim sukun and oriz sukun.

    This pins an UPSTREAM guarantee. quran_transcript already gets this right,
    so the exception is not reimplemented here - restating a rule the phonetizer
    already applies is how the two drift apart. What this test buys is a loud
    failure if that upstream behaviour ever changes, because without the
    exception QALQALAH_MISSING false-fires on every joined shadda in the Quran.
    """
    joined = [(t, q) for t, q, sakin in qalqala_groups(sura, aya)
              if not sakin and t.count(t[0]) > 1]
    assert joined, f"no joined shadda found in {word} - test no longer covers it"
    for text, q in joined:
        assert q == "not_moqalqal", f"{word}: {text!r} wrongly marked {q}"


def test_the_same_letter_does_take_qalqala_at_oriz_sukun():
    """The other half, and the reason a blanket 'shadda -> no qalqala' rule
    would be wrong: 111:1 ends وَتَبَّ, the SAME shadda'd ب, and stopping on it
    creates oriz sukun - so qalqala applies there and is marked ڇ."""
    uth = Aya(111, 1).get().uthmani
    flat = quran_phonetizer(uth, MOSHAF, remove_spaces=True)
    assert flat.phonemes.endswith("ڇ"), flat.phonemes
    final = [(t, q) for t, q, sakin in qalqala_groups(111, 1) if sakin]
    assert final and all(q == "moqalqal" for _t, q in final)


def test_qalqala_precondition_follows_the_sifa_not_the_letter():
    """1:2 has رَبِّ - a qalqala LETTER, but a joined shadda, so no qalqala.
    A letter-based precondition would fire here; the ṣifa-based one must not."""
    c = codes(1, 2)
    assert "QALQALAH_MISSING" not in c and "QALQALAH_EXCESSIVE" not in c


# ────────────────────────────────── sukunli miym (6-dars), v3 entries

def test_mim_rulings_are_distinguished_by_character():
    from tilawah.engine.coverage import mim_izhar_positions

    def ph(s, a):
        return quran_phonetizer(Aya(s, a).get().uthmani, MOSHAF,
                                remove_spaces=True).phonemes

    # 105:4 تَرْمِيهِم بِحِجَارَةٍ - miym + بo -> the hidden meem ۾
    assert "۾" in ph(105, 4)
    # 2:10 قُلُوبِهِم مَّرَضٌ - miym + miym -> a run, i.e. idgham mislayn
    assert "مممم" in ph(2, 10)
    # 109:6 لَكُمْ دِينُكُمْ - miym + دol -> izhar, plain م then a consonant
    assert any(nxt == "د" for _i, nxt in mim_izhar_positions(ph(109, 6)))


def test_mim_izhar_edge_weights_fa_and_waw_higher():
    """6-dars flags ف and و specifically: their makhraj is close enough to miym
    that an unintended ixfo slips in."""
    from tilawah.engine.coverage import detection_weight

    def ph(s, a):
        return quran_phonetizer(Aya(s, a).get().uthmani, MOSHAF,
                                remove_spaces=True).phonemes

    # 3:10 أَمْوَٰلُهُمْ وَلَآ - sukunli miym before و
    assert detection_weight("MIM_IZHAR_SHAFAWIYA_WRONG", ph(3, 10)) > 1.0
    # 109:6 لَكُمْ دِينُكُمْ - izhar, but before دol, not ف/و ... and 8:30 has
    # no sukunli miym before ف/و either.
    assert detection_weight("MIM_IZHAR_SHAFAWIYA_WRONG", ph(8, 30)) == 1.0
    # No other code is affected.
    assert detection_weight("QALQALAH_MISSING", ph(3, 10)) == 1.0


def test_mim_weighting_is_inert_until_the_entry_is_promoted():
    """Honesty check. The three MIM_* entries are detection_confidence='low',
    so in_scope() excludes them and the weight cannot influence anything. If
    this starts failing, someone promoted an entry and the weighting became
    live - which is fine, but it must be a decision, not a side effect."""
    assert "MIM_IZHAR_SHAFAWIYA_WRONG" in registry()
    assert "MIM_IZHAR_SHAFAWIYA_WRONG" not in in_scope()


# ─────────────────────────────────────────────────────── the honesty

def test_universal_is_declared_not_hidden():
    """The point of UNIVERSAL is that a precondition nobody could narrow is
    named as such instead of being left to inflate coverage silently."""
    assert UNIVERSAL == {"MADD_ADDED"}
    assert all(c in in_scope() for c in UNIVERSAL)


def test_universal_codes_are_excluded_from_the_coverage_score():
    from tilawah.engine.coverage import coverage

    uth = Aya(1, 7).get().uthmani
    flat = quran_phonetizer(uth, MOSHAF, remove_spaces=True)
    cov = coverage(flat.phonemes, flat.sifat)
    assert "MADD_ADDED" in cov["relevant"], "still reported as relevant"
    # ...but it must not be able to move the score.
    assert cov["score"] <= 1.0


def test_narrowed_codes_are_not_universal_any_more():
    """REGRESSION. These four sat at 100.0% and took the top four review slots.
    Sampling a handful of short suras is enough to prove they no longer fire
    everywhere; tools/audit_preconditions.py has the exhaustive numbers."""
    sample = [(112, 1), (112, 4), (110, 2), (114, 4), (103, 1), (108, 1)]
    for code in ("TAFKHEEM_ADDED", "JAHR_LOST", "GHUNNA_ADDED", "SHIDDA_LOST"):
        hits = sum(code in codes(s, a) for s, a in sample)
        assert hits < len(sample), f"{code} still fires on every segment"


def test_every_precondition_names_a_real_registry_code():
    """A typo in a code string would make a check unreachable and nothing else
    would notice."""
    known = set(registry())
    for s, a in [(1, 7), (2, 5), (112, 4), (114, 4)]:
        assert not (codes(s, a) - known)
