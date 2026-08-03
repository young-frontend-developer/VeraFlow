import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Segment } from "../lib/api";

type Mode = "still" | "listening" | "waiting";

/** One letter to mark, tied back to the card that explains it. */
export type Mark = {
  /** Unit index from the engine. */
  at: number;
  /** Which card this belongs to — the key Feedback renders its cards under. */
  cardId: string;
  /** The letter itself, for the tap target's accessible name. */
  letter: string;
};

type Props = {
  uthmani: string;
  segments: Segment[];
  /**
   * EVERY errored letter, not just the first. One entry per occurrence, so a
   * letter mispronounced four times is marked in all four places even though
   * the learner reads one merged card.
   */
  marks?: Mark[];
  /** The card currently being read — its letters are drawn stronger. */
  activeCardId?: string | null;
  /** Tapping a marked letter asks the page to scroll to its card. */
  onPick?: (cardId: string) => void;
  mode?: Mode;
};

type Box = { left: number; top: number; width: number; height: number };
/**
 * One marked letter, in TWO coordinate spaces — they are not the same box and
 * conflating them is what put a second, offset copy of the whole ayah on screen.
 *
 *   left/top      relative to the container's PADDING box, where absolutely
 *                 positioned children are placed. Used for the tap target.
 *   clipLeft/Top  relative to the TEXT box, which sits inside the container's
 *                 padding. Used for the clip, because the clipped copy is
 *                 positioned over the text, not over the container.
 */
type Hit = Box & {
  cardId: string;
  letter: string;
  clipLeft: number;
  clipTop: number;
};

/**
 * The ayah, set as one unbroken text node.
 *
 * Arabic is cursive: wrapping letter-groups in their own elements to colour one
 * of them breaks the joining forms and the word visibly falls apart. So the
 * text is never split.
 *
 * HOW A LETTER IS TURNED RED WITHOUT SPLITTING IT. The whole ayah is painted a
 * second time, in red, directly on top of itself, and that red copy is clipped
 * to the rectangles the errored letters occupy. Identical text, identical
 * position, identical shaping — so the joining forms are the original's and
 * only the clipped letters show through. That is what makes this red ON THE
 * GLYPH rather than a highlight behind it: there is no fill, just the letter in
 * another colour.
 *
 * The alternative — a coloured box under the text — was the previous behaviour
 * and reads as a marker pen over a mistake, which is the tone this app avoids.
 *
 * Remeasured on resize and after the Arabic webfont loads: measuring against a
 * fallback face would clip the wrong letters.
 */
export default function AyahText({
  uthmani,
  segments,
  marks = [],
  activeCardId = null,
  onPick,
  mode = "still",
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  const [hits, setHits] = useState<Hit[]>([]);
  /** Where the text sits inside the container, so the red copy lands on it. */
  const [textBox, setTextBox] = useState<Box | null>(null);

  // Marks change identity on every render otherwise, which would remeasure on
  // every parent update.
  const key = marks.map((m) => `${m.at}:${m.cardId}`).join("|");

  const measure = useCallback(() => {
    const host = hostRef.current;
    const span = textRef.current;
    const node = span?.firstChild;
    if (!host || !span || !node || marks.length === 0) {
      setHits([]);
      setTextBox(null);
      return;
    }
    // Absolutely positioned children are placed against the PADDING box, not
    // the border box that getBoundingClientRect reports. `.ayah` has a 1px
    // border and 2.4rem of top padding, so using the border box put every
    // overlay a border-width out and — far worse — made the red copy's own
    // text start at the top of the padding instead of where the real text is.
    const hostBox = host.getBoundingClientRect();
    const padLeft = hostBox.left + host.clientLeft;
    const padTop = hostBox.top + host.clientTop;

    const tb = span.getBoundingClientRect();
    setTextBox({
      left: tb.left - padLeft,
      top: tb.top - padTop,
      width: tb.width,
      height: tb.height,
    });

    const next: Hit[] = [];
    // SEVERAL ERRORS CAN SHARE ONE LETTER-GROUP. A segment covers a whole
    // group, so two errors on different units inside it measure to the SAME
    // rectangle — and stacking identical absolutely-positioned buttons means
    // the topmost one swallows every tap meant for the others. Keyed by
    // geometry, first writer wins: the letter is painted once and one card
    // owns the tap. Found by driving a real recitation; both the paint and the
    // hit layer were duplicated 17 times over 10 distinct letters.
    const seen = new Set<string>();

    for (const mark of marks) {
      const seg = segments.find((s) => s.units.includes(mark.at));
      if (!seg) continue;
      const range = document.createRange();
      try {
        range.setStart(node, seg.start);
        range.setEnd(node, seg.end);
      } catch {
        continue; // offsets outside the node; nothing to point at
      }
      for (const r of Array.from(range.getClientRects())) {
        if (r.width <= 0.5) continue;
        const left = r.left - padLeft;
        const top = r.top - padTop;
        const key = `${Math.round(left)}:${Math.round(top)}:${Math.round(
          r.width,
        )}:${Math.round(r.height)}`;
        if (seen.has(key)) continue;
        seen.add(key);
        next.push({
          cardId: mark.cardId,
          letter: mark.letter,
          left,
          top,
          width: r.width,
          height: r.height,
          clipLeft: r.left - tb.left,
          clipTop: r.top - tb.top,
        });
      }
      range.detach?.();
    }
    setHits(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, segments, uthmani]);

  useLayoutEffect(() => {
    measure();
    const host = hostRef.current;
    if (!host) return;
    const ro = new ResizeObserver(measure);
    ro.observe(host);
    // Webfonts land after first paint; a clip measured against Georgia would
    // expose the wrong letters.
    document.fonts?.ready.then(measure).catch(() => {});
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [measure]);

  // Nothing here depends on activeCardId: it changes colour, not geometry, so
  // remeasuring on it would be wasted work on every card tap.

  return (
    <div className="ayah" ref={hostRef}>
      <span className="ayah__text" dir="rtl" lang="ar" ref={textRef}>
        {uthmani}
      </span>

      {/*
        The red layer. One absolutely-positioned copy per rectangle, each
        clipped to just that rectangle, so several letters can be red at once
        and each can carry its own strength. aria-hidden throughout: this is the
        same text again, and a screen reader must not read the ayah twice.
      */}
      {textBox &&
        hits.map((b, i) => (
          <span
            key={`${b.cardId}-${i}`}
            className={
              activeCardId === b.cardId
                ? "ayah__mark ayah__mark--active"
                : "ayah__mark"
            }
            aria-hidden="true"
            style={{
              // Sized and placed to sit exactly on the real text, so the copy
              // wraps identically and every glyph lands on its original.
              left: textBox.left,
              top: textBox.top,
              width: textBox.width,
              // Clip coordinates are in THIS element's space, hence clipLeft /
              // clipTop rather than the container-relative left / top.
              clipPath: `polygon(${b.clipLeft}px ${b.clipTop}px, ${
                b.clipLeft + b.width
              }px ${b.clipTop}px, ${b.clipLeft + b.width}px ${
                b.clipTop + b.height
              }px, ${b.clipLeft}px ${b.clipTop + b.height}px)`,
            }}
          >
            <span className="ayah__text" dir="rtl" lang="ar">
              {uthmani}
            </span>
          </span>
        ))}

      {/*
        Tap targets, laid over the red letters. Separate from the paint layer,
        which is clipped to the glyph and so a poor thing to aim a finger at.

        EXACTLY the measured rectangle, with NO padding. Padding them out to a
        comfier size made neighbouring targets overlap, and on an ayah with
        errors on adjacent letters the overlap swallowed the taps entirely —
        the topmost box covered its neighbour's centre, so tapping a red letter
        either did nothing or opened the wrong card. A range rect already spans
        the full line box (line-height 2.35), so the honest rectangle is a
        comfortable target on its own.
      */}
      {onPick &&
        hits.map((b, i) => (
          <button
            key={`hit-${b.cardId}-${i}`}
            type="button"
            className="ayah__hit"
            style={{
              left: b.left,
              top: b.top,
              width: b.width,
              height: b.height,
            }}
            onClick={() => onPick(b.cardId)}
          >
            <span className="sr-only" lang="ar">
              {b.letter}
            </span>
          </button>
        ))}

      {mode !== "still" && (
        <span
          className={
            mode === "waiting" ? "ayah__sweep ayah__sweep--slow" : "ayah__sweep"
          }
          aria-hidden="true"
        />
      )}
    </div>
  );
}

/** Compact ayah line for list rows — no highlighting, no motion. */
export function AyahLine({ uthmani }: { uthmani: string }) {
  return (
    <span className="row__ar" dir="rtl" lang="ar">
      {uthmani}
    </span>
  );
}
