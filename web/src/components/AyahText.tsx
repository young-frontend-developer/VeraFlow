import { useLayoutEffect, useRef, useState } from "react";
import type { Segment } from "../lib/api";

type Mode = "still" | "listening" | "waiting";

type Props = {
  uthmani: string;
  segments: Segment[];
  /** Unit index of the error to point at, from the engine. */
  highlightUnit?: number | null;
  mode?: Mode;
};

type Box = { left: number; top: number; width: number; height: number };

/**
 * The ayah, set as one unbroken text node.
 *
 * Arabic is cursive: wrapping letter-groups in their own elements to colour one
 * of them breaks the joining forms and the word visibly falls apart. So the
 * text is never split. To point at a letter-group we measure a DOM Range over
 * the character offsets the server computed, and lay a lamp underneath the
 * rectangles it reports.
 *
 * Remeasured on resize and after the Arabic webfont loads — measuring against
 * a fallback face would put the lamp under the wrong letter.
 */
export default function AyahText({
  uthmani,
  segments,
  highlightUnit = null,
  mode = "still",
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  const [boxes, setBoxes] = useState<Box[]>([]);

  const target =
    highlightUnit === null
      ? null
      : segments.find((s) => s.units.includes(highlightUnit)) ?? null;

  useLayoutEffect(() => {
    const host = hostRef.current;
    const node = textRef.current?.firstChild;

    if (!target || !host || !node) {
      setBoxes([]);
      return;
    }

    const measure = () => {
      const text = textRef.current?.firstChild;
      if (!text || !hostRef.current) return;
      const range = document.createRange();
      try {
        range.setStart(text, target.start);
        range.setEnd(text, target.end);
      } catch {
        return; // offsets outside the node; nothing to point at
      }
      const origin = hostRef.current.getBoundingClientRect();
      const next = Array.from(range.getClientRects())
        .filter((r) => r.width > 0.5)
        .map((r) => ({
          left: r.left - origin.left,
          top: r.top - origin.top,
          width: r.width,
          height: r.height,
        }));
      range.detach?.();
      setBoxes(next);
    };

    measure();

    const ro = new ResizeObserver(measure);
    ro.observe(host);
    // Webfonts land after first paint; a lamp measured against Georgia would
    // sit under the wrong letters.
    document.fonts?.ready.then(measure).catch(() => {});
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [target, uthmani]);

  return (
    <div className="ayah" ref={hostRef}>
      {boxes.map((b, i) => (
        <span
          key={i}
          className="ayah__lamp"
          aria-hidden="true"
          style={{
            left: b.left - 3,
            top: b.top - 2,
            width: b.width + 6,
            height: b.height + 4,
          }}
        />
      ))}

      <span className="ayah__text" dir="rtl" lang="ar" ref={textRef}>
        {uthmani}
      </span>

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
