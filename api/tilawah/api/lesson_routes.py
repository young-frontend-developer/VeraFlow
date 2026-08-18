# -*- coding: utf-8 -*-
"""Academy endpoints. Additive — no changes to existing routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..db.models import Lesson, LessonProgress, QuizQuestion, User
from .deps import current_user
from .schemas import (
    LessonDetailOut,
    LessonSummaryOut,
    QuizAnswerIn,
    QuizQuestionOut,
    QuizResultOut,
)

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


def _user_status(
    lesson: Lesson,
    progress_map: dict[int, LessonProgress],
    prev_completed: bool,
) -> tuple[str, int | None, bool]:
    prog = progress_map.get(lesson.id)
    if prog and prog.completed_at is not None:
        return "completed", prog.quiz_score, prog.practice_done
    if lesson.order == 1 or prev_completed:
        score = prog.quiz_score if prog else None
        practice = prog.practice_done if prog else False
        return "available", score, practice
    return "locked", None, False


@router.get("", response_model=list[LessonSummaryOut])
def list_lessons(
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> list[LessonSummaryOut]:
    lessons = db.exec(
        select(Lesson)
        .where(Lesson.published == True)  # noqa: E712
        .order_by(Lesson.order)
    ).all()

    progress = db.exec(
        select(LessonProgress).where(LessonProgress.user_id == user.id)
    ).all()
    progress_map = {p.lesson_id: p for p in progress}

    out: list[LessonSummaryOut] = []
    prev_completed = False
    for lesson in lessons:
        status, score, practice = _user_status(lesson, progress_map, prev_completed)
        out.append(LessonSummaryOut(
            id=lesson.id,
            order=lesson.order,
            slug=lesson.slug,
            difficulty=lesson.difficulty,
            title_uz=lesson.title_uz,
            title_ru=lesson.title_ru,
            practice_sura=lesson.practice_sura,
            practice_aya=lesson.practice_aya,
            video_url=lesson.video_url,
            rule_codes=lesson.rule_codes,
            status=status,
            quiz_score=score,
            practice_done=practice,
        ))
        prev_completed = status == "completed"
    return out


@router.get("/{lesson_id}", response_model=LessonDetailOut)
def get_lesson(
    lesson_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> LessonDetailOut:
    lesson = db.get(Lesson, lesson_id)
    if not lesson or not lesson.published:
        raise HTTPException(404)

    questions = db.exec(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.order)
    ).all()

    prog = db.exec(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    ).first()

    status = "available"
    if prog and prog.completed_at is not None:
        status = "completed"

    return LessonDetailOut(
        id=lesson.id,
        order=lesson.order,
        slug=lesson.slug,
        difficulty=lesson.difficulty,
        title_uz=lesson.title_uz,
        title_ru=lesson.title_ru,
        body_uz=lesson.body_uz,
        body_ru=lesson.body_ru,
        practice_sura=lesson.practice_sura,
        practice_aya=lesson.practice_aya,
        video_url=lesson.video_url,
        rule_codes=lesson.rule_codes,
        pass_score=lesson.pass_score,
        quiz=[QuizQuestionOut(
            id=q.id, order=q.order,
            question_uz=q.question_uz, question_ru=q.question_ru,
            options_uz=q.options_uz, options_ru=q.options_ru,
        ) for q in questions],
        status=status,
        quiz_score=prog.quiz_score if prog else None,
        practice_done=prog.practice_done if prog else False,
    )


@router.post("/{lesson_id}/quiz", response_model=QuizResultOut)
def submit_quiz(
    lesson_id: int,
    body: QuizAnswerIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> QuizResultOut:
    lesson = db.get(Lesson, lesson_id)
    if not lesson or not lesson.published:
        raise HTTPException(404)

    questions = db.exec(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson_id)
        .order_by(QuizQuestion.order)
    ).all()

    if len(body.answers) != len(questions):
        raise HTTPException(422, "Answer count must match question count")

    results = []
    correct_count = 0
    for q, ans in zip(questions, body.answers):
        is_correct = ans == q.correct
        if is_correct:
            correct_count += 1
        results.append({
            "question_id": q.id,
            "given": ans,
            "correct": q.correct,
            "is_correct": is_correct,
            "explanation_uz": q.explanation_uz,
            "explanation_ru": q.explanation_ru,
        })

    score = round(correct_count / len(questions) * 100) if questions else 0
    passed = score >= lesson.pass_score

    prog = db.exec(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    ).first()

    if not prog:
        prog = LessonProgress(user_id=user.id, lesson_id=lesson_id)
        db.add(prog)

    prog.attempts += 1
    if prog.quiz_score is None or score > prog.quiz_score:
        prog.quiz_score = score

    if passed and prog.completed_at is None:
        from datetime import datetime, timezone
        prog.completed_at = datetime.now(timezone.utc)

    db.commit()

    return QuizResultOut(
        score=score,
        passed=passed,
        total=len(questions),
        correct_count=correct_count,
        results=results,
    )


@router.post("/{lesson_id}/practice")
def mark_practice(
    lesson_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_session),
) -> dict:
    lesson = db.get(Lesson, lesson_id)
    if not lesson or not lesson.published:
        raise HTTPException(404)

    prog = db.exec(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    ).first()

    if not prog:
        prog = LessonProgress(user_id=user.id, lesson_id=lesson_id)
        db.add(prog)

    prog.practice_done = True
    db.commit()

    return {"ok": True}
