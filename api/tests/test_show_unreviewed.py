# -*- coding: utf-8 -*-
"""TILAWAH_SHOW_UNREVIEWED — the diagnostic that bypasses the content gate.

The gate is the single most important safety property in the app: no correction
about the Quran reaches a learner unless a qori signed the words off. This flag
turns it off on purpose, so the tests here are as much about what it must NOT
do as what it does.

No model and no HTTP: pipeline.present() is the whole gate.
"""
import dataclasses

import pytest

from tilawah import content
from tilawah.config import Settings, settings
from tilawah.engine import pipeline
from tilawah.engine.typed_errors import TypedError


@pytest.fixture
def flag(monkeypatch):
    """Flip settings.show_unreviewed without re-importing the module."""
    def _set(on: bool, production: bool = False):
        patched = dataclasses.replace(
            settings, show_unreviewed=on,
            env="production" if production else "dev")
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


# ───────────────────────────────────────────────────────── gate closed

def test_gate_closed_hides_unreviewed(flag):
    flag(False)
    shown, silent = pipeline.present(sample(), "uz")
    assert [s["code"] for s in shown] == ["SUB_AYN_HAMZA"]
    assert {s["code"] for s in silent} == {"GHUNNA_SHORT", "GHUNNA_LONG"}


def test_gate_closed_marks_nothing_draft(flag):
    """`draft` must be present and false, not absent - a client that keys off
    its presence would then render nothing for a genuinely unreviewed card."""
    flag(False)
    shown, _ = pipeline.present(sample(), "uz")
    assert all(s["draft"] is False for s in shown)


def test_gate_closed_still_caps_at_two(flag):
    flag(False)
    many = [TypedError(code="SUB_AYN_HAMZA", at=i, letter="ع",
                       expected="ع", heard="ء") for i in range(5)]
    shown, silent = pipeline.present(many, "uz")
    assert len(shown) == pipeline.MAX_SHOWN and len(silent) == 3


# ───────────────────────────────────────────────────────── gate open

def test_gate_open_shows_everything(flag):
    flag(True)
    shown, silent = pipeline.present(sample(), "uz")
    assert {s["code"] for s in shown} == {"SUB_AYN_HAMZA", "GHUNNA_SHORT",
                                          "GHUNNA_LONG"}
    assert silent == []


def test_gate_open_lifts_the_display_cap(flag):
    """The point is to see everything the engine found, so the two-error cap
    goes too - otherwise the diagnostic hides the thing being diagnosed."""
    flag(True)
    many = [TypedError(code="SUB_AYN_HAMZA", at=i, letter="ع",
                       expected="ع", heard="ء") for i in range(5)]
    shown, silent = pipeline.present(many, "uz")
    assert len(shown) == 5 and silent == []


def test_gate_open_marks_only_the_unreviewed(flag):
    """A reviewed correction must NOT be labelled draft even in this mode, or
    the marker means nothing and gets ignored."""
    flag(True)
    shown, _ = pipeline.present(sample(), "uz")
    by_code = {s["code"]: s for s in shown}
    assert by_code["SUB_AYN_HAMZA"]["draft"] is False
    assert by_code["GHUNNA_SHORT"]["draft"] is True
    assert by_code["GHUNNA_LONG"]["draft"] is True


def test_unauthored_code_gets_a_body_without_invented_rulings(flag):
    """GHUNNA_LONG has no authored content. It still has to render, so it gets
    a stand-in - but decision 4 holds even here: the stand-in states the CODE
    and nothing else. No rule, no correction, no reason."""
    flag(True)
    shown, _ = pipeline.present(sample(), "uz")
    body = next(s for s in shown if s["code"] == "GHUNNA_LONG")["content"]
    assert body["unauthored"] is True
    assert body["rule"] == "GHUNNA_LONG"
    assert body["you_did"] == "" and body["fix"] == "" and body["drill"] == ""
    assert body["reviewed"] is False


def test_authored_content_is_untouched(flag):
    """The flag changes what is SHOWN, never what the content says."""
    flag(True)
    shown, _ = pipeline.present(sample(), "uz")
    body = next(s for s in shown if s["code"] == "SUB_AYN_HAMZA")["content"]
    assert body == content.render("SUB_AYN_HAMZA", "uz",
                                  sample()[0].dict())


# ───────────────────────────────────────────────── refuses to boot in prod

def test_default_is_off():
    """Anyone who has not opted in must get the gate closed."""
    assert Settings().show_unreviewed is False


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


@pytest.mark.parametrize("env", ["production", "prod", "PRODUCTION"])
def test_refuses_to_boot_in_production(env, monkeypatch):
    """Same contract as TILAWAH_DEBUG_AUDIO. Telling a learner they erred in
    the Quran on unreviewed content is the trust failure the whole project is
    arranged to avoid, so it must be impossible to deploy by accident."""
    with pytest.raises(RuntimeError, match="TILAWAH_SHOW_UNREVIEWED"):
        boot(monkeypatch, show_unreviewed=True, env=env)


def test_boots_in_dev(monkeypatch):
    """The other half: the flag has to be usable on a laptop, or it is not a
    diagnostic, it is just an obstacle."""
    boot(monkeypatch, show_unreviewed=True, env="dev")


def test_production_boots_with_the_flag_off(monkeypatch):
    """Guard against over-correcting into refusing to start at all."""
    boot(monkeypatch, show_unreviewed=False, env="production")


def test_meta_forces_the_pilot_banner(monkeypatch):
    """The banner must not be forgettable: bypassing the review gate implies
    pilot, whatever TILAWAH_PILOT says."""
    from tilawah.api import routes

    patched = dataclasses.replace(settings, show_unreviewed=True, pilot=False)
    monkeypatch.setattr(routes, "settings", patched)
    out = routes.meta()
    assert out.show_unreviewed is True and out.pilot is True
