import { useState } from "react";
import ConsentGate from "./ConsentGate";
import { ArchOrnament, StarOrnament, Tick } from "./Ornament";
import { Lang, t } from "../lib/i18n";
import { withBrand } from "../lib/brand";
import { Level, QUESTIONS, levelFrom, storeLevel } from "../lib/level";

/**
 * First run: welcome → language → experience → knowledge assessment → consent.
 *
 * THERE IS NO SIGN UP OR LOG IN, and that is a decision rather than an
 * omission. Tilawah has no accounts: identity is an anonymous id in this
 * browser's storage, consent is held per device, and withdrawing it deletes the
 * server rows. An auth screen would be a privacy architecture change dressed as
 * a visual one, and a designed-but-inert one would be a form that cannot work.
 * The CONSENT step is the real account decision here, so it is where the flow
 * ends.
 *
 * THE EXPERIENCE STEP DOES SOMETHING. It sets the default reciter — a muallim
 * recording repeats each phrase and is genuinely easier to follow when you are
 * starting, a murattal is not. A step that only recorded an answer nobody reads
 * would be a survey pretending to be personalisation, and this app does not
 * have anywhere else to spend that answer yet.
 */

export type Experience = "new" | "some" | "fluent";

// welcome, language, experience, ASSESSMENT, consent
const STEPS = 5;

export default function Onboarding({
  lang,
  audioOffered,
  onLang,
  onDone,
}: {
  lang: Lang;
  audioOffered: boolean;
  onLang: (l: Lang) => void;
  onDone: (
    consented: boolean,
    audioConsented: boolean,
    experience: Experience | null,
  ) => void;
}) {
  const [step, setStep] = useState(0);
  const [experience, setExperience] = useState<Experience | null>(null);
  /**
   * The knowledge assessment's answers, 0-2 per question, null while unanswered.
   *
   * ASKED ONCE, HERE, AND NOWHERE ELSE. The result is a stored setting the
   * learner can change from Profile - never a banner, a badge or a widget in
   * the running app. See lib/level.ts.
   */
  const [answers, setAnswers] = useState<(number | null)[]>(
    QUESTIONS.map(() => null),
  );

  function finishAssessment(next: number) {
    const level: Level = levelFrom(answers);
    storeLevel(level);
    setStep(next);
  }

  return (
    <div className="onboard">
      {/* The same centred column and card as Welcome, Personalize and the
          account screen. The consent step is exempt: ConsentGate draws its own
          panel, and a panel inside a card is two nested cards. */}
      <div className="onboard__inner">
        <div
          key={step}
          className={
            step === 4
              ? "onboard__step"
              : "card onboard__card onboard__step"
          }
        >
        {step === 0 && (
          <>
            <StarOrnament className="onboard__ornament" size={46} />
            <h2 className="onboard__display">{withBrand(t(lang, "onboard_welcome"))}</h2>
            <p className="onboard__lede">{t(lang, "onboard_welcome_body")}</p>
            <div className="onboard__foot">
              <button className="btn-primary" onClick={() => setStep(1)}>
                {t(lang, "onboard_begin")}
              </button>
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <h2 className="onboard__display">{t(lang, "onboard_lang")}</h2>
            <p className="onboard__lede">{t(lang, "onboard_lang_body")}</p>
            {/* Each language is shown IN ITSELF, at reading size. A dropdown
                asks you to recognise a code; this asks you to recognise your
                own language, which is the actual question. */}
            <div className="choice">
              {(
                [
                  ["uz", "Oʻzbekcha", "Uzbek"],
                  ["ru", "Русский", "Russian"],
                ] as const
              ).map(([code, native, english]) => (
                <button
                  key={code}
                  className="choice__item"
                  aria-pressed={lang === code}
                  onClick={() => onLang(code)}
                >
                  <span>
                    <span className="choice__name">{native}</span>
                    <span className="choice__note">{english}</span>
                  </span>
                  <span className="choice__tick">
                    <Tick />
                  </span>
                </button>
              ))}
            </div>
            <div className="onboard__foot">
              <button className="btn-primary" onClick={() => setStep(2)}>
                {t(lang, "onboard_next")}
              </button>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <ArchOrnament className="onboard__ornament" size={46} />
            <h2 className="onboard__display">{t(lang, "onboard_level")}</h2>
            <p className="onboard__lede">{t(lang, "onboard_level_body")}</p>
            <div className="choice">
              {(
                [
                  ["new", "onboard_level_new", "onboard_level_new_note"],
                  ["some", "onboard_level_some", "onboard_level_some_note"],
                  ["fluent", "onboard_level_fluent", "onboard_level_fluent_note"],
                ] as const
              ).map(([code, label, note]) => (
                <button
                  key={code}
                  className="choice__item"
                  aria-pressed={experience === code}
                  onClick={() => setExperience(code)}
                >
                  <span>
                    <span className="choice__name">{t(lang, label)}</span>
                    <span className="choice__note">{t(lang, note)}</span>
                  </span>
                  <span className="choice__tick">
                    <Tick />
                  </span>
                </button>
              ))}
            </div>
            <div className="onboard__foot">
              <button className="btn-primary" onClick={() => setStep(3)}>
                {t(lang, "onboard_next")}
              </button>
              {/* Optional means skippable, and skippable means the skip is
                  visible rather than hidden behind a back gesture. */}
              <button className="onboard__skip" onClick={() => setStep(3)}>
                {t(lang, "onboard_skip")}
              </button>
            </div>
          </>
        )}

        {/* THE KNOWLEDGE ASSESSMENT. Three questions, not a quiz: it decides a
            starting setting, so a wrong answer costs a slightly gentler start
            and nothing else. Skippable, and skipping lands on "beginner",
            which is the harmless direction to be wrong in. */}
        {step === 3 && (
          <>
            <ArchOrnament className="onboard__ornament" size={46} />
            <h2 className="onboard__display">{t(lang, "assess_title")}</h2>
            <p className="onboard__lede">{t(lang, "assess_body")}</p>

            {QUESTIONS.map((q, qi) => (
              <div className="assess__q" key={q.id}>
                <p className="assess__prompt">{t(lang, q.prompt as never)}</p>
                <div className="choice choice--tight">
                  {q.options.map((opt, oi) => (
                    <button
                      key={opt}
                      className="choice__item"
                      aria-pressed={answers[qi] === oi}
                      onClick={() =>
                        setAnswers((a) =>
                          a.map((v, i) => (i === qi ? oi : v)),
                        )
                      }
                    >
                      <span>
                        <span className="choice__name">
                          {t(lang, opt as never)}
                        </span>
                      </span>
                      <span className="choice__tick">
                        <Tick />
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ))}

            <div className="onboard__foot">
              <button
                className="btn-primary"
                onClick={() => finishAssessment(4)}
              >
                {t(lang, "onboard_next")}
              </button>
              <button
                className="onboard__skip"
                onClick={() => finishAssessment(4)}
              >
                {t(lang, "onboard_skip")}
              </button>
            </div>
          </>
        )}

        {step === 4 && (
          <ConsentGate
            lang={lang}
            audioOffered={audioOffered}
            onDecide={(c, a) => onDone(c, a, experience)}
          />
        )}
        </div>

        <div className="onboard__dots" aria-hidden="true">
          {Array.from({ length: STEPS }, (_, i) => (
            <span
              key={i}
              className={i === step ? "onboard__dot onboard__dot--on" : "onboard__dot"}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
