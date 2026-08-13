import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { RuleLayer } from "../lib/rules";

/**
 * Arabic text with rule-coloured letters, and NO container of its own.
 *
 * WHY NOT AyahText. AyahText does this already, and it also draws a card —
 * `.ayah` has a border, a background, a blur and a shadow — plus tap targets,
 * duration notes and an active-card state, all of which belong to the results
 * screen. The reader shows the verse as bare text on the page; dropping the
 * results component into it would put a card box around every ayah and change
 * that screen's design in order to add a colour. So the MECHANISM is shared and
 * the chrome is not.
 *
 * THE MECHANISM. The text is painted a second time on top of itself in the rule
 * tone, and that copy is clipped to the rectangles the governed letters occupy.
 * Arabic is cursive: wrapping letters in their own elements to colour them
 * breaks the joining forms and the word visibly falls apart, so the text is
 * never split. Identical text, identical position, identical shaping — only the
 * clipped letters show through, and the colour is ON the glyph rather than a
 * highlight behind it.
 *
 * PAINT ORDER IS PRIORITY ORDER, REVERSED. `layers` arrives highest-priority
 * first (see lib/rules.ruleLayers) and is painted last-first, so the highest
 * priority ends up on top. This matters for NESTED spans, which is the common
 * case rather than the exotic one: on الٓمٓ the madd lozim covers لٓمٓ and the
 * ghunna covers مٓ inside it, and whichever paints later wins the overlap.
 *
 * Remeasured on resize and after the Arabic webfont loads — measuring against a
 * fallback face clips the wrong letters.
 */
type Rect = { left: number; top: number; width: number; height: number };
type Hit = Rect & { code: string; color: string };

export default function PaintedArabic({
  text,
  layers,
}: {
  text: string;
  layers: RuleLayer[];
}) {
  const wrapRef = useRef<HTMLSpanElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  const [hits, setHits] = useState<Hit[]>([]);

  const key = layers
    .map((l) => `${l.code}:${l.spans.map((s) => s.join("-")).join(",")}`)
    .join("|");

  const measure = useCallback(() => {
    const span = textRef.current;
    const node = span?.firstChild;
    if (!span || !node || layers.length === 0) {
      setHits([]);
      return;
    }
    const base = span.getBoundingClientRect();
    const next: Hit[] = [];
    const seen = new Set<string>();

    for (const layer of layers) {
      for (const [from, to] of layer.spans) {
        if (to <= from) continue;
        const range = document.createRange();
        try {
          range.setStart(node, from);
          range.setEnd(node, to);
        } catch {
          continue;
        }
        for (const r of Array.from(range.getClientRects())) {
          if (r.width <= 0.5) continue;
          // Identical rectangles: first writer wins, and `layers` is priority
          // ordered, so that is the higher-priority rule. Overlapping but
          // DIFFERENT rectangles are settled by paint order instead.
          const k = `${Math.round(r.left)}:${Math.round(r.top)}:${Math.round(r.width)}`;
          if (seen.has(k)) continue;
          seen.add(k);
          next.push({
            code: layer.code,
            color: layer.color,
            left: r.left - base.left,
            top: r.top - base.top,
            width: r.width,
            height: r.height,
          });
        }
        range.detach?.();
      }
    }
    setHits(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, text]);

  useLayoutEffect(() => {
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [measure]);

  useEffect(() => {
    document.fonts?.ready.then(measure).catch(() => {});
  }, [measure]);

  return (
    <span className="painted" ref={wrapRef}>
      <span className="painted__text" ref={textRef}>
        {text}
      </span>
      {hits
        .slice()
        .reverse()
        .map((h, i) => (
          // aria-hidden: this is the same text again, and a screen reader must
          // not read the ayah once per rule that occurs in it.
          <span
            key={`${h.code}-${i}`}
            className={`painted__layer ayah__rule--${h.color}`}
            aria-hidden="true"
            style={{
              clipPath: `polygon(${h.left}px ${h.top}px, ${h.left + h.width}px ${
                h.top
              }px, ${h.left + h.width}px ${h.top + h.height}px, ${h.left}px ${
                h.top + h.height
              }px)`,
            }}
          >
            {text}
          </span>
        ))}
    </span>
  );
}
