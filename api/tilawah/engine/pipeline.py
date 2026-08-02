# -*- coding: utf-8 -*-
"""audio bytes -> learner-facing feedback. The whole engine in one function.

Order matters:
  1. decode
  2. QUALITY GATE - reject before inference, never after (see audio.py)
  3. computed target (decision 1)
  4. transcribe
  5. typed errors (decision 2)
  6. TOLERANCE GATE - drop deviations too small to be real (config/tolerances.json)
  7. content gate - production only, see present()

Everything the learner sees comes from content/rules.json. This module decides
WHICH errors to mention and in what order; it never writes a sentence.
"""
import logging
from dataclasses import dataclass, field

from .. import content
from ..config import settings
from ..content import coaching
from .audio import DecodeInfo, check_quality, decode
from .collapse import looks_collapsed
from .debug_capture import capture
from .model import transcribe
from .ranges import Range, is_legal_range, n_words, reference
from .segments import segments_for_range, unit_words
from .target import Target
from .tolerances import apply as apply_tolerances
from .typed_errors import TypedError, typed_diff

log = logging.getLogger(__name__)

# THE DISPLAY CAP IS GONE. It was MAX_SHOWN = 2, on the theory that two
# actionable errors beat ten true ones. In practice it meant a learner who made
# five mistakes was told about two of them and never learned the rest existed,
# and combined with the content gate below it was usually a cap on nothing -
# the gate had already emptied the list. If the engine found five, show five;
# ranking by severity already puts the most important one first.

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
    # False when the model returned nothing to compare against, so no judgement
    # of any kind was formed. Distinct from `suppressed`, which means a
    # judgement WAS formed and then withheld. The UI must not print the same
    # sentence for both - see Feedback.tsx.
    analysable: bool = True
    errors: list[dict] = field(default_factory=list)      # shown to the learner
    silent_errors: list[dict] = field(default_factory=list)  # logged only
    # Deviations measured but judged too small to be real - see the tolerance
    # gate below. Logged, never shown, and the input to threshold calibration.
    within_tolerance: list[dict] = field(default_factory=list)
    snr_db: float = 0.0
    duration_s: float = 0.0
    mean_prob: float = 0.0


def _is_allocation_failure(exc: BaseException) -> bool:
    """Torch raises a bare RuntimeError for an allocator failure, so the message
    is the only thing distinguishing it from a genuine bug. Matched narrowly on
    purpose - swallowing every RuntimeError here would hide real breakage as
    "your ayah was too long"."""
    if isinstance(exc, MemoryError):
        return True
    text = str(exc).lower()
    return ("not enough memory" in text
            or "defaultcpuallocator" in text
            or "out of memory" in text
            or "cannot allocate" in text)


def _sifat_errors(phonetized, pred) -> list[TypedError]:
    """Ṣifa disagreements, as GENERIC_SIFAT_MISMATCH.

    ⚠️ THE FALSE-POSITIVE FLOOR FOR THIS IS UNMEASURED. sifa_compare.py was
    written to quantify it - how often the predicted ṣifa disagrees with the
    reference on recitation a qori certifies as CORRECT - and that calibration
    has not been run. Every entry is status='draft' and carries the draft
    marker, and production withholds them, so the exposure is bounded; but this
    is the one detector here resting on an unknown rather than on a measurement.
    Run tools/calibrate.py before this goes anywhere near a real learner.

    `at` is remapped from ṣifa-group index to run-length unit index. The two
    are equal for most ayat and NOT for all - 112:1 has 11 units to 10 groups -
    so using the group index directly would put the highlight, and the word in
    the headline, on the wrong letter exactly where the text is unusual.
    """
    from .sifa_compare import compare, reference_groups

    ref = reference_groups(phonetized.sifat)
    got = pred.sifat or []
    if not ref or not got:
        return []
    to_unit = _group_to_unit(phonetized.phonemes, ref)
    out = []
    for d in compare(ref, got):
        out.append(TypedError(code="GENERIC_SIFAT_MISMATCH",
                              at=to_unit.get(d.at, d.at), letter=d.letter,
                              expected=d.expected, heard=d.heard))
    return out


def _group_to_unit(phonemes: str, ref_groups: list[dict]) -> dict[int, int]:
    """ṣifa-group index -> run-length unit index, via character offsets.

    The groups tile the phoneme string in order, so walking their lengths gives
    each group's span, and unit_char_spans gives the units'. Anything that does
    not line up is dropped rather than guessed.
    """
    from .segments import unit_char_spans

    spans = unit_char_spans(phonemes)
    char_to_unit = {}
    for unit, (a, b) in enumerate(spans):
        for c in range(a, b):
            char_to_unit[c] = unit

    out, pos = {}, 0
    for i, g in enumerate(ref_groups):
        text = g.get("phonemes") or ""
        if pos in char_to_unit:
            out[i] = char_to_unit[pos]
        pos += len(text)
    return out


def _rank(e: TypedError) -> tuple:
    rule = content.rules().get(e.code, {})
    return (SEVERITY_RANK.get(rule.get("severity", "medium"), 1), e.at)


def _unauthored_body(code: str) -> dict:
    """Stand-in for a code nobody has written content for.

    It deliberately does NOT invent a rule, a correction or a reason - decision
    4 forbids exactly that, and showing drafts by default is not an exemption.
    It carries the raw code so it is clear WHICH check fired, and empty strings
    everywhere a sentence about tajweed would otherwise go.

    Reaching this is now rare and getting rarer: GENERIC_LETTER_SUBSTITUTED
    catches every unlisted letter confusion and GENERIC_SIFAT_MISMATCH every
    unlisted sifa one, so what is left is the handful of duration codes with no
    entry in either registry. The learner still sees the word and the letter -
    those travel on the error itself, not in this body - which is the whole
    requirement: located, always, even when we have nothing to say about it.
    """
    return {"headline": "", "fix": "", "rule": "", "drill": "", "label": code,
            "severity": content.rules().get(code, {}).get("severity", "medium"),
            "reviewed": False, "unauthored": True}


def present(raw: list[TypedError], lang: str) -> tuple[list[dict], list[dict]]:
    """Detected errors -> (shown to the learner, logged only).

    Split out of analyze() so the gate is testable without the 2.42 GB model.

    EVERYTHING DETECTED IS SHOWN, in severity order, uncapped - unless this is
    production, where an unreviewed correction is withheld instead. `draft` is
    the contract with the client: any record carrying it must be rendered with
    a visible marker and never as settled guidance.

    The two halves are asymmetric on purpose. Hiding a real error from the
    person building the app buys nothing and costs the whole feedback loop;
    hiding one from a learner, on the strength of words no qori has read, is
    the trust failure this project is arranged to avoid.
    """
    shown, silent = [], []
    for e in sorted(raw, key=_rank):
        status = content.status_of(e.code)
        try:
            body = content.render(e.code, lang, e.dict())
        except coaching.UnfilledTemplate as exc:
            # LOUD, but not fatal to the whole attempt. A template the detector
            # cannot fill is a bug in one entry; raising here would throw away
            # every other correction in the same recitation and hand the
            # learner a 500 after minutes of waiting. So: shout in the log,
            # drop this one card, keep the rest. What must never happen -
            # showing a brace to a learner - still cannot.
            log.error("UNFILLED TEMPLATE %s: %s", e.code, exc)
            silent.append({**e.dict(), "status": "template_error",
                           "content": None, "draft": True})
            continue
        # A coaching entry is authored content in its own right. rules.json
        # knows nothing about the v4/v5 codes, so status_of() returns
        # "collect" for them - treating that as "not shippable" would silence
        # every new entry including the generics, which is exactly the failure
        # they exist to fix. They are still status='draft' and so still
        # unreviewed; production withholds them like anything else.
        if coaching.has(e.code):
            status = "draft"
        reviewed = status != "collect" and bool(body) and body.get("reviewed", False)
        record = {**e.dict(), "status": status, "content": body,
                  "draft": False, "needs_teacher": status == "teacher"}

        if reviewed:
            shown.append(record)
        elif settings.show_unreviewed:
            record["draft"] = True
            if body is None:
                record["content"] = _unauthored_body(e.code)
            shown.append(record)
        else:
            # Production only. Flip `reviewed` in rules.json once a qualified
            # qori has signed the string off.
            silent.append(record)
    return shown, silent


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

    try:
        pred = transcribe(wave, phonetized)
    except (RuntimeError, MemoryError) as exc:
        # Running out of memory mid-forward is a 500 if left alone, and the
        # learner has already waited minutes for it. The cause is quadratic:
        # wav2vec2-BERT's relative-position attention allocates
        # (47*seconds)^2 * 256 bytes, so a long ayah asks for gigabytes.
        # settings.max_audio_seconds is meant to catch this before inference;
        # this is the net for when it is set too high for the box.
        if not _is_allocation_failure(exc):
            raise
        capture(audio, wave, sura, aya, info.as_dict(), meas,
                {"outcome": "out_of_memory", "error": str(exc)[:400],
                 "duration_s": q.duration_s},
                device_id=device_id, audio_consented=audio_consented)
        log.error("[%03d:%03d] OOM on %.0fs of audio: %s",
                  sura, aya, q.duration_s, exc)
        return Feedback(status="retry_recording", sura=sura, aya=aya,
                        reason="too_long_for_engine", snr_db=q.snr_db,
                        duration_s=q.duration_s)

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

    # Nothing came back to diff against. Not a collapse (that is caught above,
    # and returns huruf muqatta'at rather than silence) and not a clean read
    # either - the engine simply has no opinion to offer. It gets its own flag
    # so the UI can say precisely that, instead of borrowing the sentence meant
    # for a suppressed correction.
    if not pred.phonemes.strip():
        capture(audio, wave, sura, aya, info.as_dict(), meas,
                {"outcome": "not_analysable", "expected": target.phonemes,
                 "heard": pred.phonemes, "mean_prob": pred.mean_prob},
                device_id=device_id, audio_consented=audio_consented)
        log.warning("[%03d:%03d] model returned no phonemes", sura, aya)
        return Feedback(status="ok", sura=sura, aya=aya, analysable=False,
                        expected_phonemes=target.phonemes, heard_phonemes="",
                        snr_db=q.snr_db, duration_s=q.duration_s,
                        mean_prob=pred.mean_prob)

    detected = typed_diff(target.phonemes, pred.phonemes)
    detected += _sifat_errors(phonetized, pred)

    # Locate every error in a word before anything renders. The headlines open
    # with it and `content.render` refuses to emit an unfilled {word}, so this
    # has to happen here - the pipeline is the only layer holding both the
    # error's unit index and the Uthmani text it indexes into.
    words = unit_words(uthmani, segments_for_range(
        sura, aya, rng.start_word, rng.num_words))
    for e in detected:
        e.word = words.get(e.at, "")

    # Two correct takes of the same ayah by the same reciter do not produce the
    # same phoneme string - a madd held 4 counts in one reads as 5 in the other -
    # so an untoleranced duration check reports an error on correct recitation.
    # Thresholds come from config/tolerances.json and are calibrated by
    # tools/calibrate.py against recordings certified correct. The shipped
    # defaults are deliberately inert (min_delta = 1, i.e. no change in
    # behaviour) until that calibration has actually been run.
    raw, within_tolerance = apply_tolerances(detected, pred.mean_prob)

    shown, silent = present(raw, lang)

    # Within-tolerance deviations are logged in full, never just counted. They
    # are the raw material tools/calibrate.py turns into thresholds, and once a
    # threshold is raised this list is where you find out what it started hiding.
    tolerated = [{**e.dict(), "margin": v.margin, "threshold": v.threshold,
                  "reason": v.reason} for e, v in within_tolerance]

    capture(audio, wave, sura, aya, info.as_dict(), meas,
            {"outcome": "ok", "expected": target.phonemes,
             "heard": pred.phonemes, "mean_prob": pred.mean_prob,
             "errors_detected": [e.code for e in raw],
             "errors_shown": [e["code"] for e in shown],
             "errors_suppressed": [e["code"] for e in silent],
             "within_tolerance": tolerated},
            device_id=device_id, audio_consented=audio_consented)

    # `clean` must mean "nothing was detected", not "nothing was displayed".
    # Praising a recitation the engine flagged - but suppressed for lack of
    # reviewed content - is a false reassurance, and decision 5 cuts both ways:
    # do not claim an error you are unsure of, and do not claim perfection you
    # are equally unsure of. The UI shows a neutral "not fully assessed" instead.
    #
    # A within-tolerance deviation does NOT block `clean`, and that is the one
    # deliberate difference. Suppressing for lack of reviewed content means "we
    # found something and cannot talk about it"; falling under a tolerance means
    # "we measured it and it is not an error". Only the first is uncertainty.
    # That distinction is only as good as the thresholds, which is why the
    # shipped ones are inert until calibrate.py has been run against real
    # certified-correct takes.
    return Feedback(
        status="ok", sura=sura, aya=aya, analysable=True,
        expected_phonemes=target.phonemes, heard_phonemes=pred.phonemes,
        clean=not raw, suppressed=bool(raw) and not shown,
        errors=shown, silent_errors=silent, within_tolerance=tolerated,
        snr_db=q.snr_db, duration_s=q.duration_s, mean_prob=pred.mean_prob,
    )
