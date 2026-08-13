import { useRef } from "react";
import { PracticeRung, TajweedError } from "../lib/api";
import { Key, Lang, t } from "../lib/i18n";
import DurationMeter from "./DurationMeter";

/**
 * The practice section of a correction card — slots 6, 7 and 8 of RULE 12's
 * canonical shape (listen, practise, re-check), which are one thing in the UI
 * because they are one thing to do: hear it, say it, prove it.
 *
 * ONE ACTION, NOT A LADDER — and the name is now historical. The server sends
 * exactly one rung: the affected word, with the thing to attend to named by its
 * focus (sound the letter you skipped / leave out the one you added / hold for
 * the count / say it as written). This component renders whatever arrives, so
 * it needed no change when four rungs became one.
 *
 * WHAT WAS REMOVED, AND WHY IT MATTERED:
 *
 *   letter, syllables   the bare sound and the sound under three harakat. Both
 *                       carried `check: "self"` because THE ENGINE HAS NO
 *                       TARGET FOR A BARE LETTER — the phonetizer works on
 *                       Quranic text and the model is trained on connected
 *                       recitation, so a 300 ms isolated consonant lands in the
 *                       muqatta'at collapse. The learner graded themselves on
 *                       the first thing they touched.
 *
 *   ayah                appended to EVERY card. Ten corrections meant ten whole
 *                       recitations, one per card — and card 2, fixed last,
 *                       still demanded the entire verse after cards 8, 5 and 1
 *                       had each already demanded it. Reciting the ayah is the
 *                       TEST; running the test after every correction is not
 *                       practice, it is nine redundant examinations.
 *
 * The full ayah is now requested ONCE, by Feedback.tsx, gated on there being no
 * open cards left. See engine/practice.ladder for the server half.
 *
 * Every rung that remains is `check: "score"` — recorded, transcribed and
 * diffed against a real target — because a word range of an ayah is exactly
 * what the engine can judge. The unlock machinery below is retained and inert:
 * with one rung there is nothing to lock, and removing it would be a rewrite of
 * a component that is currently correct.
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

/**
 * focus -> the i18n key naming that rung.
 *
 * Exhaustive by type: adding a focus on the server without a label here is a
 * compile error rather than a rung rendered with a blank name.
 */
const FOCUS_KEY: Record<PracticeRung["focus"], Key> = {
  letter: "rung_letter",
  syllables: "rung_syllables",
  word_include: "rung_word_include",
  word_omit: "rung_word_omit",
  word_hold: "rung_word_hold",
  word: "rung_word",
  ayah: "rung_ayah",
};

/** The three rungs that are a SLOW, deliberate first pass at the word. */
const SLOW_FOCUSES: PracticeRung["focus"][] = [
  "word_include",
  "word_omit",
  "word_hold",
];

/**
 * The label for one rung, in the context of the whole ladder.
 *
 * Only one rung needs the context: the plain `word` rung is "this word" when it
 * opens the word section, and "now at normal pace" when a slow pass at the SAME
 * word came before it. Without that, the omission, insertion and duration
 * ladders print the identical word twice under the identical label, which reads
 * as a rendering bug rather than as a second, faster pass.
 */
function labelFor(rung: PracticeRung, rungs: PracticeRung[]): Key {
  if (
    rung.focus === "word" &&
    rungs.some((r) => r.level < rung.level && SLOW_FOCUSES.includes(r.focus))
  ) {
    return "rung_word_normal";
  }
  return FOCUS_KEY[rung.focus];
}

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
            label={labelFor(rung, rungs)}
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
  label,
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
  /** Resolved by labelFor() — the plain `word` rung is renamed in context. */
  label: Key;
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
        <span className="rung__name">{t(lang, label)}</span>
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

      {/* THE COUNT, on the one rung that is about duration. "Hold it for 4
          harakat" is not actionable — a haraka is a relative unit and a
          beginner has no reference for it — so the rung carries the counter
          that beats it out, which is what a teacher does with their hand.
          countOnly: the needed-vs-yours comparison is already in the card body
          a few lines above, and repeating what they got wrong at the moment
          they are about to try again teaches nothing. */}
      {rung.focus === "word_hold" && rung.hold > 0 && !locked && (
        <DurationMeter
          lang={lang}
          letter={error.letter}
          expected={rung.hold}
          heard={0}
          countOnly
        />
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
