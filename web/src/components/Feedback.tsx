import { useEffect, useRef, useState } from "react";
import { Attempt, PracticeRung, TajweedError, flagWrong } from "../lib/api";
import { Key, Lang, retryCopy, t } from "../lib/i18n";
import DurationMeter from "./DurationMeter";
import ErrorBoundary from "./ErrorBoundary";
import PracticeLadder, { RungState } from "./PracticeLadder";

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
  shadda: "kind_shadda",
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
  /** Per card: which rungs are cleared, which failed, and the last score. */
  rungs: Record<string, RungState>;
};

export const EMPTY_RUNGS: RungState = { done: [], failed: null, score: null };

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
  ayahAudio,
  onRecordRung,
  onStopRetry,
  onSelfCheck,
  onFocusLetter,
  onRetry,
  cardRefs,
}: {
  lang: Lang;
  attempt: Attempt;
  activeCardId: string | null;
  retry: RetryState;
  /** Whole-ayah recitation, for the ladder's top rung. */
  ayahAudio: string;
  /** Record one rung of a card's practice ladder — the word, or the ayah. */
  onRecordRung: (e: TajweedError, rung: PracticeRung) => void;
  onStopRetry: () => void;
  /** A listen-and-say rung the learner confirms they have done. */
  onSelfCheck: (e: TajweedError, rung: PracticeRung) => void;
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

  const open = attempt.errors.filter((e) => !retry.fixed.includes(cardId(e)));

  return (
    <>
      {/* THE OUTCOME, IN A SENTENCE, BEFORE ANY CARD.
          No ring, no badge, no percentage, no confetti. A learner arriving at
          results should be able to read one line and know where they stand —
          how many places to look at, and that looking at them is the ordinary
          business of learning rather than a verdict.

          It counts the OPEN cards, so as they fix things the sentence comes
          down with them and reads "everything sorted" at the end instead of
          still announcing the original tally. */}
      <section className="card verdict">
        <p className="verdict__title">
          {open.length === 0
            ? t(lang, "verdict_all_fixed")
            : t(lang, "verdict_title").replace("{n}", String(open.length))}
        </p>
        <p className="verdict__body">
          {open.length === 0
            ? t(lang, "verdict_all_fixed_body")
            : t(lang, "verdict_body")}
        </p>
      </section>

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
              ayahAudio={ayahAudio}
              passScore={attempt.pass_score ?? 0.9}
              onRecordRung={onRecordRung}
              onStopRetry={onStopRetry}
              onSelfCheck={onSelfCheck}
              onFocusLetter={onFocusLetter}
              cardRefs={cardRefs}
            />
          </ErrorBoundary>
        );
      })}
      {/* The way out. After working through the cards the learner should be
          able to read the whole ayah again in one tap — that IS the practice,
          and leaving them to scroll back up to find the record button makes
          the loop feel unfinished. */}
      <div className="actions">
        <button className="btn-quiet" onClick={onRetry}>
          {t(lang, "verdict_again")}
        </button>
      </div>

      <WrongFlag lang={lang} attemptId={attempt.id} />
    </>
  );
}

/**
 * ONE card, in the SAME EIGHT SLOTS every time — RULE 12's canonical shape:
 *
 *   1  error            the category, and the letter it happened to
 *   2  rule name        which ruling this is
 *   3  location         which word, which instance of the letter, how often
 *   4  what happened    one sentence, plus the duration meter where length is
 *                       the mistake
 *   5  how to fix it    the correction, and the physical instruction under it
 *   6  listen           7  practise           8  re-check
 *                       all three inside the ladder, because they are one act:
 *                       hear it, say it, prove it
 *
 * FIXED, NOT ADAPTIVE. The previous card had four slots and dropped any it had
 * nothing for, so two cards for two different mistakes had two different
 * shapes and the learner re-learned the layout on each one. Now every slot has
 * a fixed position; a slot with nothing in it renders its fallback rather than
 * collapsing, and the only things that genuinely vanish are those that would be
 * lies — a heard/expected pair for an error with neither, a meter for an error
 * with no length.
 *
 * WHAT NEVER APPEARS. The error code, in any slot. It travels on the wire for
 * logs and for the "this is wrong" report, and the client's job is to make sure
 * a learner never meets it. Slots 1 and 2 are the two that used to leak it, and
 * both now fall back to a real name rather than an identifier.
 */
function Correction({
  id,
  lang,
  error,
  active,
  retry,
  ayahAudio,
  passScore,
  onRecordRung,
  onStopRetry,
  onSelfCheck,
  onFocusLetter,
  cardRefs,
}: {
  id: string;
  lang: Lang;
  error: TajweedError;
  active: boolean;
  retry: RetryState;
  ayahAudio: string;
  passScore: number;
  /** Record one rung of THIS card's ladder. */
  onRecordRung: (e: TajweedError, rung: PracticeRung) => void;
  onStopRetry: () => void;
  onSelfCheck: (e: TajweedError, rung: PracticeRung) => void;
  onFocusLetter: (id: string | null) => void;
  cardRefs: React.MutableRefObject<Record<string, HTMLElement | null>>;
}) {
  const c = error.content;
  const busy = retry.cardId === id;
  const kindTitle = t(lang, KIND_KEY[error.kind] ?? "kind_pronunciation");
  // Slot 2 in order of specificity: the registry entry's own title, then the
  // ṣifa's name, then the category. All three are real names — the point is
  // that there is no fourth option where the code could surface.
  const ruleName = error.rule_name || error.sifa_name || kindTitle;
  // Where the mistake is a LENGTH, the numbers are the whole finding.
  const meter =
    (error.expected_count ?? 0) > 0 && (error.heard_count ?? 0) > 0;

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
          here has been reviewed by a qori, and it must not read as if it had. */}
      {error.draft && (
        <p className="card__draft">
          <span className="card__draft-chip">{t(lang, "draft_chip")}</span>
          {c.unauthored ? t(lang, "draft_unauthored") : t(lang, "draft_note")}
        </p>
      )}

      {/* 1. ERROR — the learner-facing category and the letter. Never the code. */}
      <p className="card__kicker">
        {kindTitle}
        {error.letter && (
          <>
            {" — "}
            <span className="card__letter" dir="rtl" lang="ar">
              {error.letter}
            </span>
          </>
        )}
      </p>

      {/* 2. RULE NAME — which ruling this is, so the learner can look it up,
             ask a teacher about it by name, or recognise it next time. The card
             used to name the CATEGORY and stop, which is a description rather
             than a name.

             Printed only when it says something the kicker did not. Where no
             registry title and no ṣifa name exist, `ruleName` falls back to the
             category — and the category is already slot 1, so rendering it
             again puts the same three words on two consecutive lines and makes
             the card look like it failed to load. The slot keeps its position;
             it just does not repeat. */}
      {ruleName !== kindTitle && <p className="card__rule">{ruleName}</p>}

      {/* 3. LOCATION — the word, WHICH instance of the letter within it, and
             how often. "The letter ه was wrong" in a word with two of them
             leaves the learner guessing, and the red mark is on only one — so
             the words and the highlight disagreed about how many mistakes
             there were. */}
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
        <Which lang={lang} error={error} />

        {/* What we heard against what to say. Only when BOTH are single
            letters — a haraka error reports a name ("fatha"), a duration error
            reports nothing, and neither belongs in an Arabic chip. */}
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

      {/* 4. WHAT HAPPENED. */}
      {c.headline && <h3 className="card__headline">{c.headline}</h3>}

      {/* ...and where the mistake IS a length, the two lengths side by side.
          "Held for 2 instead of 6" is a sentence the learner has to convert
          into a duration, which is the exact thing they got wrong. */}
      {meter && (
        <DurationMeter
          lang={lang}
          letter={error.letter}
          expected={error.expected_count ?? 0}
          heard={error.heard_count ?? 0}
        />
      )}

      {/* 5. HOW TO FIX IT — the correction, then the physical instruction.
             Two different answers to two different questions: `fix` is what to
             do about THIS mistake, `articulation` is how the sound is made at
             all — where the tongue, throat or lips go. A card that named the
             ṣifa and stopped ("the ṣifa did not come out right") answered
             neither, and it was the most-shown correction in the app. */}
      {c.fix && <p className="card__body card__body--fix">{c.fix}</p>}
      {error.articulation && (
        <p className="card__body card__body--how">
          {error.sifa_name && (
            <span className="card__sifa">{error.sifa_name}</span>
          )}
          {error.articulation}
        </p>
      )}

      {/* 6, 7, 8. LISTEN, PRACTISE, RE-CHECK. */}
      <PracticeLadder
        lang={lang}
        error={error}
        activeLevel={busy ? retry.level : null}
        phase={busy ? retry.phase : null}
        state={retry.rungs[id] ?? EMPTY_RUNGS}
        ayahAudio={ayahAudio}
        passScore={passScore}
        onRecord={onRecordRung}
        onStop={onStopRetry}
        onSelfCheck={onSelfCheck}
      />

      {busy && retry.phase === "recording" && (
        <p className="card__retry-hint">{t(lang, "retry_word_hint")}</p>
      )}

      {error.needs_teacher && (
        <span className="card__teacher">{t(lang, "teacher_note")}</span>
      )}
    </article>
  );
}

/**
 * RULE 10 — which instance of the letter, when there is more than one.
 *
 * Rendered only when the word really does contain the letter twice or more:
 * "the 1st ص in ٱلصَّمَدُ" is noise in a word with one ص, and noise on every card
 * is how a genuinely useful disambiguation gets ignored on the cards that need
 * it. The server counts over the written CHARACTERS of the word, which is what
 * the learner counts too.
 */
function Which({ lang, error }: { lang: Lang; error: TajweedError }) {
  const first = error.occurrences?.[0];
  if (!first?.ordinal || !first.of || first.of < 2) return null;
  return (
    <p className="where__which">
      {t(lang, "which_letter")
        .replace("{n}", String(first.ordinal))
        .replace("{of}", String(first.of))}
      <span className="card__letter card__letter--small" dir="rtl" lang="ar">
        {error.letter}
      </span>
    </p>
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
