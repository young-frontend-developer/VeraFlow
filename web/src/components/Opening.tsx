import { useEffect, useState } from "react";
import { BRAND } from "../lib/brand";

/**
 * FIRST OPEN — the Basmala.
 *
 * Ivory, empty, and quiet. No navigation, no buttons, no logo animation, no
 * particles, no gradient, no sound. The Basmala fades in slowly, the brand name
 * sits small at the foot of the screen, and after a beat the app moves on by
 * itself. It should feel like opening a well-made book, not launching software.
 *
 * ── WHY THE TIMING IS WHAT IT IS ───────────────────────────────────────────
 *
 * The fade is 1.6s and the hold is 2.2s, which is slower than a splash screen
 * and deliberately so: a splash is a thing you wait through, and this is a thing
 * you read. Under about a second it reads as a loading state; much over three
 * and a returning user starts to resent it — which is why this is shown ONCE,
 * on first open, and never again.
 *
 * ── REDUCED MOTION IS NOT A DEGRADED PATH ──────────────────────────────────
 *
 * With prefers-reduced-motion the Basmala is simply present, at full opacity,
 * for the same duration. The moment is not the animation; the moment is the
 * pause. Someone who cannot tolerate motion should get the pause, not a
 * skipped screen.
 *
 * ── IT CANNOT TRAP ANYONE ──────────────────────────────────────────────────
 *
 * A tap anywhere advances immediately, and the timer is cleared on unmount. A
 * ceremonial screen with no exit is a hang with good typography.
 */

/** ms. See the note above before changing either. */
const FADE = 1600;
const HOLD = 2200;

export default function Opening({ onDone }: { onDone: () => void }) {
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const t = window.setTimeout(() => {
      setLeaving(true);
      window.setTimeout(onDone, 420);
    }, HOLD);
    return () => window.clearTimeout(t);
  }, [onDone]);

  return (
    <div
      className={leaving ? "opening opening--out" : "opening"}
      onClick={onDone}
      role="presentation"
    >
      <p
        className="opening__basmala"
        dir="rtl"
        lang="ar"
        style={{ animationDuration: `${FADE}ms` }}
      >
        بِسْمِ اللهِ الرَّحْمٰنِ الرَّحِيمِ
      </p>
      <p className="opening__brand">{BRAND}</p>
    </div>
  );
}
