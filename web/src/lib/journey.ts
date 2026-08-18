/**
 * MY JOURNEY — the learner's long-term plan, and the source Home reads from.
 *
 * ── MY JOURNEY vs TODAY'S JOURNEY ──────────────────────────────────────────
 *
 * MY JOURNEY is the standing plan: the goal, the daily commitment, the focus,
 * the practice time, the weekly intention. It changes rarely and only when the
 * learner changes it.
 *
 * TODAY'S JOURNEY is that plan resolved against today — what to actually do in
 * the next fifteen minutes. Home renders that, and never asks the learner to
 * assemble it. See todaysJourney().
 *
 * ── WHAT THIS DELIBERATELY DOES NOT CONTAIN ────────────────────────────────
 *
 * A CURRICULUM. The spec's example journey names a path called "Makharij
 * Foundations" and a day made of Listen / Learn / Practice / Reflect with
 * per-minute timings. None of that exists: there are no courses, no lessons and
 * no listening modules in this product. Writing those four steps in anyway
 * would produce a plan that looks complete and points at nothing, which is the
 * fabricated-curriculum failure the whole project has refused since Soon.tsx.
 *
 * So a day is built from the two things that ARE real:
 *
 *   PRACTICE  recite an ayah, get Tajweed feedback. The engine exists, it
 *             works, and it is what this app is for. Duration comes from the
 *             engine's own per-ayah estimate, not from a number picked to look
 *             tidy.
 *   REFLECT   the day's hadith, cited and gated. Real content, real source.
 *
 * When lessons exist, addSteps here and Home picks them up — the shape is
 * ready, it is simply not filled with imaginary things in the meantime.
 */

import { Key, Lang } from "./i18n";

export type Goal =
  | "recitation" | "tajweed" | "memorize" | "habit" | "understand" | "everything";
export type Stage = "beginning" | "improving" | "comfortable" | "memorizing";
export type Focus = "recitation" | "tajweed" | "memorization" | "consistency" | "understanding";
export type Minutes = 5 | 10 | 15 | 20 | 30;
export type When =
  | "after_fajr" | "morning" | "afternoon" | "after_maghrib" | "evening" | "later";

export type Journey = {
  goal: Goal | null;
  stage: Stage | null;
  focus: Focus | null;
  minutes: Minutes | null;
  when: When | null;
  /** Sessions a week the learner intends. Derived, editable. */
  weekly: number;
  /** ISO date the journey was created. */
  created: string;
};

export const JOURNEY_KEY = "tilawah_journey";

export const DEFAULT_JOURNEY: Journey = {
  goal: null, stage: null, focus: null, minutes: null, when: null,
  weekly: 5, created: "",
};

export function storedJourney(): Journey | null {
  try {
    const raw = localStorage.getItem(JOURNEY_KEY);
    if (!raw) return null;
    const j = JSON.parse(raw) as Journey;
    return j && typeof j === "object" ? { ...DEFAULT_JOURNEY, ...j } : null;
  } catch {
    return null;
  }
}

export function storeJourney(j: Journey): void {
  localStorage.setItem(JOURNEY_KEY, JSON.stringify(j));
}

/**
 * Change one field without losing the rest.
 *
 * The brief is explicit that adjusting the plan must not cost the learner their
 * history, so this merges rather than replaces and `created` is never rewritten
 * — the journey is the same journey after an edit, not a new one.
 */
export function adjustJourney(patch: Partial<Journey>): Journey {
  const base = storedJourney() ?? { ...DEFAULT_JOURNEY, created: today() };
  const next = { ...base, ...patch, created: base.created || today() };
  storeJourney(next);
  return next;
}

export const today = () => new Date().toISOString().slice(0, 10);

/* ── today's journey ─────────────────────────────────────────────────────── */

export type StepKind = "practice" | "reflect";

export type DayStep = {
  kind: StepKind;
  /** Minutes, derived from the learner's commitment — never a fixed literal. */
  minutes: number;
  labelKey: Key;
  noteKey: Key;
};

/**
 * The plan, resolved against today.
 *
 * The split follows the learner's own daily commitment rather than fixed
 * numbers: reflection is a couple of minutes at any commitment level, and the
 * rest is practice, because practice is the thing the app actually does. A
 * learner who chose 5 minutes gets a 5-minute day, not a 13-minute day rounded
 * down in the copy.
 */
export function todaysJourney(j: Journey | null): DayStep[] {
  const total = j?.minutes ?? 10;
  const reflect = total <= 5 ? 1 : 2;
  const practice = Math.max(1, total - reflect);
  return [
    { kind: "practice", minutes: practice,
      labelKey: "step_practice", noteKey: "step_practice_note" },
    { kind: "reflect", minutes: reflect,
      labelKey: "step_reflect", noteKey: "step_reflect_note" },
  ];
}

/* ── labels ──────────────────────────────────────────────────────────────── */

export const GOAL_KEY: Record<Goal, Key> = {
  recitation: "goal_recitation", tajweed: "goal_tajweed",
  memorize: "goal_memorize", habit: "goal_habit",
  understand: "goal_understand", everything: "goal_everything",
};
export const STAGE_KEY: Record<Stage, Key> = {
  beginning: "stage_beginning", improving: "stage_improving",
  comfortable: "stage_comfortable", memorizing: "stage_memorizing",
};
export const FOCUS_KEY: Record<Focus, Key> = {
  recitation: "focus_recitation", tajweed: "focus_tajweed",
  memorization: "focus_memorization", consistency: "focus_consistency",
  understanding: "focus_understanding",
};
export const WHEN_KEY: Record<When, Key> = {
  after_fajr: "when_after_fajr", morning: "when_morning",
  afternoon: "when_afternoon", after_maghrib: "when_after_maghrib",
  evening: "when_evening", later: "when_later",
};

/**
 * What the journey card shows as CURRENT PATH.
 *
 * There is no course catalogue, so this names the learner's chosen focus rather
 * than inventing a path with a title like "Makharij Foundations". It is the
 * honest answer to "what am I working on" given what this app can currently
 * teach, and it changes when they change their focus.
 */
export function currentPathKey(j: Journey | null): Key {
  if (!j?.focus) return "path_unset";
  return FOCUS_KEY[j.focus];
}

/** True once the learner has actually built a journey. */
export const hasJourney = (j: Journey | null): boolean =>
  Boolean(j && j.created);

export type { Lang };
