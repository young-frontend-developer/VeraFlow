/**
 * STREAK, HASANAT, XP AND RANK — every one of them counted from real attempts.
 *
 * ── THE DECISION THIS FILE IMPLEMENTS ──────────────────────────────────────
 *
 * The original brief ruled out reward mechanics, and the comments in
 * WeekStats.tsx still argue against them at length. That was reversed
 * deliberately and on the record: streaks, hasanat, XP, levels and badges are a
 * committed product decision. This file builds them properly rather than
 * bolting a counter onto the side of a serious design.
 *
 * ── THE RULE THAT WAS NOT REVERSED ─────────────────────────────────────────
 *
 * NOTHING HERE IS INVENTED. Gamification was reconsidered; fabricated numbers
 * were not. Every figure below is a function of rows the learner actually
 * produced by reciting:
 *
 *   streak    distinct calendar days with a real timestamp on them
 *   hasanat   letters counted by the SERVER from the Uthmani text of the exact
 *             range recited — see api/tilawah/content/letters.py
 *   xp        attempts the engine could judge, attempts that passed, and days
 *             returned. Three things the learner did.
 *   rank      a band of that xp
 *
 * There is no XP for opening the app, no streak freeze, no daily bonus, no
 * multiplier that decays, and nothing at all that moves while the learner is
 * not reciting. A number that can go up without practice is a number that
 * measures engagement rather than recitation, and this app does not need
 * engagement — it needs someone to open their mouth and read.
 *
 * ── THE ZERO STATE IS A REAL STATE ─────────────────────────────────────────
 *
 * With no history every figure here is 0, and callers are expected to DRAW the
 * zeroes rather than hide the section. That is the opposite of what WeekStats
 * does with the week card, and the difference is deliberate: a week strip full
 * of zeroes reads as a verdict on how the learner's week went, whereas "0
 * hasanat, 0 kun" on a brand-new account reads as a counter that has not
 * started yet. The visual treatment carries that — see `.stat--empty`.
 */

import { Attempt } from "./api";
import { Key } from "./i18n";

/* ══ days ═════════════════════════════════════════════════════════════════ */

/** Local calendar day of a timestamp, as YYYY-MM-DD.
 *
 *  LOCAL, not UTC. A learner in Tashkent reciting after ʿIshāʾ is on tomorrow's
 *  date in UTC, and a streak that breaks at 05:00 local because of a timezone
 *  is a bug the learner experiences as the app forgetting them. */
function dayKey(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function daysBetween(a: string, b: string): number {
  return Math.round(
    (new Date(`${b}T00:00:00`).getTime() - new Date(`${a}T00:00:00`).getTime()) /
      86400_000,
  );
}

/** Distinct days with at least one dated attempt, oldest first. */
export function activeDays(rows: Attempt[]): string[] {
  return [
    ...new Set(
      rows
        .filter((r) => Boolean(r.created_at))
        .map((r) => dayKey(new Date(r.created_at as string))),
    ),
  ].sort();
}

export type Streak = { current: number; best: number };

/**
 * Consecutive days of practice, now and at their longest.
 *
 * TODAY OR YESTERDAY KEEPS IT ALIVE. A streak that reads 0 from midnight until
 * the learner next opens the app tells them they have already lost something
 * they have all day to keep, which is the single most punitive way to draw
 * this number. A gap of two days ends it, and nothing in this app can buy it
 * back — there is no freeze and no repair, because those turn the streak into
 * a currency.
 */
export function streak(rows: Attempt[], now = new Date()): Streak {
  const days = activeDays(rows);
  if (days.length === 0) return { current: 0, best: 0 };

  let best = 1;
  let run = 1;
  for (let i = 1; i < days.length; i++) {
    run = daysBetween(days[i - 1], days[i]) === 1 ? run + 1 : 1;
    if (run > best) best = run;
  }

  // The run that reaches the most recent day, counted only if that day is
  // today or yesterday.
  const last = days[days.length - 1];
  const lag = daysBetween(last, dayKey(now));
  let current = 0;
  if (lag <= 1) {
    current = 1;
    for (let i = days.length - 1; i > 0; i--) {
      if (daysBetween(days[i - 1], days[i]) !== 1) break;
      current++;
    }
  }
  return { current, best };
}

/* ══ hasanat ══════════════════════════════════════════════════════════════ */

/**
 * The multiplier from the hadith, and the only magic number in this file.
 *
 *   "Whoever reads a letter from the Book of Allah has a hasana for it, and a
 *    hasana is multiplied tenfold."   — Jami' at-Tirmidhi 2910
 *
 * The client does NOT hold that text. It fetches the entry by id from
 * hadith.json so the words shown beside the number are the reviewed ones —
 * see hadithById() in api.ts and the gate in content/hadith.py. If the source
 * cannot be shown, the CLAIM must not be shown either: the card falls back to
 * reporting letters recited, which is a plain count of what happened and needs
 * no citation at all.
 */
export const HASANAT_PER_LETTER = 10;

/** The hadith this feature rests on. Fetched, never inlined. */
export const HASANAT_HADITH_ID = "tirmidhi-2910";

/**
 * Letters recited, summed from the server's own count.
 *
 * Legacy rows carry no `letters` field and contribute 0 rather than an
 * estimate — the same rule the week strip follows for rows with no timestamp.
 */
export function lettersRecited(rows: Attempt[]): number {
  return rows.reduce((sum, r) => sum + (r.letters || 0), 0);
}

export function hasanat(rows: Attempt[]): number {
  return lettersRecited(rows) * HASANAT_PER_LETTER;
}

/* ══ xp and rank ══════════════════════════════════════════════════════════ */

/**
 * THE THREE THINGS XP IS MADE OF, and why each is worth what it is.
 *
 *   heard    10   the engine received a recording it could analyse. This is
 *                 the floor: you recited, and it counted, whatever the result.
 *                 An attempt that was too noisy to judge earns nothing —
 *                 not as a punishment, but because there is nothing to
 *                 record about it.
 *   clean    15   on top of `heard`, when the attempt cleared the engine's own
 *                 pass mark. Worth more than showing up and less than twice as
 *                 much: reciting is the thing, reciting well is the goal.
 *   day      30   a distinct day returned to. The largest single award,
 *                 because coming back tomorrow is the behaviour that actually
 *                 produces a reciter, and it is the one thing that cannot be
 *                 farmed in a single sitting.
 */
export const XP = { heard: 10, clean: 15, day: 30 } as const;

export function xpFrom(rows: Attempt[]): number {
  const heard = rows.filter((r) => r.analysable).length;
  const clean = rows.filter(
    (r) => r.analysable && (r.score ?? 0) >= (r.pass_score ?? 0.8),
  ).length;
  return heard * XP.heard + clean * XP.clean + activeDays(rows).length * XP.day;
}

export type RankId = "mubtadi" | "tolib" | "qori" | "mutqin" | "mujavvid";

export type Rank = {
  id: RankId;
  /** XP at which this rank begins. */
  at: number;
  /** i18n key for the title. */
  nameKey: Key;
  /** i18n key for the one-line description of what the rank means. */
  noteKey: Key;
};

/**
 * FIVE NAMED STAGES, from the vocabulary the learner already lives in.
 *
 * Arabic terms in their Uzbek forms, each naming a real relationship to the
 * text rather than a rung number: one who begins, one who seeks, one who
 * recites, one who is exact, one who beautifies. They are ORDINARY WORDS in
 * this tradition, which is the point — a learner who reaches "Qori" has been
 * given a word their grandmother would recognise, not a tier from a game.
 *
 * NO TITLE HERE CLAIMS MEMORISATION. There is no Hafiz rank and there will not
 * be one until there is a hifz feature to earn it, because "Hafiz" means
 * something specific and definite to every single user of this app.
 *
 * The thresholds are round numbers chosen for pacing, not derived from
 * anything, and they are stated here rather than computed so they stay put:
 * a rank boundary that moves as the population changes is a rank that means
 * nothing.
 */
export const RANKS: Rank[] = [
  { id: "mubtadi", at: 0, nameKey: "rank_mubtadi", noteKey: "rank_mubtadi_note" },
  { id: "tolib", at: 120, nameKey: "rank_tolib", noteKey: "rank_tolib_note" },
  { id: "qori", at: 400, nameKey: "rank_qori", noteKey: "rank_qori_note" },
  { id: "mutqin", at: 1000, nameKey: "rank_mutqin", noteKey: "rank_mutqin_note" },
  {
    id: "mujavvid",
    at: 2200,
    nameKey: "rank_mujavvid",
    noteKey: "rank_mujavvid_note",
  },
];

export type Standing = {
  rank: Rank;
  /** The one above, or null at the top of the ladder. */
  next: Rank | null;
  xp: number;
  /** 0–1 through the current band. 1 when there is nothing above. */
  fraction: number;
  /** XP still to earn before `next`. 0 at the top. */
  toNext: number;
};

export function standing(xp: number): Standing {
  let i = 0;
  while (i + 1 < RANKS.length && xp >= RANKS[i + 1].at) i++;
  const rank = RANKS[i];
  const next = RANKS[i + 1] ?? null;
  if (!next) return { rank, next, xp, fraction: 1, toNext: 0 };
  const span = next.at - rank.at;
  return {
    rank,
    next,
    xp,
    fraction: Math.min(1, Math.max(0, (xp - rank.at) / span)),
    toNext: Math.max(0, next.at - xp),
  };
}

/* ══ the four numbers Home shows ══════════════════════════════════════════ */

export type Totals = {
  streak: Streak;
  hasanat: number;
  letters: number;
  /** Distinct sura:aya recited, ever. Not attempts — the same ayah practised
   *  six times is one ayah, and counting it as six would make the number a
   *  measure of repetition dressed as a measure of coverage. */
  ayat: number;
  /** Real recorded seconds, summed. */
  seconds: number;
  xp: number;
  standing: Standing;
};

export function totals(rows: Attempt[], now = new Date()): Totals {
  const xp = xpFrom(rows);
  return {
    streak: streak(rows, now),
    hasanat: hasanat(rows),
    letters: lettersRecited(rows),
    ayat: new Set(rows.map((r) => `${r.sura}:${r.aya}`)).size,
    seconds: rows.reduce((sum, r) => sum + (r.duration_s || 0), 0),
    xp,
    standing: standing(xp),
  };
}

/* ══ the week, as three states ════════════════════════════════════════════ */

export type DayState = "done" | "missed" | "pending";

/**
 * The seven days of the current week, Monday first.
 *
 * THREE STATES, AND `pending` IS THE ONE THAT MATTERS. A day that has not
 * happened yet is not a day you missed. Drawing Thursday as a miss on Tuesday
 * morning is how a week strip turns into a list of failures you have not had
 * the chance to avoid yet, and it is the specific thing that makes these
 * widgets feel accusatory. Today counts as pending until something is recited,
 * then flips to done.
 */
export function week(rows: Attempt[], now = new Date()): DayState[] {
  const done = new Set(activeDays(rows));
  const monday = new Date(now);
  monday.setHours(0, 0, 0, 0);
  monday.setDate(monday.getDate() - ((now.getDay() + 6) % 7));

  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    if (done.has(dayKey(d))) return "done";
    return dayKey(d) >= dayKey(now) ? "pending" : "missed";
  });
}
