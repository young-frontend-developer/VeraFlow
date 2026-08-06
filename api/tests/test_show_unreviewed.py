# -*- coding: utf-8 -*-
"""The content gate — now derived from TILAWAH_ENV rather than its own flag.

The gate is the single most important safety property in the app: no correction
about the Quran reaches a LEARNER unless a qori signed the words off. It used to
be a flag defaulting closed, which meant the default build also hid every
correction from the person building it — with 2 of 11 authored codes reviewed,
three real mistakes showed up as one, or as "we couldn't fully assess".

So the polarity is inverted: drafts show by default, and the gate closes in
production. These tests are as much about what production must NOT do as about
what dev does.

No model and no HTTP: pipeline.present() is the whole gate.
"""
import dataclasses

import pytest

from tilawah import content
from tilawah.config import Settings, settings
from tilawah.content import coaching
from tilawah.engine import pipeline
from tilawah.engine.typed_errors import TypedError


@pytest.fixture
def env(monkeypatch):
    """Run present() as dev or as production.

    Patches TILAWAH_ENV, not the gate — settings.show_unreviewed is a derived
    property now, so going through env is the only way to move it, and that is
    exactly the switch a deploy actually flips.
    """
    def _set(name: str):
        patched = dataclasses.replace(settings, env=name)
        monkeypatch.setattr(pipeline, "settings", patched)
        return patched
    return _set


@pytest.fixture
def reviewed(monkeypatch):
    """Mark ONE registry entry status='reviewed', for the duration of a test.

    Nothing in this project is genuinely reviewed - every entry in every
    registry is status='draft' by design, and the only two codes rules.json
    calls reviewed carry a DEV-OVERRIDE that test_no_dev_overrides_remain fails
    on. So the "reviewed content behaves differently" property has no real data
    to exercise it, and asserting it against the dev override tested an
    accident of the fixtures rather than the gate.

    Patching one entry tests the MECHANISM, which is the thing that has to keep
    working when a qori does start signing text off.
    """
    reg = coaching.registry()
    monkeypatch.setitem(reg, "MAKHARIJ_AIN_TO_HAMZA",
                        dict(reg["MAKHARIJ_AIN_TO_HAMZA"], status="reviewed"))


@pytest.fixture
def reviewed_all(monkeypatch):
    """The same, for every entry — used where a test needs SEVERAL distinct
    codes to survive the production gate at once."""
    reg = coaching.registry()
    for code, spec in list(reg.items()):
        monkeypatch.setitem(reg, code, dict(spec, status="reviewed"))


def sample() -> list[TypedError]:
    """Three codes, none of them reviewed.

    SUB_AYN_HAMZA aliases to MAKHARIJ_AIN_TO_HAMZA (v3, status=draft),
    GHUNNA_SHORT to GHUNNA_TOO_SHORT (v3, status=draft), and GHUNNA_LONG has no
    entry in any registry.

    SUB_AYN_HAMZA USED TO BE THE REVIEWED ONE, on the strength of rules.json's
    DEV-OVERRIDE. It is not any more, and that is a fix rather than a
    regression: the words a learner now sees for this code come from v3, which
    no qori has read. Production showing them because a stale override sat on
    the OLDER rules.json wording is precisely the hole the gate exists to close.
    The override is still reported by content.dev_overrides() and still fails
    test_no_dev_overrides_remain, so nothing about it has gone quiet.
    """
    return [
        TypedError(code="SUB_AYN_HAMZA", at=0, letter="ع",
                   expected="ع", heard="ء"),
        TypedError(code="GHUNNA_SHORT", at=1, letter="ن",
                   expected_count=4, heard_count=2),
        TypedError(code="GHUNNA_LONG", at=2, letter="ن",
                   expected_count=2, heard_count=4),
    ]


# ──────────────────────────────────────────────── dev: the default, gate open

def test_dev_shows_everything():
    """No fixture, no patching: this is what an unconfigured checkout does."""
    shown, silent = pipeline.present(sample(), "uz")
    assert {s["code"] for s in shown} == {"SUB_AYN_HAMZA", "GHUNNA_SHORT",
                                          "GHUNNA_LONG"}
    assert silent == []


def test_dev_is_the_default():
    """The whole point of the inversion. An unconfigured checkout leaves the
    gate open, because an opt-in flag is what made the default build useless.

    Asserts the shipped default directly rather than through monkeypatch:
    Settings' fields are dataclass defaults evaluated at import, so setting the
    variable afterwards would prove nothing.
    """
    assert Settings().env == "dev"
    assert Settings().show_unreviewed is True


def test_dev_marks_only_the_unreviewed(env, reviewed):
    """A reviewed correction must NOT be labelled draft, or the marker means
    nothing and gets ignored."""
    env("dev")
    shown, _ = pipeline.present(sample(), "uz")
    by_code = {s["code"]: s for s in shown}
    assert by_code["SUB_AYN_HAMZA"]["draft"] is False
    assert by_code["GHUNNA_SHORT"]["draft"] is True
    assert by_code["GHUNNA_LONG"]["draft"] is True


def test_dev_marks_everything_draft_as_things_actually_stand(env):
    """Without the fixture above, nothing is reviewed - so everything is draft.

    This is the honest state of the content today, asserted so that the day a
    qori signs something off, the change shows up here as a failing test rather
    than as an unnoticed shift in what production emits.
    """
    env("dev")
    shown, _ = pipeline.present(sample(), "uz")
    assert all(s["draft"] is True for s in shown)


def test_unauthored_code_gets_a_body_without_invented_rulings(env):
    """A code with no entry anywhere still has to render, so it gets a stand-in
    — and decision 4 holds even here: no headline, no correction, nothing
    invented.

    The learner is not left with nothing, and gets rather more than a location.
    `kind` gives the card a real title, `word`/`letter` travel on the error
    itself, and the PRACTICE LADDER is derived rather than authored — so an
    error nobody has written a word about still comes with the letter to drill,
    the syllables to drill it under, and the word to put it back into. That is a
    location and an exercise, neither of which is a ruling.

    THE STAND-IN NO LONGER CARRIES THE CODE. `label` is rendered as the card's
    kicker, so putting the code there printed an internal identifier on a
    learner's screen.

    THE EXAMPLE USED TO BE GHUNNA_LONG, and it is no longer available: v6
    authored it, along with SHADDA_SHORT, SHADDA_LONG and SUB_HA_HEH — the four
    codes the engine could always emit and nobody had ever written words for.
    Every emitted code now resolves, so this path is reached only by a code that
    does not exist at all. That is worth keeping tested: the stand-in is what
    stops a future code from rendering as a blank card or a crash, and it must
    stay honest when it does.
    """
    env("dev")
    errs = sample() + [TypedError(code="NOT_A_REAL_CODE", at=9, letter="ن")]
    shown, _ = pipeline.present(errs, "uz")
    card = next(s for s in shown if s["code"] == "NOT_A_REAL_CODE")
    body = card["content"]
    assert body["unauthored"] is True
    assert body["label"] == ""
    assert body["headline"] == "" and body["fix"] == ""
    assert body["reviewed"] is False
    # It still has a learner-facing title to render under.
    assert card["kind"] == "pronunciation"
    # ...and a ladder, because none of it needed authoring. This fixture's
    # error was never located in a word, so there is no word rung to build —
    # which is the point: the ladder gives what it can and omits what it
    # cannot, rather than showing an empty row.
    assert [r["focus"] for r in card["practice"]] == [
        "letter", "syllables", "ayah"]


def test_no_card_carries_the_code_into_rendered_text(env):
    """Part B: internal codes never reach a learner.

    The code stays on the record — logging, the draft marker's audit trail, the
    "this assessment is wrong" report all need it — but no field the UI prints
    as prose may contain it.
    """
    env("dev")
    shown, _ = pipeline.present(sample(), "uz")
    for card in shown:
        body = card["content"]
        for key in ("headline", "fix", "label"):
            assert card["code"] not in (body.get(key) or ""), (
                f'{card["code"]} leaked into content.{key}')
        # The ladder is Arabic text the UI prints at display size. A code
        # reaching it would be the same leak by another route.
        for rung in card["practice"]:
            for item in rung["items"]:
                assert card["code"] not in item, (
                    f'{card["code"]} leaked into a practice rung')


def test_authored_content_is_untouched(env):
    """The gate changes what is SHOWN, never what the content says."""
    env("dev")
    shown, _ = pipeline.present(sample(), "uz")
    body = next(s for s in shown if s["code"] == "SUB_AYN_HAMZA")["content"]
    assert body == content.render("SUB_AYN_HAMZA", "uz", sample()[0].dict())


# ─────────────────────────────────────────────── production: gate closed

def test_production_hides_unreviewed(env, reviewed):
    env("production")
    shown, silent = pipeline.present(sample(), "uz")
    assert [s["code"] for s in shown] == ["SUB_AYN_HAMZA"]
    assert {s["code"] for s in silent} == {"GHUNNA_SHORT", "GHUNNA_LONG"}


def test_production_currently_shows_nothing_at_all(env):
    """With no entry reviewed anywhere, production withholds every correction.

    Stated as a test because it is easy to mistake for a bug and because it is
    the real launch blocker: the gate is working, and there is simply no
    reviewed content behind it yet. Nothing here is worth "fixing" in code -
    it clears when a qori signs entries off.
    """
    env("production")
    shown, silent = pipeline.present(sample(), "uz")
    assert shown == []
    assert len(silent) == 3


def test_production_marks_nothing_draft(env):
    """`draft` must be present and false, not absent — a client that keys off
    its presence would then render nothing for a genuinely unreviewed card."""
    env("production")
    shown, _ = pipeline.present(sample(), "uz")
    assert all(s["draft"] is False for s in shown)


# ─────────────────────────────────────────────────────── no display cap

@pytest.mark.parametrize("name", ["dev", "production"])
def test_no_display_cap_in_either_environment(env, reviewed_all, name):
    """MAX_SHOWN = 2 is gone. Five DISTINCT errors are five corrections —
    telling a learner about two of them and silently dropping the rest taught
    them that the other three were fine.

    Distinct on purpose. Five occurrences of the same error on the same letter
    are now ONE card by design (see the merging tests below), so repeating one
    code five times would prove the opposite of what this test is for.

    Needs `reviewed_all` for the production leg: with nothing signed off, the
    gate would hide all five and the absence of a cap would prove nothing.
    """
    env(name)
    many = [
        TypedError(code="SUB_AYN_HAMZA", at=0, letter="ع", expected="ع", heard="ء"),
        TypedError(code="SUB_SAD_SEEN", at=1, letter="ص", expected="ص", heard="س"),
        TypedError(code="SUB_QAF_KAF", at=2, letter="ق", expected="ق", heard="ك"),
        TypedError(code="MADD_SHORT", at=3, letter="ا",
                   expected_count=4, heard_count=2),
        TypedError(code="QALQALA_DROP", at=4, letter="ڇ"),
    ]
    shown, silent = pipeline.present(many, "uz")
    assert len(shown) == 5 and silent == []
    assert not hasattr(pipeline, "MAX_SHOWN")


# ───────────────────────────────────────────────────── one card per mistake

def test_repeats_merge_into_one_card(env):
    """Five occurrences of one letter error is ONE card, not five.

    This was the single loudest defect in the results screen: «لِإِيلَٰفِ» with
    a mispronounced ل produced five identical cards, and a learner reading the
    second one has already stopped reading.
    """
    env("dev")
    many = [TypedError(code="SUB_SAD_SEEN", at=i, letter="ص", expected="ص",
                       heard="س", word="ٱلصَّمَدُ", word_index=1)
            for i in (2, 5, 8, 11, 14)]
    shown, _ = pipeline.present(many, "uz")
    assert len(shown) == 1
    card = shown[0]
    assert card["count"] == 5
    assert card["words"] == ["ٱلصَّمَدُ"]


def test_merging_keeps_every_occurrence_for_the_ayah(env):
    """Merging the CARD must not lose the positions.

    The ayah marks every errored letter red, so all five `at` values have to
    survive the fold even though one card is rendered.
    """
    env("dev")
    ats = [2, 5, 8, 11, 14]
    many = [TypedError(code="SUB_SAD_SEEN", at=i, letter="ص", expected="ص",
                       heard="س", word="ٱلصَّمَدُ", word_index=1) for i in ats]
    shown, _ = pipeline.present(many, "uz")
    assert [o["at"] for o in shown[0]["occurrences"]] == ats


def test_same_letter_in_different_words_is_still_one_card(env):
    """Grouping is (code, letter), so one drill covers all of them — but the
    card has to name every word it happened in."""
    env("dev")
    many = [
        TypedError(code="SUB_SAD_SEEN", at=1, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=0),
        TypedError(code="SUB_SAD_SEEN", at=7, letter="ص", expected="ص",
                   heard="س", word="صِرَٰطَ", word_index=2),
    ]
    shown, _ = pipeline.present(many, "uz")
    assert len(shown) == 1
    assert shown[0]["words"] == ["ٱلصَّمَدُ", "صِرَٰطَ"]


def test_different_letters_do_not_merge(env):
    """Same code, different letter, is a different mistake and a different
    drill — merging those would put two corrections behind one card."""
    env("dev")
    many = [
        TypedError(code="LETTER_DROPPED", at=1, letter="ص", expected="ص"),
        TypedError(code="LETTER_DROPPED", at=4, letter="ط", expected="ط"),
    ]
    shown, _ = pipeline.present(many, "uz")
    assert len(shown) == 2


def test_merge_preserves_severity_ranking(env):
    """Ranking happens before the fold, and the fold must not undo it."""
    env("dev")
    many = [
        TypedError(code="MADD_SHORT", at=0, letter="ا",
                   expected_count=4, heard_count=2),        # medium
        TypedError(code="SUB_AYN_HAMZA", at=9, letter="ع",
                   expected="ع", heard="ء"),                # high
    ]
    shown, _ = pipeline.present(many, "uz")
    assert [s["code"] for s in shown] == ["SUB_AYN_HAMZA", "MADD_SHORT"]


def test_ordering_is_by_severity_then_position(env):
    """Uncapped does not mean unordered — the most serious correction still
    comes first, which is what the cap was really buying."""
    env("dev")
    errs = [
        TypedError(code="MADD_LONG", at=5, letter="ا",
                   expected_count=2, heard_count=6),      # severity low
        TypedError(code="SUB_AYN_HAMZA", at=9, letter="ع",
                   expected="ع", heard="ء"),              # severity high
        TypedError(code="GHUNNA_SHORT", at=1, letter="ن",
                   expected_count=4, heard_count=2),      # severity medium
    ]
    shown, _ = pipeline.present(errs, "uz")
    assert [s["code"] for s in shown] == ["SUB_AYN_HAMZA", "GHUNNA_SHORT",
                                          "MADD_LONG"]


# ───────────────────────────────────────────── the gate cannot be configured

def test_production_closes_the_gate():
    assert dataclasses.replace(settings, env="production").show_unreviewed is False


@pytest.mark.parametrize("name", ["production", "prod", "PRODUCTION"])
def test_every_spelling_of_production_closes_it(name):
    assert dataclasses.replace(settings, env=name).show_unreviewed is False


def test_there_is_no_override_flag():
    """TILAWAH_SHOW_UNREVIEWED is gone and must not come back as a way to prise
    the gate open in production.

    Checks the source, because that is where the failure would be: any
    env-var override would have to be read here, and a settings instance built
    in-process cannot see one anyway (field defaults are bound at import).
    """
    import inspect
    import re

    from tilawah import config

    # Only READS count. config.py's docstring still names the old flag to
    # explain why it went, and that prose must not fail this test.
    read = re.findall(r"getenv\(\s*[\"']([^\"']+)", inspect.getsource(config))
    assert not [v for v in read if "SHOW_UNREVIEWED" in v], (
        "the content gate is derived from TILAWAH_ENV; an override variable "
        "would put unreviewed rulings one misconfiguration from a learner")
    # A property, not a field — so nothing can pass it to the constructor.
    assert isinstance(type(settings).show_unreviewed, property)
    assert "show_unreviewed" not in {f.name for f in
                                     dataclasses.fields(Settings)}


def boot(monkeypatch, **overrides):
    """Actually run the app's lifespan, rather than rehearsing its condition.

    A test that re-implements the guard passes just as happily after someone
    deletes the guard, which is the one failure mode that matters here.

    ⚠️ `debug_audio` IS PINNED OFF unless a caller asks otherwise. `settings` is
    built from the developer's api/.env, so every override here inherited
    whatever that file happened to say - and main.py has a SECOND production
    guard, on debug audio. Setting TILAWAH_DEBUG_AUDIO=1 locally to diagnose one
    bug therefore turned these tests red for a reason with nothing to do with
    the review gate they are about. Each guard gets its own test; neither may
    depend on an untracked file.
    """
    import anyio

    from tilawah.api import main

    overrides.setdefault("debug_audio", False)
    monkeypatch.setattr(main, "settings",
                        dataclasses.replace(settings, **overrides))

    async def run():
        async with main.lifespan(main.app):
            pass

    anyio.run(run)


def test_production_boots_with_the_gate_closed(monkeypatch):
    boot(monkeypatch, env="production")


def test_dev_boots(monkeypatch):
    boot(monkeypatch, env="dev")


def test_boot_refuses_if_the_gate_is_ever_open_in_production(monkeypatch):
    """The structural guarantee, tested through the guard rather than around
    it. show_unreviewed is derived, so this state should be unreachable — if a
    refactor makes it reachable again, production must fail to start."""
    import anyio

    from tilawah.api import main

    class Forced:
        """A settings stand-in with the gate forced open in production."""
        def __init__(self, base):
            self._base = base

        def __getattr__(self, name):
            return getattr(self._base, name)

        is_production = True
        show_unreviewed = True
        # Off, so the gate is the only thing that can refuse the boot. See
        # boot() - the debug-audio guard is real, fires first, and belongs to
        # its own test.
        debug_audio = False

    monkeypatch.setattr(main, "settings", Forced(settings))

    async def run():
        async with main.lifespan(main.app):
            pass

    with pytest.raises(RuntimeError, match="content review gate is open"):
        anyio.run(run)


def test_boot_refuses_if_debug_audio_is_on_in_production(monkeypatch):
    """The OTHER production guard, which had no test at all.

    TILAWAH_DEBUG_AUDIO=1 writes every upload to disk with no consent of any
    kind. It is the right tool on a laptop chasing a "3 mistakes, 1 card"
    report and catastrophic on a box real people can reach, which is exactly
    the combination that gets left switched on. main.py refuses to start; that
    refusal is now asserted rather than assumed.
    """
    import anyio

    from tilawah.api import main

    monkeypatch.setattr(main, "settings", dataclasses.replace(
        settings, env="production", debug_audio=True))

    async def run():
        async with main.lifespan(main.app):
            pass

    with pytest.raises(RuntimeError, match="TILAWAH_DEBUG_AUDIO"):
        anyio.run(run)


def test_meta_forces_the_pilot_banner(monkeypatch):
    """The banner must not be forgettable: an open review gate implies pilot,
    whatever TILAWAH_PILOT says."""
    from tilawah.api import routes

    patched = dataclasses.replace(settings, env="dev", pilot=False)
    monkeypatch.setattr(routes, "settings", patched)
    out = routes.meta()
    assert out.show_unreviewed is True and out.pilot is True
