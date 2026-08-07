/**
 * The learner's starting level, asked once and then left alone.
 *
 * ── WHAT IT IS AND IS NOT ──────────────────────────────────────────────────
 *
 * It is a SETTING, not a status. Asked during onboarding, stored, and editable
 * from Profile. It must never appear as a banner, a badge, a chip beside their
 * name, or a widget on Today. A learner told daily that they are a "beginner"
 * is being given an identity by an app that has heard them recite once.
 *
 * ── HOW THE ANSWER IS COMPUTED ─────────────────────────────────────────────
 *
 * Three questions, each worth 0/1/2, summed. Not a weighted model — there is no
 * evidence for weights, and inventing some would dress a guess as a measurement.
 * The bands are deliberately generous at the bottom: mis-filing someone as a
 * beginner costs them a slightly gentler start, and mis-filing a beginner as
 * advanced costs them the thing they came for.
 *
 * ⚠️ WHAT CONSUMES IT TODAY: the default reciter, and nothing else. The brief
 * asks for it to weight which verses get suggested first, and that is NOT built
 * here, because this app has no model of ayah difficulty — only length. Sorting
 * suggestions by length and calling it difficulty would be a fabricated
 * pedagogy, which is the same failure as a fabricated statistic in a different
 * coat. The answer is stored, so building that weighting later is a read of
 * this value rather than a re-survey of every learner.
 */

export type Level = "beginner" | "intermediate" | "advanced";

export const LEVEL_KEY = "tilawah_level";

/** The three questions, in order. Each answer scores its index: 0, 1 or 2. */
export const QUESTIONS = [
  {
    id: "alphabet",
    prompt: "assess_q_alphabet",
    options: ["assess_a_alphabet_0", "assess_a_alphabet_1", "assess_a_alphabet_2"],
  },
  {
    id: "tajweed",
    prompt: "assess_q_tajweed",
    options: ["assess_a_tajweed_0", "assess_a_tajweed_1", "assess_a_tajweed_2"],
  },
  {
    id: "fluency",
    prompt: "assess_q_fluency",
    options: ["assess_a_fluency_0", "assess_a_fluency_1", "assess_a_fluency_2"],
  },
] as const;

export const MAX_SCORE = QUESTIONS.length * 2;

/**
 * Answers (0–2 each) → a level.
 *
 * Unanswered questions score 0 rather than being averaged away: skipping is a
 * legitimate choice and the gentler result is the right one to land on.
 */
export function levelFrom(answers: (number | null)[]): Level {
  const score = answers.reduce<number>((sum, a) => sum + (a ?? 0), 0);
  if (score <= 2) return "beginner";
  if (score <= 4) return "intermediate";
  return "advanced";
}

export function storedLevel(): Level | null {
  const raw = localStorage.getItem(LEVEL_KEY);
  return raw === "beginner" || raw === "intermediate" || raw === "advanced"
    ? raw
    : null;
}

export function storeLevel(level: Level): void {
  localStorage.setItem(LEVEL_KEY, level);
}

/** i18n key naming a level, for Profile and for the onboarding summary. */
export const LEVEL_LABEL: Record<Level, string> = {
  beginner: "level_beginner",
  intermediate: "level_intermediate",
  advanced: "level_advanced",
};
