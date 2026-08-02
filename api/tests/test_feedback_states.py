# -*- coding: utf-8 -*-
"""`clean`, `suppressed` and `analysable` are three different answers.

They used to collapse into two sentences, and the UI printed the SAME one -
"Toʻliq baholay olmadik" - for a correction the gate withheld and for a model
that returned nothing. Those are opposite situations: one means a judgement
exists and we may not show it, the other means no judgement was formed at all.
Indistinguishable on screen, they were also indistinguishable in a bug report.

The flags are what let the UI tell them apart, so they have to stay mutually
exclusive and each has to mean exactly one thing.
"""
import dataclasses

import pytest

from tilawah.config import settings
from tilawah.engine import pipeline
from tilawah.engine.pipeline import Feedback
from tilawah.engine.typed_errors import TypedError


@pytest.fixture
def env(monkeypatch):
    def _set(name: str):
        monkeypatch.setattr(pipeline, "settings",
                            dataclasses.replace(settings, env=name))
    return _set


REVIEWED = TypedError(code="SUB_AYN_HAMZA", at=0, letter="ع",
                      expected="ع", heard="ء")
UNREVIEWED = TypedError(code="GHUNNA_SHORT", at=1, letter="ن",
                        expected_count=4, heard_count=2)


def feedback(raw, lang="uz") -> Feedback:
    """The tail of analyze(), without the 2.42 GB model."""
    shown, silent = pipeline.present(raw, lang)
    return Feedback(status="ok", analysable=True, clean=not raw,
                    suppressed=bool(raw) and not shown,
                    errors=shown, silent_errors=silent)


def test_defaults_say_analysable():
    """Anything that does not explicitly disclaim an opinion is claiming one."""
    assert Feedback(status="ok").analysable is True


def test_nothing_detected_is_clean_and_not_suppressed():
    fb = feedback([])
    assert fb.clean is True
    assert fb.suppressed is False
    assert fb.analysable is True


def test_detected_and_shown_is_neither_clean_nor_suppressed(env):
    env("dev")
    fb = feedback([REVIEWED, UNREVIEWED])
    assert fb.clean is False
    assert fb.suppressed is False
    assert len(fb.errors) == 2


def test_withheld_in_production_is_suppressed_not_clean(env):
    """The one that must never read as praise: something WAS found."""
    env("production")
    fb = feedback([UNREVIEWED])
    assert fb.clean is False
    assert fb.suppressed is True
    assert fb.errors == []
    assert fb.analysable is True      # a judgement exists; it is being withheld


def test_suppression_cannot_happen_in_dev(env):
    """With the gate open there is nothing left to withhold, so the withheld
    message must be unreachable outside production."""
    env("dev")
    fb = feedback([UNREVIEWED])
    assert fb.suppressed is False
    assert len(fb.errors) == 1


def test_not_analysable_is_not_suppression_and_not_praise():
    """The model returned nothing to diff. No opinion was formed, so neither
    `clean` nor `suppressed` may be set - both would be claims we cannot make."""
    fb = Feedback(status="ok", analysable=False, heard_phonemes="")
    assert fb.analysable is False
    assert fb.clean is False
    assert fb.suppressed is False
    assert fb.errors == []


@pytest.mark.parametrize("name", ["dev", "production"])
def test_at_most_one_state_is_ever_set(env, name):
    """clean / suppressed / not-analysable are mutually exclusive by
    construction. If two could be true at once the UI's branch order would
    silently decide which message a learner sees."""
    env(name)
    for raw in ([], [REVIEWED], [UNREVIEWED], [REVIEWED, UNREVIEWED]):
        fb = feedback(raw)
        flags = [fb.clean, fb.suppressed, not fb.analysable]
        assert sum(flags) <= 1, f"{raw} set {flags} at once"
