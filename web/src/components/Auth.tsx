import { useCallback, useState } from "react";
import { Lang, t } from "../lib/i18n";
import { GoogleMark, StarOrnament } from "./Ornament";
import { BRAND, withBrand } from "../lib/brand";
import EmailAuthForm from "./EmailAuthForm";
import GoogleButton from "./GoogleButton";

/**
 * SIGN IN — two providers, because two providers work.
 *
 * ── THE EMAIL FORM IS BACK, AND WHY THAT IS NOT A REVERSAL ────────────────
 *
 * This screen used to carry a full set of credential controls — a signup/login
 * tab pair, an email field, a password field, a submit button — all present,
 * all styled, and all DISABLED under a line saying accounts were not ready.
 * They were deleted rather than left disabled, because a visibly broken option
 * is still an option: the learner reads two tabs, picks the one matching how
 * they think about signing in, and discovers the product cannot do what it just
 * offered. The note left behind said the surface "comes back the day there are
 * endpoints behind it".
 *
 * That day is this one. Registration, login, verification and password reset
 * are real, sit on the same session system as Google, and are tested — see
 * api/tilawah/api/email_routes.py and EmailAuthForm.tsx. Nothing on this screen
 * is inert.
 *
 * The tab switch comes back with it, for the same reason it went: a toggle with
 * one position is a control that does nothing, and a toggle with two real
 * positions is how somebody says which of two things they are doing.
 *
 * APPLE IS STILL DELIBERATELY ABSENT, not pending. This ships to Android; an
 * Apple button here would be the dead control this screen keeps refusing to
 * grow.
 *
 * The provider mark is drawn to Google's own brand specification rather than
 * recoloured into the palette: the button is ours, the mark is theirs, and a
 * restyled provider mark is both a trademark problem and a recognition problem.
 * (In the live path the button is Google's entirely — see GoogleButton.tsx.)
 *
 * WHAT ELSE WORKS IS REAL. Language selection writes the same preference the
 * rest of the app reads, and "continue without an account" is not a consolation
 * prize — it is how Tilawah actually works today. Everything functions
 * anonymously against a device id, which is why the app has been usable without
 * this screen the whole time. Signing in ADDS to that account rather than
 * replacing it: an anonymous learner who registers keeps their practice
 * history, their consent decision and their user id.
 */

export default function Auth({
  lang,
  onLang,
  onContinue,
}: {
  lang: Lang;
  onLang: (l: Lang) => void;
  /** Proceed into the app. Used for "continue without an account" and for a
   *  completed sign-in by EITHER provider: the app is the same either way, and
   *  the session in hand already says which one happened. */
  onContinue: () => void;
}) {
  // Set when the server reports no Google client configured, so the disabled
  // control comes back rather than an empty gap where a button should be.
  const [googleOff, setGoogleOff] = useState(false);

  const onGoogleOff = useCallback(() => setGoogleOff(true), []);
  // ONE HANDLER FOR BOTH PROVIDERS, because there is nothing to tell apart.
  // Linking preserved the anonymous account either way, so there is nothing to
  // reconcile here - the same session simply has an identity on it now.
  // Straight into the app, exactly as the anonymous path does.
  const onSignedIn = useCallback(
    (_linked: boolean) => {
      onContinue();
    },
    [onContinue],
  );

  return (
    <div className="auth">
      <div className="auth__inner">
        <header className="auth__head">
          <StarOrnament className="auth__mark" size={40} />
          <h1 className="wordmark auth__wordmark">{BRAND}</h1>
          <p className="auth__tagline">{t(lang, "auth_tagline")}</p>
        </header>

        <div className="card auth__card">
          {/* EMAIL FIRST, GOOGLE SECOND. The form is the method that always
              works - it needs nothing configured on the server - while the
              Google button depends on a client id that a given deployment may
              not have. Ordering the reliable one first also puts the two
              fields where the eye lands rather than making the learner read
              past a provider button to find them. */}
          <EmailAuthForm lang={lang} onSignedIn={onSignedIn} />

          <div className="auth__or" role="separator">
            <span>{t(lang, "auth_or")}</span>
          </div>

          <div className="auth__providers">
            {/* Google renders its OWN button, which is the only supported way
                to get an ID token from a click - see GoogleButton.tsx. If the
                server has no client id configured it calls onUnavailable and we
                fall back to the disabled control below, because a button that
                cannot work is worse than one that says so. */}
            {googleOff ? (
              <>
                <button className="btn-provider" disabled>
                  <GoogleMark />
                  {t(lang, "auth_google")}
                </button>
                <p className="auth__pending" role="status">
                  {t(lang, "auth_google_off")}
                </p>
              </>
            ) : (
              <GoogleButton
                lang={lang}
                onSignedIn={onSignedIn}
                onUnavailable={onGoogleOff}
              />
            )}
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
        <p className="auth__note">{withBrand(t(lang, "auth_anon_note"))}</p>
      </div>
    </div>
  );
}
