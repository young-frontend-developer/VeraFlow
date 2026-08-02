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

  // THE THREE "NO CORRECTIONS" CASES ARE DIFFERENT AND SAY DIFFERENT THINGS.
  //
  // They all used to print "Toʻliq baholay olmadik", which made a content-gate
  // decision indistinguishable from a model failure — for the learner AND for
  // whoever was debugging it. Each now names its own cause:
  //
  //   !analysable  the model returned nothing to judge   -> "couldn't assess"
  //   clean        judged, and nothing was wrong         -> praise
  //   suppressed   judged, and we are not allowed to say -> "withheld"

  // The model gave us nothing to compare against. This — and only this — is
  // what "we could not assess it" means.
  if (!attempt.analysable) {
    return (
      <div className="notice">
        <p className="notice__title">{t(lang, "unsure_title")}</p>
        <p className="notice__body">{t(lang, "unsure_body")}</p>
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

  // Something was found and every correction was withheld by the review gate.
  // Not the same as failing to assess: the assessment exists. Saying so plainly
  // also keeps us from implying the recitation was perfect.
  if (attempt.errors.length === 0) {
    return (
      <div className="notice">
        <p className="notice__title">{t(lang, "withheld_title")}</p>
        <p className="notice__body">{t(lang, "withheld_body")}</p>
      </div>
    );
  }

  return (
    <>
      {attempt.errors.map((e, i) => (
        // `code`+`at` is NOT unique: typed_diff reports every inserted phoneme
        // in one opcode at the same index, so a take with six extra sounds
        // yields six INSERTION errors all at the same `at`. That collided the
        // moment the two-error cap came off, and React silently drops
        // duplicate-keyed siblings — corrections would have gone missing.
        <Correction
          key={`${e.code}-${e.at}-${i}`}
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
    <article className={error.draft ? "card card--draft" : "card card--lit"}>
      {/* The server sends `draft` precisely so this cannot be omitted: nothing
          here has been reviewed by a qori, and it must not read as if it had. */}
      {error.draft && (
        <p className="card__draft">
          <span className="card__draft-chip">{t(lang, "draft_chip")}</span>
          {c.unauthored ? t(lang, "draft_unauthored") : t(lang, "draft_note")}
          <code className="card__code">{error.code}</code>
        </p>
      )}

      {c.label && <p className="card__kicker">{c.label}</p>}

      {/*
        THE HEADLINE IS THE CARD. It names the word, the letter and what
        happened, and it is the one thing that is never collapsed — a learner
        who reads nothing else still learns where the mistake was.

        When nothing is authored for the code we still have the location, so we
        show that rather than falling back to silence. It is not a ruling about
        tajweed, just a pointer: this word, this letter.
      */}
      <h3 className="card__headline">
        {c.headline || <Located lang={lang} word={error.word} letter={letter || error.letter} />}
        {c.headline && letter && (
          <span className="card__letter" dir="rtl" lang="ar">
            {letter}
          </span>
        )}
      </h3>

      {/* Fix is open by default: it is the actionable part, and burying the
          answer one tap deep to keep the card tidy would be a bad trade. */}
      {c.fix && <p className="card__body card__body--fix">{c.fix}</p>}

      {/* Rule and drill are collapsed. They are worth having and not worth
          reading every single time — <details> keeps them one tap away without
          any state of our own. */}
      {c.rule && (
        <details className="card__more">
          <summary>{t(lang, "label_rule")}</summary>
          <p className="card__body">{c.rule}</p>
        </details>
      )}
      {c.drill && (
        <details className="card__more">
          <summary>{t(lang, "label_drill")}</summary>
          <p className="card__body">{c.drill}</p>
        </details>
      )}

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

/**
 * The last-resort headline: word and letter, no claim about either.
 *
 * Reached only when neither coaching registry has an entry for the code. The
 * requirement it satisfies is "if any error was detected, the learner sees the
 * word and the letter — always"; the requirement it must not break is that
 * nothing invents a ruling about the Quran. Naming a location does neither.
 */
function Located({
  lang,
  word,
  letter,
}: {
  lang: Lang;
  word?: string;
  letter: string;
}) {
  if (!word && !letter) return <>{t(lang, "located_unknown")}</>;
  return (
    <>
      {word && (
        <span className="card__word" dir="rtl" lang="ar">
          {word}
        </span>
      )}
      {letter && (
        <span className="card__letter" dir="rtl" lang="ar">
          {letter}
        </span>
      )}
    </>
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
