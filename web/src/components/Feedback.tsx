import { useEffect, useRef, useState } from "react";
import {
  Attempt,
  TajweedError,
  flagWrong,
  letterAudioUrl,
} from "../lib/api";
import { Key, Lang, retryCopy, t } from "../lib/i18n";
import ErrorBoundary from "./ErrorBoundary";

/** Stable identity for one merged card, shared with the ayah's red marks. */
export const cardId = (e: TajweedError) => `${e.code}:${e.letter}`;

/** kind -> the i18n key holding its learner-facing title. */
const KIND_KEY: Record<string, Key> = {
  extra_letter: "kind_extra_letter",
  missing_letter: "kind_missing_letter",
  wrong_letter: "kind_wrong_letter",
  pronunciation: "kind_pronunciation",
  tajweed: "kind_tajweed",
  madd: "kind_madd",
  ghunna: "kind_ghunna",
  haraka: "kind_haraka",
};

export type RetryState = {
  /** Card currently being re-recorded, or null. */
  cardId: string | null;
  phase: "recording" | "checking" | null;
  /** Cards the learner has since fixed — these close. */
  fixed: string[];
  /** Card re-read that still shows the same mistake. */
  stillWrong: string | null;
};

/**
 * Result states. The tone rule governs every branch here: no red, no marks
 * against, no score. A correction is phrased as what we heard, then what to do
 * about it — never as a verdict on the person reciting.
 */
export default function Feedback({
  lang,
  attempt,
  activeCardId,
  retry,
  onRetryWord,
  onStopRetry,
  onFocusLetter,
  onRetry,
  cardRefs,
}: {
  lang: Lang;
  attempt: Attempt;
  activeCardId: string | null;
  retry: RetryState;
  /** Re-record ONE word — the word this error is in. */
  onRetryWord: (e: TajweedError) => void;
  onStopRetry: () => void;
  /** Card tapped: light its letters in the ayah. */
  onFocusLetter: (id: string | null) => void;
  onRetry: () => void;
  cardRefs: React.MutableRefObject<Record<string, HTMLElement | null>>;
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
  //   !analysable  the model returned nothing to judge   -> "couldn't assess"
  //   clean        judged, and nothing was wrong         -> praise
  //   suppressed   judged, and we are not allowed to say -> "withheld"

  if (!attempt.analysable) {
    return (
      <div className="notice">
        <p className="notice__title">{t(lang, "unsure_title")}</p>
        <p className="notice__body">{t(lang, "unsure_body")}</p>
      </div>
    );
  }

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
      {attempt.errors.map((e) => {
        const id = cardId(e);
        // A card the learner has re-read correctly closes into a confirmation.
        // The loop ends where it started — on the same card — rather than
        // scrolling them somewhere new.
        if (retry.fixed.includes(id)) {
          return <Fixed key={id} lang={lang} error={e} />;
        }
        return (
          // Per-card, not per-page. A card that cannot render is one lost
          // correction; the others, and the ayah above them, still stand.
          <ErrorBoundary
            key={id}
            label={`card ${e.code}`}
            resetKey={attempt.id}
            fallback={
              <article className="card card--broken" role="status">
                <p className="card__body">{t(lang, "card_broken")}</p>
              </article>
            }
          >
            <Correction
              id={id}
              lang={lang}
              error={e}
              active={activeCardId === id}
              retry={retry}
              onRetryWord={onRetryWord}
              onStopRetry={onStopRetry}
              onFocusLetter={onFocusLetter}
              cardRefs={cardRefs}
            />
          </ErrorBoundary>
        );
      })}
      <WrongFlag lang={lang} attemptId={attempt.id} />
    </>
  );
}

/**
 * ONE card, in the six slots Part B specifies:
 *
 *   1 what happened   the headline
 *   2 where           the word(s), and the letter marked red in the ayah
 *   3 correct         the expected letter, shown
 *   4 why             the rule
 *   5 fix it          one instruction
 *   6 practice        the LETTER's sound, not the ayah
 *
 * Slots 4-6 are collapsed by default. The card has to stay short enough to
 * read: what happened, where, and what the right letter is, is the part a
 * learner acts on.
 */
function Correction({
  id,
  lang,
  error,
  active,
  retry,
  onRetryWord,
  onStopRetry,
  onFocusLetter,
  cardRefs,
}: {
  id: string;
  lang: Lang;
  error: TajweedError;
  active: boolean;
  retry: RetryState;
  onRetryWord: (e: TajweedError) => void;
  onStopRetry: () => void;
  onFocusLetter: (id: string | null) => void;
  cardRefs: React.MutableRefObject<Record<string, HTMLElement | null>>;
}) {
  const c = error.content;
  const audio = letterAudioUrl(c.audio_pair ?? "");
  const audioRef = useRef<HTMLAudioElement>(null);
  const busy = retry.cardId === id;
  const stillWrong = retry.stillWrong === id;
  // A word we can actually isolate. -1 means the unit could not be placed in a
  // word, and re-recording "word -1" would silently re-record the whole ayah.
  const canRetryWord = (error.word_index ?? -1) >= 0;

  return (
    <article
      ref={(node) => {
        cardRefs.current[id] = node;
      }}
      className={[
        "card",
        error.draft ? "card--draft" : "card--lit",
        active ? "card--active" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      onClick={() => onFocusLetter(id)}
    >
      {/* The server sends `draft` precisely so this cannot be omitted: nothing
          here has been reviewed by a qori, and it must not read as if it had.
          The CODE is deliberately absent — Part B: no internal identifiers on
          a learner's screen. It still travels on the wire for logs and for the
          "this is wrong" report. */}
      {error.draft && (
        <p className="card__draft">
          <span className="card__draft-chip">{t(lang, "draft_chip")}</span>
          {c.unauthored ? t(lang, "draft_unauthored") : t(lang, "draft_note")}
        </p>
      )}

      {/* 1. WHAT HAPPENED — the title is the learner-facing category, and the
             letter it happened to. Never the code. */}
      <p className="card__kicker">
        {t(lang, KIND_KEY[error.kind] ?? "kind_pronunciation")}
        {error.letter && (
          <>
            {" — "}
            <span className="card__letter" dir="rtl" lang="ar">
              {error.letter}
            </span>
          </>
        )}
      </p>

      {c.headline && <h3 className="card__headline">{c.headline}</h3>}

      {/* 2. WHERE. Merged repeats say how often and in which words, on ONE
             card — five identical cards for one letter is the bug this
             replaces. */}
      <p className="card__where">
        {error.count > 1 && (
          <span className="card__count">
            {error.count} {t(lang, "card_times")}
            {" · "}
          </span>
        )}
        {error.words.map((w, i) => (
          <span key={`${w}-${i}`} className="card__word" dir="rtl" lang="ar">
            {w}
          </span>
        ))}
      </p>

      {/* 3. CORRECT — the expected letter, shown as a letter. Only where the
             detector actually has one: duration and ṣifa errors have no
             "right letter" to show, and an empty box would be noise. */}
      {error.content && expectedLetter(error) && (
        <p className="card__correct">
          <span className="card__correct-label">{t(lang, "card_correct")}</span>
          <span className="card__letter card__letter--good" dir="rtl" lang="ar">
            {expectedLetter(error)}
          </span>
        </p>
      )}

      {/* 5. FIX IT — open by default. It is the actionable part, and burying
             the answer one tap deep to keep the card tidy is a bad trade. */}
      {c.fix && <p className="card__body card__body--fix">{c.fix}</p>}

      {/* 4. WHY — collapsed. Worth having, not worth reading every time. */}
      {c.rule && (
        <details className="card__more">
          <summary>{t(lang, "card_why")}</summary>
          <p className="card__body">{c.rule}</p>
        </details>
      )}

      {/* 6. PRACTICE — the LETTER's sound. The ayah playback lives on the
             recitation screen; a whole-ayah recording teaches nothing about
             one consonant. The button appears ONLY when the file exists —
             `audio_pair` is empty otherwise, and a control that plays nothing
             is worse than no control. */}
      {(c.drill || audio) && (
        <details className="card__more">
          <summary>{t(lang, "card_practice")}</summary>
          {c.drill && <p className="card__body">{c.drill}</p>}
          {audio && (
            <>
              <button
                className="card__replay"
                onClick={(ev) => {
                  ev.stopPropagation();
                  audioRef.current?.play();
                }}
              >
                <Play />
                {t(lang, "listen_letter")}
              </button>
              <audio ref={audioRef} src={audio} preload="none" />
            </>
          )}
        </details>
      )}

      {/* THE RECOVERY LOOP. Re-records ONLY this word, through the same
          word-range machinery the practice segments use — not the whole ayah,
          which is what made re-checking one letter cost a full re-read. */}
      {canRetryWord && (
        <div className="card__retry">
          <button
            className={busy ? "card__retry-btn card__retry-btn--live" : "card__retry-btn"}
            onClick={(ev) => {
              ev.stopPropagation();
              busy ? onStopRetry() : onRetryWord(error);
            }}
            disabled={retry.phase === "checking" && !busy}
          >
            {busy
              ? retry.phase === "checking"
                ? t(lang, "retry_checking")
                : t(lang, "retry_word_stop")
              : t(lang, "retry_word")}
          </button>
          {busy && retry.phase === "recording" && (
            <span className="card__retry-hint">{t(lang, "retry_word_hint")}</span>
          )}
          {/* Not scolding. The same card stays exactly as it was; this one
              line is the only acknowledgement that the re-read did not land. */}
          {stillWrong && !busy && (
            <span className="card__retry-hint">{t(lang, "not_yet")}</span>
          )}
        </div>
      )}

      {error.needs_teacher && (
        <span className="card__teacher">{t(lang, "teacher_note")}</span>
      )}
    </article>
  );
}

/**
 * The expected letter, for slot 3 — but only when there genuinely is one.
 *
 * `expected` carries different things for different detectors: a letter for a
 * substitution, a haraka NAME ("fatha") for a vowel error, and nothing at all
 * for a duration or ṣifa error. Showing "fatha" inside an Arabic-script chip
 * would be wrong, so this returns a value only for the single-character case.
 */
function expectedLetter(e: TajweedError): string {
  const v = e.expected ?? "";
  return v.length === 1 ? v : "";
}

/** The end of the loop: brief, warm, and then out of the way. */
function Fixed({ lang, error }: { lang: Lang; error: TajweedError }) {
  return (
    <article className="card card--fixed" role="status">
      <p className="card__kicker">
        {t(lang, KIND_KEY[error.kind] ?? "kind_pronunciation")}
        {error.letter && (
          <>
            {" — "}
            <span className="card__letter" dir="rtl" lang="ar">
              {error.letter}
            </span>
          </>
        )}
      </p>
      <p className="card__fixed-title">{t(lang, "fixed_title")}</p>
    </article>
  );
}

function Play() {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 12 12"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M3 1.6 10 6 3 10.4Z" />
    </svg>
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

/**
 * Playback of the learner's OWN recording.
 *
 * Session-only: the Blob lives in memory for as long as the result is on
 * screen and is revoked when it is replaced. Nothing is uploaded and no consent
 * default is touched — hearing yourself back is not data collection, and making
 * it one would be the wrong trade for a feature whose whole point is letting
 * the learner check our work.
 */
export function SelfPlayback({ lang, blob }: { lang: Lang; blob: Blob | null }) {
  const [url, setUrl] = useState<string>("");
  const ref = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!blob) {
      setUrl("");
      return;
    }
    const next = URL.createObjectURL(blob);
    setUrl(next);
    // Revoked on replacement AND on unmount: an object URL pins the whole blob
    // in memory until it is released, and these are megabytes each.
    return () => URL.revokeObjectURL(next);
  }, [blob]);

  if (!url) return null;
  return (
    <div className="selfplay">
      <button
        className="selfplay__btn"
        onClick={() => {
          const a = ref.current;
          if (!a) return;
          if (playing) {
            a.pause();
            a.currentTime = 0;
          } else {
            a.play().catch(() => {});
          }
        }}
      >
        <Play />
        {playing ? t(lang, "hear_yourself_stop") : t(lang, "hear_yourself")}
      </button>
      <audio
        ref={ref}
        src={url}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />
    </div>
  );
}
