import { useEffect, useRef, useState } from "react";
import {
  Attempt,
  PracticeRung,
  TajweedError,
  flagWrong,
  letterAudioUrl,
} from "../lib/api";
import { Key, Lang, retryCopy, t } from "../lib/i18n";
import ErrorBoundary from "./ErrorBoundary";
import PracticeLadder from "./PracticeLadder";

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
  /**
   * Which rung of that card's ladder is recording. A card can be re-read at
   * the word rung or at the ayah rung, and the button that shows "stop" has to
   * be the one that was tapped.
   */
  level: number | null;
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
  onRecordRung,
  onStopRetry,
  onFocusLetter,
  onRetry,
  cardRefs,
}: {
  lang: Lang;
  attempt: Attempt;
  activeCardId: string | null;
  retry: RetryState;
  /** Record one rung of a card's practice ladder — the word, or the ayah. */
  onRecordRung: (e: TajweedError, rung: PracticeRung) => void;
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
              onRecordRung={onRecordRung}
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
 * ONE card, in EXACTLY FOUR SLOTS. A correction answers four questions and
 * stops:
 *
 *   1  what happened    the category, the letter, one sentence
 *   2  where            the word(s), and what we heard against what to say
 *   3  how to fix it    ONE instruction
 *   4  what to practise the ladder — letter, syllables, word, ayah
 *
 * IT USED TO HAVE SIX, and the two that are gone are the reason the card read
 * like a textbook. A "Why" disclosure carried 13-44 words of tajweed theory in
 * vocabulary a beginner does not have; a "Practice" disclosure carried a
 * paragraph describing an exercise. Both were collapsed, which is the tell —
 * material nobody expects to be read every time is material that does not
 * belong on a correction card. Neither is deleted; the server simply stops
 * sending them, and the review tool still shows a qori the full entry.
 *
 * NOTHING IS COLLAPSED NOW. Four short slots, all open, read top to bottom in
 * about five seconds. If a slot has nothing in it, it is omitted rather than
 * shown empty.
 */
function Correction({
  id,
  lang,
  error,
  active,
  retry,
  onRecordRung,
  onStopRetry,
  onFocusLetter,
  cardRefs,
}: {
  id: string;
  lang: Lang;
  error: TajweedError;
  active: boolean;
  retry: RetryState;
  /** Record one rung of THIS card's ladder. */
  onRecordRung: (e: TajweedError, rung: PracticeRung) => void;
  onStopRetry: () => void;
  onFocusLetter: (id: string | null) => void;
  cardRefs: React.MutableRefObject<Record<string, HTMLElement | null>>;
}) {
  const c = error.content;
  const audio = letterAudioUrl(c.audio_pair ?? "");
  const busy = retry.cardId === id;
  const stillWrong = retry.stillWrong === id;

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

      {/* 2. WHERE — the word(s), then what we heard against what to say.
             Merged repeats say how often and in which words on ONE card; five
             identical cards for one letter is the bug this replaces.

             The heard/expected pair is the answer to "what should it have
             sounded like", which used to be a lone "correct: ذ" chip with
             nothing to compare it against. Shown only when BOTH are single
             letters — a haraka error reports a name ("fatha") and a duration
             error reports nothing, and neither belongs in an Arabic chip. */}
      <div className="where">
        <p className="where__words">
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

        {oneLetter(error.heard) && oneLetter(error.expected) && (
          <p className="where__pair">
            <span className="where__side">
              <span className="where__label">{t(lang, "card_you_said")}</span>
              <span className="card__letter card__letter--said" dir="rtl" lang="ar">
                {error.heard}
              </span>
            </span>
            <span className="where__arrow" aria-hidden="true">
              →
            </span>
            <span className="where__side">
              <span className="where__label">{t(lang, "card_correct")}</span>
              <span className="card__letter card__letter--good" dir="rtl" lang="ar">
                {error.expected}
              </span>
            </span>
          </p>
        )}
      </div>

      {/* 3. HOW TO FIX IT — one instruction, always open. It is the actionable
             part, and burying the answer one tap deep to keep the card tidy is
             a bad trade. The server sends the first paragraph of the authored
             `fix` and nothing after it; see coaching.instruction(). */}
      {c.fix && <p className="card__body card__body--fix">{c.fix}</p>}

      {/* 4. WHAT TO PRACTISE — the ladder. Replaces both the prose drill and
             the single "re-record this word" button: a learner who got one
             letter wrong practises THAT LETTER first and arrives back at the
             ayah having already said it right three times. */}
      <PracticeLadder
        lang={lang}
        error={error}
        activeLevel={busy ? retry.level : null}
        phase={busy ? retry.phase : null}
        letterAudio={audio}
        onRecord={onRecordRung}
        onStop={onStopRetry}
      />

      {busy && retry.phase === "recording" && (
        <p className="card__retry-hint">{t(lang, "retry_word_hint")}</p>
      )}
      {/* Not scolding. The same card stays exactly as it was; this one line is
          the only acknowledgement that the re-read did not land. */}
      {stillWrong && !busy && (
        <p className="card__retry-hint">{t(lang, "not_yet")}</p>
      )}

      {error.needs_teacher && (
        <span className="card__teacher">{t(lang, "teacher_note")}</span>
      )}
    </article>
  );
}

/**
 * True when a field really is one letter, and so can go in an Arabic chip.
 *
 * `expected` and `heard` carry different things for different detectors: a
 * letter for a substitution, a haraka NAME ("fatha") for a vowel error, a ṣifa
 * name ("mofakham") for a ṣifa error, and nothing at all for a duration one.
 * Only the single-character case is a letter; "fatha" set in Amiri at chip size
 * is nonsense.
 */
function oneLetter(v: string | undefined): boolean {
  return (v ?? "").length === 1;
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
