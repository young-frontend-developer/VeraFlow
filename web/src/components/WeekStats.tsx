import { Attempt } from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { Blank } from "./States";
import { ArchOrnament } from "./Ornament";

/**
 * THE WEEK STRIP AND THREE NUMBERS — drawn only from attempts that happened.
 *
 * This is the section of the reference design most likely to be built as a
 * decoration. A week row with today highlighted and three big serif figures
 * under it looks finished the moment it is drawn, and it looks equally
 * finished when the figures are placeholders. In an app that reports on
 * someone's recitation, a fabricated accuracy percentage is the worst possible
 * thing to draw well.
 *
 * So every figure here is counted from real rows:
 *
 *   verses    distinct sura:aya the learner actually recited this week
 *   time      the sum of their real recording durations
 *   accuracy  the mean of the engine's own scores, over the attempts that
 *             produced one. NOT over all attempts — a rejected recording has
 *             no score, and averaging it in as a zero would invent a failure
 *             that never happened.
 *
 * WITH NO ATTEMPTS THERE ARE NO STATISTICS, and the card becomes a designed
 * empty state rather than three zeroes. Zeroes read as a verdict on the
 * learner; the empty state reads as the app waiting for them, which is what is
 * actually true. It gets the same card, the same ornament and the same care as
 * the populated version — an empty state built carelessly is how a new user
 * decides the app is unfinished.
 *
 * CONSENT COMES FIRST. With retention declined there is no history to count and
 * the section is not drawn at all — not even the empty state, which would
 * quietly imply the numbers are coming once they recite. They are not; the
 * learner turned them off, and Profile is where that gets changed.
 */

/** Monday-indexed, because the week starts on Monday here. */
function mondayIndex(d: Date): number {
  return (d.getDay() + 6) % 7;
}

function startOfWeek(now: Date): Date {
  const d = new Date(now);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - mondayIndex(d));
  return d;
}

export default function WeekStats({
  lang,
  rows,
  consented,
  onBrowse,
}: {
  lang: Lang;
  /** Real attempts, newest first. Null while loading. */
  rows: Attempt[] | null;
  consented: boolean;
  onBrowse: () => void;
}) {
  // Nothing to count and no prospect of counting anything. Say nothing.
  if (!consented) return null;
  if (rows === null) return null;

  const now = new Date();
  const weekStart = startOfWeek(now);

  // Only rows the server timestamped. A legacy row with no created_at leaves
  // its day unmarked rather than landing on an arbitrary one.
  const dated = rows.filter((r) => Boolean(r.created_at));
  const thisWeek = dated.filter(
    (r) => new Date(r.created_at as string) >= weekStart,
  );

  const verses = new Set(thisWeek.map((r) => `${r.sura}:${r.aya}`)).size;
  const seconds = thisWeek.reduce((sum, r) => sum + (r.duration_s || 0), 0);
  // Scored attempts only — see the note above on why a rejected recording is
  // not an accuracy of zero.
  const scored = thisWeek.filter((r) => typeof r.score === "number" && r.score > 0);
  const accuracy = scored.length
    ? scored.reduce((sum, r) => sum + (r.score as number), 0) / scored.length
    : null;

  // ── the month grid ────────────────────────────────────────────────────
  // Five weeks back to today, Monday-first, so the grid always ends on the
  // current week rather than on a month boundary the learner did not choose.
  const gridStart = new Date(weekStart);
  gridStart.setDate(gridStart.getDate() - 7 * 4);
  const byDay = new Set(
    dated.map((r) => new Date(r.created_at as string).toDateString()),
  );
  const monthCells = Array.from({ length: 35 }, (_, i) => {
    const d = new Date(gridStart);
    d.setDate(d.getDate() + i);
    return {
      key: d.toISOString().slice(0, 10),
      active: byDay.has(d.toDateString()),
      future: d > now,
      today: d.toDateString() === now.toDateString(),
    };
  });

  // Seconds recited per active day, oldest first. Time, not accuracy: a chart
  // of accuracy over time is a performance graph, and this app does not draw
  // one of those.
  const perDay = new Map<string, number>();
  for (const r of dated) {
    const k = new Date(r.created_at as string).toISOString().slice(0, 10);
    perDay.set(k, (perDay.get(k) ?? 0) + (r.duration_s || 0));
  }
  const trend = [...perDay.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-14)
    .map(([key, value]) => ({ key, value }));
  const trendMax = Math.max(1, ...trend.map((d) => d.value));

  if (thisWeek.length === 0) {
    return (
      <section className="stats card">
        <Blank
          title={t(lang, "stats_empty_title")}
          body={t(lang, "stats_empty_body")}
          action={t(lang, "stats_empty_action")}
          onAction={onBrowse}
          ornament={<ArchOrnament className="blank__ornament" size={40} />}
        />
      </section>
    );
  }

  return (
    <section className="stats card">
      {/* THE WEEK ROW USED TO BE HERE and it has moved out, to WeekRow in
          Standing.tsx. Both were drawn on the Progress screen, one above the
          other, saying the same thing in two visual languages — seven dots and
          then seven glyphs. WeekRow is the better of the two (three shapes, not
          one shape in two colours, and it distinguishes a day not yet reached
          from a day missed), so this one goes rather than being kept for
          continuity. What remains below is what this card alone can say: the
          month, the trend, and the week's figures. */}

      {/* ── THE MONTH ────────────────────────────────────────────────────
             A calendar grid of the last 5 weeks, one cell per day, filled
             where a real attempt exists. Structure borrowed from a progress
             dashboard; the reward mechanics deliberately NOT borrowed with it.

             NO STREAK, NO FLAME, NO BADGE, NO POINTS. A grid with a streak
             counter on it stops being a record of practice and becomes a thing
             to protect, and the day it breaks is the day people stop opening
             the app. Missed days here are simply empty — they carry no penalty
             styling, no red, and nothing counts them. That was the original
             design brief's rule and copying someone else's dashboard is not a
             reason to quietly drop it. */}
      <div className="stats__rule" />
      <ol className="month" aria-label={t(lang, "stats_month_label")}>
        {monthCells.map((cell) => (
          <li
            key={cell.key}
            className={[
              "month__cell",
              cell.active ? "month__cell--on" : "",
              cell.future ? "month__cell--future" : "",
              cell.today ? "month__cell--today" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            title={cell.key}
          />
        ))}
      </ol>

      {/* A plain bar per active day: how much was recited, not how well. Drawn
          only when there are at least two days to compare - a "chart" of one
          bar is a decoration. */}
      {trend.length >= 2 && (
        <div className="trend" aria-label={t(lang, "stats_trend_label")}>
          {trend.map((d) => (
            <span
              key={d.key}
              className="trend__bar"
              style={{ height: `${Math.max(6, (d.value / trendMax) * 100)}%` }}
              title={`${d.key} · ${Math.round(d.value / 60)}m`}
            />
          ))}
        </div>
      )}

      <div className="stats__rule" />

      <div className="stats__row">
        <Stat value={String(verses)} label={t(lang, "stats_verses")} />
        <Stat value={hhmm(seconds)} label={t(lang, "stats_time")} />
        {/* Omitted, not dashed, when nothing scored this week. An empty slot
            with a "—" in it invites someone to fill it later. */}
        {accuracy !== null && (
          <Stat
            value={`${Math.round(accuracy * 100)}%`}
            label={t(lang, "stats_accuracy")}
          />
        )}
      </div>
    </section>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="stat">
      <span className="stat__value">{value}</span>
      <span className="stat__label">{label}</span>
    </div>
  );
}

function hhmm(seconds: number): string {
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}
