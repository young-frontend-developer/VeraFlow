import { useState } from "react";
import { Key, Lang, t } from "../lib/i18n";
import { withBrand } from "../lib/brand";
import {
  Focus, Goal, Journey, Minutes, Stage, When,
} from "../lib/journey";
import { Tick } from "./Ornament";

/**
 * PERSONALIZATION — five questions, each of which changes something.
 *
 * ── THE TEST EVERY QUESTION HAD TO PASS ────────────────────────────────────
 *
 * "What does the app do differently depending on the answer?" A question that
 * fails it is a survey wearing onboarding's clothes, and this codebase has
 * refused those before — the original experience step survived only because it
 * picks the default reciter.
 *
 *   goal     names the journey, and is the headline of MY JOURNEY
 *   stage    sets the starting knowledge level (the thing the old three-question
 *            assessment computed, now derived from one honest question instead)
 *   focus    becomes CURRENT PATH, since there is no course catalogue to name
 *   minutes  sizes today's journey. A 5-minute commitment produces a 5-minute
 *            day, not a 15-minute day with the number changed
 *   when     the practice time shown on MY JOURNEY
 *
 * ⚠️ `when` DOES NOT SCHEDULE A NOTIFICATION, because there are no
 * notifications in this app. It is displayed on the journey card and nothing
 * else. That is a real limit and it is why "I'll choose myself" is an option
 * rather than a nag — a reminder setting that reminds nobody would be the
 * control-that-lies failure with a clock on it.
 *
 * EVERY QUESTION IS SKIPPABLE. Nulls flow through to the journey and the cards
 * simply omit what was not answered.
 *
 * SELECTION IS NEVER COLOUR ALONE: an emerald border, a background shift AND a
 * check mark, all three, plus aria-pressed for anyone not looking at any of it.
 *
 * ── ONE QUESTION, ONE CARD ─────────────────────────────────────────────────
 *
 * Each question renders inside the same centred 420px card the account screen
 * uses, with the progress dots beneath it. It was previously a full-bleed
 * column, which meant six option plates stretched to whatever width the
 * viewport happened to be and a continue button as wide as a desktop monitor.
 * See the onboarding block in index.css.
 */

type Q = {
  key: keyof Pick<Journey, "goal" | "stage" | "focus" | "minutes" | "when">;
  title: Key;
  options: { value: string | number; label: Key }[];
};

const QUESTIONS: Q[] = [
  {
    key: "goal", title: "q_goal",
    options: [
      { value: "recitation", label: "goal_recitation" },
      { value: "tajweed", label: "goal_tajweed" },
      { value: "memorize", label: "goal_memorize" },
      { value: "habit", label: "goal_habit" },
      { value: "understand", label: "goal_understand" },
      { value: "everything", label: "goal_everything" },
    ],
  },
  {
    key: "stage", title: "q_stage",
    options: [
      { value: "beginning", label: "stage_beginning" },
      { value: "improving", label: "stage_improving" },
      { value: "comfortable", label: "stage_comfortable" },
      { value: "memorizing", label: "stage_memorizing" },
    ],
  },
  {
    key: "focus", title: "q_focus",
    options: [
      { value: "recitation", label: "focus_recitation" },
      { value: "tajweed", label: "focus_tajweed" },
      { value: "memorization", label: "focus_memorization" },
      { value: "consistency", label: "focus_consistency" },
      { value: "understanding", label: "focus_understanding" },
    ],
  },
  {
    key: "minutes", title: "q_minutes",
    options: ([5, 10, 15, 20, 30] as const).map((n) => ({
      value: n, label: `min_${n}` as Key,
    })),
  },
  {
    key: "when", title: "q_when",
    options: [
      { value: "after_fajr", label: "when_after_fajr" },
      { value: "morning", label: "when_morning" },
      { value: "afternoon", label: "when_afternoon" },
      { value: "after_maghrib", label: "when_after_maghrib" },
      { value: "evening", label: "when_evening" },
      { value: "later", label: "when_later" },
    ],
  },
];

export default function Personalize({
  lang,
  onDone,
}: {
  lang: Lang;
  onDone: (answers: {
    goal: Goal | null; stage: Stage | null; focus: Focus | null;
    minutes: Minutes | null; when: When | null;
  }) => void;
}) {
  const [i, setI] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string | number | null>>({
    goal: null, stage: null, focus: null, minutes: null, when: null,
  });

  const q = QUESTIONS[i];
  const last = i === QUESTIONS.length - 1;

  function finish() {
    onDone({
      goal: (answers.goal as Goal) ?? null,
      stage: (answers.stage as Stage) ?? null,
      focus: (answers.focus as Focus) ?? null,
      minutes: (answers.minutes as Minutes) ?? null,
      when: (answers.when as When) ?? null,
    });
  }

  return (
    <div className="onboard">
      <div className="onboard__inner">
        <div className="card onboard__card">
          <div className="onboard__step" key={q.key}>
            <p className="onboard__count">
              {i + 1} / {QUESTIONS.length}
            </p>
            <h2 className="onboard__display">{withBrand(t(lang, q.title))}</h2>

            {/* Compact option plates bounded by the card, not text rows
                stretched across the viewport. `choice--tight` because six goal
                options at full plate height would push the primary action off
                a short phone screen. */}
            <div className="choice choice--tight">
              {q.options.map((opt) => {
                const on = answers[q.key] === opt.value;
                return (
                  <button
                    key={String(opt.value)}
                    className={on ? "choice__item is-on" : "choice__item"}
                    aria-pressed={on}
                    onClick={() =>
                      setAnswers((a) => ({
                        ...a,
                        [q.key]: on ? null : opt.value,
                      }))
                    }
                  >
                    <span>
                      <span className="choice__name">{t(lang, opt.label)}</span>
                    </span>
                    <span className="choice__tick">
                      <Tick />
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="onboard__foot">
              <button
                className="btn-primary"
                onClick={() => (last ? finish() : setI(i + 1))}
              >
                {t(lang, last ? "personalize_done" : "onboard_next")}
              </button>
              {/* Skippable, and the skip is visible rather than hidden behind a
                  gesture. An unanswered question is simply omitted from the
                  journey card later. */}
              <button
                className="onboard__skip"
                onClick={() => (last ? finish() : setI(i + 1))}
              >
                {t(lang, "onboard_choose_later")}
              </button>
            </div>
          </div>
        </div>

        {/* Five questions, five dots, immediately under the card they describe.
            The counter above the question says the same thing in words for
            anyone who cannot see the dots. */}
        <div className="onboard__dots" aria-hidden="true">
          {QUESTIONS.map((x, n) => (
            <span
              key={x.key}
              className={n === i ? "onboard__dot onboard__dot--on" : "onboard__dot"}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
