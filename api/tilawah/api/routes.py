# -*- coding: utf-8 -*-
"""HTTP surface. A handful of endpoints is the whole MVP."""
import functools
import json
import threading

import anyio
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from quran_transcript import Aya
from sqlmodel import Session, select

from .. import content
from ..config import settings
from ..content import coaching, hadith, letters
from ..db import delete_stored_audio, get_session
from ..db.models import Attempt, User
from ..engine import cards
from ..engine.pipeline import analyze
from ..engine.ranges import (Range, estimate_seconds, legal_cuts, n_words,
                             uthmani_of)
from ..engine.segments import segments_for, segments_for_range
from ..engine.target import target_for
from .deps import current_user, require_own_device
from .schemas import (AttemptOut, AyahBriefOut, AyahOut, AyahSegmentsOut,
                      HadithOut, MetaOut, PracticeSegmentOut, ReciterOut,
                      RecitersOut, ReviewDecisionIn, ReviewEntryOut,
                      ReviewQueueOut, RuleBadgeOut, SegmentOut, SuraAyatOut,
                      SuraOut, WrongFlagIn)

router = APIRouter(prefix="/api")

# Consent writes delete rows and files. Two of them landing at once - a
# double-tap, or a client that fires from two places - collide on SQLite and
# kill the connection mid-response, which reaches the browser as a bare CORS
# error with no clue attached. One worker serves this app, so a lock is the
# whole fix.
_consent_lock = threading.Lock()


# _user() USED TO LIVE HERE and it was the whole authorization model: take the
# device_id off the request, look it up, create it if absent, and serve
# whoever asked as that person. It is gone rather than fixed. Any helper that
# turns a caller-supplied string into a User is the vulnerability itself, and
# leaving one in the module invites the next route to call it.
#
# Identity now comes from the session and only from the session - see
# api/deps.py:current_user. A device_id on a request is a claim to be checked
# against that session (deps.require_own_device), never a way to name a user.


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


@router.get("/suras", response_model=list[SuraOut])
def list_suras() -> list[SuraOut]:
    """All 114. Static, tiny, and the entry point to the whole catalogue.

    Separate from /api/ayat on purpose: that one returns the curated worked
    examples with their full text and letter-segments, which is a different
    thing entirely and does not scale to 6236 ayat.
    """
    return [SuraOut(**s) for s in content.suras()]


@functools.lru_cache(maxsize=32)
def _sura_ayat(sura: int, lang: str = "uz") -> SuraAyatOut:
    """Every ayah of one sura, with enough text to recognise it.

    Al-Baqara is 286 ayat, so this is the largest response in the app. It stays
    a single call rather than paging: the picker needs to be searchable and
    scrollable at once, and paging an ayah list is worse than the payload.

    PERFORMANCE - two separate traps, both measured on al-Baqara's 286 ayat:

      43.1 s  uthmani_of(Range(sura, aya, 0, n_words(...)))
               Correct, but it routes a whole-ayah range through the
               imlaey-to-uthmani encoder at ~150 ms a call. A whole ayah needs
               no range encoding at all - read the text off Aya directly.
       6.1 s  Aya(sura, aya).get() per ayah
               The cost is CONSTRUCTION, ~23 ms each, not .get(). Building 286
               Aya objects rebuilds the same lookup structure 286 times.
       0.3 s  one Aya, .set(sura, aya) per ayah   <- what this does

    The reuse is verified equivalent, not assumed: 492 ayat across 5 suras give
    byte-identical uthmani, word counts, sura name and ayah count either way.
    The lru_cache is a second line of defence - the first request has to be fast
    too, and it is the one a learner actually waits on.
    """
    meta = content.sura_index().get(sura)
    if meta is None:
        raise HTTPException(404, "sura not found")

    out = []
    cursor = Aya(sura, 1)
    for aya in range(1, meta["n_ayat"] + 1):
        cursor.set(sura, aya)
        got = cursor.get()
        segs = content.segments_of(sura, aya)
        n_phon = sum(s["n_phonemes"] for s in segs)
        out.append(AyahBriefOut(
            aya=aya, uthmani=got.uthmani, n_words=len(got.imlaey_words),
            n_segments=len(segs) or 1,
            seconds=round(estimate_seconds(n_phon), 1) if n_phon else 0.0,
            translation=content.translation_of(sura, aya, lang)))

    # The mushaf prints the basmala as an opening line above every sura except
    # two, and the exceptions run in opposite directions: in al-Fatiha it IS
    # ayah 1, so printing it again would duplicate it, and at-Tawba has none at
    # all. Both are properties of the text, not preferences, so they are stated
    # here rather than left to the client to remember.
    has_basmala = sura not in (1, 9)
    cursor.set(sura, 1)
    bismillah = cursor.get().bismillah_uthmani if has_basmala else ""
    return SuraAyatOut(sura=sura, name_ar=meta["name_ar"],
                       translit=meta["translit"], n_ayat=meta["n_ayat"],
                       ayat=out, has_basmala=has_basmala,
                       bismillah=bismillah or "")


@router.get("/suras/{sura}/ayat", response_model=SuraAyatOut)
def sura_ayat(sura: int, lang: str = "uz") -> SuraAyatOut:
    if lang not in content.LANGS:
        lang = "uz"
    return _sura_ayat(sura, lang)


@router.get("/reciters", response_model=RecitersOut)
def list_reciters() -> RecitersOut:
    """Reciters everyayah actually serves, probed at build time.

    The client persists a choice from this list. It is served rather than
    hardcoded in the frontend so that adding a reciter is a re-run of
    tools/build_reciters.py, and so the probe result is what ships.
    """
    return RecitersOut(
        default=content.default_reciter(),
        base_url=content.reciter_base_url(),
        reciters=[ReciterOut(**r) for r in content.reciters()],
    )


@router.post("/attempts", response_model=AttemptOut)
async def create_attempt(
    audio: UploadFile = File(...),
    sura: int = Form(...),
    aya: int = Form(...),
    lang: str = Form("uz"),
    # ACCEPTED, VALIDATED, AND OTHERWISE IGNORED. It used to name the account
    # this recording was filed under, which meant anyone could file a
    # recitation against anyone. The attempt is now written for the session's
    # user; sending someone else's device id is a 403, not a redirect.
    # Optional so a session-only client need not send it at all.
    device_id: str | None = Form(None),
    # The practice range, relative to the ayah. num_words=0 means whole ayah,
    # which keeps every existing client working unchanged.
    start_word: int = Form(0),
    num_words: int = Form(0),
    include_bismillah: bool = Form(False),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> AttemptOut:
    data = await audio.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "recording too large")
    if lang not in content.LANGS:
        lang = "uz"

    require_own_device(session, user, device_id)

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
        suppressed=fb.suppressed, analysable=fb.analysable,
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
        suppressed=fb.suppressed, analysable=fb.analysable,
        errors=fb.errors, snr_db=row.snr_db, duration_s=row.duration_s,
        score=fb.score, pass_score=fb.pass_score,
    )


@router.post("/attempts/{attempt_id}/wrong")
def flag_wrong(attempt_id: int, body: WrongFlagIn,
               user: User = Depends(current_user),
               session: Session = Depends(get_session)) -> dict:
    """The learner says the feedback was wrong. Decision 7: this is the label
    you cannot buy - it feeds the uncertainty-prioritised expert review queue.

    THIS ROUTE HAD NO OWNERSHIP CHECK AT ALL. `attempt_id` is a sequential
    integer, so anyone could walk 1..n and write wrong_note - free text - onto
    every learner's attempts. That is both a privacy leak and a corruption of
    the one label this project cannot buy: the expert review queue is
    prioritised by these flags, so poisoning them steers what the qori sees.

    404 AND NOT 403 for an attempt owned by someone else. 403 would confirm the
    row exists, which is exactly the enumeration this closes. To this caller,
    an attempt that is not theirs and an attempt that does not exist are the
    same thing, and the API says so.
    """
    row = session.get(Attempt, attempt_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "attempt not found")
    row.wrong_flag = True
    row.wrong_note = body.note
    session.add(row)
    session.commit()
    return {"ok": True}


def _rule_badges(rng: Range, uthmani: str) -> list[RuleBadgeOut]:
    """The tajweed rules present in this range, as learner-facing badges.

    Two phonetizer runs, and both are needed. The flat one is what every other
    precondition in the engine reads; the SPACED one is the only thing that
    separates madd muttasil from madd munfasil, which differ by a word boundary
    and by nothing else. `remove_spaces=True` destroys exactly that.

    A failure here costs badges, not the segment. This endpoint is what the
    reader calls to open an ayah, and an ayah that will not open because a
    decorative pill could not be computed would be a bad trade.
    """
    try:
        from quran_transcript import quran_phonetizer

        from ..engine.moshaf import MOSHAF
        from ..engine.rule_presence import badges, is_reviewed, rules_present

        flat = quran_phonetizer(uthmani, MOSHAF, remove_spaces=True)
        spaced = quran_phonetizer(uthmani, MOSHAF, remove_spaces=False)
        codes = rules_present(flat.phonemes, flat.sifat, spaced.phonemes,
                              n_words=len(uthmani.split()))
    except Exception:
        return []

    out: list[RuleBadgeOut] = []
    catalogue = badges()
    for code in codes:
        entry = catalogue.get(code, {})
        # NO RUSSIAN WAS AUTHORED for these entries and none is invented here -
        # see rule_badges.json _meta. The Uzbek is served for both languages
        # and the client says so; the alternative is a model writing tajweed
        # instruction, which is the one thing this content may not be.
        uz = entry.get("uz", {})
        target = entry.get("target_harakat", "")
        out.append(RuleBadgeOut(
            code=code,
            color=entry.get("color", "gray"),
            name=uz.get("name", code),
            rule=uz.get("rule", ""),
            example=uz.get("example", ""),
            target=str(target) if target != "" else "",
            source=entry.get("source", ""),
            reviewed=is_reviewed(code),
        ))
    return out


def _practice_segment(sura: int, aya: int, index: int, start_word: int,
                      num_words: int, n_phonemes: int) -> PracticeSegmentOut:
    rng = Range(sura, aya, start_word, num_words)
    text_segments = segments_for_range(sura, aya, start_word, num_words)
    # n_phonemes is 0 only when the prebuilt artifact is missing for this ayah;
    # compute it rather than showing the learner "0 s".
    n_phon = n_phonemes or sum(len(t["text"]) for t in text_segments)
    uthmani = uthmani_of(rng)
    return PracticeSegmentOut(
        index=index, start_word=start_word, num_words=num_words,
        n_phonemes=n_phonemes,
        seconds=round(estimate_seconds(n_phon), 1),
        uthmani=uthmani,
        text_segments=[SegmentOut(**t) for t in text_segments],
        rules=_rule_badges(rng, uthmani),
    )


@router.get("/segments/{sura}/{aya}", response_model=AyahSegmentsOut)
def ayah_segments(sura: int, aya: int) -> AyahSegmentsOut:
    """The whole ayah, the optional parts, and the legal cut points.

    `whole` is computed for every ayah regardless of length. The parts list is
    only what segmentation would have forced, kept as a choice.
    """
    try:
        total = n_words(sura, aya)
    except Exception:
        raise HTTPException(404, "ayah not found")

    segs = content.segments_of(sura, aya)
    whole_phonemes = sum(s["n_phonemes"] for s in segs)
    whole = _practice_segment(sura, aya, 0, 0, total, whole_phonemes)

    # A single segment IS the whole ayah, so it is not an alternative to it -
    # offering a one-item "choose a part" list would be a control that does
    # nothing. Parts are offered only where there is a real choice.
    parts = ([_practice_segment(sura, aya, i, s["start_word"], s["num_words"],
                                s["n_phonemes"])
              for i, s in enumerate(segs)]
             if len(segs) > 1 else [])

    return AyahSegmentsOut(sura=sura, aya=aya, n_words=total,
                           legal_cuts=list(legal_cuts(sura, aya)),
                           whole=whole, parts=parts)


# ─────────────────────────────────────────────────────────────── review

@functools.lru_cache(maxsize=1)
def _ranking() -> dict[str, dict]:
    """review_order and reach per code, from the frequency ranking artifact.

    Regenerated by tools/rank_error_frequency.py. If it is missing the queue
    still works - it just falls back to alphabetical, and says so.
    """
    from pathlib import Path

    path = (Path(__file__).resolve().parents[3] / "spike" / "step0-results"
            / "error_frequency_ranking.json")
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))["ranking"]
    return {r["code"]: r for r in rows}


def _guard_review() -> None:
    """The review tool edits tajweed rulings and marks them approved.

    It is unauthenticated, because it is a tool for one person on a laptop. That
    is fine there and indefensible anywhere a stranger can reach it, so it is
    refused outright in production rather than left to a firewall.
    """
    if settings.is_production:
        raise HTTPException(
            403,
            "The review tool is unavailable in production. It edits tajweed "
            "content and flips it to reviewed, with no authentication. Run it "
            "locally against the repo and commit the result.")


UNRANKED = 9999          # sorts last; never promotes an unknown code to the top


def _review_entry(code: str, entry: dict) -> ReviewEntryOut:
    r = _ranking().get(code, {})
    return ReviewEntryOut(
        code=code,
        group=entry.get("group", ""),
        severity=entry.get("severity", ""),
        detection_confidence=entry.get("detection_confidence", ""),
        source_ref=entry.get("source_ref", ""),
        status=entry.get("status", "draft"),
        reviewed_by=entry.get("reviewed_by", ""),
        reviewed_at=entry.get("reviewed_at", ""),
        review_note=entry.get("review_note", ""),
        uz_edited_fields=entry.get("uz_edited_fields", []),
        uz=entry.get("uz", {}) or {},
        review_order=r.get("review_order", UNRANKED),
        beginner_pct=r.get("beginner_pct", 0.0),
        all_pct=r.get("all_pct", 0.0),
    )


@router.get("/review/queue", response_model=ReviewQueueOut)
def review_queue() -> ReviewQueueOut:
    """Everything in scope, highest reach first."""
    _guard_review()
    from ..engine.coverage import in_scope

    entries = [_review_entry(c, e) for c, e in in_scope().items()]
    # Highest reach first. Codes the ranking does not know about sort last
    # rather than first, so a stale artifact cannot promote an unranked entry
    # to the top of a qori's queue.
    entries.sort(key=lambda e: (e.review_order, e.code))

    reviewed = sum(1 for e in entries if e.status == "reviewed")
    rejected = sum(1 for e in entries if e.status == "rejected")
    return ReviewQueueOut(
        total=len(entries), reviewed=reviewed, rejected=rejected,
        remaining=len(entries) - reviewed - rejected,
        entries=entries,
        ranking_stale=any(e.review_order == UNRANKED for e in entries),
    )


@router.post("/review/{code}", response_model=ReviewEntryOut)
def review_decide(code: str, body: ReviewDecisionIn) -> ReviewEntryOut:
    """approve | reject | edit | reset. Persisted to tajweed_registry_review.json.

    `edit` saves the Uzbek without deciding anything - a reviewer fixes the
    wording first and approves second, and conflating the two would make it
    impossible to correct a typo without also vouching for the ruling.
    """
    _guard_review()
    from ..engine import review
    from ..engine.coverage import in_scope

    if code not in in_scope():
        raise HTTPException(404, f"{code} is not a reviewable entry")

    action = (body.action or "").lower()
    status = {"approve": "reviewed", "reject": "rejected",
              "reset": "draft", "edit": None}.get(action, ...)
    if status is ...:
        raise HTTPException(422, "action must be approve, reject, edit or reset")

    if status is None:
        # An edit keeps whatever decision already stood, which for an unreviewed
        # entry is 'draft' - editing must never approve by side effect.
        status = review.decisions().get(code, {}).get("status", "draft")

    try:
        review.record(code, status, reviewed_by=body.reviewed_by,
                      uz=body.uz, note=body.note)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    return _review_entry(code, in_scope()[code])


@router.get("/meta", response_model=MetaOut)
def meta() -> MetaOut:
    """Cheap, uncached, called on app load. Drives the pilot banner."""
    unverified = content.dev_overrides()
    return MetaOut(
        # Either the operator says this is a pilot, or a correction that reaches
        # learners has not been reviewed by a qori, or the review gate is off
        # entirely. All three warrant the banner, and the last one most of all.
        pilot=settings.pilot or bool(unverified) or settings.show_unreviewed,
        unverified_codes=unverified,
        collect_audio_offered=settings.collect_audio,
        show_unreviewed=settings.show_unreviewed,
        max_audio_seconds=settings.max_audio_seconds,
        missing_registries=coaching.missing_sources(),
        missing_audio=coaching.missing_audio(),
        error_fields=list(cards.WIRE_KEYS),
    )


@router.post("/consent")
def set_consent(consented: bool = Form(...),
                audio_consented: bool = Form(False),
                device_id: str | None = Form(None),
                user: User = Depends(current_user),
                session: Session = Depends(get_session)) -> dict:
    """Two separate permissions. Keeping a record of what you recited is not the
    same as keeping a recording of your voice, so granting the first never
    implies the second, and audio can be revoked on its own.

    THE MOST DANGEROUS ROUTE IN THE APP, and the reason is `consented=false`:
    it calls delete_user(), which hard-deletes every attempt and every stored
    recording. Until now the account it deleted was named by a form field, so
    any caller who knew - or guessed - a device id could destroy that learner's
    entire practice history, and the server would answer 200. There is no undo
    and no backup a learner can reach.

    It now deletes the session's own account and nothing else. `device_id` is
    accepted only so existing clients keep working, is validated against the
    session, and is never used to choose whose data is destroyed.
    """
    with _consent_lock:
        require_own_device(session, user, device_id)

        # Audio consent cannot outlive attempt consent, and revoking it must
        # delete the recordings made under it - not just stop making new ones.
        audio = bool(audio_consented and consented and settings.collect_audio)
        if user.audio_consented and not audio:
            # user.id, not the form field. Audio is named with the id that
            # recorded it, which for every legacy account IS the device id -
            # so this is the same file set, chosen by the session instead of
            # by the caller.
            delete_stored_audio(user.id)

        user.consented = consented
        user.audio_consented = audio
        user.consent_seen = True
        session.add(user)
        session.commit()

        if not consented:
            from ..db import delete_user
            # Deletes this user's rows AND cascades to their sessions, so the
            # token that authorised the deletion stops working immediately -
            # which is correct: the account it belonged to no longer exists.
            delete_user(session, user.id)
    return {"ok": True, "consented": consented, "audio_consented": audio}


@router.get("/hadith/today", response_model=HadithOut | None)
def hadith_today(lang: str = "uz") -> HadithOut | None:
    """The day's hadith, or null.

    NULL IS A REAL ANSWER and the client draws nothing for it. In production
    only reviewed entries are eligible, and none have been reviewed yet, so
    this returns null there today - which is correct. An unchecked hadith with
    a citation nobody has verified is worse than no card at all.

    Selection is deterministic by date: same day, same hadith, every device.
    See content/hadith.py.
    """
    got = hadith.today(lang, show_unreviewed=settings.show_unreviewed)
    return HadithOut(**got) if got else None


@router.get("/hadith/{hadith_id}", response_model=HadithOut | None)
def hadith_by_id(hadith_id: str, lang: str = "uz") -> HadithOut | None:
    """One named hadith, or null.

    THIS EXISTS FOR THE HASANAT CARD and for anything like it. That card makes
    a claim about reward per letter, and a claim like that carries its source or
    it does not ship. The source is not a string in a TSX file: it is an entry
    in hadith.json, under the same review gate as everything else, fetched by
    id so that the card and the reviewer are looking at the same words.

    The consequence is deliberate: in production, where nothing is reviewed
    yet, this returns null and the hasanat card draws its citation line as
    absent - which means the client must not draw the reward claim either. A
    reward figure with no citation beside it is precisely the failure the whole
    content-gate exists to prevent.
    """
    got = hadith.by_id(hadith_id, lang,
                       show_unreviewed=settings.show_unreviewed)
    return HadithOut(**got) if got else None


@router.get("/attempts", response_model=list[AttemptOut])
def history(limit: int = 20, device_id: str | None = None,
            user: User = Depends(current_user),
            session: Session = Depends(get_session)) -> list[AttemptOut]:
    """This learner's recent attempts. Always theirs, whatever the query says.

    THE WORST OF THE OLD ROUTES. `device_id` was a REQUIRED QUERY PARAMETER and
    the sole authorization: send someone else's and you got their whole
    practice history. Being in the query string made it worse than the form
    posts - it lands in access logs, browser history, referrer headers and any
    proxy on the path, so the credential was being written down everywhere by
    design.

    The parameter survives only so existing callers do not break, is validated
    against the session, and no longer selects anything. The scope is
    Attempt.user_id == the session's user, full stop. Response shape is
    unchanged.
    """
    require_own_device(session, user, device_id)
    rows = session.exec(
        select(Attempt).where(Attempt.user_id == user.id)
        .order_by(Attempt.created_at.desc()).limit(limit)
    ).all()
    # Rows written before card merging existed have no `words`, `occurrences`,
    # `count` or `kind`. The client indexes those directly, so replaying a
    # legacy row verbatim hands it a shape that throws. ensure_shape rebuilds
    # the missing fields from what the row does carry - see cards.ensure_shape.
    return [AttemptOut(id=r.id, sura=r.sura, aya=r.aya,
                       status=r.status, reason="", clean=r.clean,
                       suppressed=r.suppressed, analysable=r.analysable,
                       errors=[cards.ensure_shape(e) for e in (r.errors or [])],
                       snr_db=r.snr_db, duration_s=r.duration_s,
                       # Read straight off the row. The Today screen's week
                       # strip and its "last practiced" line are drawn from
                       # these and from nothing else - a missing timestamp
                       # leaves a day unmarked rather than guessed.
                       created_at=r.created_at,
                       # num_words == 0 means the whole ayah - see the column
                       # comment on Attempt.num_words. Resolving it to the real
                       # word count here rather than passing 0 through is what
                       # keeps a whole-ayah attempt from counting as no letters
                       # at all.
                       letters=letters.in_range(
                           r.sura, r.aya, r.start_word,
                           r.num_words or n_words(r.sura, r.aya)))
            for r in rows]
