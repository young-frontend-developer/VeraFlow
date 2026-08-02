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


def sample() -> list[TypedError]:
    """One reviewed code, one unreviewed, one with no content at all.

    SUB_AYN_HAMZA is ship+reviewed (via the dev override), GHUNNA_SHORT is
    status=collect, and GHUNNA_LONG has no rules.json entry whatsoever.
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


def test_dev_marks_only_the_unreviewed(env):
    """A reviewed correction must NOT be labelled draft, or the marker means
    nothing and gets ignored."""
    env("dev")
    shown, _ = pipeline.present(sample(), "uz")
    by_code = {s["code"]: s for s in shown}
    assert by_code["SUB_AYN_HAMZA"]["draft"] is False
    assert by_code["GHUNNA_SHORT"]["draft"] is True
    assert by_code["GHUNNA_LONG"]["draft"] is True


def test_unauthored_code_gets_a_body_without_invented_rulings(env):
    """GHUNNA_LONG has no entry in rules.json or either coaching registry. It
    still has to render, so it gets a stand-in — but decision 4 holds even
    here: the stand-in states the CODE and nothing else. No headline, no rule,
    no correction, no drill.

    The learner is not left with nothing: `word` and `letter` travel on the
    error itself, so the UI can still say where the mistake was. That is a
    location, not a ruling.
    """
    env("dev")
    shown, _ = pipeline.present(sample(), "uz")
    body = next(s for s in shown if s["code"] == "GHUNNA_LONG")["content"]
    assert body["unauthored"] is True
    assert body["label"] == "GHUNNA_LONG"
    assert body["headline"] == "" and body["fix"] == ""
    assert body["rule"] == "" and body["drill"] == ""
    assert body["reviewed"] is False


def test_authored_content_is_untouched(env):
    """The gate changes what is SHOWN, never what the content says."""
    env("dev")
    shown, _ = pipeline.present(sample(), "uz")
    body = next(s for s in shown if s["code"] == "SUB_AYN_HAMZA")["content"]
    assert body == content.render("SUB_AYN_HAMZA", "uz", sample()[0].dict())


# ─────────────────────────────────────────────── production: gate closed

def test_production_hides_unreviewed(env):
    env("production")
    shown, silent = pipeline.present(sample(), "uz")
    assert [s["code"] for s in shown] == ["SUB_AYN_HAMZA"]
    assert {s["code"] for s in silent} == {"GHUNNA_SHORT", "GHUNNA_LONG"}


def test_production_marks_nothing_draft(env):
    """`draft` must be present and false, not absent — a client that keys off
    its presence would then render nothing for a genuinely unreviewed card."""
    env("production")
    shown, _ = pipeline.present(sample(), "uz")
    assert all(s["draft"] is False for s in shown)


# ─────────────────────────────────────────────────────── no display cap

@pytest.mark.parametrize("name", ["dev", "production"])
def test_no_display_cap_in_either_environment(env, name):
    """MAX_SHOWN = 2 is gone. Five real errors are five corrections — telling a
    learner about two of them and silently dropping the rest taught them that
    the other three were fine."""
    env(name)
    many = [TypedError(code="SUB_AYN_HAMZA", at=i, letter="ع",
                       expected="ع", heard="ء") for i in range(5)]
    shown, silent = pipeline.present(many, "uz")
    assert len(shown) == 5 and silent == []
    assert not hasattr(pipeline, "MAX_SHOWN")


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
    """
    import anyio

    from tilawah.api import main

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

    monkeypatch.setattr(main, "settings", Forced(settings))

    async def run():
        async with main.lifespan(main.app):
            pass

    with pytest.raises(RuntimeError, match="content review gate is open"):
        anyio.run(run)


def test_meta_forces_the_pilot_banner(monkeypatch):
    """The banner must not be forgettable: an open review gate implies pilot,
    whatever TILAWAH_PILOT says."""
    from tilawah.api import routes

    patched = dataclasses.replace(settings, env="dev", pilot=False)
    monkeypatch.setattr(routes, "settings", patched)
    out = routes.meta()
    assert out.show_unreviewed is True and out.pilot is True
