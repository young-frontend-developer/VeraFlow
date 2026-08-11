import { useEffect, useRef, useState } from "react";
import { GoogleSignInError, googleSignIn, googleStart } from "../lib/api";
import { Lang, t } from "../lib/i18n";

/**
 * "Google bilan davom etish", wired to the real thing.
 *
 * ── WHY GOOGLE'S OWN BUTTON AND NOT THE STYLED ONE NEXT TO IT ─────────────
 *
 * The rest of this screen draws its own controls, and the Apple button still
 * does. This one does not, because Google Identity Services has no supported
 * way to hand a custom button an ID token: the credential is delivered only
 * from a button GIS renders itself, or from One Tap, which the browser may
 * decline to show. The alternatives are an invisible Google button overlaid on
 * ours - an illusion that breaks the moment Google changes its iframe - or a
 * button that sometimes does nothing. This codebase already refuses that class
 * of thing in four places; a sign-in control is not where to start allowing it.
 *
 * So the button is Google's, themed as close to the surrounding palette as its
 * API permits, and the mark inside it is theirs, which is what their brand
 * terms ask for anyway.
 *
 * ── IF GOOGLE IS NOT CONFIGURED, NOTHING IS DRAWN ─────────────────────────
 *
 * /api/auth/google/start answers 503 when the server has no client id. The
 * caller then keeps the existing disabled button and its honest "not ready
 * yet" line, rather than showing a control that cannot work.
 */

const GIS_SRC = "https://accounts.google.com/gsi/client";

/** Load the GIS script once per page, however many buttons ask for it. */
let gisLoading: Promise<void> | null = null;

function loadGis(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (gisLoading) return gisLoading;
  gisLoading = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${GIS_SRC}"]`,
    );
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("gis")));
      return;
    }
    const el = document.createElement("script");
    el.src = GIS_SRC;
    el.async = true;
    el.defer = true;
    el.onload = () => resolve();
    el.onerror = () => {
      gisLoading = null; // a failed load must not poison later attempts
      reject(new Error("gis"));
    };
    document.head.appendChild(el);
  });
  return gisLoading;
}

/** Re-arm this long before the nonce dies, so the button is never stale. */
const RENEW_MARGIN_S = 45;

export default function GoogleButton({
  lang,
  onSignedIn,
  onUnavailable,
}: {
  lang: Lang;
  /** Signed in or linked. `linked` is true when an anonymous account kept
   *  its history rather than a new one being created. */
  onSignedIn: (linked: boolean) => void;
  /** Google is not configured here; fall back to the disabled control. */
  onUnavailable: () => void;
}) {
  const slot = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<"conflict" | "failed" | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let dead = false;
    let renew: number | undefined;

    async function arm() {
      // A nonce expires. Re-arming on a timer keeps the button honest: the
      // alternative is a control that looks fine and fails on click because
      // the learner read the page for six minutes first.
      const start = await googleStart();
      await loadGis();
      if (dead || !slot.current) return;

      // Narrowed rather than asserted: the script can load and still leave no
      // global behind if a privacy extension neuters it, and `!` there would
      // turn that into a crash inside a callback nobody is watching.
      const gis = window.google?.accounts?.id;
      if (!gis) throw new Error("gis");

      gis.initialize({
        client_id: start.client_id,
        nonce: start.nonce,
        // FedCM is where Chrome is going; opting out now would need undoing.
        use_fedcm_for_prompt: true,
        callback: async (resp: { credential?: string }) => {
          if (!resp?.credential) return setError("failed");
          setBusy(true);
          setError(null);
          try {
            const session = await googleSignIn(resp.credential, start.nonce);
            onSignedIn(session.linked_now);
          } catch (e) {
            setError(
              e instanceof GoogleSignInError && e.isConflict
                ? "conflict"
                : "failed",
            );
            // The nonce was spent by that attempt, successful or not. Without
            // a fresh one the next click fails for a reason the learner
            // cannot see or fix.
            arm().catch(() => {});
          } finally {
            setBusy(false);
          }
        },
      });

      slot.current.replaceChildren();
      gis.renderButton(slot.current, {
        theme: "filled_black",
        size: "large",
        shape: "pill",
        text: "continue_with",
        logo_alignment: "center",
        width: 300,
      });

      renew = window.setTimeout(
        () => arm().catch(() => {}),
        Math.max(30, start.expires_in - RENEW_MARGIN_S) * 1000,
      );
    }

    arm().catch((e) => {
      if (dead) return;
      if (e instanceof GoogleSignInError && e.isUnavailable) onUnavailable();
      else setError("failed");
    });

    return () => {
      dead = true;
      if (renew) window.clearTimeout(renew);
      window.google?.accounts?.id?.cancel?.();
    };
    // Armed once per mount. onSignedIn/onUnavailable are stable in Auth.tsx.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="auth__google">
      <div ref={slot} aria-busy={busy} />
      {error && (
        <p className="auth__google-error" role="alert">
          {t(lang, error === "conflict" ? "auth_google_conflict" : "auth_google_failed")}
        </p>
      )}
    </div>
  );
}
