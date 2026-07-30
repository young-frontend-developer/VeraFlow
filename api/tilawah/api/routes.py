# -*- coding: utf-8 -*-
"""HTTP surface. Four endpoints is the whole MVP."""
import anyio
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from .. import content
from ..config import settings
from ..db import get_session
from ..db.models import Attempt, User
from ..engine.pipeline import analyze
from ..engine.segments import segments_for
from ..engine.target import target_for
from .schemas import AttemptOut, AyahOut, SegmentOut, WrongFlagIn

router = APIRouter(prefix="/api")


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
    session: Session = Depends(get_session),
) -> AttemptOut:
    data = await audio.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "recording too large")
    if lang not in content.LANGS:
        lang = "uz"

    user = _user(session, device_id, lang)

    # Inference is CPU-bound and holds a semaphore; keep the event loop free.
    fb = await anyio.to_thread.run_sync(analyze, data, sura, aya, lang)

    row = Attempt(
        user_id=user.id, sura=sura, aya=aya, status=fb.status, clean=fb.clean,
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


@router.post("/consent")
def set_consent(device_id: str = Form(...), consented: bool = Form(...),
                session: Session = Depends(get_session)) -> dict:
    user = _user(session, device_id, "uz")
    user.consented = consented
    session.add(user)
    session.commit()
    if not consented:
        from ..db import delete_user
        delete_user(session, device_id)
    return {"ok": True, "consented": consented}


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
