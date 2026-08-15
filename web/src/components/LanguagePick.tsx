import { Lang, t } from "../lib/i18n";
import { Tick } from "./Ornament";

/**
 * THE FIRST QUESTION, BEFORE ANY OTHER QUESTION.
 *
 * ── WHY THIS MOVED TO THE FRONT ────────────────────────────────────────────
 *
 * Language used to be settled late — a toggle on the account screen near the
 * end of the entry flow, and a step in the middle of the old onboarding. That
 * ordering asks somebody to answer five personalization questions in a language
 * they may not read, and an answer given to a question you could not read is
 * not an answer. Every screen after this one is prose: the welcome, the
 * questions, the journey summary, the consent text. All of it depends on this.
 *
 * So it is the first thing after the Basmala, and it is the one step in the
 * entry flow WITHOUT a skip. Skipping every other question costs a default;
 * skipping this one costs the learner the rest of the flow. There is still no
 * wrong answer available — both options are always tappable, one is always
 * already selected, and Davom etish is never disabled — so nobody is trapped.
 *
 * EACH LANGUAGE IS SHOWN IN ITSELF, at reading size. A dropdown of language
 * codes asks you to recognise an abbreviation; this asks you to recognise your
 * own language, which is the actual question being put.
 *
 * The choice applies ON TAP, not on continue: the heading, the body and the
 * button below all switch under the learner's finger, which is the only
 * confirmation this screen needs and the only one it can give in a language
 * they have just told us they read.
 */

const LANGS = [
  { code: "uz", native: "Oʻzbekcha", english: "Uzbek" },
  { code: "ru", native: "Русский", english: "Russian" },
] as const;

export default function LanguagePick({
  lang,
  onLang,
  onDone,
}: {
  lang: Lang;
  onLang: (l: Lang) => void;
  onDone: () => void;
}) {
  return (
    <div className="onboard">
      <div className="onboard__inner">
        <div className="card onboard__card">
          <div className="onboard__step">
            <h2 className="onboard__display">{t(lang, "onboard_lang")}</h2>
            <p className="onboard__lede">{t(lang, "onboard_lang_body")}</p>

            <div className="choice">
              {LANGS.map((l) => (
                <button
                  key={l.code}
                  className={
                    lang === l.code ? "choice__item is-on" : "choice__item"
                  }
                  aria-pressed={lang === l.code}
                  onClick={() => onLang(l.code)}
                >
                  <span>
                    <span className="choice__name">{l.native}</span>
                    <span className="choice__note">{l.english}</span>
                  </span>
                  <span className="choice__tick">
                    <Tick />
                  </span>
                </button>
              ))}
            </div>

            {/* No skip. See the note above: this is the one step where
                skipping would cost the learner every screen after it. */}
            <div className="onboard__foot">
              <button className="btn-primary" onClick={onDone}>
                {t(lang, "onboard_next")}
              </button>
            </div>
          </div>
        </div>

        {/* One dot, filled, so the flow's progress indicator starts here
            rather than appearing two screens in. */}
        <div className="onboard__dots" aria-hidden="true">
          <span className="onboard__dot onboard__dot--on" />
        </div>
      </div>
    </div>
  );
}
