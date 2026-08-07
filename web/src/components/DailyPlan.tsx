import { AyahBrief, Sura } from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { PlanMemorize, PlanReflect, PlanRevise } from "./Ornament";

/**
 * A GENTLE PLAN FOR TODAY — three steps, every one of them derived.
 *
 * The reference design shows three plan cards with titles, types and durations
 * on them. The obvious way to build that is to write three plausible steps into
 * the component and ship it, and it would look exactly right on the first run
 * and be a lie on every run after: a "plan" that says the same thing regardless
 * of what the learner has done is not a plan, it is a decorative list.
 *
 * So each step comes from something real or the section is not drawn:
 *
 *   MEMORIZE  the ayah they are actually on. Duration is the engine's own
 *             estimate of how long that ayah takes to recite, not a guess.
 *   REVISE    the ayah BEFORE it — the thing most recently learnt, which is
 *             the one revision worth doing. Absent on the first ayah of a
 *             sura, where there is nothing behind them yet.
 *   REFLECT   the daily verse shown further down the same screen, so the step
 *             points at something already on the page rather than somewhere
 *             the app cannot take them.
 *
 * WITH NO STORED PLACE THERE IS NO PLAN, and the section disappears rather than
 * showing three empty rows. A new learner has not left off anywhere, and
 * inventing a syllabus for them is the fabricated-curriculum failure that
 * Soon.tsx exists to refuse — the same rule, one screen over.
 *
 * The faint 01/02/03 in the corner is ordinal, not a count of anything. It says
 * which step comes first; it does not claim progress through a course.
 */

export type PlanStep = {
  key: "memorize" | "revise" | "reflect";
  /** Ayah this step points at, or null for the reflect step. */
  target: { sura: number; aya: number } | null;
  title: string;
  detail: string;
};

export function buildPlan(
  lang: Lang,
  sura: Sura,
  current: AyahBrief,
  previous: AyahBrief | null,
): PlanStep[] {
  const steps: PlanStep[] = [
    {
      key: "memorize",
      target: { sura: sura.number, aya: current.aya },
      title: `${sura.translit} ${sura.number}:${current.aya}`,
      detail: `${t(lang, "plan_type_recite")} · ${mins(lang, current.seconds)}`,
    },
  ];
  if (previous) {
    steps.push({
      key: "revise",
      target: { sura: sura.number, aya: previous.aya },
      title: `${sura.translit} ${sura.number}:${previous.aya}`,
      detail: `${t(lang, "plan_type_revise")} · ${mins(lang, previous.seconds)}`,
    });
  }
  steps.push({
    key: "reflect",
    target: null,
    title: t(lang, "plan_reflect_title"),
    detail: t(lang, "plan_reflect_detail"),
  });
  return steps;
}

const ICON = {
  memorize: <PlanMemorize />,
  revise: <PlanRevise />,
  reflect: <PlanReflect />,
};

const LABEL = {
  memorize: "plan_label_memorize",
  revise: "plan_label_revise",
  reflect: "plan_label_reflect",
} as const;

export default function DailyPlan({
  lang,
  steps,
  onOpen,
}: {
  lang: Lang;
  steps: PlanStep[];
  onOpen: (sura: number, aya: number) => void;
}) {
  if (steps.length === 0) return null;

  return (
    <section className="plan">
      <header className="section-head">
        <div>
          <p className="section-label">{t(lang, "plan_kicker")}</p>
          <h2 className="section-title">{t(lang, "plan_title")}</h2>
        </div>
        {/* Counted from the steps actually built, never written as a literal —
            the revise step is absent on the first ayah of a sura, and a
            hard-coded "three quiet steps" over two cards is a small lie that
            costs nothing to avoid. */}
        <p className="section-aside">
          {t(lang, "plan_count").replace("{n}", String(steps.length))}
        </p>
      </header>

      <ol className="plan__list">
        {steps.map((step, i) => {
          const body = (
            <>
              <span className="plan__ordinal" aria-hidden="true">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="plan__label">
                <span className="plan__icon" aria-hidden="true">
                  {ICON[step.key]}
                </span>
                {t(lang, LABEL[step.key])}
              </span>
              <span className="plan__title">{step.title}</span>
              <span className="plan__detail">{step.detail}</span>
            </>
          );
          // A step with somewhere to go is a button; the reflect step points
          // at a card further down this same screen and is not one. A card
          // styled as tappable that does nothing is the control-that-lies
          // failure in its smallest form.
          return (
            <li className="card plan__step" key={step.key}>
              {step.target ? (
                <button
                  className="plan__hit"
                  onClick={() =>
                    onOpen(step.target!.sura, step.target!.aya)
                  }
                >
                  {body}
                </button>
              ) : (
                <div className="plan__hit plan__hit--static">{body}</div>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/** The engine's own per-ayah estimate, rounded to something a person says. */
function mins(lang: Lang, seconds: number): string {
  if (seconds >= 90) {
    return t(lang, "plan_minutes").replace("{n}", String(Math.round(seconds / 60)));
  }
  return t(lang, "plan_seconds").replace("{n}", String(Math.round(seconds)));
}
