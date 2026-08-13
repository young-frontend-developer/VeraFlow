import { Attempt, TajweedError, ErrorKind, ErrorContent, PracticeRung } from "./api";

export type ErrorKey = `${string}:${string}`;

export type WeaknessEntry = {
  code: string;
  letter: string;
  kind: ErrorKind;
  count: number;
  attempts: number;
  recentCount: number;
  olderCount: number;
  corrected: number;
  correctionRate: number;
  firstSeen: string;
  lastSeen: string;
  isL1Pair: boolean;
  wrongFlagged: number;
  content: ErrorContent;
  practice: PracticeRung[];
  ruleName: string;
  makhraj: string;
  articulation: string;
  words: string[];
  sura: number;
  aya: number;
};

export type ProgressEntry = {
  code: string;
  letter: string;
  firstRate: number;
  latestRate: number;
  improving: boolean | null;
};

export type TimeBucket = {
  weekLabel: string;
  errorRate: number;
  count: number;
};

const keyOf = (e: TajweedError): ErrorKey => `${e.code}:${e.letter}`;

const RECENT_DAYS = 7;

function isRecent(created: string, now: Date): boolean {
  return now.getTime() - new Date(created).getTime() < RECENT_DAYS * 86400_000;
}

// ponytail: all L1_PAIRS codes start with SUB_ — checked against typed_errors.py
const isL1 = (code: string) => code.startsWith("SUB_");

type Acc = {
  code: string;
  letter: string;
  kind: ErrorKind;
  count: number;
  recentCount: number;
  olderCount: number;
  attemptIds: Set<number | null>;
  firstSeen: string;
  lastSeen: string;
  content: ErrorContent;
  practice: PracticeRung[];
  ruleName: string;
  makhraj: string;
  articulation: string;
  words: string[];
  sura: number;
  aya: number;
  locations: { sura: number; aya: number; created: string }[];
};

export function weaknesses(rows: Attempt[], now = new Date()): WeaknessEntry[] {
  const valid = rows.filter(
    (r) => r.status === "ok" && r.analysable && !r.wrong_flag,
  );
  const flagged = rows.filter((r) => r.wrong_flag);

  const map = new Map<ErrorKey, Acc>();

  for (const row of valid) {
    const created = row.created_at ?? "";
    const recent = created ? isRecent(created, now) : false;

    for (const e of row.errors) {
      const key = keyOf(e);
      let acc = map.get(key);
      if (!acc) {
        acc = {
          code: e.code,
          letter: e.letter,
          kind: e.kind,
          count: 0,
          recentCount: 0,
          olderCount: 0,
          attemptIds: new Set(),
          firstSeen: created,
          lastSeen: created,
          content: e.content,
          practice: e.practice,
          ruleName: e.rule_name ?? "",
          makhraj: e.makhraj ?? "",
          articulation: e.articulation ?? "",
          words: e.words ?? [],
          sura: row.sura,
          aya: row.aya,
          locations: [],
        };
        map.set(key, acc);
      }
      acc.count++;
      acc.attemptIds.add(row.id);
      if (recent) acc.recentCount++;
      else acc.olderCount++;
      if (created && created < acc.firstSeen) acc.firstSeen = created;
      if (created && created > acc.lastSeen) {
        acc.lastSeen = created;
        acc.content = e.content;
        acc.practice = e.practice;
        acc.ruleName = e.rule_name ?? "";
        acc.makhraj = e.makhraj ?? "";
        acc.articulation = e.articulation ?? "";
        acc.words = e.words ?? [];
        acc.sura = row.sura;
        acc.aya = row.aya;
      }
      acc.locations.push({ sura: row.sura, aya: row.aya, created });
    }
  }

  // Count wrong-flagged occurrences per key
  const flagCounts = new Map<ErrorKey, number>();
  for (const row of flagged) {
    for (const e of row.errors) {
      const key = keyOf(e);
      flagCounts.set(key, (flagCounts.get(key) ?? 0) + 1);
    }
  }

  // Correction rate: for each (code, letter), find attempts on the same sura:aya
  // where the error appeared, and check if the NEXT attempt on that sura:aya
  // no longer contains it
  const bySuraAya = new Map<string, Attempt[]>();
  for (const row of valid) {
    const loc = `${row.sura}:${row.aya}`;
    if (!bySuraAya.has(loc)) bySuraAya.set(loc, []);
    bySuraAya.get(loc)!.push(row);
  }
  for (const arr of bySuraAya.values()) {
    arr.sort(
      (a, b) =>
        new Date(a.created_at ?? 0).getTime() -
        new Date(b.created_at ?? 0).getTime(),
    );
  }

  const entries: WeaknessEntry[] = [];

  for (const [key, acc] of map) {
    let corrected = 0;
    const locs = acc.locations;
    const seen = new Set<string>();
    for (const loc of locs) {
      const locKey = `${loc.sura}:${loc.aya}`;
      if (seen.has(`${locKey}:${loc.created}`)) continue;
      seen.add(`${locKey}:${loc.created}`);

      const chain = bySuraAya.get(locKey);
      if (!chain) continue;
      const idx = chain.findIndex(
        (r) => r.created_at === loc.created,
      );
      if (idx < 0 || idx + 1 >= chain.length) continue;
      const next = chain[idx + 1];
      const stillThere = next.errors.some((e) => keyOf(e) === key);
      if (!stillThere) corrected++;
    }

    entries.push({
      code: acc.code,
      letter: acc.letter,
      kind: acc.kind,
      count: acc.count,
      attempts: acc.attemptIds.size,
      recentCount: acc.recentCount,
      olderCount: acc.olderCount,
      corrected,
      correctionRate: acc.count > 0 ? corrected / acc.count : 0,
      firstSeen: acc.firstSeen,
      lastSeen: acc.lastSeen,
      isL1Pair: isL1(acc.code),
      wrongFlagged: flagCounts.get(key) ?? 0,
      content: acc.content,
      practice: acc.practice,
      ruleName: acc.ruleName,
      makhraj: acc.makhraj,
      articulation: acc.articulation,
      words: acc.words,
      sura: acc.sura,
      aya: acc.aya,
    });
  }

  entries.sort(
    (a, b) => b.recentCount - a.recentCount || b.count - a.count,
  );
  return entries;
}

export function todaysFocus(entries: WeaknessEntry[]): WeaknessEntry | null {
  return entries.length > 0 && entries[0].recentCount > 0
    ? entries[0]
    : null;
}

export function progressPairs(rows: Attempt[]): ProgressEntry[] {
  const valid = rows
    .filter((r) => r.status === "ok" && r.analysable && !r.wrong_flag)
    .sort(
      (a, b) =>
        new Date(a.created_at ?? 0).getTime() -
        new Date(b.created_at ?? 0).getTime(),
    );

  const byKey = new Map<ErrorKey, { code: string; letter: string; indices: number[] }>();
  for (let i = 0; i < valid.length; i++) {
    for (const e of valid[i].errors) {
      const key = keyOf(e);
      if (!byKey.has(key)) byKey.set(key, { code: e.code, letter: e.letter, indices: [] });
      byKey.get(key)!.indices.push(i);
    }
  }

  const result: ProgressEntry[] = [];
  for (const [, entry] of byKey) {
    if (entry.indices.length < 3) {
      result.push({
        code: entry.code,
        letter: entry.letter,
        firstRate: 0,
        latestRate: 0,
        improving: null,
      });
      continue;
    }
    const n = valid.length;
    const third = Math.ceil(n / 3);
    const firstThird = valid.slice(0, third);
    const lastThird = valid.slice(n - third);

    const firstHits = firstThird.filter((r) =>
      r.errors.some((e) => `${e.code}:${e.letter}` === `${entry.code}:${entry.letter}`),
    ).length;
    const lastHits = lastThird.filter((r) =>
      r.errors.some((e) => `${e.code}:${e.letter}` === `${entry.code}:${entry.letter}`),
    ).length;

    const firstRate = firstThird.length > 0 ? firstHits / firstThird.length : 0;
    const latestRate = lastThird.length > 0 ? lastHits / lastThird.length : 0;

    result.push({
      code: entry.code,
      letter: entry.letter,
      firstRate,
      latestRate,
      improving: latestRate < firstRate,
    });
  }
  return result;
}

function mondayOf(d: Date): string {
  const copy = new Date(d);
  copy.setHours(0, 0, 0, 0);
  copy.setDate(copy.getDate() - ((d.getDay() + 6) % 7));
  const p = (n: number) => String(n).padStart(2, "0");
  return `${copy.getFullYear()}-${p(copy.getMonth() + 1)}-${p(copy.getDate())}`;
}

export function timeBuckets(
  rows: Attempt[],
  code: string,
  letter: string,
): TimeBucket[] {
  const valid = rows.filter(
    (r) => r.status === "ok" && r.analysable && !r.wrong_flag && r.created_at,
  );

  const weeks = new Map<string, { total: number; hits: number }>();
  for (const row of valid) {
    const week = mondayOf(new Date(row.created_at!));
    if (!weeks.has(week)) weeks.set(week, { total: 0, hits: 0 });
    const w = weeks.get(week)!;
    w.total++;
    if (row.errors.some((e) => e.code === code && e.letter === letter)) {
      w.hits++;
    }
  }

  return [...weeks.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([weekLabel, { total, hits }]) => ({
      weekLabel,
      errorRate: total > 0 ? hits / total : 0,
      count: hits,
    }));
}

export type SessionImprovement = {
  before: number;
  after: number;
  fixed: boolean;
};

export function sessionImprovement(
  original: Attempt,
  retry: Attempt,
  error: TajweedError,
): SessionImprovement {
  const key = keyOf(error);
  const beforeHits = original.errors.filter((e) => keyOf(e) === key).length;
  const afterHits = retry.errors.filter((e) => keyOf(e) === key).length;
  const total = original.errors.length || 1;
  return {
    before: beforeHits / total,
    after: afterHits / total,
    fixed: afterHits === 0,
  };
}
