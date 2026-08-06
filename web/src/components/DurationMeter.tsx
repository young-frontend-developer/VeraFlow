import { useEffect, useRef, useState } from "react";
import { Lang, t } from "../lib/i18n";

/**
 * RULE 11 — how long it should have been, as a LENGTH rather than as a number.
 *
 *     Kerak:  آ ══════  6 harakat
 *     Siz:    آ══       ≈2 harakat
 *
 * "You held it for 2 counts instead of 6" is a sentence a learner has to
 * convert into a duration before it means anything, and duration is precisely
 * the thing they got wrong. Two bars of different lengths need no conversion:
 * the gap IS the mistake, drawn at the size of the mistake.
 *
 * THE COUNTER IS THE PART THAT TEACHES. Reading "6 harakat" does not tell you
 * how fast a haraka is — it is a relative unit, roughly the time to say one
 * short vowel, and a beginner has no reference for it. So the bar can be
 * PLAYED: tapping it counts out the target at a steady beat and fills the bar
 * in time with the count, which is the same thing a teacher does with their
 * hand. The learner holds along with it.
 *
 * ≈ ON THE HEARD SIDE IS DELIBERATE. The engine measures run length in phoneme
 * units, not in milliseconds, so "2" is a count of units and not a stopwatch
 * reading. Printing it as an exact number would claim a precision the
 * measurement does not have.
 */

/** One haraka, in milliseconds, at the unhurried pace a teacher counts. */
const BEAT_MS = 600;

export default function DurationMeter({
  lang,
  letter,
  expected,
  heard,
}: {
  lang: Lang;
  /** The letter being held, drawn at the head of each bar. */
  letter: string;
  /** Harakat the reference calls for, and what we heard. */
  expected: number;
  heard: number;
}) {
  const [beat, setBeat] = useState(0);
  const timer = useRef<number | null>(null);

  // Stop counting if the card unmounts mid-count, or the interval outlives the
  // component and keeps setting state on a dead node.
  useEffect(
    () => () => {
      if (timer.current !== null) window.clearInterval(timer.current);
    },
    [],
  );

  if (expected <= 0 || heard <= 0) return null;

  function count() {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
      timer.current = null;
      setBeat(0);
      return;
    }
    setBeat(1);
    timer.current = window.setInterval(() => {
      setBeat((n) => {
        if (n >= expected) {
          if (timer.current !== null) window.clearInterval(timer.current);
          timer.current = null;
          return 0;
        }
        return n + 1;
      });
    }, BEAT_MS);
  }

  const counting = beat > 0;
  // The bars share one scale so their lengths are comparable — the whole point
  // of drawing them. Whichever is longer sets it.
  const scale = Math.max(expected, heard);

  return (
    <div className="meter">
      <Bar
        lang={lang}
        label={t(lang, "meter_needed")}
        letter={letter}
        count={expected}
        scale={scale}
        filled={counting ? beat : expected}
        tone="good"
      />
      <Bar
        lang={lang}
        label={t(lang, "meter_yours")}
        letter={letter}
        count={heard}
        scale={scale}
        filled={heard}
        tone="said"
        approximate
      />
      <button className="meter__count" onClick={count}>
        {counting
          ? `${beat} / ${expected}`
          : `${t(lang, "meter_count_with_me")} 1 … ${expected}`}
      </button>
    </div>
  );
}

function Bar({
  lang,
  label,
  letter,
  count,
  scale,
  filled,
  tone,
  approximate = false,
}: {
  lang: Lang;
  label: string;
  letter: string;
  count: number;
  scale: number;
  /** Segments actually lit, so the counter can fill the target bar in time. */
  filled: number;
  tone: "good" | "said";
  approximate?: boolean;
}) {
  return (
    <p className="meter__row">
      <span className="meter__label">{label}</span>
      <span className="meter__letter" dir="rtl" lang="ar">
        {letter}
      </span>
      <span className="meter__track" aria-hidden="true">
        {Array.from({ length: scale }, (_, i) => (
          <span
            key={i}
            className={[
              "meter__tick",
              i < count ? `meter__tick--${tone}` : "meter__tick--empty",
              i < filled && i < count ? "meter__tick--lit" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          />
        ))}
      </span>
      <span className="meter__count-text">
        {approximate ? "≈" : ""}
        {count} {t(lang, "harakat")}
      </span>
    </p>
  );
}
