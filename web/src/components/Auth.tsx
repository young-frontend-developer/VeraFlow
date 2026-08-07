import { useState } from "react";
import { Lang, t } from "../lib/i18n";
import { AppleMark, GoogleMark, StarOrnament } from "./Ornament";
import { BRAND } from "../lib/brand";

/**
 * SIGN IN / SIGN UP.
 *
 * ── READ THIS BEFORE WIRING ANYTHING TO IT ─────────────────────────────────
 *
 * THERE IS NO AUTH BACKEND. No user table beyond the anonymous device row, no
 * session, no token, no Google or Apple client registered. This screen is
 * built to the design system and is deliberately NOT wired to a fake one.
 *
 * The tempting version accepts an email and a password, shows a spinner, and
 * drops the learner onto Today as though something happened. It demos
 * perfectly. It is also a login form that does not log anyone in, and the
 * moment a second device is opened the illusion costs a real person their
 * place. This codebase already refuses that class of thing in three places —
 * a record button on a rung the engine cannot score, an audio URL for a file
 * that is not on disk, a course card for a course that does not exist — and an
 * auth form is the same failure with higher stakes.
 *
 * So every credential control is present, styled, and DISABLED, under one line
 * saying accounts are not ready yet. The provider marks are drawn to Google's
 * and Apple's own brand specification rather than recoloured into the palette:
 * the buttons are ours, the marks are theirs, and a restyled provider mark is
 * both a trademark problem and a recognition problem.
 *
 * WHAT DOES WORK IS REAL. Language selection writes the same preference the
 * rest of the app reads, and "continue without an account" is not a
 * consolation prize — it is how Tilawah actually works today. Everything
 * functions anonymously against a device id, which is why the app has been
 * usable without this screen the whole time.
 *
 * To bring it up: implement the endpoints, delete `PENDING`, and wire
 * onSubmit/onProvider. The markup does not need to change.
 */

/** Flip to false in the same commit that lands real auth endpoints. */
const PENDING = true;

export default function Auth({
  lang,
  onLang,
  onContinue,
}: {
  lang: Lang;
  onLang: (l: Lang) => void;
  /** Proceed anonymously — the only path that currently does anything. */
  onContinue: () => void;
}) {
  const [mode, setMode] = useState<"in" | "up">("up");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <div className="auth">
      <div className="auth__inner">
        <header className="auth__head">
          <StarOrnament className="auth__mark" size={40} />
          <h1 className="wordmark auth__wordmark">{BRAND}</h1>
          <p className="auth__tagline">{t(lang, "auth_tagline")}</p>
        </header>

        <div className="card auth__card">
          <div className="auth__switch" role="tablist">
            <button
              role="tab"
              aria-selected={mode === "up"}
              className={mode === "up" ? "auth__tab is-on" : "auth__tab"}
              onClick={() => setMode("up")}
            >
              {t(lang, "auth_signup")}
            </button>
            <button
              role="tab"
              aria-selected={mode === "in"}
              className={mode === "in" ? "auth__tab is-on" : "auth__tab"}
              onClick={() => setMode("in")}
            >
              {t(lang, "auth_login")}
            </button>
          </div>

          {/* The honest line, above the controls rather than buried under
              them. A learner should know the form is inert before they type
              into it, not after. */}
          {PENDING && (
            <p className="auth__pending" role="status">
              {t(lang, "auth_pending")}
            </p>
          )}

          <form
            className="auth__form"
            onSubmit={(e) => e.preventDefault()}
            aria-disabled={PENDING}
          >
            <label className="field">
              <span className="field__label">{t(lang, "auth_email")}</span>
              <input
                className="field__input"
                type="email"
                autoComplete="email"
                value={email}
                disabled={PENDING}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>

            <label className="field">
              <span className="field__label">{t(lang, "auth_password")}</span>
              <input
                className="field__input"
                type="password"
                autoComplete={
                  mode === "up" ? "new-password" : "current-password"
                }
                value={password}
                disabled={PENDING}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            <button className="btn-primary auth__submit" disabled={PENDING}>
              {mode === "up" ? t(lang, "auth_signup") : t(lang, "auth_login")}
            </button>
          </form>

          <div className="auth__or">
            <span>{t(lang, "auth_or")}</span>
          </div>

          <div className="auth__providers">
            <button className="btn-provider" disabled={PENDING}>
              <GoogleMark />
              {t(lang, "auth_google")}
            </button>
            <button className="btn-provider" disabled={PENDING}>
              <span className="btn-provider__apple">
                <AppleMark />
              </span>
              {t(lang, "auth_apple")}
            </button>
          </div>
        </div>

        {/* ── what actually works ──────────────────────────────────────── */}

        <div className="auth__lang" role="group" aria-label={t(lang, "auth_lang")}>
          <span className="auth__lang-label">{t(lang, "auth_lang")}</span>
          <div className="auth__lang-choices">
            <button
              className={lang === "uz" ? "chip chip--on" : "chip"}
              onClick={() => onLang("uz")}
            >
              O‘zbekcha
            </button>
            <button
              className={lang === "ru" ? "chip chip--on" : "chip"}
              onClick={() => onLang("ru")}
            >
              Русский
            </button>
          </div>
        </div>

        {/* Not a fallback. This is how the app works today, and it is stated
            as a real choice rather than as the thing you do when the real
            thing is broken. */}
        <button className="btn-quiet auth__skip" onClick={onContinue}>
          {t(lang, "auth_continue")}
        </button>
        <p className="auth__note">{t(lang, "auth_anon_note")}</p>
      </div>
    </div>
  );
}
