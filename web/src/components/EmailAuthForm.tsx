import { FormEvent, useState } from "react";
import {
  EmailAuthError,
  forgotPassword,
  login,
  register,
} from "../lib/api";
import { Key, Lang, t } from "../lib/i18n";

/**
 * EMAIL AND PASSWORD, WIRED TO A REAL BACKEND.
 *
 * This surface was deleted once. It used to be a full set of controls — a tab
 * pair, two fields, a submit button — all disabled under a line saying accounts
 * were not ready, and removing it was right: a visibly broken option is still
 * an option, and a learner who picks it discovers the product cannot do what it
 * just offered. It comes back now on exactly the condition stated at the time —
 * "the day there are endpoints behind it" — and those endpoints exist. See
 * api/tilawah/api/email_routes.py.
 *
 * ── NO ERROR TEXT FROM THE SERVER EVER REACHES A LEARNER ──────────────────
 *
 * The API answers with machine codes (`invalid_credentials`, `weak_password`
 * plus a list of specific problems) and this component maps them to sentences
 * in the learner's own language. That is not politeness: an API string is
 * written for whoever is reading the logs, it arrives in one language, and it
 * describes the request rather than the person's situation. "422 Unprocessable
 * Entity" in a form is how software tells somebody their problem is not worth
 * explaining.
 *
 * ── WHAT IS CHECKED HERE AND WHAT IS CHECKED THERE ────────────────────────
 *
 * The client checks that the fields are not empty and that the address has an
 * @ in it, because a round trip to be told so is a waste of the learner's time.
 * IT DOES NOT ENFORCE THE PASSWORD POLICY — the server does, and the server's
 * answer is the one that counts. A client-side rule would only tell somebody
 * what to expect; it could never be the thing keeping a weak password out,
 * because anything running in a browser can be skipped.
 *
 * ── THE PASSWORD IS NEVER KEPT ────────────────────────────────────────────
 *
 * It lives in one piece of state while the form is open and is cleared on
 * success. It is never written to storage, never put in a URL, and never
 * retried automatically — a password held for a retry is a password sitting in
 * memory for as long as the tab is.
 */

type Mode = "login" | "signup";

/** The server's codes → the i18n keys that explain them. */
const ERROR_KEYS: Record<string, Key> = {
  invalid_email: "auth_err_email",
  email_taken: "auth_err_taken",
  already_has_email: "auth_err_has_email",
  invalid_credentials: "auth_err_credentials",
  email_not_verified: "auth_err_unverified",
  too_many_attempts: "auth_err_throttled",
  invalid_token: "auth_err_token",
  network: "auth_err_network",
};

/** The password-policy codes, each its own sentence. */
const PROBLEM_KEYS: Record<string, Key> = {
  too_short: "auth_pw_too_short",
  too_long: "auth_pw_too_long",
  too_common: "auth_pw_too_common",
  looks_like_email: "auth_pw_looks_like_email",
  blank: "auth_pw_blank",
};

/**
 * Every reason this request was refused, as sentences.
 *
 * `weak_password` deliberately has no entry of its own in ERROR_KEYS: it is a
 * heading with nothing under it, and what the learner needs is the specific
 * problems. Anything unrecognised falls back to one honest line rather than
 * rendering a code.
 */
function messages(lang: Lang, err: unknown): string[] {
  if (!(err instanceof EmailAuthError)) return [t(lang, "auth_err_network")];

  if (err.problems.length) {
    return err.problems.map((p) =>
      t(lang, PROBLEM_KEYS[p] ?? "auth_err_unknown"),
    );
  }
  return [t(lang, ERROR_KEYS[err.code] ?? "auth_err_unknown")];
}

export default function EmailAuthForm({
  lang,
  onSignedIn,
}: {
  lang: Lang;
  /** A session is in hand. `linked` is true when an anonymous account kept its
   *  history rather than a new one being created. */
  onSignedIn: (linked: boolean) => void;
}) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [reveal, setReveal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  /** A completed action that produced no session: "check your email". */
  const [notice, setNotice] = useState<string[]>([]);
  const [forgot, setForgot] = useState(false);

  const clear = () => {
    setErrors([]);
    setNotice([]);
  };

  function switchMode(next: Mode) {
    setMode(next);
    setForgot(false);
    // Errors belong to the attempt that produced them. Carrying a login
    // failure across into the signup tab tells somebody their brand new
    // account is wrong.
    clear();
  }

  /** The two checks worth making before spending a round trip. */
  function localProblems(): string[] {
    const found: string[] = [];
    if (!email.trim()) found.push(t(lang, "auth_err_email_empty"));
    else if (!/^[^@\s]+@[^@\s.]+\.[^@\s]+$/.test(email.trim()))
      found.push(t(lang, "auth_err_email"));
    if (!forgot && !password) found.push(t(lang, "auth_err_password_empty"));
    return found;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    clear();

    const local = localProblems();
    if (local.length) return setErrors(local);

    setBusy(true);
    try {
      if (forgot) {
        await forgotPassword(email.trim(), lang);
        // SAYS "IF". The server answers identically whether or not that
        // address is registered, and a confident "sent!" would turn this form
        // into the membership test the server just refused to be.
        setNotice([t(lang, "auth_forgot_sent")]);
      } else if (mode === "signup") {
        const res = await register(email.trim(), password, lang);
        setPassword("");
        if ("verification_required" in res) {
          // No session: the address has to be confirmed first. Both lines are
          // shown together when no mail provider is wired, so nobody is sent
          // to check an inbox nothing was sent to.
          setNotice(
            res.sent
              ? [t(lang, "auth_check_email")]
              : [t(lang, "auth_check_email"), t(lang, "auth_mail_off")],
          );
        } else {
          onSignedIn(res.linked_now);
        }
      } else {
        const res = await login(email.trim(), password);
        setPassword("");
        onSignedIn(res.linked_now);
      }
    } catch (err) {
      setErrors(messages(lang, err));
    } finally {
      setBusy(false);
    }
  }

  const submitLabel = busy
    ? t(lang, "auth_working")
    : forgot
      ? t(lang, "auth_forgot_send")
      : mode === "signup"
        ? t(lang, "auth_do_signup")
        : t(lang, "auth_do_login");

  return (
    <div className="emailauth">
      {/* TWO TABS BECAUSE THERE ARE TWO REAL ACTIONS. The switch was removed
          when Google was the only working method — a toggle with one position
          is a control that does nothing — and it is back now that both
          positions lead somewhere. */}
      <div className="emailauth__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "login" && !forgot}
          className={
            mode === "login" ? "emailauth__tab emailauth__tab--on" : "emailauth__tab"
          }
          onClick={() => switchMode("login")}
        >
          {t(lang, "auth_tab_login")}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "signup" && !forgot}
          className={
            mode === "signup" ? "emailauth__tab emailauth__tab--on" : "emailauth__tab"
          }
          onClick={() => switchMode("signup")}
        >
          {t(lang, "auth_tab_signup")}
        </button>
      </div>

      <form className="emailauth__form" onSubmit={submit} noValidate>
        {forgot && <p className="emailauth__lead">{t(lang, "auth_forgot_body")}</p>}

        <label className="emailauth__label" htmlFor="auth-email">
          {t(lang, "auth_email")}
        </label>
        <input
          id="auth-email"
          className="emailauth__input"
          type="email"
          inputMode="email"
          autoComplete="email"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          placeholder={t(lang, "auth_email_ph")}
          value={email}
          disabled={busy}
          onChange={(e) => {
            setEmail(e.target.value);
            clear();
          }}
        />

        {!forgot && (
          <>
            <label className="emailauth__label" htmlFor="auth-password">
              {t(lang, "auth_password")}
            </label>
            <div className="emailauth__pw">
              <input
                id="auth-password"
                className="emailauth__input"
                type={reveal ? "text" : "password"}
                // The browser is told which of the two this is, so a password
                // manager offers to save a new one on signup and fill the
                // existing one on login instead of guessing.
                autoComplete={
                  mode === "signup" ? "new-password" : "current-password"
                }
                value={password}
                disabled={busy}
                onChange={(e) => {
                  setPassword(e.target.value);
                  clear();
                }}
              />
              <button
                type="button"
                className="emailauth__reveal"
                aria-label={t(
                  lang,
                  reveal ? "auth_hide_password" : "auth_show_password",
                )}
                aria-pressed={reveal}
                onClick={() => setReveal((v) => !v)}
              >
                {reveal ? "🙈" : "👁"}
              </button>
            </div>
            {/* The rule, stated BEFORE the attempt. A policy a learner meets
                for the first time in an error message is a policy they were
                never given. */}
            {mode === "signup" && (
              <p className="emailauth__hint">{t(lang, "auth_password_hint")}</p>
            )}
          </>
        )}

        {errors.length > 0 && (
          <ul className="emailauth__errors" role="alert">
            {errors.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        )}

        {notice.length > 0 && (
          <div className="emailauth__notice" role="status">
            {notice.map((m) => (
              <p key={m}>{m}</p>
            ))}
          </div>
        )}

        <button className="btn-primary emailauth__submit" disabled={busy}>
          {submitLabel}
        </button>

        {forgot ? (
          <button
            type="button"
            className="linkish emailauth__link"
            onClick={() => {
              setForgot(false);
              clear();
            }}
          >
            {t(lang, "auth_back")}
          </button>
        ) : (
          mode === "login" && (
            <button
              type="button"
              className="linkish emailauth__link"
              onClick={() => {
                setForgot(true);
                clear();
              }}
            >
              {t(lang, "auth_forgot")}
            </button>
          )
        )}
      </form>
    </div>
  );
}
