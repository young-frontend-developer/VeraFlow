# -*- coding: utf-8 -*-
"""HTTP surface. A handful of endpoints is the whole MVP."""
import functools
import threading

import anyio
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from .. import content
from ..config import settings
from ..db import delete_stored_audio, get_session
from ..db.models import Attempt, User
from ..engine.pipeline import analyze
from ..engine.ranges import (Range, estimate_seconds, legal_cuts, n_words,
                             uthmani_of)
from ..engine.segments import segments_for
from ..engine.target import target_for
from .schemas import (AttemptOut, AyahOut, AyahSegmentsOut, MetaOut,
                      PracticeSegmentOut, SegmentOut, WrongFlagIn)

router = APIRouter(prefix="/api")

# Consent writes delete rows and files. Two of them landing at once - a
# double-tap, or a client that fires from two places - collide on SQLite and
# kill the connection mid-response, which reaches the browser as a bare CORS
# error with no clue attached. One worker serves this app, so a lock is the
# whole fix.
_consent_lock = threading.Lock()


def _user(session: Session, device_id: str, lang: str) -> User:
    user = session.get(User, device_id)
    if user is None:
        user = User(id=device_id, lang=lang)
        session.add(user)
        session.commit()
    return user


@router.get("/ayat", response_model=list[AyahOut])
def list_ayat() -> list[AyahOut]:
    out = []
    for a in content.ayat():
        t = target_for(a["sura"], a["aya"])
        out.append(AyahOut(sura=a["sura"], aya=a["aya"], slug=a["slug"],
                           level=a["level"], uthmani=t.uthmani,
                           name_uz=a["uz"], name_ru=a["ru"],
                           segments=[SegmentOut(**s) for s in segments_for(a["sura"], a["aya"])]))
    return out


@router.post("/attempts", response_model=AttemptOut)
async def create_attempt(
    audio: UploadFile = File(...),
    sura: int = Form(...),
    aya: int = Form(...),
    lang: str = Form("uz"),
    device_id: str = Form(...),
    # The practice range, relative to the ayah. num_words=0 means whole ayah,
    # which keeps every existing client working unchanged.
    start_word: int = Form(0),
    num_words: int = Form(0),
    include_bismillah: bool = Form(False),
    session: Session = Depends(get_session),
) -> AttemptOut:
    data = await audio.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "recording too large")
    if lang not in content.LANGS:
        lang = "uz"

    user = _user(session, device_id, lang)

    # Inference is CPU-bound and holds a semaphore; keep the event loop free.
    # The learner's audio consent travels with the call - the engine decides
    # nothing about retention on its own.
    fb = await anyio.to_thread.run_sync(
        functools.partial(analyze, data, sura, aya, lang,
                          start_word=start_word, num_words=num_words,
                          include_bismillah=include_bismillah,
                          device_id=user.id,
                          audio_consented=user.audio_consented))

    row = Attempt(
        user_id=user.id, sura=sura, aya=aya,
        start_word=start_word, num_words=num_words,
        include_bismillah=include_bismillah,
        status=fb.status, clean=fb.clean,
        suppressed=fb.suppressed,
        snr_db=round(fb.snr_db, 1), duration_s=round(fb.duration_s, 2),
        mean_prob=round(fb.mean_prob, 4),
        expected_phonemes=fb.expected_phonemes, heard_phonemes=fb.heard_phonemes,
        errors=fb.errors, silent_errors=fb.silent_errors,
    )
    if user.consented:
        session.add(row)
        session.commit()
        session.refresh(row)

    return AttemptOut(
        id=row.id, sura=sura, aya=aya,
        status=fb.status, reason=fb.reason, clean=fb.clean,
        suppressed=fb.suppressed,
        errors=fb.errors, snr_db=row.snr_db, duration_s=row.duration_s,
    )


@router.post("/attempts/{attempt_id}/wrong")
def flag_wrong(attempt_id: int, body: WrongFlagIn,
               session: Session = Depends(get_session)) -> dict:
    """The learner says the feedback was wrong. Decision 7: this is the label
    you cannot buy - it feeds the uncertainty-prioritised expert review queue."""
    row = session.get(Attempt, attempt_id)
    if row is None:
        raise HTTPException(404, "attempt not found")
    row.wrong_flag = True
    row.wrong_note = body.note
    session.add(row)
    session.commit()
    return {"ok": True}


@router.get("/segments/{sura}/{aya}", response_model=AyahSegmentsOut)
def ayah_segments(sura: int, aya: int) -> AyahSegmentsOut:
    """Precomputed practice ranges, plus the legal cut points so the UI can
    offer custom ranges without ever constructing an illegal one."""
    try:
        total = n_words(sura, aya)
    except Exception:
        raise HTTPException(404, "ayah not found")

    segs = content.segments_of(sura, aya)
    if not segs:
        # Artifact missing or not yet built for this ayah - the whole ayah is
        # always a legal range, so degrade to that rather than 500.
        segs = [{"start_word": 0, "num_words": total, "n_phonemes": 0}]

    out = []
    for i, s in enumerate(segs):
        rng = Range(sura, aya, s["start_word"], s["num_words"])
        out.append(PracticeSegmentOut(
            index=i, start_word=s["start_word"], num_words=s["num_words"],
            n_phonemes=s["n_phonemes"],
            seconds=round(estimate_seconds(s["n_phonemes"]), 1),
            uthmani=uthmani_of(rng),
        ))
    return AyahSegmentsOut(sura=sura, aya=aya, n_words=total,
                           legal_cuts=list(legal_cuts(sura, aya)), segments=out)


@router.get("/meta", response_model=MetaOut)
def meta() -> MetaOut:
    """Cheap, uncached, called on app load. Drives the pilot banner."""
    unverified = content.dev_overrides()
    return MetaOut(
        # Either the operator says this is a pilot, or a correction that reaches
        # learners has not been reviewed by a qori. Both warrant the banner.
        pilot=settings.pilot or bool(unverified),
        unverified_codes=unverified,
        collect_audio_offered=settings.collect_audio,
    )


@router.post("/consent")
def set_consent(device_id: str = Form(...), consented: bool = Form(...),
                audio_consented: bool = Form(False),
                session: Session = Depends(get_session)) -> dict:
    """Two separate permissions. Keeping a record of what you recited is not the
    same as keeping a recording of your voice, so granting the first never
    implies the second, and audio can be revoked on its own."""
    with _consent_lock:
        user = _user(session, device_id, "uz")

        # Audio consent cannot outlive attempt consent, and revoking it must
        # delete the recordings made under it - not just stop making new ones.
        audio = bool(audio_consented and consented and settings.collect_audio)
        if user.audio_consented and not audio:
            delete_stored_audio(device_id)

        user.consented = consented
        user.audio_consented = audio
        user.consent_seen = True
        session.add(user)
        session.commit()

        if not consented:
            from ..db import delete_user
            delete_user(session, device_id)
    return {"ok": True, "consented": consented, "audio_consented": audio}


@router.get("/attempts", response_model=list[AttemptOut])
def history(device_id: str, limit: int = 20,
            session: Session = Depends(get_session)) -> list[AttemptOut]:
    rows = session.exec(
        select(Attempt).where(Attempt.user_id == device_id)
        .order_by(Attempt.created_at.desc()).limit(limit)
    ).all()
    return [AttemptOut(id=r.id, sura=r.sura, aya=r.aya,
                       status=r.status, reason="", clean=r.clean,
                       suppressed=r.suppressed,
                       errors=r.errors, snr_db=r.snr_db, duration_s=r.duration_s)
            for r in rows]
