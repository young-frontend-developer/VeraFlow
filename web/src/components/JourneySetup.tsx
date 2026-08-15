import { Key, Lang, t } from "../lib/i18n";
import {
  GOAL_KEY, Journey, STAGE_KEY, WHEN_KEY, currentPathKey, todaysJourney,
} from "../lib/journey";
import { StarOrnament, Tick } from "./Ornament";

/**
 * CREATE MY JOURNEY, then JOURNEY READY.
 *
 * Two screens between the questions and the app, and they exist for one reason:
 * the learner should watch their answers become a plan, rather than answer five
 * questions and get dropped on a dashboard. The verb on the button is theirs —
 * they create the journey, the app assists.
 *
 * ── WHAT THESE SCREENS WILL NOT SAY ────────────────────────────────────────
 *
 * The brief's example shows CURRENT PATH: "Makharij Foundations" and a day of
 * Listen 2 min / Learn 4 min / Practice 5 min / Reflect 2 min. There is no
 * course called Makharij Foundations, there are no Listen or Learn modules, and
 * those minute figures describe nothing. Rendering them would hand a learner a
 * plan on day one whose first two steps do not exist — the exact fabricated
 * curriculum this project has refused everywhere else, and the failure is worse
 * here because this screen is designed to be believed.
 *
 * So CURRENT PATH names the focus they chose, and the day is built from the two
 * things that are real: practice and reflection. The shape is the brief's; the
 * contents are only what exists. When lessons are built they slot in and these
 * screens need no redesign.
 *
 * An unanswered question is OMITTED from the summary rather than filled with a
 * default. A plan that quietly answers for you is not your plan.
 */

export function CreateJourney({
  lang,
  journey,
  onCreate,
  onBack,
}: {
  lang: Lang;
  journey: Journey;
  onCreate: () => void;
  onBack: () => void;
}) {
  const rows: [Key, string][] = [];
  if (journey.goal) rows.push(["journey_goal", t(lang, GOAL_KEY[journey.goal])]);
  if (journey.minutes)
    rows.push([
      "journey_daily",
      t(lang, "minutes_n").replace("{n}", String(journey.minutes)),
    ]);
  if (journey.focus)
    rows.push(["journey_focus", t(lang, currentPathKey(journey))]);
  if (journey.when && journey.when !== "later")
    rows.push(["journey_when", t(lang, WHEN_KEY[journey.when])]);
  if (journey.stage)
    rows.push(["journey_stage", t(lang, STAGE_KEY[journey.stage])]);
  rows.push([
    "journey_weekly",
    t(lang, "sessions_n").replace("{n}", String(journey.weekly)),
  ]);

  // Same centred 420px column as every other step. These two screens already
  // carry their own card — the summary IS the card — so they take the column
  // without a second one wrapped around it, the way the account screen sets its
  // heading above its card rather than inside it.
  return (
    <div className="onboard">
      <div className="onboard__inner onboard__step">
        <h2 className="onboard__display">{t(lang, "journey_build_title")}</h2>
        <p className="onboard__lede">{t(lang, "journey_build_body")}</p>

        <article className="card journey">
          <p className="section-label">{t(lang, "journey_mine")}</p>
          <dl className="journey__list">
            {rows.map(([k, v]) => (
              <div className="journey__row" key={k}>
                <dt className="journey__key">{t(lang, k)}</dt>
                <dd className="journey__val">{v}</dd>
              </div>
            ))}
          </dl>
        </article>

        <div className="onboard__foot">
          <button className="btn-primary" onClick={onCreate}>
            {t(lang, "journey_create_cta")}
          </button>
          <button className="onboard__skip" onClick={onBack}>
            {t(lang, "journey_change")}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * The payoff. Restrained: an ornament, a line, the day, the week, and one
 * button into it. No confetti, no celebration graphic, no sound.
 */
export function JourneyReady({
  lang,
  journey,
  onBegin,
}: {
  lang: Lang;
  journey: Journey;
  onBegin: () => void;
}) {
  const day = todaysJourney(journey);

  return (
    <div className="onboard">
      <div className="onboard__inner onboard__step">
        <StarOrnament className="onboard__ornament ready__mark" size={44} />
        <h2 className="onboard__display">{t(lang, "journey_ready_title")}</h2>

        <article className="card">
          <p className="section-label">{t(lang, "journey_today")}</p>
          <ul className="ready__steps">
            {day.map((s) => (
              <li className="ready__step" key={s.kind}>
                <span className="ready__step-name">{t(lang, s.labelKey)}</span>
                <span className="ready__step-min">
                  {t(lang, "minutes_n").replace("{n}", String(s.minutes))}
                </span>
              </li>
            ))}
          </ul>

          <div className="stats__rule" />

          <p className="section-label">{t(lang, "journey_this_week")}</p>
          <p className="ready__week">
            {t(lang, "sessions_n").replace("{n}", String(journey.weekly))}
            {journey.minutes
              ? ` · ${t(lang, "minutes_per_day").replace("{n}", String(journey.minutes))}`
              : ""}
          </p>

          {journey.focus && (
            <>
              <div className="stats__rule" />
              <p className="section-label">{t(lang, "journey_path")}</p>
              <p className="ready__path">
                <span className="ready__path-mark" aria-hidden="true">
                  <Tick />
                </span>
                {t(lang, currentPathKey(journey))}
              </p>
            </>
          )}
        </article>

        <div className="onboard__foot">
          <button className="btn-primary" onClick={onBegin}>
            {t(lang, "journey_begin_cta")}
          </button>
        </div>
      </div>
    </div>
  );
}
