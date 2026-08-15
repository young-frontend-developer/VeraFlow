import { FormEvent, useEffect, useRef, useState } from "react";
import { EmailAuthError, resetPassword, verifyEmail } from "../lib/api";
import { Key, Lang, t } from "../lib/i18n";
import { BRAND } from "../lib/brand";
import { StarOrnament } from "./Ornament";

/**
 * WHERE A LINK FROM AN EMAIL LANDS. Two of them, and nothing else.
 *
 *   /verify-email?token=…     confirm an address
 *   /reset-password?token=…   choose a new password
 *
 * ── WHY THIS EXISTS AT ALL ────────────────────────────────────────────────
 *
 * The API can mint and redeem both tokens without any of this. But a link in
 * an email has to arrive SOMEWHERE, and without these two screens the flow
 * dead-ends on the app's own front door with a token in the address bar that
 * nothing reads — which is a broken password reset no matter how correct the
 * endpoints are. The scaffolding is not finished until the link works.
 *
 * Dispatched by path in App.tsx, the same way /review is, and for the same
 * reason: this is a different situation from the learner app - no tab bar, no
 * consent gate, no session assumed - and an early return inside LearnerApp
 * would call hooks conditionally.
 *
 * ── THE TOKEN IS REMOVED FROM THE URL IMMEDIATELY ─────────────────────────
 *
 * It is a credential, and a credential in an address bar is a credential in
 * browser history, in a screenshot, and in the Referer header of the next
 * request the page makes. It is read once into memory and the URL is rewritten
 * without it before anything else happens.
 */

type Kind = "verify" | "reset";

const TOKEN_KEYS: Record<string, Key> = {
  invalid_token: "auth_err_token",
  too_many_attempts: "auth_err_throttled",
};

const PROBLEM_KEYS: Record<string, Key> = {
  too_short: "auth_pw_too_short",
  too_long: "auth_pw_too_long",
  too_common: "auth_pw_too_common",
  looks_like_email: "auth_pw_looks_like_email",
  blank: "auth_pw_blank",
};

function messages(lang: Lang, err: unknown): string[] {
  if (!(err instanceof EmailAuthError)) return [t(lang, "auth_err_network")];
  if (err.problems.length)
    return err.problems.map((p) => t(lang, PROBLEM_KEYS[p] ?? "auth_err_unknown"));
  return [t(lang, TOKEN_KEYS[err.code] ?? "auth_err_unknown")];
}

/** Read the token out of the URL and scrub it from the address bar. */
function takeToken(): string {
  const token = new URLSearchParams(window.location.search).get("token") ?? "";
  if (token) {
    window.history.replaceState({}, "", window.location.pathname);
  }
  return token;
}

export default function MailAction({
  kind,
  lang,
  onDone,
}: {
  kind: Kind;
  lang: Lang;
  /** Leave this screen and go to the app's own front door, so the learner can
   *  sign in with what they just confirmed or just chose. */
  onDone: () => void;
}) {
  const [token] = useState(takeToken);
  const [busy, setBusy] = useState(kind === "verify");
  const [done, setDone] = useState(false);
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  // StrictMode mounts twice in development, and the second run would spend a
  // single-use token that the first one already consumed - reporting a valid
  // link as expired. The flow is idempotent from the learner's side only
  // because of this guard.
  const spent = useRef(false);

  useEffect(() => {
    if (kind !== "verify" || spent.current) return;
    spent.current = true;
    if (!token) {
      setBusy(false);
      setErrors([t(lang, "auth_err_token")]);
      return;
    }
    verifyEmail(token)
      .then(() => setDone(true))
      .catch((e) => setErrors(messages(lang, e)))
      .finally(() => setBusy(false));
  }, [kind, token, lang]);

  async function submitReset(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setErrors([]);
    if (!password) return setErrors([t(lang, "auth_err_password_empty")]);
    if (!token) return setErrors([t(lang, "auth_err_token")]);

    setBusy(true);
    try {
      await resetPassword(token, password);
      // Every session died server-side, including this browser's, and
      // resetPassword() has already dropped the local token. The learner signs
      // in again with the password they just chose - which is the correct cost
      // of a reset, and is said plainly rather than hidden by a silent
      // re-login.
      setPassword("");
      setDone(true);
    } catch (err) {
      setErrors(messages(lang, err));
    } finally {
      setBusy(false);
    }
  }

  const title = t(lang, kind === "verify" ? "mail_verify_title" : "mail_reset_title");

  return (
    <div className="auth">
      <div className="auth__inner">
        <header className="auth__head">
          <StarOrnament className="auth__mark" size={40} />
          <h1 className="wordmark auth__wordmark">{BRAND}</h1>
          <p className="auth__tagline">{title}</p>
        </header>

        <div className="card auth__card">
          {done ? (
            <div className="emailauth__notice" role="status">
              <p>
                {t(lang, kind === "verify" ? "mail_verify_ok" : "mail_reset_ok")}
              </p>
            </div>
          ) : kind === "verify" ? (
            busy ? (
              <p className="emailauth__lead" role="status">
                {t(lang, "mail_verify_working")}
              </p>
            ) : null
          ) : (
            <form className="emailauth__form" onSubmit={submitReset} noValidate>
              <p className="emailauth__lead">{t(lang, "mail_reset_body")}</p>
              <label className="emailauth__label" htmlFor="new-password">
                {t(lang, "auth_password")}
              </label>
              <input
                id="new-password"
                className="emailauth__input"
                type="password"
                autoComplete="new-password"
                value={password}
                disabled={busy}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setErrors([]);
                }}
              />
              <p className="emailauth__hint">{t(lang, "auth_password_hint")}</p>

              {errors.length > 0 && (
                <ul className="emailauth__errors" role="alert">
                  {errors.map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              )}

              <button className="btn-primary emailauth__submit" disabled={busy}>
                {busy ? t(lang, "auth_working") : t(lang, "mail_reset_do")}
              </button>
            </form>
          )}

          {/* The failure path for verification, which has no form of its own
              to hang its errors on. */}
          {kind === "verify" && errors.length > 0 && (
            <ul className="emailauth__errors" role="alert">
              {errors.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          )}
        </div>

        <button className="btn-quiet auth__skip" onClick={onDone}>
          {t(lang, done ? "auth_do_login" : "mail_open_app")}
        </button>
      </div>
    </div>
  );
}
