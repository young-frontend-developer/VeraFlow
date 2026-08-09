/**
 * ONE GOAL, FOUR FIELDS.
 *
 * ══ THE SHAPE IS THE FEATURE ═══════════════════════════════════════════════
 *
 * The reference implementation this was drawn against exposes: Action,
 * Portion, Range, Schedule, Starting Time, Strict Order, four session-type
 * toggles, Completion behaviour, Falling-Behind behaviour and Rounding
 * behaviour. Eleven decisions before you have a goal.
 *
 * This audience skews older and less comfortable with apps, and every one of
 * those fields is a place to get stuck. So the whole model is:
 *
 *     what     ayat | minutes | suras
 *     amount   a number
 *     period   day | week
 *     remind   a time, or nothing
 *
 * Everything else the reference asks about either has one sensible answer or
 * is a question about the app's own bookkeeping wearing the costume of a
 * preference. Those answers are made HERE, in code, once:
 *
 *   STARTING TIME      today. Nobody sets a goal to begin on a date.
 *   STRICT ORDER       no. Progress counts whatever was recited; a learner
 *                      who jumps to Al-Kahf has still practised.
 *   SESSION TYPES      all of them. Every recorded attempt counts. Asking
 *                      which kinds of practice count is asking the learner to
 *                      audit our own event taxonomy.
 *   ROUNDING           none. The period boundary is local midnight, and the
 *                      week starts Monday — the same boundary the streak and
 *                      the week strip already use, so three parts of the app
 *                      cannot disagree about what "today" was.
 *   FALLING BEHIND     nothing happens. No debt carried forward, no catch-up
 *                      quota, no scolding. A missed day is a missed day and
 *                      the next period starts clean. This is the one that
 *                      would most change the feel of the app if it were a
 *                      setting, and it is the one that most clearly should
 *                      not be: a religious-practice app must not invoice you.
 *
 * If any of those ever needs to vary, it becomes a field with a default —
 * never a control that ships switched off.
 *
 * ══ THE REMINDER TIME IS STORED, THE REMINDER IS NOT SENT ══════════════════
 *
 * `remindAt` is "HH:MM" local, and it is written down properly so a scheduler
 * can be attached later without the learner re-entering anything or this
 * feature being rebuilt. Nothing in the app currently delivers it — see the
 * header of lib/notifications.ts for exactly what delivery still needs.
 */

const KEY = "tilawah_goal";

export type GoalUnit = "ayah" | "minute" | "sura";
export type GoalPeriod = "day" | "week";

export type Goal = {
  id: string;
  unit: GoalUnit;
  /** How many `unit` per `period`. Always >= 1. */
  amount: number;
  period: GoalPeriod;
  /** "HH:MM" local, or null for no reminder. */
  remindAt: string | null;
  /** Epoch ms. */
  createdAt: number;
};

/**
 * The three presets, plus the custom starting point.
 *
 * They are plain goals rather than a separate concept — picking a preset
 * writes exactly the goal a learner could have built by hand. That is what
 * keeps "Oʻzim tanlayman" from being a second, more powerful feature: it is
 * the same four fields with the stepper showing.
 */
export const PRESETS = {
  ayah_daily: { unit: "ayah", amount: 1, period: "day" },
  minutes_daily: { unit: "minute", amount: 5, period: "day" },
  sura_weekly: { unit: "sura", amount: 1, period: "week" },
  custom: { unit: "ayah", amount: 3, period: "day" },
} as const satisfies Record<string, Omit<Goal, "id" | "remindAt" | "createdAt">>;

export type PresetId = keyof typeof PRESETS;

/** The step and the ceiling per unit, for the +/- control. */
export const LIMITS: Record<GoalUnit, { min: number; max: number; step: number }> = {
  // One ayah at a time. Someone aiming at ten a day still gets there by tapping.
  ayah: { min: 1, max: 50, step: 1 },
  // Five-minute steps: the difference between 5 and 6 minutes is not a goal.
  minute: { min: 5, max: 120, step: 5 },
  sura: { min: 1, max: 10, step: 1 },
};

export function clampAmount(unit: GoalUnit, n: number): number {
  const { min, max, step } = LIMITS[unit];
  const snapped = Math.round(n / step) * step;
  return Math.min(max, Math.max(min, snapped));
}

export function storedGoal(): Goal | null {
  try {
    const g = JSON.parse(localStorage.getItem(KEY) ?? "null");
    if (!g || typeof g !== "object") return null;
    if (!["ayah", "minute", "sura"].includes(g.unit)) return null;
    if (!["day", "week"].includes(g.period)) return null;
    if (typeof g.amount !== "number" || !(g.amount >= 1)) return null;
    return {
      id: typeof g.id === "string" ? g.id : newId(),
      unit: g.unit,
      amount: clampAmount(g.unit, g.amount),
      period: g.period,
      remindAt: typeof g.remindAt === "string" && /^\d\d:\d\d$/.test(g.remindAt)
        ? g.remindAt
        : null,
      createdAt: typeof g.createdAt === "number" ? g.createdAt : Date.now(),
    };
  } catch {
    return null;
  }
}

export function saveGoal(g: Omit<Goal, "id" | "createdAt"> & Partial<Goal>): Goal {
  const goal: Goal = {
    id: g.id ?? newId(),
    unit: g.unit,
    amount: clampAmount(g.unit, g.amount),
    period: g.period,
    remindAt: g.remindAt ?? null,
    createdAt: g.createdAt ?? Date.now(),
  };
  try {
    localStorage.setItem(KEY, JSON.stringify(goal));
  } catch {
    // Storage full or blocked. The goal stays in React state for this session;
    // silently failing is better than an error dialog about localStorage in
    // front of someone who just set their first goal.
  }
  return goal;
}

export function clearGoal(): void {
  localStorage.removeItem(KEY);
}

/* ── progress, counted from real attempts and nothing else ───────────────── */

/**
 * The window a goal is measured over, as [startMs, nowMs).
 *
 * Local midnight for a day; Monday local midnight for a week. Deliberately the
 * same boundaries lib/progress.ts uses for the streak and the week strip — if
 * this file drew its own, Home could show a goal met on a day the strip called
 * empty, and there would be no way for the learner to tell which was lying.
 */
export function periodStart(period: GoalPeriod, now = new Date()): number {
  const d = new Date(now);
  d.setHours(0, 0, 0, 0);
  if (period === "week") {
    // getDay(): 0 = Sunday. The app's week runs Monday-first.
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  }
  return d.getTime();
}

/**
 * How far into the goal this period is, from stored attempts.
 *
 * NOTHING IS INVENTED HERE. With retention declined there are no rows, so this
 * returns 0 and the card says 0 — it does not fall back to a guess, and it
 * does not hide itself to avoid showing a zero.
 *
 *   ayah    distinct sura:aya recited in the period. DISTINCT, because
 *           reciting the same verse eight times is practice but it is not
 *           eight ayat, and a goal that counts it as eight is a goal you can
 *           meet without moving.
 *   minute  recorded seconds, which is real elapsed recitation.
 *   sura    distinct suras touched. A generous reading of "one sura a week" —
 *           the strict one needs every ayah of it, which turns a gentle
 *           weekly goal into a 286-ayah obligation on Al-Baqara.
 */
export function progress(
  goal: Goal,
  rows: {
    sura: number;
    aya: number;
    created_at?: string | null;
    duration_s?: number;
  }[],
): { done: number; target: number; fraction: number } {
  const from = periodStart(goal.period);
  const inPeriod = rows.filter((r) => {
    const t = r.created_at ? Date.parse(r.created_at) : NaN;
    return Number.isFinite(t) && t >= from;
  });

  let done = 0;
  if (goal.unit === "ayah") {
    done = new Set(inPeriod.map((r) => `${r.sura}:${r.aya}`)).size;
  } else if (goal.unit === "sura") {
    done = new Set(inPeriod.map((r) => r.sura)).size;
  } else {
    done = Math.floor(
      inPeriod.reduce((s, r) => s + (r.duration_s ?? 0), 0) / 60,
    );
  }

  const target = goal.amount;
  return { done, target, fraction: Math.min(1, target > 0 ? done / target : 0) };
}

const newId = () =>
  `g_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
