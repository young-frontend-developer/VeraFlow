# -*- coding: utf-8 -*-
"""audio bytes -> learner-facing feedback. The whole engine in one function.

Order matters:
  1. decode
  2. QUALITY GATE - reject before inference, never after (see audio.py)
  3. computed target (decision 1)
  4. transcribe
  5. typed errors (decision 2)
  6. precision gate + cap at 2 (decisions 5 and 2)

Everything the learner sees comes from content/rules.json. This module decides
WHICH errors to mention and in what order; it never writes a sentence.
"""
from dataclasses import dataclass, field

from .. import content
from .audio import check_quality, decode
from .model import transcribe
from .target import _phonetized, target_for
from .typed_errors import TypedError, typed_diff

MAX_SHOWN = 2          # decision 2: two actionable errors beat ten true ones

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Feedback:
    status: str                      # ok | retry_recording | error
    sura: int = 0
    aya: int = 0
    reason: str = ""                 # why status != ok
    expected_phonemes: str = ""
    heard_phonemes: str = ""
    clean: bool = False              # nothing detected at all - safe to praise
    suppressed: bool = False         # detected something, showed nothing
    errors: list[dict] = field(default_factory=list)      # shown to the learner
    silent_errors: list[dict] = field(default_factory=list)  # logged only
    snr_db: float = 0.0
    duration_s: float = 0.0
    mean_prob: float = 0.0


def _rank(e: TypedError) -> tuple:
    rule = content.rules().get(e.code, {})
    return (SEVERITY_RANK.get(rule.get("severity", "medium"), 1), e.at)


def analyze(audio: bytes, sura: int, aya: int, lang: str = "uz") -> Feedback:
    if (sura, aya) not in content.ayat_index():
        return Feedback(status="error", sura=sura, aya=aya, reason="ayah_not_in_catalogue")

    try:
        wave = decode(audio)
    except Exception as exc:
        return Feedback(status="error", sura=sura, aya=aya,
                        reason=f"decode_failed: {exc}")

    q = check_quality(wave)
    if not q.ok:
        # Deliberately BEFORE inference. Noisy audio makes the model produce
        # confident nonsense, and tajweed corrections built on it are worse
        # than no feedback at all.
        return Feedback(status="retry_recording", sura=sura, aya=aya,
                        reason=q.reason, snr_db=q.snr_db, duration_s=q.duration_s)

    target = target_for(sura, aya)
    pred = transcribe(wave, _phonetized(sura, aya))
    raw = typed_diff(target.phonemes, pred.phonemes)

    shown, silent = [], []
    for e in sorted(raw, key=_rank):
        status = content.status_of(e.code)
        body = content.render(e.code, lang, e.dict())
        record = {**e.dict(), "status": status, "content": body}

        if status == "collect" or body is None or not body.get("reviewed", False):
            # Unreviewed content never reaches a learner. Flip `reviewed` in
            # rules.json once a qualified qori has signed the string off.
            silent.append(record)
        elif len(shown) < MAX_SHOWN:
            record["needs_teacher"] = (status == "teacher")
            shown.append(record)
        else:
            silent.append(record)

    # `clean` must mean "nothing was detected", not "nothing was displayed".
    # Praising a recitation the engine flagged - but suppressed for lack of
    # reviewed content - is a false reassurance, and decision 5 cuts both ways:
    # do not claim an error you are unsure of, and do not claim perfection you
    # are equally unsure of. The UI shows a neutral "not fully assessed" instead.
    return Feedback(
        status="ok", sura=sura, aya=aya,
        expected_phonemes=target.phonemes, heard_phonemes=pred.phonemes,
        clean=not raw, suppressed=bool(raw) and not shown,
        errors=shown, silent_errors=silent,
        snr_db=q.snr_db, duration_s=q.duration_s, mean_prob=pred.mean_prob,
    )
