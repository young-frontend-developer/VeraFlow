#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ingest partner-authored lesson JSON files into the database.

Usage:
    .venv/bin/python tools/ingest_lessons.py lessons/*.json
    .venv/bin/python tools/ingest_lessons.py --dry-run lessons/01-noon-sakinah.json

Each JSON file follows the format documented in the academy plan.
Existing lessons (matched by slug) are updated in place.
"""
import argparse
import json
import sys
from pathlib import Path

# Add parent to path so tilawah is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select
from tilawah.db import engine
from tilawah.db.models import Lesson, QuizQuestion


def load_lesson(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def ingest_one(data: dict, db: Session, *, verbose: bool = False) -> str:
    slug = data["slug"]
    existing = db.exec(select(Lesson).where(Lesson.slug == slug)).first()

    if existing:
        for key in ("order", "difficulty", "title_uz", "title_ru",
                     "body_uz", "body_ru", "rule_codes", "practice_sura",
                     "practice_aya", "video_url", "pass_score", "published"):
            if key in data:
                setattr(existing, key, data[key])
        lesson = existing
        action = "updated"
    else:
        lesson = Lesson(
            order=data["order"],
            slug=slug,
            difficulty=data.get("difficulty", "beginner"),
            title_uz=data.get("title_uz", ""),
            title_ru=data.get("title_ru", ""),
            body_uz=data.get("body_uz", ""),
            body_ru=data.get("body_ru", ""),
            rule_codes=data.get("rule_codes", []),
            practice_sura=data.get("practice_sura", 0),
            practice_aya=data.get("practice_aya", 0),
            video_url=data.get("video_url"),
            pass_score=data.get("pass_score", 70),
            published=data.get("published", False),
        )
        db.add(lesson)
        action = "created"

    db.flush()

    if "quiz" in data:
        # Remove old questions for this lesson on update
        old_qs = db.exec(
            select(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id)
        ).all()
        for q in old_qs:
            db.delete(q)
        db.flush()

        for i, q in enumerate(data["quiz"]):
            db.add(QuizQuestion(
                lesson_id=lesson.id,
                order=i,
                question_uz=q.get("question_uz", ""),
                question_ru=q.get("question_ru", ""),
                options_uz=q.get("options_uz", []),
                options_ru=q.get("options_ru", []),
                correct=q.get("correct", 0),
                explanation_uz=q.get("explanation_uz"),
                explanation_ru=q.get("explanation_ru"),
            ))

    if verbose:
        n_quiz = len(data.get("quiz", []))
        print(f"  {action}: [{lesson.order}] {slug} ({n_quiz} questions)")

    return action


def main():
    parser = argparse.ArgumentParser(description="Ingest lesson JSON files")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true", default=True)
    args = parser.parse_args()

    created = updated = errors = 0

    with Session(engine) as db:
        for path in sorted(args.files):
            try:
                data = load_lesson(path)
                action = ingest_one(data, db, verbose=args.verbose)
                if action == "created":
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                print(f"  ERROR: {path.name}: {exc}", file=sys.stderr)
                errors += 1

        if args.dry_run:
            db.rollback()
            print(f"\nDry run: {created} would create, {updated} would update, {errors} errors")
        else:
            db.commit()
            print(f"\nDone: {created} created, {updated} updated, {errors} errors")


if __name__ == "__main__":
    main()
