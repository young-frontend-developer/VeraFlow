/**
 * ACHIEVEMENTS.
 *
 * ── WHY THIS EXISTS AT ALL, ON THE RECORD ──────────────────────────────────
 *
 * The project brief ruled out badges and reward mechanics, and that rule was
 * restated as recently as the dashboard work. It was then explicitly reversed:
 * asked directly, with the conflict laid out, the decision was to build the
 * achievement system and to show a preview on Home. That is a legitimate
 * product call and it is implemented here without further argument. The history
 * is recorded because a future reader finding badges in a codebase whose
 * comments elsewhere forbid them deserves to know it was deliberate.
 *
 * ── THE RULE THAT WAS NOT REVERSED ─────────────────────────────────────────
 *
 * Every badge is EARNED FROM REAL ATTEMPTS. Gamification was reconsidered;
 * fabricated statistics were not, and a badge is a statistic with a picture on
 * it. Nothing here unlocks on a timer, on app opens, or on anything the learner
 * did not actually do.
 *
 * ── THE HONEST HALF-BUILT PROBLEM ──────────────────────────────────────────
 *
 * The requested list names achievements for features THIS PRODUCT DOES NOT
 * HAVE: memorization, and a course path with milestones. Those cannot be earned
 * because the thing they measure cannot be done. Two bad options were rejected:
 *
 *   - award them on some loosely related signal, which makes the badge a lie
 *   - draw them locked and say nothing, so the learner hunts for a way to earn
 *     something unreachable
 *
 * So they carry `blocked: true` and the UI says plainly that this part of the
 * app is not built yet. A locked badge you can work toward and a locked badge
 * nobody can earn are different things and must not look identical.
 */

import { Attempt } from "./api";
import { Key } from "./i18n";

export type AchievementId =
  | "first_step" | "first_voice" | "beginning_hifz" | "moment_reflect"
  | "ayah_by_ayah" | "one_surah" | "every_letter" | "steady_tongue"
  | "first_ayahs" | "surah_by_heart" | "returning_daily" | "month_returning"
  | "words_to_carry" | "returning_heart" | "journey_completed";

export type Achievement = {
  id: AchievementId;
  /** i18n keys for the name and the one-line "how" note. */
  nameKey: Key;
  howKey: Key;
  /**
   * The feature this measures does not exist yet, so it cannot be earned by
   * anyone. Shown differently from an ordinary locked badge — see the note
   * above.
   */
  blocked?: boolean;
};

/** Signals computed once from real history, then read by every predicate. */
export type Signals = {
  attempts: number;
  /** Attempts the engine actually judged. */
  judged: number;
  distinctAyat: number;
  /** Largest count of distinct ayat recited within one sura. */
  bestSuraCoverage: { covered: number; total: number };
  /** Attempts scoring at or above the pass mark. */
  clean: number;
  /** Distinct calendar days with at least one attempt. */
  activeDays: number;
  /** Distinct active days within the last 30. */
  activeDays30: number;
  /** Returned after a gap of 7+ days. */
  returnedAfterGap: boolean;
  /** Reflections the learner opened. Local, private, never uploaded. */
  reflections: number;
  /** They completed onboarding and built a journey. */
  hasJourney: boolean;
};

export const ALL: Achievement[] = [
  { id: "first_step", nameKey: "ach_first_step", howKey: "ach_first_step_how" },
  { id: "first_voice", nameKey: "ach_first_voice", howKey: "ach_first_voice_how" },
  { id: "moment_reflect", nameKey: "ach_moment_reflect", howKey: "ach_moment_reflect_how" },
  { id: "ayah_by_ayah", nameKey: "ach_ayah_by_ayah", howKey: "ach_ayah_by_ayah_how" },
  { id: "steady_tongue", nameKey: "ach_steady_tongue", howKey: "ach_steady_tongue_how" },
  { id: "one_surah", nameKey: "ach_one_surah", howKey: "ach_one_surah_how" },
  { id: "returning_daily", nameKey: "ach_returning_daily", howKey: "ach_returning_daily_how" },
  { id: "words_to_carry", nameKey: "ach_words_to_carry", howKey: "ach_words_to_carry_how" },
  { id: "month_returning", nameKey: "ach_month_returning", howKey: "ach_month_returning_how" },
  { id: "returning_heart", nameKey: "ach_returning_heart", howKey: "ach_returning_heart_how" },
  // ── not earnable yet: the feature they measure does not exist ──────────
  { id: "every_letter", nameKey: "ach_every_letter", howKey: "ach_every_letter_how", blocked: true },
  { id: "beginning_hifz", nameKey: "ach_beginning_hifz", howKey: "ach_beginning_hifz_how", blocked: true },
  { id: "first_ayahs", nameKey: "ach_first_ayahs", howKey: "ach_first_ayahs_how", blocked: true },
  { id: "surah_by_heart", nameKey: "ach_surah_by_heart", howKey: "ach_surah_by_heart_how", blocked: true },
  { id: "journey_completed", nameKey: "ach_journey_completed", howKey: "ach_journey_completed_how", blocked: true },
];

const EARNED: Record<AchievementId, (s: Signals) => boolean> = {
  first_step: (s) => s.hasJourney,
  first_voice: (s) => s.attempts >= 1,
  moment_reflect: (s) => s.reflections >= 1,
  ayah_by_ayah: (s) => s.distinctAyat >= 10,
  steady_tongue: (s) => s.clean >= 10,
  one_surah: (s) =>
    s.bestSuraCoverage.total > 0 &&
    s.bestSuraCoverage.covered >= s.bestSuraCoverage.total,
  returning_daily: (s) => s.activeDays >= 3,
  words_to_carry: (s) => s.reflections >= 7,
  month_returning: (s) => s.activeDays30 >= 20,
  returning_heart: (s) => s.returnedAfterGap,
  // Unreachable by construction. Never true — see `blocked`.
  every_letter: () => false,
  beginning_hifz: () => false,
  first_ayahs: () => false,
  surah_by_heart: () => false,
  journey_completed: () => false,
};

export const REFLECTIONS_KEY = "veyraflow_reflections";

/** Reflections opened, counted locally. Private: never sent anywhere. */
export function countReflection(): number {
  const n = Number(localStorage.getItem(REFLECTIONS_KEY) ?? 0) + 1;
  localStorage.setItem(REFLECTIONS_KEY, String(n));
  return n;
}

export function readReflections(): number {
  return Number(localStorage.getItem(REFLECTIONS_KEY) ?? 0) || 0;
}

/**
 * Real history → the signals every predicate reads.
 *
 * `suraTotals` maps sura number to its ayah count, so "one surah, well known"
 * can mean what it says. Without it that badge stays locked rather than
 * guessing a denominator.
 */
export function signalsFrom(
  rows: Attempt[],
  suraTotals: Record<number, number>,
  opts: { hasJourney: boolean },
): Signals {
  const dated = rows.filter((r) => Boolean(r.created_at));
  const days = [
    ...new Set(dated.map((r) => (r.created_at as string).slice(0, 10))),
  ].sort();

  const now = Date.now();
  const activeDays30 = days.filter(
    (d) => now - new Date(d).getTime() <= 30 * 86400_000,
  ).length;

  // A real return: a gap of a week or more, and then another session.
  let returnedAfterGap = false;
  for (let i = 1; i < days.length; i++) {
    const gap =
      (new Date(days[i]).getTime() - new Date(days[i - 1]).getTime()) / 86400_000;
    if (gap >= 7) returnedAfterGap = true;
  }

  const perSura = new Map<number, Set<number>>();
  for (const r of rows) {
    if (!perSura.has(r.sura)) perSura.set(r.sura, new Set());
    perSura.get(r.sura)!.add(r.aya);
  }
  let best = { covered: 0, total: 0 };
  for (const [sura, ayat] of perSura) {
    const total = suraTotals[sura] ?? 0;
    if (total && ayat.size / total > (best.total ? best.covered / best.total : 0)) {
      best = { covered: ayat.size, total };
    }
  }

  return {
    attempts: rows.length,
    judged: rows.filter((r) => r.analysable).length,
    distinctAyat: new Set(rows.map((r) => `${r.sura}:${r.aya}`)).size,
    bestSuraCoverage: best,
    clean: rows.filter(
      (r) => (r.score ?? 0) >= (r.pass_score ?? 0.8) && r.analysable,
    ).length,
    activeDays: days.length,
    activeDays30,
    returnedAfterGap,
    reflections: readReflections(),
    hasJourney: opts.hasJourney,
  };
}

export type Awarded = Achievement & { earned: boolean };

export function award(signals: Signals): Awarded[] {
  return ALL.map((a) => ({ ...a, earned: EARNED[a.id](signals) }));
}

/**
 * The few Home shows. Earned only — a "recent achievements" row full of locked
 * badges is a list of things you have not done, on the screen that is supposed
 * to answer what to do next.
 */
export function recent(signals: Signals, n = 3): Awarded[] {
  return award(signals).filter((a) => a.earned).slice(0, n);
}
