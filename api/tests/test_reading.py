# -*- coding: utf-8 -*-
"""Translations, reciters, and the two things the mushaf view must not get wrong.

Neither artifact is authored here: translations.json is a verbatim download of
two human translations and reciters.json is a probe result. So these tests are
about INTEGRITY and MAPPING - is every ayah covered, is verse 2:255 actually
verse 2:255 - rather than about the text being good, which is not something a
test can judge.
"""
import pytest

from tilawah import content
from tilawah.api.routes import _sura_ayat, list_reciters

pytestmark = pytest.mark.filterwarnings("ignore")


# ── translations ─────────────────────────────────────────────────────────

def test_every_ayah_has_both_translations():
    """A gap shows up as a blank space under an ayah, which reads as a bug in
    the app rather than as missing data."""
    table = content._translations_file()["translations"]
    assert len(table) == 6236
    missing = [k for k, v in table.items() if not v.get("uz") or not v.get("ru")]
    assert not missing, f"{len(missing)} ayat missing a translation: {missing[:5]}"


def test_the_mapping_is_not_shifted():
    """The source is a flat ordered list with no verse key, so the sura:aya
    mapping is positional and an off-by-one would silently shift EVERY verse.
    These four are unmistakable and spread across the mushaf."""
    tr = content.translation_of
    assert "alloh" in tr(1, 1, "uz").lower()          # basmala
    assert "yagonadir" in tr(112, 1, "uz").lower()    # qul huwa Allahu ahad
    assert "qayyum" in tr(2, 255, "uz").lower()       # ayat al-kursi
    assert "odamlar" in tr(114, 1, "uz").lower()      # qul a'udhu bi-rabbi n-nas


def test_the_last_ayah_of_the_quran_is_present():
    assert content.translation_of(114, 6, "uz")
    assert content.translation_of(114, 6, "ru")


def test_no_markup_survives():
    """The source carries <sup> footnote markers whose bodies are not in the
    response. Left in, they render as a stray digit mid-sentence."""
    table = content._translations_file()["translations"]
    bad = [k for k, v in table.items()
           if "<" in v["uz"] or "<" in v["ru"]]
    assert not bad, bad[:5]


def test_uzbek_uses_the_proper_modifier_letters():
    """The source types oʻ/gʻ with a backtick and the tutuq belgisi with an
    ASCII apostrophe. lib/i18n.ts holds the rest of the app to the real
    characters; the translation must not be the one place that differs."""
    table = content._translations_file()["translations"]
    typewriter = [k for k, v in table.items()
                  if "`" in v["uz"] or "'" in v["uz"]]
    assert not typewriter, typewriter[:5]
    assert "oʻzga" in content.translation_of(2, 255, "uz")


def test_unknown_language_falls_back_rather_than_blanking():
    assert content.translation_of(112, 1, "de")
    assert content.translation_of(9999, 1, "uz") == ""


def test_suspect_transliterations_are_recorded_not_silently_fixed():
    """The Uzbek source has a transliteration error at 112:2 - "Comaddir" for
    Somaddir, Cyrillic С read as Latin C. It is recorded in the artifact and
    deliberately NOT corrected: editing a scholar's rendering of an attribute
    of Allah on a heuristic is the machine-authored content decision 4 exists
    to prevent.

    This test pins the CONTRACT (findings are surfaced), not the count. If the
    upstream edition is fixed, the list empties and this still passes.
    """
    meta = content.translations_meta()
    assert "uz_suspect_transliteration" in meta
    for finding in meta["uz_suspect_transliteration"]:
        assert {"ayah", "word", "why"} <= set(finding)
        # Whatever was flagged must still be in the text, untouched.
        sura, aya = (int(x) for x in finding["ayah"].split(":"))
        assert finding["word"] in content.translation_of(sura, aya, "uz")


# ── the basmala, which has two opposite exceptions ───────────────────────

def test_most_suras_open_with_the_basmala():
    for sura in (2, 3, 18, 36, 112, 114):
        assert _sura_ayat(sura, "uz").has_basmala
        assert _sura_ayat(sura, "uz").bismillah


def test_al_fatiha_does_not_repeat_its_own_first_ayah():
    """In al-Fatiha the basmala IS ayah 1. Printing it above as well would show
    it twice."""
    out = _sura_ayat(1, "uz")
    assert out.has_basmala is False
    assert out.bismillah == ""


def test_at_tawba_has_no_basmala_at_all():
    out = _sura_ayat(9, "uz")
    assert out.has_basmala is False
    assert out.bismillah == ""


# ── reciters ─────────────────────────────────────────────────────────────

def test_reciters_are_offered():
    out = list_reciters()
    assert len(out.reciters) >= 10
    assert out.base_url.startswith("https://")


def test_the_default_is_one_of_them():
    """A default pointing at a folder that failed its probe would 404 on the
    very first play, for every learner who never opens the picker."""
    out = list_reciters()
    assert out.default in {r.id for r in out.reciters}


def test_ids_are_unique():
    ids = [r.id for r in list_reciters().reciters]
    assert len(ids) == len(set(ids))


def test_every_reciter_is_named_and_styled():
    """The everyayah folder is a filesystem path, not something to show a
    learner. Each entry has to carry a display name and a style the UI groups
    by, or the select degrades to directory listings."""
    for r in list_reciters().reciters:
        assert r.name
        # A human name, not the folder: no underscores and no bitrate in it.
        # (Sharing a prefix with the folder is fine and expected — the folder
        # is named after the reciter.)
        assert "_" not in r.name and "kbps" not in r.name.lower()
        assert r.name != r.id
        assert r.style in {"muallim", "murattal", "mujawwad"}


def test_a_teaching_recitation_is_available_and_preferred():
    """A muallim recording repeats each phrase for the listener. For a practice
    app that is the most useful thing on the host, so it should not be buried
    or absent."""
    out = list_reciters()
    assert any(r.style == "muallim" for r in out.reciters)
    default = next(r for r in out.reciters if r.id == out.default)
    assert default.style == "muallim"


def test_known_reciter_check_rejects_a_dropped_folder():
    """The client validates its saved choice against this list, so a folder
    removed by a rebuild stops being selectable rather than 404ing forever."""
    assert content.is_known_reciter(list_reciters().default)
    assert not content.is_known_reciter("Ghost_Reciter_9kbps")


def test_the_probe_covered_the_ayah_that_used_to_break_playback():
    """2:282 is the longest ayah and the file most likely missing from a
    partial mirror - the "playback dies on long suras" failure. Every shipped
    reciter must have been probed against it."""
    probed = content._reciters_file()["_meta"]["probed_ayat"]
    assert "2:282" in probed and "114:6" in probed
