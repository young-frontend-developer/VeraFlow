import { useEffect, useRef, useState } from "react";
import { Lang, t } from "../lib/i18n";
import { Mic, Stop } from "./Ornament";

/**
 * THE RECORDING CONTROL. ONE OF THEM, EVERYWHERE.
 *
 * ══ WHAT THIS REPLACED ═════════════════════════════════════════════════════
 *
 * There were two. The reader's verse view had a bare disc floating on the
 * background with one label under it; the practice screen had a deep navy card
 * containing a header, a waveform, a stats row, and a SMALL disc laid out
 * horizontally beside two lines of copy. Same moment, same action, two designs
 * — and the boxed one made recitation look like a piece of equipment being
 * operated rather than something the learner does.
 *
 * The card is gone entirely. Its contents were not all furniture, so what was
 * load-bearing survives without it:
 *
 *   THE WAVEFORM STAYS, floating. It is a level meter, not decoration, and it
 *     is the only thing on screen that answers "can it hear me". It appears
 *     while recording and at no other time.
 *   THE TIMER STAYS, as the line under the disc, because a recitation being
 *     measured needs its length visible.
 *   THE STATS ROW IS GONE. "Last take: 0:14, 92%" belonged to the card's spare
 *     space, and the results screen says both properly a moment later.
 *   THE HEADER IS GONE. "YOZISHGA TAYYOR" over a mic is a caption for a
 *     control that is already unambiguous.
 *
 * ══ THE IDLE STATE IS THE CONTRACT ═════════════════════════════════════════
 *
 * Disc, then one label. Nothing else, no container, generous space around it.
 * That is what the reader shows and it is what the practice screen shows, from
 * the same component with the same props, so the two cannot drift apart again.
 * A second line of copy is added only once recording is under way, where it is
 * telling the learner something that is actually true at that moment.
 *
 * ══ NO RED, EVER ═══════════════════════════════════════════════════════════
 *
 * Recording does not turn the disc red and analysing does not turn it amber.
 * A person reciting the Qur'an is not in an error state. The disc gains a slow
 * pulse ring while live and a slow breath while thinking; nothing shifts hue.
 *
 * THE ANALYSING STATE IS DESIGNED FOR FIFTEEN-PLUS SECONDS. Inference runs
 * about ten times realtime. A generic spinner at that length reads as a hang,
 * so the wait gets a slow glow on the control the learner already has their eye
 * on, plus a line that says the wait is expected.
 */

/** How many bars the meter draws. Odd, so there is a true centre. */
const BARS = 41;

export type RecorderPhase = "idle" | "recording" | "analyzing";

export default function Recorder({
  lang,
  phase,
  elapsed,
  level,
  disabled,
  longWait,
  onStart,
  onStop,
}: {
  lang: Lang;
  phase: RecorderPhase;
  /** Seconds recorded so far. Ignored unless recording. */
  elapsed: number;
  /** 0–1 live microphone level. Ignored unless recording. */
  level: () => number;
  disabled?: boolean;
  /** This range is long enough that the wait needs naming. See the copy below. */
  longWait?: boolean;
  onStart: () => void;
  onStop: () => void;
}) {
  const live = phase === "recording";
  const thinking = phase === "analyzing";

  return (
    <section className="recorder">
      {/* Only while live. An idle meter that is drawn at all — even flat — is a
          row of ticks the learner has to work out the meaning of before they
          have done anything. */}
      {live && <Waveform level={level} />}

      <button
        className={[
          "mic",
          "recorder__mic",
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

      <p className="recorder__primary">
        {live ? (
          <span className="recorder__timer">{mmss(elapsed)}</span>
        ) : thinking ? (
          t(lang, "studio_thinking_primary")
        ) : (
          t(lang, "studio_idle_primary")
        )}
      </p>

      {/* The calmer line, and ONLY once there is something happening. At rest
          the control is a disc and a label, which is the whole point. */}
      {(live || thinking) && (
        <p className="recorder__secondary">
          {live
            ? t(lang, "studio_live_secondary")
            : // A LONG AYAH GETS ITS OWN WAIT LINE. Inference runs about ten
              // times realtime, so a two-minute recitation is a twenty-minute
              // wait — and the generic "this takes a moment" copy, read at
              // minute four, is indistinguishable from a hang. Naming the
              // length is the difference between waiting and wondering.
              longWait
              ? t(lang, "long_wait_note")
              : t(lang, "studio_thinking_secondary")}
        </p>
      )}
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
function Waveform({ level }: { level: () => number }) {
  const host = useRef<HTMLDivElement>(null);
  const trace = useRef<number[]>(new Array(BARS).fill(0));

  useEffect(() => {
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
          (bars[i] as HTMLElement).style.height = `${3 + v * 46}px`;
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [level]);

  return (
    <div className="wave" ref={host} aria-hidden="true">
      {Array.from({ length: BARS }, (_, i) => (
        <span key={i} className="wave__bar" style={{ height: 3 }} />
      ))}
    </div>
  );
}

const mmss = (s: number) =>
  `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

/**
 * The elapsed clock, shared by every screen that owns a recording.
 *
 * Four ticks a second rather than sixty: the waveform draws itself at frame
 * rate straight to the DOM, and this only has to keep a mm:ss readout honest.
 */
export function useElapsed(active: boolean, startedAt: number | undefined) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!active || !startedAt) return setElapsed(0);
    setElapsed((Date.now() - startedAt) / 1000);
    const id = window.setInterval(
      () => setElapsed((Date.now() - startedAt) / 1000),
      250,
    );
    return () => window.clearInterval(id);
  }, [active, startedAt]);
  return elapsed;
}
