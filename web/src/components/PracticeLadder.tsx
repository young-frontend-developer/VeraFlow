import { useRef } from "react";
import { PracticeRung, TajweedError } from "../lib/api";
import { Key, Lang, t } from "../lib/i18n";

/**
 * The practice section of a correction card — slot 4 of 4.
 *
 * WHAT IT REPLACES. Practice was a disclosure containing a paragraph of prose
 * about practising ("say ذَ ten times in front of a mirror…") and a button that
 * re-recorded the whole word. Reading a description of an exercise is not
 * doing one, and the ayah is the TEST, not the drill.
 *
 * So the ladder is climbed, not read. Four rungs, narrow to wide — the letter
 * alone, the letter under each haraka, the word they actually misread, then
 * back to the ayah. The learner meets the sound by itself before meeting it
 * inside anything, which is how a teacher would introduce it.
 *
 * THE RECORD BUTTON APPEARS ONLY WHERE THE ENGINE CAN ACTUALLY SCORE. Rungs 1
 * and 2 are listen-and-say: there is no target for a bare letter, and a button
 * that cannot check what it claims to check is worse than no button. `rung
 * .recordable` is the server saying which rungs it can judge, and this
 * component never second-guesses it.
 */

/** focus -> the i18n key naming that rung. */
const FOCUS_KEY: Record<PracticeRung["focus"], Key> = {
  letter: "rung_letter",
  syllables: "rung_syllables",
  word: "rung_word",
  ayah: "rung_ayah",
};

export default function PracticeLadder({
  lang,
  error,
  /** The rung currently being recorded on THIS card, or null. */
  activeLevel,
  phase,
  letterAudio,
  onRecord,
  onStop,
}: {
  lang: Lang;
  error: TajweedError;
  activeLevel: number | null;
  phase: "recording" | "checking" | null;
  /**
   * The isolated letter-pair recording, or "" when no file exists. Empty is
   * the signal to render NO control — see api.letterAudioUrl.
   */
  letterAudio: string;
  onRecord: (error: TajweedError, rung: PracticeRung) => void;
  onStop: () => void;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const rungs = error.practice ?? [];
  if (rungs.length === 0) return null;

  return (
    <section className="ladder">
      <p className="ladder__title">{t(lang, "card_practice")}</p>
      <ol className="ladder__list">
        {rungs.map((rung) => {
          const busy = activeLevel === rung.level;
          return (
            <li
              key={rung.level}
              className={busy ? "rung rung--live" : "rung"}
              // Not a step counter with its own numbers — `level` is already
              // 1-based and gapless from the server, and a madd error whose
              // syllable rung is skipped must still read 1, 2, 3.
              value={rung.level}
            >
              <div className="rung__head">
                <span className="rung__name">{t(lang, FOCUS_KEY[rung.focus])}</span>
              </div>

              {/* The thing to say. Arabic at a size you can actually copy —
                  a letter shown at body size teaches nothing about where the
                  tongue goes. The ayah rung has no items: it is on screen
                  above, and reprinting it here would be the whole-ayah wall
                  this redesign exists to remove. */}
              {rung.items.length > 0 && (
                <p className="rung__items" dir="rtl" lang="ar">
                  {rung.items.map((item, i) => (
                    <span key={`${item}-${i}`} className="rung__item">
                      {item}
                    </span>
                  ))}
                </p>
              )}

              {rung.recordable ? (
                <button
                  className={busy ? "rung__btn rung__btn--live" : "rung__btn"}
                  // Only one rung records at a time, anywhere on the page.
                  disabled={phase === "checking" && !busy}
                  onClick={(ev) => {
                    ev.stopPropagation();
                    busy ? onStop() : onRecord(error, rung);
                  }}
                >
                  {busy
                    ? phase === "checking"
                      ? t(lang, "retry_checking")
                      : t(lang, "retry_word_stop")
                    : t(lang, "rung_record")}
                </button>
              ) : rung.focus === "letter" && letterAudio ? (
                // THE ONE PLACE LETTER AUDIO BELONGS: next to the letter
                // itself, on the rung that asks the learner to say it. It used
                // to sit at the bottom of a collapsed "practice" disclosure,
                // three taps from the sound it plays.
                <button
                  className="rung__btn rung__btn--quiet"
                  onClick={(ev) => {
                    ev.stopPropagation();
                    audioRef.current?.play().catch(() => {});
                  }}
                >
                  <Play />
                  {t(lang, "listen_letter")}
                </button>
              ) : (
                // Says what to do rather than leaving the rung looking broken
                // next to its neighbours' buttons.
                <span className="rung__say">{t(lang, "rung_say")}</span>
              )}
            </li>
          );
        })}
      </ol>
      {letterAudio && (
        <audio ref={audioRef} src={letterAudio} preload="none" />
      )}
    </section>
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
