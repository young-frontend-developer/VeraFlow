import { useState, useEffect, useCallback } from "react";
import { Lang, t } from "../lib/i18n";
import {
  listLessons,
  getLesson,
  submitQuiz,
  markPractice,
  type LessonSummary,
  type LessonDetail,
  type QuizResult,
} from "../lib/api";
import { BookOrnament } from "./Ornament";

// ── lesson list ─────────────────────────────────────────────────────────

export function Academy({ lang }: { lang: Lang }) {
  const [lessons, setLessons] = useState<LessonSummary[] | null>(null);
  const [active, setActive] = useState<number | null>(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    listLessons()
      .then(setLessons)
      .catch(() => setErr("Failed to load lessons"));
  }, []);

  useEffect(load, [load]);

  if (active !== null)
    return (
      <LessonView
        lessonId={active}
        lang={lang}
        onBack={() => {
          setActive(null);
          load();
        }}
      />
    );

  if (err)
    return (
      <section className="soon">
        <p className="soon__body">{err}</p>
      </section>
    );

  if (!lessons) return <div className="academy__loading" />;

  if (lessons.length === 0)
    return (
      <section className="soon">
        <BookOrnament className="soon__ornament" size={54} />
        <h2 className="soon__title">{t(lang, "learn_empty")}</h2>
        <p className="soon__body">{t(lang, "learn_empty_body")}</p>
      </section>
    );

  const done = lessons.filter((l) => l.status === "completed").length;

  return (
    <section className="academy">
      <header className="academy__head">
        <h2 className="academy__title">{t(lang, "learn_title")}</h2>
        <span className="academy__count">
          {t(lang, "learn_progress")
            .replace("{done}", String(done))
            .replace("{total}", String(lessons.length))}
        </span>
      </header>

      <ol className="academy__list">
        {lessons.map((l) => (
          <li key={l.id} className={`academy__item academy__item--${l.status}`}>
            <button
              className="academy__card"
              disabled={l.status === "locked"}
              onClick={() => setActive(l.id)}
            >
              <span className="academy__order">{l.order}</span>
              <div className="academy__info">
                <span className="academy__name">
                  {lang === "uz" ? l.title_uz : l.title_ru}
                </span>
                <span className="academy__meta">
                  {t(
                    lang,
                    l.difficulty === "intermediate"
                      ? "learn_intermediate"
                      : l.difficulty === "advanced"
                        ? "learn_advanced"
                        : "learn_beginner",
                  )}
                  {l.quiz_score !== null && ` · ${l.quiz_score}%`}
                </span>
              </div>
              <span className="academy__status">
                {l.status === "completed"
                  ? "✓"
                  : l.status === "locked"
                    ? "🔒"
                    : "→"}
              </span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}

// ── single lesson view ──────────────────────────────────────────────────

function LessonView({
  lessonId,
  lang,
  onBack,
}: {
  lessonId: number;
  lang: Lang;
  onBack: () => void;
}) {
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [phase, setPhase] = useState<"read" | "quiz" | "result">("read");
  const [answers, setAnswers] = useState<(number | null)[]>([]);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getLesson(lessonId).then((d) => {
      setLesson(d);
      setAnswers(new Array(d.quiz.length).fill(null));
    });
  }, [lessonId]);

  if (!lesson) return <div className="academy__loading" />;

  const title = lang === "uz" ? lesson.title_uz : lesson.title_ru;
  const body = lang === "uz" ? lesson.body_uz : lesson.body_ru;

  // ── quiz submission
  const handleSubmit = async () => {
    if (answers.some((a) => a === null)) return;
    setSubmitting(true);
    try {
      const r = await submitQuiz(lessonId, answers as number[]);
      setResult(r);
      setPhase("result");
    } finally {
      setSubmitting(false);
    }
  };

  // ── practice mark
  const handlePractice = async () => {
    await markPractice(lessonId);
    const d = await getLesson(lessonId);
    setLesson(d);
  };

  return (
    <section className="lesson">
      <button className="lesson__back" onClick={onBack}>
        ← {t(lang, "learn_back")}
      </button>

      {phase === "read" && (
        <div className="lesson__content">
          <h2 className="lesson__title">
            {t(lang, "learn_lesson")} {lesson.order}: {title}
          </h2>
          <div
            className="lesson__body"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(body) }}
          />

          {lesson.video_url && (
            <a
              href={lesson.video_url}
              target="_blank"
              rel="noopener noreferrer"
              className="lesson__video"
            >
              ▶ {t(lang, "learn_video")}
            </a>
          )}

          <div className="lesson__actions">
            {!lesson.practice_done ? (
              <button className="lesson__btn--secondary" onClick={handlePractice}>
                {t(lang, "learn_practice_btn")}
              </button>
            ) : (
              <span className="lesson__practice-check">
                ✓ {t(lang, "learn_practice_done")}
              </span>
            )}

            {lesson.quiz.length > 0 && (
              <button
                className="lesson__btn--primary"
                onClick={() => setPhase("quiz")}
              >
                {t(lang, "learn_start_quiz")}
              </button>
            )}
          </div>
        </div>
      )}

      {phase === "quiz" && (
        <div className="lesson__quiz">
          <h3 className="lesson__quiz-title">{t(lang, "learn_quiz")}</h3>
          <p className="lesson__quiz-note">
            {t(lang, "learn_pass_threshold").replace(
              "{n}",
              String(lesson.pass_score),
            )}
          </p>

          {lesson.quiz.map((q, qi) => {
            const question = lang === "uz" ? q.question_uz : q.question_ru;
            const options = lang === "uz" ? q.options_uz : q.options_ru;
            return (
              <div key={q.id} className="quiz__question">
                <p className="quiz__text">
                  {qi + 1}. {question}
                </p>
                <div className="quiz__options">
                  {options.map((opt, oi) => (
                    <button
                      key={oi}
                      className={`quiz__option ${answers[qi] === oi ? "quiz__option--selected" : ""}`}
                      onClick={() => {
                        const next = [...answers];
                        next[qi] = oi;
                        setAnswers(next);
                      }}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}

          <button
            className="lesson__btn--primary"
            disabled={answers.some((a) => a === null) || submitting}
            onClick={handleSubmit}
          >
            {t(lang, "learn_submit")}
          </button>
        </div>
      )}

      {phase === "result" && result && (
        <div className="lesson__result">
          <div
            className={`result__badge ${result.passed ? "result__badge--pass" : "result__badge--fail"}`}
          >
            {t(lang, "learn_score").replace("{n}", String(result.score))}
          </div>
          <p className="result__message">
            {t(lang, result.passed ? "learn_passed" : "learn_failed")}
          </p>

          <div className="result__details">
            {result.results.map((r, i) => {
              const q = lesson.quiz[i];
              const question = lang === "uz" ? q.question_uz : q.question_ru;
              const options = lang === "uz" ? q.options_uz : q.options_ru;
              const explanation =
                lang === "uz" ? r.explanation_uz : r.explanation_ru;
              return (
                <div
                  key={r.question_id}
                  className={`result__item ${r.is_correct ? "result__item--correct" : "result__item--wrong"}`}
                >
                  <p className="result__q">
                    {i + 1}. {question}
                  </p>
                  <p className="result__given">
                    {r.is_correct ? "✓" : "✗"} {options[r.given]}
                  </p>
                  {!r.is_correct && (
                    <p className="result__answer">
                      {t(lang, "learn_correct")}: {options[r.correct]}
                    </p>
                  )}
                  {explanation && (
                    <p className="result__explanation">{explanation}</p>
                  )}
                </div>
              );
            })}
          </div>

          <div className="lesson__actions">
            {!result.passed && (
              <button
                className="lesson__btn--secondary"
                onClick={() => {
                  setPhase("quiz");
                  setAnswers(new Array(lesson.quiz.length).fill(null));
                  setResult(null);
                }}
              >
                {t(lang, "learn_start_quiz")}
              </button>
            )}
            <button className="lesson__btn--primary" onClick={onBack}>
              {result.passed ? t(lang, "learn_next") : t(lang, "learn_back")}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

// ponytail: minimal markdown — handles ##, **, \n. Full parser if content grows.
function renderMarkdown(md: string): string {
  return md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/## (.+)/g, "<h3>$1</h3>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/gs, "<ol>$1</ol>")
    .replace(/\n{2,}/g, "<br><br>")
    .replace(/\n/g, "<br>");
}
