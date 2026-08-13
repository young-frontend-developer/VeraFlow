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
  /**
   * EXACT Uthmani character range for this sound, when the server could derive
   * one. Preferred over the segment because a segment is a letter-GROUP: for a
   * madd it is the consonant plus its lengthening mark, so marking it lit up
   * «صَـٰ» entire while the card said "2 harakat kerak" about the ـٰ alone.
   *
   * Falls back to the segment when absent, which is how attempts recorded
   * before this existed still mark anything at all.
   */
  span?: [number, number];
  /**
   * A short note pinned to this mark — "2 harakat kerak". Attached to the
   * highlight rather than left in the card, so the instruction and the thing
   * it is about are in the same place.
   */
  note?: string;
};

/**
 * One rule's territory on the text, for colouring the GLYPHS it governs.
 *
 * WHY THIS IS NOT A Mark. A mark says "you got this wrong" and belongs to a
 * card; this says "this ruling applies here" and is true of the ayah whether or
 * not anyone has recited it — the same distinction rule_presence draws against
 * the error registry. They share the paint mechanism and nothing else.
 */
export type RuleSpan = {
  /** RULE_MADD_LOZIM etc. Only used as a React key and for debugging. */
  code: string;
  /** One of the eight: pink | dark-pink | orange-red | orange | green | gray | dark | blue. */
  color: string;
  /** Uthmani character ranges, from the server. EMPTY means "not placed". */
  spans: [number, number][];
};

type Props = {
  uthmani: string;
  segments: Segment[];
  /**
   * The rules governing this text, coloured onto the glyphs themselves.
   *
   * Drawn UNDER the error marks, deliberately. A learner looking at a result
   * needs the mistake to win the eye; the rule colour is the standing fact
   * behind it. Where a rule and an error cover the same letter, the letter
   * reads as the error and the rule colour is simply not visible there — which
   * is correct, because at that moment the mistake is the more urgent thing.
   */
  rules?: RuleSpan[];
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
  note?: string;
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
/** A painted rule rectangle: same geometry as a Hit, no card and no tap. */
type RuleHit = Box & { code: string; color: string; clipLeft: number; clipTop: number };

export default function AyahText({
  uthmani,
  segments,
  marks = [],
  rules = [],
  activeCardId = null,
  onPick,
  mode = "still",
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  const [hits, setHits] = useState<Hit[]>([]);
  const [ruleHits, setRuleHits] = useState<RuleHit[]>([]);
  /** Where the text sits inside the container, so the red copy lands on it. */
  const [textBox, setTextBox] = useState<Box | null>(null);

  // Marks change identity on every render otherwise, which would remeasure on
  // every parent update.
  const key = marks.map((m) => `${m.at}:${m.cardId}`).join("|");
  const ruleKey = rules
    .map((r) => `${r.code}:${r.spans.map((s) => s.join("-")).join(",")}`)
    .join("|");

  const measure = useCallback(() => {
    const host = hostRef.current;
    const span = textRef.current;
    const node = span?.firstChild;
    // Rules alone are enough to need a measurement now: an ayah with no
    // mistakes still colours its rulings, which is the whole point of them
    // being facts about the text rather than about the recitation.
    if (!host || !span || !node || (marks.length === 0 && rules.length === 0)) {
      setHits([]);
      setRuleHits([]);
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

    /** Client rects for one character range of the text node. */
    const rectsFor = (from: number, to: number): DOMRect[] => {
      if (to <= from) return [];
      const range = document.createRange();
      try {
        range.setStart(node, from);
        range.setEnd(node, to);
      } catch {
        return []; // offsets outside the node; nothing to point at
      }
      const out = Array.from(range.getClientRects()).filter(
        (r) => r.width > 0.5,
      );
      range.detach?.();
      return out;
    };

    // ── the rule layer, measured first because it is drawn first ──────────
    const nextRules: RuleHit[] = [];
    const ruleSeen = new Set<string>();
    for (const rule of rules) {
      for (const [from, to] of rule.spans) {
        for (const r of rectsFor(from, to)) {
          // Two rules CAN legitimately cover one letter — the نَّ of ٱلنَّاسِ is
          // both an idgham and a ghunna — and painting both stacks two
          // translucent copies into a muddier third colour. First writer wins,
          // which is `rules` order, which is the server's sorted order: stable
          // across renders, so a letter does not change colour on a resize.
          const key = `${Math.round(r.left)}:${Math.round(r.top)}:${Math.round(
            r.width,
          )}`;
          if (ruleSeen.has(key)) continue;
          ruleSeen.add(key);
          nextRules.push({
            code: rule.code,
            color: rule.color,
            left: r.left - padLeft,
            top: r.top - padTop,
            width: r.width,
            height: r.height,
            clipLeft: r.left - tb.left,
            clipTop: r.top - tb.top,
          });
        }
      }
    }
    setRuleHits(nextRules);

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
      // THE SPAN WINS WHERE THERE IS ONE. It is the sound; the segment is the
      // letter-group the sound sits in, which for a madd is one character too
      // wide and marks the consonant the instruction is not about.
      const seg = segments.find((s) => s.units.includes(mark.at));
      const from = mark.span?.[0] ?? seg?.start;
      const to = mark.span?.[1] ?? seg?.end;
      if (from === undefined || to === undefined) continue;
      for (const r of rectsFor(from, to)) {
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
          note: mark.note,
          left,
          top,
          width: r.width,
          height: r.height,
          clipLeft: r.left - tb.left,
          clipTop: r.top - tb.top,
        });
      }
    }
    setHits(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, ruleKey, segments, uthmani]);

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
        THE RULE LAYER, under everything. Same mechanism as the red layer
        below — the whole ayah painted again and clipped to one rectangle — so
        the colour is ON THE GLYPH and the cursive joining is the original's.
        A coloured box behind the text would read as a highlighter, which is
        the tone this app avoids, and on Arabic it would also sit under the
        letters it is meant to identify rather than on them.

        FIRST IN THE DOM, so the error marks paint over it. A rule colour and
        an error on the same letter is not a conflict to resolve — the mistake
        wins the eye and the rule is still named in the strip below.
      */}
      {textBox &&
        // PAINTED IN REVERSE PRIORITY ORDER, so the highest-priority rule ends
        // up LAST in the DOM and therefore on top.
        //
        // The geometry dedupe above only protects IDENTICAL rectangles, and the
        // contested case is not identical — it is NESTED. On الٓمٓ the madd
        // lozim covers لٓمٓ and the ghunna covers مٓ inside it, two different
        // widths, so both survive dedupe and the later one simply paints over
        // the earlier. Painted in array order that made the winner "whichever
        // sorted last", which is not a decision. Reversed, it is the priority
        // in Recite.rulePriority.
        //
        // Caught in a screenshot: green was in the DOM with the right colour
        // and the right clip, and no green pixel reached the screen.
        ruleHits
          .slice()
          .reverse()
          .map((b, i) => (
          <span
            key={`${b.code}-${i}`}
            className={`ayah__rule ayah__rule--${b.color}`}
            aria-hidden="true"
            style={{
              left: textBox.left,
              top: textBox.top,
              width: textBox.width,
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

      {/*
        RULE 2's other half: the requirement is not only that the right glyph
        turns red, but that the instruction is attached TO it. "2 harakat
        kerak" sitting in a card three inches below the word is a fact the
        learner has to carry; sitting on the mark, it is a label.

        Rendered only for marks that carry a note — duration errors — so an
        ordinary substitution stays a clean red letter with nothing hanging
        off it.
      */}
      {hits.map((b, i) =>
        b.note ? (
          <span
            key={`note-${b.cardId}-${i}`}
            className={
              activeCardId === b.cardId
                ? "ayah__note ayah__note--active"
                : "ayah__note"
            }
            aria-hidden="true"
            style={{ left: b.left + b.width / 2, top: b.top + b.height }}
          >
            {b.note}
          </span>
        ) : null,
      )}

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
