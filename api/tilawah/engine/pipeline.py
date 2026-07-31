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
import logging
from dataclasses import dataclass, field

from .. import content
from .audio import DecodeInfo, check_quality, decode
from .collapse import looks_collapsed
from .debug_capture import capture
from .model import transcribe
from .ranges import Range, is_legal_range, n_words, reference
from .target import Target
from .typed_errors import TypedError, typed_diff

log = logging.getLogger(__name__)

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


def analyze(audio: bytes, sura: int, aya: int, lang: str = "uz", *,
            start_word: int = 0, num_words: int = 0,
            include_bismillah: bool = False,
            device_id: str = "", audio_consented: bool = False) -> Feedback:
    """`num_words=0` means the whole ayah. Indices are relative to the ayah."""
    try:
        total_words = n_words(sura, aya)
    except Exception:
        return Feedback(status="error", sura=sura, aya=aya,
                        reason="ayah_not_in_catalogue")

    if num_words <= 0:
        start_word, num_words = 0, total_words
    if not is_legal_range(sura, aya, start_word, num_words):
        # The UI is expected to offer only legal cuts, so reaching here means a
        # hand-built request or a stale client - name it rather than let
        # PartOfUthmaniWord surface as a 500.
        return Feedback(status="error", sura=sura, aya=aya,
                        reason="illegal_word_range")
    rng = Range(sura, aya, start_word, num_words, include_bismillah)

    info = DecodeInfo()
    try:
        wave = decode(audio, info)
    except Exception as exc:
        # Log the bytes even when decoding fails - that is precisely the case
        # you cannot diagnose without them.
        capture(audio, None, sura, aya, info.as_dict(), {},
                {"outcome": "decode_failed", "error": str(exc)},
                device_id=device_id, audio_consented=audio_consented)
        log.error("[%03d:%03d] decode failed (%s): %s",
                  sura, aya, info.sniff, exc)
        return Feedback(status="error", sura=sura, aya=aya,
                        reason=f"decode_failed: {exc}")

    q = check_quality(wave)
    meas = {"duration_s": q.duration_s, "peak": q.peak, "rms": q.rms,
            "clipped_pct": q.clipped_pct, "speech_db": q.speech_db,
            "noise_db": q.noise_db, "snr_db": q.snr_db,
            "snr_measurable": q.snr_measurable}

    if not q.ok:
        capture(audio, wave, sura, aya, info.as_dict(), meas,
                {"outcome": "retry_recording", "reason": q.reason},
                device_id=device_id, audio_consented=audio_consented)
        return Feedback(status="retry_recording", sura=sura, aya=aya,
                        reason=q.reason, snr_db=q.snr_db, duration_s=q.duration_s)

    # The target covers the SELECTED RANGE only, not the whole ayah - otherwise
    # every segment would read as a huge deletion error.
    uthmani, phonetized = reference(rng)
    target = Target(sura=sura, aya=aya, uthmani=uthmani,
                    phonemes=phonetized.phonemes, n_sifat=len(phonetized.sifat))
    pred = transcribe(wave, phonetized)

    # The model answers confidently even when the audio was unusable, returning
    # huruf muqatta'at rather than low probabilities. Catch that from the output
    # itself - it is the failure the audio gate was aiming at and never hit.
    collapsed, detail = looks_collapsed(pred.phonemes, sura, aya, target.phonemes)
    if collapsed:
        capture(audio, wave, sura, aya, info.as_dict(), meas,
                {"outcome": "collapsed", "detail": detail,
                 "expected": target.phonemes, "heard": pred.phonemes,
                 "mean_prob": pred.mean_prob},
                device_id=device_id, audio_consented=audio_consented)
        log.warning("[%03d:%03d] muqatta'at collapse: %s | heard=%s expected=%s",
                    sura, aya, detail, pred.phonemes, target.phonemes)
        return Feedback(status="retry_recording", sura=sura, aya=aya,
                        reason="unclear_recitation", snr_db=q.snr_db,
                        duration_s=q.duration_s, mean_prob=pred.mean_prob,
                        expected_phonemes=target.phonemes,
                        heard_phonemes=pred.phonemes)

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

    capture(audio, wave, sura, aya, info.as_dict(), meas,
            {"outcome": "ok", "expected": target.phonemes,
             "heard": pred.phonemes, "mean_prob": pred.mean_prob,
             "errors_detected": [e.code for e in raw],
             "errors_shown": [e["code"] for e in shown],
             "errors_suppressed": [e["code"] for e in silent]},
            device_id=device_id, audio_consented=audio_consented)

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
