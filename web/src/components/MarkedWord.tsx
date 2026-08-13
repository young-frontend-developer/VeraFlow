import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

/**
 * One word with ONE letter inside it marked.
 *
 * WHY THIS EXISTS. A duration card names the letter in its meter — "Kerak: و —
 * 4 harakat" — and prints the word above it, and nothing connected the two. On
 * «يَقُولُونَ», which has two و, the learner had to guess which one the card
 * meant. The letter was named but never pointed at.
 *
 * WHY IT IS NOT `<span>`s. Arabic is cursive. Wrapping one letter of a word in
 * its own element to colour it breaks the joining forms and the word visibly
 * falls apart — «قَالَ» becomes three disconnected pieces. This is the same
 * constraint AyahText solves and it is solved the same way: the word is painted
 * a SECOND time on top of itself in the mark colour, and that copy is clipped
 * to the rectangle the target letter occupies. Identical text, identical
 * shaping, so the joining is the original's and only the clipped letter shows
 * through.
 *
 * WHICH INSTANCE. `ordinal` is 1-based and comes from the server, which counted
 * occurrences of this letter inside this word when it built the card — the same
 * number the "2-chi «و»" line prints. Without one, the first occurrence is
 * marked, which is right far more often than it is wrong and is never a
 * different WORD.
 *
 * Remeasured after the Arabic webfont loads, for the reason AyahText documents:
 * a clip measured against the fallback face exposes the wrong letter.
 */
export default function MarkedWord({
  word,
  letter,
  ordinal = 1,
  className = "",
}: {
  word: string;
  /** The letter to mark. Ignored when it does not occur in the word. */
  letter: string;
  /** Which occurrence of it, 1-based. */
  ordinal?: number;
  className?: string;
}) {
  const hostRef = useRef<HTMLSpanElement>(null);
  const textRef = useRef<HTMLSpanElement>(null);
  const [box, setBox] = useState<{ left: number; top: number; width: number; height: number } | null>(null);

  /** Character index of the wanted occurrence, or -1. */
  const index = (() => {
    if (!letter || letter.length !== 1) return -1;
    let seen = 0;
    for (let i = 0; i < word.length; i++) {
      if (word[i] === letter) {
        seen += 1;
        if (seen === Math.max(1, ordinal)) return i;
      }
    }
    // Asked for the 3rd و in a word with two. Fall back to the last one found
    // rather than marking nothing: the card is still about this word, and the
    // count being off is a smaller error than pointing at no letter at all.
    for (let i = word.length - 1; i >= 0; i--) if (word[i] === letter) return i;
    return -1;
  })();

  const measure = useCallback(() => {
    const host = hostRef.current;
    const span = textRef.current;
    const node = span?.firstChild;
    if (!host || !span || !node || index < 0) {
      setBox(null);
      return;
    }
    const range = document.createRange();
    try {
      range.setStart(node, index);
      // The letter PLUS any combining marks that sit on it — a bare consonant
      // index would clip the glyph and leave its own fatha in the base colour,
      // which reads as a rendering fault rather than as a mark.
      let end = index + 1;
      while (end < word.length && /\p{M}/u.test(word[end])) end += 1;
      range.setEnd(node, end);
    } catch {
      setBox(null);
      return;
    }
    const rects = Array.from(range.getClientRects()).filter((r) => r.width > 0.5);
    range.detach?.();
    if (rects.length === 0) {
      setBox(null);
      return;
    }
    const r = rects[0];
    const tb = span.getBoundingClientRect();
    setBox({
      left: r.left - tb.left,
      top: r.top - tb.top,
      width: r.width,
      height: r.height,
    });
  }, [word, index]);

  useLayoutEffect(() => {
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [measure]);

  useEffect(() => {
    document.fonts?.ready.then(measure).catch(() => {});
  }, [measure]);

  return (
    <span className={`mword ${className}`} ref={hostRef} dir="rtl" lang="ar">
      <span className="mword__text" ref={textRef}>
        {word}
      </span>
      {box && (
        // aria-hidden: this is the same word again, and a screen reader must
        // not read it twice.
        <span
          className="mword__mark"
          aria-hidden="true"
          style={{
            clipPath: `polygon(${box.left}px ${box.top}px, ${
              box.left + box.width
            }px ${box.top}px, ${box.left + box.width}px ${
              box.top + box.height
            }px, ${box.left}px ${box.top + box.height}px)`,
          }}
        >
          {word}
        </span>
      )}
    </span>
  );
}
