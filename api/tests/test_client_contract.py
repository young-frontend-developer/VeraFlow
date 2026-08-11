# -*- coding: utf-8 -*-
"""The client's expectations, read out of the client, asserted against the API.

test_wire_shape.py pins the payload against cards.WIRE_KEYS — a list a human
maintains. That is one edit away from being wrong in exactly the way that broke
the results screen: a field gets used in Feedback.tsx, nobody adds it to the
tuple, and the tuple keeps passing while the browser throws.

So this file does not trust the tuple. It READS Feedback.tsx, extracts every
`error.<field>` the component dereferences, and asserts the API actually sends
each one. The coupling is the point: add `error.foo` to a card and this fails
until the server sends `foo`.

It also goes through the real HTTP route rather than calling present() directly,
because `response_model` is a place fields disappear silently — a stricter type
on AttemptOut.errors would filter unknown keys and the only symptom would be a
broken card.
"""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tilawah.engine import cards, pipeline
from tilawah.engine.typed_errors import TypedError

WEB = Path(__file__).resolve().parents[2] / "web" / "src"
CARD = WEB / "components" / "Feedback.tsx"

# Optional chaining is a deliberate opt-out: `error.word_index ?? -1` says the
# client has a defined answer when the field is absent. A BARE `error.words.map`
# does not, and those are what must be guaranteed.
_ACCESS = re.compile(r"\berror\.([A-Za-z_][A-Za-z0-9_]*)")


def client_fields() -> set[str]:
    src = CARD.read_text(encoding="utf-8")
    # Strip comments so a field named only in prose does not become a
    # requirement.
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    return set(_ACCESS.findall(src))


def sample() -> list[TypedError]:
    return [
        TypedError(code="LETTER_ADDED", at=0, letter="ل", heard="ل",
                   word="لَمْ", word_index=0),
        TypedError(code="SUB_SAD_SEEN", at=3, letter="ص", expected="ص",
                   heard="س", word="ٱلصَّمَدُ", word_index=1),
        TypedError(code="GHUNNA_LONG", at=7, letter="ن", expected_count=2,
                   heard_count=5, word="مِنْ", word_index=2),
    ]


def test_the_card_component_is_where_we_think_it_is():
    """If this file moves, every assertion below silently passes on nothing."""
    assert CARD.is_file(), f"cannot find the card component at {CARD}"
    assert client_fields(), "no error.<field> accesses found — regex is stale"


def test_every_field_the_card_reads_is_sent_by_the_api():
    """THE test this whole class of bug needed.

    `error.words.map(...)` at Feedback.tsx:255 threw on every card because the
    API sent no `words`. Nothing failed, because nothing compared the two.
    """
    shown, _ = pipeline.present(sample(), "uz")
    assert shown
    sent = set(shown[0].keys())

    missing = sorted(f for f in client_fields() if f not in sent)
    assert not missing, (
        "Feedback.tsx dereferences fields the API does not send:\n  "
        + "\n  ".join(missing)
        + "\n\nEither the server must send them, or the card must stop reading "
          "them. Do NOT paper over it with `?? []` — a card with no location "
          "is the same as no card."
    )


def test_client_fields_are_declared_in_the_wire_contract():
    """Keeps cards.WIRE_KEYS honest against the component as well."""
    undeclared = sorted(f for f in client_fields() if f not in cards.WIRE_KEYS)
    assert not undeclared, (
        f"read by Feedback.tsx but absent from cards.WIRE_KEYS: {undeclared}")


# ── through the real HTTP route ───────────────────────────────────────────

@pytest.fixture
def api(monkeypatch, tmp_path):
    """The real app, with inference replaced and a throwaway database.

    Only the SERIALISATION is under test here; running the 2.42 GB model would
    make this a slow test that people skip, and skipped tests catch nothing.

    TWO THINGS CHANGED IN PHASE 3A and both are load-bearing:

    * A SESSION IS NOW REQUIRED. /api/attempts no longer takes the caller's
      word for who they are, so this fixture signs in like a real client would
      - POST /api/auth/anonymous, then carry the bearer token. Without it every
      request here is a 401 and the wire shape is never reached.

    * ITS OWN DATABASE. This fixture used to run against api/tilawah.db, which
      is why a user called `contract-test` is sitting in the developer's real
      data. A test suite must not write to the live database, least of all one
      holding learner recitations.
    """
    from sqlalchemy import event
    from sqlmodel import Session, SQLModel, create_engine

    from tilawah.api import routes
    from tilawah.api.main import app
    from tilawah.db import get_session
    from tilawah.engine.pipeline import Feedback

    def fake_analyze(*_a, **_k):
        shown, silent = pipeline.present(sample(), "uz")
        return Feedback(status="ok", sura=112, aya=3, analysable=True,
                        clean=False, errors=shown, silent_errors=silent,
                        snr_db=42.0, duration_s=2.4)

    monkeypatch.setattr(routes, "analyze", fake_analyze)

    engine = create_engine(f"sqlite:///{tmp_path / 'contract.db'}",
                           connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    SQLModel.metadata.create_all(engine)

    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    client = TestClient(app)
    # `contract-test` as the device id so it matches what the posts below send:
    # for an account with no sign-in, user.id IS the device id.
    token = client.post("/api/auth/anonymous",
                        json={"device_id": "contract-test"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    yield client

    app.dependency_overrides.clear()
    engine.dispose()


def test_http_response_carries_every_client_field(api):
    r = api.post(
        "/api/attempts",
        data={"sura": "112", "aya": "3", "lang": "uz",
              "device_id": "contract-test", "start_word": "0",
              "num_words": "0", "include_bismillah": "false"},
        files={"audio": ("r.wav", b"RIFF0000WAVEfmt ", "audio/wav")},
    )
    assert r.status_code == 200, r.text
    errors = r.json()["errors"]
    assert errors, "the route returned no errors to check"

    needed = client_fields()
    for err in errors:
        missing = sorted(f for f in needed if f not in err)
        assert not missing, (
            f'{err.get("code")}: response_model dropped {missing}')


def test_http_response_is_json_serialisable_end_to_end(api):
    """Arabic text and nested occurrence dicts both survive the round trip."""
    r = api.post(
        "/api/attempts",
        data={"sura": "112", "aya": "3", "lang": "uz",
              "device_id": "contract-test", "start_word": "0",
              "num_words": "0", "include_bismillah": "false"},
        files={"audio": ("r.wav", b"RIFF0000WAVEfmt ", "audio/wav")},
    )
    body = json.loads(r.text)
    card = body["errors"][0]
    assert isinstance(card["words"], list) and card["words"]
    assert isinstance(card["occurrences"], list) and card["occurrences"]
    assert isinstance(card["kind"], str) and card["kind"]
    # The word has to survive as real Uthmani text, not as escaped mojibake.
    assert any("ل" in w for w in card["words"])  # ل


def test_history_route_also_satisfies_the_contract(api):
    """Legacy rows go out through /api/attempts too. ensure_shape must make
    them satisfy exactly the same contract as a fresh analysis."""
    legacy = {"code": "SUB_SAD_SEEN", "at": 4, "letter": "ص",
              "expected": "ص", "heard": "س", "word": "ٱلصَّمَدُ",
              "status": "collect", "draft": True, "needs_teacher": False,
              "content": {"headline": "x", "fix": "", "rule": "", "drill": "",
                          "severity": "high", "group": "makharij"}}
    fixed = cards.ensure_shape(legacy)
    missing = sorted(f for f in client_fields() if f not in fixed)
    assert not missing, f"ensure_shape leaves {missing} absent"
