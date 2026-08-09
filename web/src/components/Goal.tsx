import { useState } from "react";
import { Lang, Key, t } from "../lib/i18n";
import {
  Goal,
  GoalPeriod,
  GoalUnit,
  LIMITS,
  PRESETS,
  PresetId,
  clampAmount,
  progress,
} from "../lib/goals";
import { Attempt } from "../lib/api";
import { Close, Target, Tick } from "./Ornament";

/**
 * SETTING A GOAL, ON ONE SCREEN, WITH FOUR THINGS TO TAP.
 *
 * ══ WHAT THIS DELIBERATELY IS NOT ══════════════════════════════════════════
 *
 * The reference this was drawn against asks for Action, Portion, Range,
 * Schedule, Starting Time, Strict Order, four session-type checkboxes,
 * Completion behaviour, Falling-Behind behaviour and Rounding behaviour —
 * eleven decisions, most of them in vocabulary that belongs to the scheduler
 * rather than to the learner. Every one of those is answered in lib/goals.ts
 * instead, in code, with the reasoning written down next to the answer.
 *
 * What is left is: pick one of four cards. That is the screen.
 *
 * ══ AND NOT A WIZARD ═══════════════════════════════════════════════════════
 *
 * One screen, no steps, no Next. The custom controls do not replace the cards
 * — they open UNDER the fourth one, so the learner can still see what they
 * chose and change their mind without going back anywhere. The Save button is
 * present from the first render and stays in the same place the whole time.
 *
 * ══ THE STEPPER IS A STEPPER AND NOT A FIELD ═══════════════════════════════
 *
 * Two 56px buttons and a number between them. No text input, no dropdown, no
 * slider — a slider is precise pointing, which is the single hardest gesture
 * to make on a phone with unsteady hands, and a number field summons a
 * keyboard on top of the thing you are editing.
 */

const PRESET_ORDER: PresetId[] = [
  "ayah_daily",
  "minutes_daily",
  "sura_weekly",
  "custom",
];

const PRESET_COPY: Record<PresetId, { title: Key; body: Key }> = {
  ayah_daily: { title: "goal_p_ayah_title", body: "goal_p_ayah_body" },
  minutes_daily: { title: "goal_p_minutes_title", body: "goal_p_minutes_body" },
  sura_weekly: { title: "goal_p_sura_title", body: "goal_p_sura_body" },
  custom: { title: "goal_p_custom_title", body: "goal_p_custom_body" },
};

const UNIT_KEY: Record<GoalUnit, Key> = {
  ayah: "goal_unit_ayah",
  minute: "goal_unit_minute",
  sura: "goal_unit_sura",
};

/** "Har kuni 3 oyat" — the goal as one plain sentence, used in four places. */
export function goalSentence(lang: Lang, g: Pick<Goal, "amount" | "unit" | "period">) {
  return t(lang, g.period === "day" ? "goal_sum_day" : "goal_sum_week")
    .replace("{n}", String(g.amount))
    .replace("{unit}", t(lang, UNIT_KEY[g.unit]));
}

export default function GoalScreen({
  lang,
  goal,
  onSave,
  onRemove,
  onClose,
}: {
  lang: Lang;
  /** The goal being edited, or null when setting the first one. */
  goal: Goal | null;
  onSave: (g: Omit<Goal, "id" | "createdAt">) => void;
  onRemove: () => void;
  onClose: () => void;
}) {
  /**
   * Which card is lit.
   *
   * An existing goal reopens on the preset it matches, or on "custom" when it
   * matches none — editing a goal you built by hand must not silently snap it
   * back to "one ayah a day" because that is the first card.
   */
  const [picked, setPicked] = useState<PresetId>(() => matchPreset(goal));
  const [unit, setUnit] = useState<GoalUnit>(goal?.unit ?? PRESETS.ayah_daily.unit);
  const [amount, setAmount] = useState(goal?.amount ?? PRESETS.ayah_daily.amount);
  const [period, setPeriod] = useState<GoalPeriod>(
    goal?.period ?? PRESETS.ayah_daily.period,
  );
  const [remind, setRemind] = useState(goal?.remindAt !== null && goal !== null);
  // 08:00 by default. A reminder to recite belongs to the morning in this
  // app's day, and a default of "now" would fire at whatever minute the
  // learner happened to be setting it.
  const [time, setTime] = useState(goal?.remindAt ?? "08:00");

  function pick(id: PresetId) {
    setPicked(id);
    // A preset REWRITES the three fields rather than merging into them. Tapping
    // "one sura a week" after fiddling with the stepper has to give you one
    // sura a week, not one sura a week at whatever amount was left behind.
    const p = PRESETS[id];
    setUnit(p.unit);
    setAmount(p.amount);
    setPeriod(p.period);
  }

  const custom = picked === "custom";
  const { min, max, step } = LIMITS[unit];

  return (
    <>
      <div className="ayah-nav goal__top">
        <button
          className="ayah-nav__close"
          aria-label={t(lang, "goal_cancel")}
          onClick={onClose}
        >
          <Close />
        </button>
      </div>

      <header className="goal__head">
        <span className="goal__mark" aria-hidden="true">
          <Target size={30} />
        </span>
        <h2 className="goal__title">{t(lang, "goal_new_cta")}</h2>
        <p className="goal__sub">{t(lang, "goal_screen_sub")}</p>
      </header>

      <ul className="goal-picks">
        {PRESET_ORDER.map((id) => {
          const on = picked === id;
          return (
            <li key={id}>
              <button
                className={`goal-pick${on ? " goal-pick--on" : ""}`}
                aria-pressed={on}
                onClick={() => pick(id)}
              >
                <span className="goal-pick__text">
                  <span className="goal-pick__title">
                    {t(lang, PRESET_COPY[id].title)}
                  </span>
                  <span className="goal-pick__body">
                    {t(lang, PRESET_COPY[id].body)}
                  </span>
                </span>
                {/* The chosen card carries a tick rather than only a colour —
                    "which one did I pick" must survive being read by someone
                    who cannot separate the hues. */}
                <span className="goal-pick__state" aria-hidden="true">
                  {on && <Tick size={18} />}
                </span>
              </button>

              {/* THE ONLY TWO CONTROLS THE CUSTOM PATH REVEALS, and they open
                  under the card that asked for them rather than on a second
                  screen. */}
              {id === "custom" && custom && (
                <div className="goal-custom">
                  <p className="goal-custom__label">{t(lang, "goal_what")}</p>
                  <div className="goal-seg">
                    {(["ayah", "minute", "sura"] as const).map((u) => (
                      <button
                        key={u}
                        className={`goal-seg__btn${unit === u ? " is-on" : ""}`}
                        aria-pressed={unit === u}
                        onClick={() => {
                          setUnit(u);
                          // Re-clamp: 5 minutes is legal, 5 suras is not.
                          setAmount((n) => clampAmount(u, n));
                        }}
                      >
                        {t(lang, UNIT_KEY[u])}
                      </button>
                    ))}
                  </div>

                  <p className="goal-custom__label">{t(lang, "goal_how_much")}</p>
                  <div className="stepper">
                    <button
                      className="stepper__btn"
                      aria-label={t(lang, "goal_less")}
                      disabled={amount <= min}
                      onClick={() => setAmount((n) => clampAmount(unit, n - step))}
                    >
                      −
                    </button>
                    <span className="stepper__value">
                      <span className="stepper__num">{amount}</span>
                      <span className="stepper__unit">
                        {t(lang, UNIT_KEY[unit])}
                      </span>
                    </span>
                    <button
                      className="stepper__btn"
                      aria-label={t(lang, "goal_more")}
                      disabled={amount >= max}
                      onClick={() => setAmount((n) => clampAmount(unit, n + step))}
                    >
                      +
                    </button>
                  </div>

                  <p className="goal-custom__label">{t(lang, "goal_how_often")}</p>
                  <div className="goal-seg">
                    {(["day", "week"] as const).map((p) => (
                      <button
                        key={p}
                        className={`goal-seg__btn${period === p ? " is-on" : ""}`}
                        aria-pressed={period === p}
                        onClick={() => setPeriod(p)}
                      >
                        {t(lang, p === "day" ? "goal_every_day" : "goal_every_week")}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {/* ── the one toggle ─────────────────────────────────────────────────
             A switch and, if it is on, a time. Nothing else: no repeat rule,
             no snooze, no per-day schedule. `<input type="time">` on purpose —
             the platform's own picker is the one control on this screen that
             every learner has already used, in every other app on the phone. */}
      <div className="card goal-remind">
        <label className="goal-remind__row">
          <span className="goal-remind__text">
            <span className="goal-remind__label">{t(lang, "goal_remind")}</span>
            <span className="goal-remind__help">{t(lang, "goal_remind_help")}</span>
          </span>
          <input
            type="checkbox"
            className="switch"
            checked={remind}
            onChange={(e) => setRemind(e.target.checked)}
          />
        </label>

        {remind && (
          <div className="goal-remind__when">
            <span className="goal-remind__label">{t(lang, "goal_remind_time")}</span>
            <input
              type="time"
              className="time-input"
              value={time}
              onChange={(e) => setTime(e.target.value || "08:00")}
            />
          </div>
        )}
      </div>

      <div className="goal__actions">
        <button
          className="btn-primary"
          onClick={() =>
            onSave({
              unit,
              amount: clampAmount(unit, amount),
              period,
              remindAt: remind ? time : null,
            })
          }
        >
          {t(lang, "goal_save")}
        </button>

        {/* Only when there is one to remove. Quiet, and last. */}
        {goal && (
          <button className="btn-quiet goal__remove" onClick={onRemove}>
            {t(lang, "goal_remove")}
          </button>
        )}
      </div>
    </>
  );
}

/* ══ the card on Home ═════════════════════════════════════════════════════ */

/**
 * Either an invitation to set a goal, or the goal with its progress.
 *
 * THE PROGRESS FIGURE IS COUNTED FROM REAL ATTEMPTS and nothing else — see
 * `progress` in lib/goals.ts. With retention declined there are no rows and
 * this reads 0, which is true; it does not estimate and it does not hide.
 */
export function GoalCard({
  lang,
  goal,
  rows,
  onOpen,
}: {
  lang: Lang;
  goal: Goal | null;
  rows: Attempt[] | null;
  onOpen: () => void;
}) {
  if (!goal) {
    return (
      <section className="today__block">
        <article className="card goal-invite">
          <span className="goal-invite__mark" aria-hidden="true">
            <Target size={26} />
          </span>
          <p className="section-label">{t(lang, "goal_home_kicker")}</p>
          <h3 className="goal-invite__title">{t(lang, "goal_home_title")}</h3>
          <p className="goal-invite__body">{t(lang, "goal_home_body")}</p>
          <button className="btn-primary" onClick={onOpen}>
            {t(lang, "goal_new_cta")}
          </button>
        </article>
      </section>
    );
  }

  const { done, target, fraction } = progress(goal, rows ?? []);
  const met = done >= target;

  return (
    <section className="today__block">
      <article className={`card goal-live${met ? " goal-live--met" : ""}`}>
        <div className="goal-live__head">
          <div>
            <p className="section-label">{t(lang, "goal_active_kicker")}</p>
            <h3 className="goal-live__name">{goalSentence(lang, goal)}</h3>
          </div>
          <span className="goal-live__mark" aria-hidden="true">
            {met ? <Tick size={26} /> : <Target size={26} />}
          </span>
        </div>

        <div className="progress" aria-hidden="true">
          <span
            className="progress__fill"
            style={{ width: `${Math.round(fraction * 100)}%` }}
          />
        </div>

        <div className="goal-live__foot">
          <span className="goal-live__count">
            {done} / {target} {t(lang, UNIT_KEY[goal.unit])}
          </span>
          <span className="goal-live__remind">
            {goal.remindAt
              ? t(lang, "goal_reminder_at").replace("{t}", goal.remindAt)
              : t(lang, "goal_no_reminder")}
          </span>
        </div>

        <button className="btn-quiet goal-live__edit" onClick={onOpen}>
          {t(lang, "goal_change")}
        </button>
      </article>
    </section>
  );
}

/** Which preset a stored goal came from, or "custom" when it matches none. */
function matchPreset(goal: Goal | null): PresetId {
  if (!goal) return "ayah_daily";
  for (const id of PRESET_ORDER) {
    if (id === "custom") continue;
    const p = PRESETS[id];
    if (p.unit === goal.unit && p.amount === goal.amount && p.period === goal.period)
      return id;
  }
  return "custom";
}
