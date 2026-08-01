# -*- coding: utf-8 -*-
"""The qori review tool: decisions, edits, and the overlay that survives a
registry regeneration.

The property that matters most here is the last one. v3 is generated, so an
approval written into it would vanish the next time anyone ran
tools/apply_v3_patch.py — losing the scarcest data in the project.
"""
import dataclasses
import json

import pytest

from tilawah.api import routes
from tilawah.config import settings
from tilawah.engine import coverage, review


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Point the decisions file at a temp path and clear the registry cache."""
    path = tmp_path / "tajweed_registry_review.json"
    monkeypatch.setattr(review, "PATH", path)
    coverage.registry.cache_clear()
    coverage.in_scope.cache_clear()
    yield path
    coverage.registry.cache_clear()
    coverage.in_scope.cache_clear()


def a_code() -> str:
    """Any in-scope reviewable code, taken from the live registry."""
    return sorted(coverage.in_scope())[0]


# ─────────────────────────────────────────────────────────── decisions

def test_approve_persists_and_flips_status(store):
    code = a_code()
    assert coverage.registry()[code]["status"] == "draft"

    review.record(code, "reviewed", reviewed_by="Rahmatulloh")

    assert store.exists()
    assert coverage.registry()[code]["status"] == "reviewed"
    assert coverage.is_reviewed(code), "must feed the coverage gate"


def test_approve_requires_a_name(store):
    """An approval with nobody's name on it is not an audit trail, and this is
    the record asserting that a human vouched for a ruling about the Quran."""
    with pytest.raises(ValueError, match="reviewed_by"):
        review.record(a_code(), "reviewed", reviewed_by="   ")


def test_reject_is_not_reviewed(store):
    code = a_code()
    review.record(code, "rejected", reviewed_by="Q")
    assert coverage.registry()[code]["status"] == "rejected"
    assert not coverage.is_reviewed(code)


def test_reset_withdraws_a_decision(store):
    code = a_code()
    review.record(code, "reviewed", reviewed_by="Q")
    review.record(code, "draft")
    assert coverage.registry()[code]["status"] == "draft"
    assert not coverage.is_reviewed(code)


def test_decision_records_who_and_when(store):
    code = a_code()
    entry = review.record(code, "reviewed", reviewed_by="Odilxon qori")
    assert entry["reviewed_by"] == "Odilxon qori"
    assert entry["reviewed_at"].startswith("20")
    assert coverage.registry()[code]["reviewed_by"] == "Odilxon qori"


# ──────────────────────────────────────────────────────────────── edits

def test_edit_overrides_only_the_changed_field(store):
    code = a_code()
    before = coverage.registry()[code]["uz"]
    review.record(code, "draft", uz={"qoida": "TAHRIRLANGAN"})

    after = coverage.registry()[code]["uz"]
    assert after["qoida"] == "TAHRIRLANGAN"
    # Everything else still tracks the generated registry rather than being
    # frozen into a copy at edit time.
    for key, value in before.items():
        if key != "qoida":
            assert after[key] == value
    assert coverage.registry()[code]["uz_edited_fields"] == ["qoida"]


def test_edit_cannot_rewrite_non_content_fields(store):
    """The content editor must not be a way to change detection_confidence or
    group — those are engineering decisions, not review decisions."""
    code = a_code()
    review.record(code, "draft",
                  uz={"group": "hacked", "detection_confidence": "high",
                      "qoida": "ok"})
    entry = coverage.registry()[code]
    assert entry["group"] != "hacked"
    assert "group" not in entry["uz"]


def test_edit_does_not_approve(store):
    """Fixing a typo must never vouch for the ruling as a side effect."""
    code = a_code()
    review.record(code, "draft", uz={"qoida": "x"})
    assert coverage.registry()[code]["status"] == "draft"


def test_approving_after_an_edit_keeps_the_edit(store):
    code = a_code()
    review.record(code, "draft", uz={"qoida": "TAHRIRLANGAN"})
    review.record(code, "reviewed", reviewed_by="Q")
    entry = coverage.registry()[code]
    assert entry["status"] == "reviewed"
    assert entry["uz"]["qoida"] == "TAHRIRLANGAN"


# ──────────────────────────────────── the reason the overlay exists

def test_decisions_survive_a_registry_regeneration(store):
    """THE point of the overlay. Approvals live outside the generated file, so
    rebuilding v3 from its inputs cannot discard them."""
    code = a_code()
    review.record(code, "reviewed", reviewed_by="Q", uz={"qoida": "KEEP ME"})

    # Simulate the generator rewriting the registry underneath: drop every
    # cache and re-read from disk, exactly as a fresh process would.
    coverage.registry.cache_clear()
    coverage.in_scope.cache_clear()

    entry = coverage.registry()[code]
    assert entry["status"] == "reviewed"
    assert entry["uz"]["qoida"] == "KEEP ME"


def test_the_generated_registry_is_never_written_to(store):
    """Belt and braces: recording a decision must not touch v3 itself."""
    v3 = coverage._REGISTRY_PATH
    before = v3.read_bytes()
    review.record(a_code(), "reviewed", reviewed_by="Q")
    assert v3.read_bytes() == before


def test_corrupt_decisions_file_is_loud(store):
    store.write_text("{ not json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unreadable"):
        review.load()


# ──────────────────────────────────────────────────────────── the queue

def test_queue_is_ordered_by_reach(store):
    q = routes.review_queue()
    orders = [e.review_order for e in q.entries]
    assert orders == sorted(orders), "highest reach must come first"
    assert q.total == len(q.entries)
    assert q.reviewed + q.rejected + q.remaining == q.total


def test_queue_counts_track_decisions(store):
    q0 = routes.review_queue()
    review.record(q0.entries[0].code, "reviewed", reviewed_by="Q")
    q1 = routes.review_queue()
    assert q1.reviewed == q0.reviewed + 1
    assert q1.remaining == q0.remaining - 1


def test_queue_matches_the_ranking_size(store):
    """'12 of 32' has to mean something - the queue is exactly the in-scope,
    rankable set the frequency ranking covers."""
    q = routes.review_queue()
    assert q.total == len(coverage.in_scope())
    assert not q.ranking_stale, (
        "ranking artifact is out of step with the registry - re-run "
        "tools/rank_error_frequency.py")


def test_unknown_code_is_rejected(store):
    from fastapi import HTTPException
    from tilawah.api.schemas import ReviewDecisionIn

    with pytest.raises(HTTPException) as exc:
        routes.review_decide("NOT_A_CODE",
                             ReviewDecisionIn(action="approve",
                                              reviewed_by="Q"))
    assert exc.value.status_code == 404


def test_bad_action_is_rejected(store):
    from fastapi import HTTPException
    from tilawah.api.schemas import ReviewDecisionIn

    with pytest.raises(HTTPException) as exc:
        routes.review_decide(a_code(),
                             ReviewDecisionIn(action="delete", reviewed_by="Q"))
    assert exc.value.status_code == 422


# ────────────────────────────────────────────────── not in production

def test_review_tool_is_refused_in_production(monkeypatch):
    """It edits tajweed content and marks it approved, with no authentication.
    That is fine on a laptop and indefensible on a box a stranger can reach."""
    from fastapi import HTTPException

    monkeypatch.setattr(routes, "settings",
                        dataclasses.replace(settings, env="production"))
    for call in (routes.review_queue,
                 lambda: routes._guard_review()):
        with pytest.raises(HTTPException) as exc:
            call()
        assert exc.value.status_code == 403


def test_review_tool_works_in_dev(monkeypatch):
    monkeypatch.setattr(routes, "settings",
                        dataclasses.replace(settings, env="dev"))
    assert routes.review_queue().total > 0


def test_decisions_file_is_valid_json_after_a_write(store):
    review.record(a_code(), "reviewed", reviewed_by="Q", note="ok")
    data = json.loads(store.read_text(encoding="utf-8"))
    assert "decisions" in data and "_meta" in data
