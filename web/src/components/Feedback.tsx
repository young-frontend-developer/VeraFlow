import { useState } from "react";
import { Attempt, TajweedError, flagWrong } from "../lib/api";
import { Lang, retryCopy, t } from "../lib/i18n";

/**
 * Result states. The tone rule governs every branch here: no red, no marks
 * against, no score. A correction is phrased as what we heard, then what to do
 * about it — never as a verdict on the person reciting.
 */
export default function Feedback({
  lang,
  attempt,
  letter,
  onRetry,
  onReplay,
}: {
  lang: Lang;
  attempt: Attempt;
  /** The Arabic letter-group the first correction points at, if any. */
  letter: string;
  onRetry: () => void;
  onReplay: () => void;
}) {
  if (attempt.status === "retry_recording") {
    const copy = retryCopy(lang, attempt.reason);
    return (
      <div className="notice notice--warm">
        <p className="notice__title">{copy.title}</p>
        <p className="notice__body">{copy.body}</p>
        {copy.tips.length > 0 && (
          <ul className="notice__list">
            {copy.tips.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ul>
        )}
        <div className="actions">
          <button className="btn-quiet" onClick={onRetry}>
            {t(lang, "retry_again")}
          </button>
        </div>
      </div>
    );
  }

  if (attempt.status === "error") {
    return (
      <div className="notice">
        <p className="notice__body">{t(lang, "error_generic")}</p>
      </div>
    );
  }

  // Nothing detected at all — the only case where praise is honest.
  if (attempt.clean) {
    return (
      <div className="clear">
        <div className="clear__mark" aria-hidden="true">
          <span className="clear__flame" />
        </div>
        <p className="clear__title">{t(lang, "clear_title")}</p>
        <p className="clear__body">{t(lang, "clear_body")}</p>
      </div>
    );
  }

  // Something was found but nothing is shippable — say so plainly rather than
  // implying the recitation was perfect.
  if (attempt.suppressed || attempt.errors.length === 0) {
    return (
      <div className="notice">
        <p className="notice__title">{t(lang, "unsure_title")}</p>
        <p className="notice__body">{t(lang, "unsure_body")}</p>
      </div>
    );
  }

  return (
    <>
      {attempt.errors.map((e, i) => (
        <Correction
          key={`${e.code}-${e.at}`}
          lang={lang}
          error={e}
          letter={i === 0 ? letter : ""}
          onReplay={onReplay}
        />
      ))}
      <WrongFlag lang={lang} attemptId={attempt.id} />
    </>
  );
}

function Correction({
  lang,
  error,
  letter,
  onReplay,
}: {
  lang: Lang;
  error: TajweedError;
  letter: string;
  onReplay: () => void;
}) {
  const c = error.content;
  return (
    <article className="card card--lit">
      <h3 className="card__rule">
        {c.rule}
        {letter && (
          <span className="card__letter" dir="rtl" lang="ar">
            {letter}
          </span>
        )}
      </h3>

      <p className="card__label">{t(lang, "label_heard")}</p>
      <p className="card__said">{c.you_did}</p>

      <p className="card__label">{t(lang, "label_fix")}</p>
      <p className="card__body">{c.fix}</p>

      <p className="card__label">{t(lang, "label_drill")}</p>
      <p className="card__body">{c.drill}</p>

      <button className="card__replay" onClick={onReplay}>
        <svg width="10" height="10" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
          <path d="M3 1.6 10 6 3 10.4Z" />
        </svg>
        {t(lang, "listen")}
      </button>

      {error.needs_teacher && (
        <span className="card__teacher">{t(lang, "teacher_note")}</span>
      )}
    </article>
  );
}

function WrongFlag({ lang, attemptId }: { lang: Lang; attemptId: number | null }) {
  const [done, setDone] = useState(false);
  if (attemptId === null) return null;
  return (
    <button
      className="linkish"
      disabled={done}
      onClick={() => {
        flagWrong(attemptId).catch(() => {});
        setDone(true);
      }}
    >
      {done ? t(lang, "wrong_thanks") : t(lang, "wrong_button")}
    </button>
  );
}
