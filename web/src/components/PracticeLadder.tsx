import { useRef } from "react";
import { PracticeRung, TajweedError } from "../lib/api";
import { Key, Lang, t } from "../lib/i18n";

/**
 * The practice section of a correction card — slots 6, 7 and 8 of RULE 12's
 * canonical shape (listen, practise, re-check), which are one thing in the UI
 * because they are one thing to do: hear it, say it, prove it.
 *
 * THE LADDER. Four rungs, narrow to wide — the letter alone, the letter under
 * each haraka, the word they actually misread, then back to the ayah. The
 * learner meets the sound by itself before meeting it inside anything, which is
 * how a teacher introduces it, and arrives back at the ayah having already said
 * it right three times.
 *
 * ── PROGRESSIVE UNLOCK (RULE 9) ────────────────────────────────────────────
 *
 * A rung opens only when the one before it is cleared. Not to gamify it: the
 * ladder is an ORDER, and a learner who jumps to the ayah is doing the test
 * again rather than the practice — which is the exact behaviour the old single
 * "re-record" button forced on everyone.
 *
 * Clearing means different things on different rungs, and the UI has to be
 * honest about which:
 *
 *   check: "score"   recorded, transcribed, diffed against a real target. The
 *                    engine says whether the mistake is still there and what
 *                    the range scored. Word and ayah rungs.
 *
 *   check: "self"    the learner confirms they said it. Letter and syllable
 *                    rungs, because THE ENGINE HAS NO TARGET FOR A BARE LETTER
 *                    — the phonetizer works on Quranic text, and the model is
 *                    trained on connected recitation, so a 300 ms isolated
 *                    consonant lands in the muqatta'at collapse. A percentage
 *                    there would be a number with nothing behind it, shown to a
 *                    beginner on the first rung they touch.
 *
 * So the chain is complete and the judging is not uniform. That is stated on
 * the rung rather than hidden: a self-checked rung says "men aytdim", a scored
 * one shows what it scored.
 *
 * ── AUDIO (RULES 6 AND 8) ──────────────────────────────────────────────────
 *
 * Every rung that HAS a recording offers it, at normal speed and slowed. Slow
 * is the same file at a reduced playback rate — genuinely the recording slowed
 * down, not a second file nobody has made.
 *
 * A rung with no recording offers NO BUTTON. Today that is the word rung
 * always, and the letter rung until the isolated-letter files are recorded:
 * everyayah serves whole-ayah audio with no word timings to clip, so there is
 * nothing to play and nothing honest to claim. A control that cannot do what it
 * says teaches the learner the app lies.
 */

/** focus -> the i18n key naming that rung. */
const FOCUS_KEY: Record<PracticeRung["focus"], Key> = {
  letter: "rung_letter",
  syllables: "rung_syllables",
  word: "rung_word",
  ayah: "rung_ayah",
};

/** How much slower "slow" is. Slow enough to hear the shape, not a drone. */
const SLOW_RATE = 0.6;

export type RungState = {
  /** Levels the learner has cleared, so the next one opens. */
  done: number[];
  /** Level whose re-read did not clear it, if any. */
  failed: number | null;
  /** Score of the last scored attempt on this card, 0–1. */
  score: number | null;
};

export default function PracticeLadder({
  lang,
  error,
  activeLevel,
  phase,
  state,
  ayahAudio,
  passScore,
  onRecord,
  onStop,
  onSelfCheck,
}: {
  lang: Lang;
  error: TajweedError;
  /** The rung currently being recorded on THIS card, or null. */
  activeLevel: number | null;
  phase: "recording" | "checking" | null;
  state: RungState;
  /** Whole-ayah recitation URL, resolved from the reciter the learner chose. */
  ayahAudio: string;
  /** The mark a scored rung must clear. Sent by the server, never hard-coded. */
  passScore: number;
  onRecord: (error: TajweedError, rung: PracticeRung) => void;
  onStop: () => void;
  /** A `self` rung the learner says they have done. */
  onSelfCheck: (error: TajweedError, rung: PracticeRung) => void;
}) {
  const rungs = error.practice ?? [];
  if (rungs.length === 0) return null;

  // Open rungs: the first uncleared one, everything before it, and anything
  // already cleared. Never more — see the note on ordering above.
  const firstOpen =
    rungs.find((r) => !state.done.includes(r.level))?.level ??
    rungs[rungs.length - 1].level;

  return (
    <section className="ladder">
      <p className="ladder__title">{t(lang, "card_practice")}</p>
      <ol className="ladder__list">
        {rungs.map((rung) => (
          <Rung
            key={rung.level}
            lang={lang}
            error={error}
            rung={rung}
            busy={activeLevel === rung.level}
            phase={phase}
            locked={rung.level > firstOpen}
            done={state.done.includes(rung.level)}
            failed={state.failed === rung.level}
            score={state.failed === rung.level ? state.score : null}
            passScore={passScore}
            ayahAudio={ayahAudio}
            anyBusy={activeLevel !== null}
            onRecord={onRecord}
            onStop={onStop}
            onSelfCheck={onSelfCheck}
          />
        ))}
      </ol>
    </section>
  );
}

function Rung({
  lang,
  error,
  rung,
  busy,
  phase,
  locked,
  done,
  failed,
  score,
  passScore,
  ayahAudio,
  anyBusy,
  onRecord,
  onStop,
  onSelfCheck,
}: {
  lang: Lang;
  error: TajweedError;
  rung: PracticeRung;
  busy: boolean;
  phase: "recording" | "checking" | null;
  locked: boolean;
  done: boolean;
  failed: boolean;
  score: number | null;
  passScore: number;
  ayahAudio: string;
  anyBusy: boolean;
  onRecord: (error: TajweedError, rung: PracticeRung) => void;
  onStop: () => void;
  onSelfCheck: (error: TajweedError, rung: PracticeRung) => void;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  // The server names the SOURCE for ayah audio rather than the URL, because the
  // URL depends on the reciter the learner picked and the server does not hold
  // that choice.
  const src = rung.audio_source === "ayah" ? ayahAudio : rung.audio;

  function play(rate: number) {
    const a = audioRef.current;
    if (!a) return;
    a.pause();
    a.currentTime = 0;
    a.playbackRate = rate;
    a.play().catch(() => {});
  }

  return (
    <li
      className={[
        "rung",
        busy ? "rung--live" : "",
        locked ? "rung--locked" : "",
        done ? "rung--done" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      value={rung.level}
      aria-disabled={locked}
    >
      <div className="rung__head">
        <span className="rung__name">{t(lang, FOCUS_KEY[rung.focus])}</span>
        {done && (
          <span className="rung__tick" aria-label={t(lang, "rung_done")}>
            ✓
          </span>
        )}
      </div>

      {/* The thing to say. Arabic at a size you can actually copy — a letter
          shown at body size teaches nothing about where the tongue goes. The
          ayah rung has no items: it is on screen above, and reprinting it here
          would be the whole-ayah wall this design exists to remove. */}
      {rung.items.length > 0 && (
        <p className="rung__items" dir="rtl" lang="ar">
          {rung.items.map((item, i) => (
            <span key={`${item}-${i}`} className="rung__item">
              {item}
            </span>
          ))}
        </p>
      )}

      {locked ? (
        <span className="rung__say rung__say--locked">
          {t(lang, "rung_locked")}
        </span>
      ) : (
        <div className="rung__actions">
          {/* LISTEN, at both speeds — but only where there is something to
              play. `src` empty means no recording exists for this rung and no
              button is drawn, rather than one that fails silently. */}
          {src && (
            <>
              <button
                className="rung__btn rung__btn--quiet"
                onClick={(ev) => {
                  ev.stopPropagation();
                  play(1);
                }}
              >
                <Play />
                {t(lang, "listen_normal")}
              </button>
              <button
                className="rung__btn rung__btn--quiet"
                onClick={(ev) => {
                  ev.stopPropagation();
                  play(SLOW_RATE);
                }}
              >
                <Play />
                {t(lang, "listen_slow")}
              </button>
              <audio ref={audioRef} src={src} preload="none" />
            </>
          )}

          {/* PRACTISE AND RE-CHECK. One control, because they are one act. */}
          {rung.recordable ? (
            <button
              className={busy ? "rung__btn rung__btn--live" : "rung__btn"}
              // Only one rung records at a time, anywhere on the page.
              disabled={anyBusy && !busy}
              onClick={(ev) => {
                ev.stopPropagation();
                busy ? onStop() : onRecord(error, rung);
              }}
            >
              {busy
                ? phase === "checking"
                  ? t(lang, "retry_checking")
                  : t(lang, "retry_word_stop")
                : t(lang, done ? "rung_again" : "rung_record")}
            </button>
          ) : (
            // A `self` rung. It still gates the next one, so it needs a way to
            // be cleared — and that way must not look like a score.
            <button
              className="rung__btn rung__btn--self"
              disabled={anyBusy}
              onClick={(ev) => {
                ev.stopPropagation();
                onSelfCheck(error, rung);
              }}
            >
              {t(lang, done ? "rung_said_again" : "rung_said")}
            </button>
          )}
        </div>
      )}

      {/* Not scolding, and not a grade. One line saying the re-read still had
          the same mistake in it, with the number that decided so — because a
          learner told "not yet" with no figure cannot tell whether they were
          close. */}
      {failed && !busy && (
        <p className="rung__verdict">
          {t(lang, "not_yet")}
          {score !== null && (
            <span className="rung__score">
              {" "}
              {Math.round(score * 100)}% · {t(lang, "rung_need")}{" "}
              {Math.round(passScore * 100)}%
            </span>
          )}
        </p>
      )}
    </li>
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
