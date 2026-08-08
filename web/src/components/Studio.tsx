import { useEffect, useRef, useState } from "react";
import { Lang, t } from "../lib/i18n";
import { Mic, Stop } from "./Ornament";

/**
 * THE ONE DARK MOMENT IN THE APP.
 *
 * Every other surface is warm ivory. This card is deep navy, and it exists for
 * exactly as long as the learner is reciting or waiting for the result. They
 * enter it to recite and come straight back out to the light. That is what
 * makes it read as a moment of focus rather than as a second theme — and it is
 * why the palette is not reused anywhere, not even for a "listening" hint.
 *
 * THE WAVEFORM IS A LEVEL METER, NOT DECORATION. Bars are driven by the real
 * microphone level at animation-frame rate, and they are FLAT when nothing is
 * being recorded. An idle waveform that animates anyway is a lie about whether
 * the app can hear you, and it is the single most common thing this component
 * could get wrong.
 *
 * NO RED, EVER. Recording does not turn the button red and analysing does not
 * turn it amber-warning. A person reciting the Quran is not in an error state.
 * The button gains a slow pulse ring while live and a slow breath while
 * thinking; nothing shifts hue.
 *
 * THE ANALYSING STATE IS DESIGNED FOR FIFTEEN-PLUS SECONDS. Inference runs
 * about ten times realtime. A generic spinner at that length reads as a hang,
 * so the wait gets a slow glow on the button the learner already has their eye
 * on, plus a second line of copy that says the wait is expected.
 */

/** How many bars the meter draws. Odd, so there is a true centre. */
const BARS = 41;

export type StudioPhase = "idle" | "recording" | "analyzing";

export default function Studio({
  lang,
  phase,
  elapsed,
  /** 0–1 live microphone level. Ignored unless recording. */
  level,
  /** Duration of the learner's previous session, in seconds. 0 to omit. */
  lastSeconds,
  /** Accuracy of the previous attempt, 0–1. Null to omit — never invent one. */
  lastScore,
  disabled,
  longWait,
  pinned = true,
  onStart,
  onStop,
}: {
  lang: Lang;
  phase: StudioPhase;
  elapsed: number;
  level: () => number;
  lastSeconds: number;
  lastScore: number | null;
  disabled?: boolean;
  /** This range is long enough that the wait needs naming. See the copy below. */
  longWait?: boolean;
  /**
   * Fixed to the viewport. True while recording is the screen's job; false
   * once a result is on screen, so this card stops covering the feedback.
   */
  pinned?: boolean;
  onStart: () => void;
  onStop: () => void;
}) {
  const live = phase === "recording";
  const thinking = phase === "analyzing";

  /**
   * PINNED TO THE VIEWPORT WHILE IN USE.
   *
   * An ayah can be a screen and a half of Arabic, and the mic sat underneath
   * all of it — so on anything longer than about four lines the control the
   * whole screen exists for was below the fold, and reciting began with a
   * scroll hunt. While recording or analysing it is worse: the state of the
   * thing you are doing is off-screen.
   *
   * So the card fixes itself to the bottom of the viewport. It is a
   * SCREEN-LOCAL element and deliberately NOT merged into the global tab bar —
   * that bar navigates between screens and this button records; putting a
   * destructive-feeling stop control into the navigation chrome would be a
   * category error. It sits above the bar, clear of it, and the page reserves
   * room so the last card never hides underneath.
   */
  return (
    <section className={`studio${pinned ? " studio--pinned" : ""}`}>
      <p className="studio__head">
        {live
          ? t(lang, "studio_live")
          : thinking
            ? t(lang, "studio_thinking")
            : t(lang, "studio_ready")}
      </p>

      <Waveform live={live} level={level} />

      <div className="studio__rule" />

      {/* Real numbers only. A stat with nothing behind it is omitted rather
          than shown as a dash — an empty slot invites someone to fill it with
          a fabricated figure later. */}
      {(lastSeconds > 0 || lastScore !== null) && (
        <div className="studio__stats">
          {lastSeconds > 0 && (
            <div>
              <span className="studio__stat-label">{t(lang, "studio_last")}</span>
              <span className="studio__stat-value">{mmss(lastSeconds)}</span>
            </div>
          )}
          {lastScore !== null && (
            <div>
              <span className="studio__stat-label">
                {t(lang, "studio_accuracy")}
              </span>
              <span className="studio__stat-value">
                {Math.round(lastScore * 100)}%
              </span>
            </div>
          )}
        </div>
      )}

      <div className="studio__control">
        <button
          className={[
            "mic",
            live ? "mic--live" : "",
            thinking ? "mic--thinking" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          disabled={disabled || thinking}
          onClick={live ? onStop : onStart}
          aria-label={live ? t(lang, "stop") : t(lang, "record")}
        >
          <span className="mic__ring" aria-hidden="true" />
          {live ? <Stop /> : <Mic />}
        </button>

        {/* Two lines, always: what to do, then the calmer line underneath that
            takes the pressure off. "Take your time" is not filler here — the
            learner is about to be measured, and the second line is the only
            place the app says that being slow is fine. */}
        <div className="studio__copy">
          <p className="studio__primary">
            {live ? (
              <span className="studio__timer">{mmss(elapsed)}</span>
            ) : thinking ? (
              t(lang, "studio_thinking_primary")
            ) : (
              t(lang, "studio_idle_primary")
            )}
          </p>
          <p className="studio__secondary">
            {live
              ? t(lang, "studio_live_secondary")
              : thinking
                ? // A LONG AYAH GETS ITS OWN WAIT LINE. Inference runs about
                  // ten times realtime, so a two-minute recitation is a
                  // twenty-minute wait — and the generic "this takes a moment"
                  // copy, read at minute four, is indistinguishable from a
                  // hang. Naming the length is the difference between waiting
                  // and wondering whether it broke.
                  longWait
                  ? t(lang, "long_wait_note")
                  : t(lang, "studio_thinking_secondary")
                : t(lang, "studio_idle_secondary")}
          </p>
        </div>
      </div>
    </section>
  );
}

/**
 * The bars. Written straight to the DOM at frame rate rather than through
 * React state — this runs at 60fps and re-rendering 41 elements that often
 * would be the most expensive thing on the page for no benefit.
 *
 * The trace SCROLLS: each frame pushes the newest level onto the end and drops
 * the oldest, so the shape is a short history of the voice rather than 41 bars
 * jumping together. That is the difference between a waveform and an equaliser.
 */
function Waveform({ live, level }: { live: boolean; level: () => number }) {
  const host = useRef<HTMLDivElement>(null);
  const trace = useRef<number[]>(new Array(BARS).fill(0));
  const [, force] = useState(0);

  useEffect(() => {
    if (!live) {
      trace.current = new Array(BARS).fill(0);
      force((n) => n + 1);
      return;
    }
    let raf = 0;
    const tick = () => {
      trace.current.push(Math.min(1, Math.max(0, level())));
      trace.current.shift();
      const bars = host.current?.children;
      if (bars) {
        for (let i = 0; i < bars.length; i++) {
          const v = trace.current[i];
          // A floor of 3px so silence still reads as a line rather than as a
          // gap — the meter is present, it simply has nothing to show.
          (bars[i] as HTMLElement).style.height = `${3 + v * 52}px`;
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [live, level]);

  return (
    <div className="wave" ref={host} aria-hidden="true">
      {Array.from({ length: BARS }, (_, i) => (
        <span
          key={i}
          className={live ? "wave__bar" : "wave__bar wave__bar--idle"}
          style={{ height: 3 }}
        />
      ))}
    </div>
  );
}

const mmss = (s: number) =>
  `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
