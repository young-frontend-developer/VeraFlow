import { Attempt } from "../lib/api";
import { Lang, Key, t } from "../lib/i18n";
import {
  DayState,
  Totals,
  week as weekOf,
} from "../lib/progress";
import {
  DayDone,
  DayMissed,
  DayPending,
  Dial,
  Flame,
  Leaf,
  Sparkle,
  StarOrnament,
} from "./Ornament";

/**
 * THE THREE PROGRESS BLOCKS ON HOME: the four figures, the rank, the week.
 *
 * They share a file because they share one rule, and keeping the rule in one
 * place is worth more than three tidy files: EVERY NUMBER IN HERE IS COUNTED
 * FROM REAL ATTEMPTS, and the zero state is drawn rather than hidden. See
 * lib/progress.ts for the arithmetic and for why each figure is worth what it
 * is worth.
 *
 * ── WHY ZEROES, WHEN THE WEEK CARD HIDES ITSELF ────────────────────────────
 *
 * WeekStats.tsx refuses to draw three zeroes and replaces itself with an empty
 * state, and that is right there: it reports on a week that has happened, and
 * zeroes read as a verdict on how it went. These are lifetime counters on the
 * first screen of a new account, and there the reasoning inverts — a counter at
 * 0 is a counter that has not started, which is true and legible. Hiding it
 * instead would make the screen change shape the first time someone recites,
 * which is the moment they most need the screen to be familiar.
 *
 * So the zeroes are STYLED, not defaulted: `.stat--empty` dims the figure and
 * the row carries one line saying plainly that nothing here is invented.
 */

/* ══ the four figures ═════════════════════════════════════════════════════ */

/**
 * One figure.
 *
 * ── THE MARK CARRIES A COLOUR AND NOTHING ELSE DOES ────────────────────────
 *
 * `tone` names which accent the icon takes: flame amber for the streak, brass
 * for hasanat, jade for ayat, a cool teal for time. The VALUE and the LABEL
 * stay in the neutral ink in every tile, which is the whole reason this can
 * have colour at all — four coloured numbers would be a dashboard, four
 * coloured icons over neutral figures is a legend.
 *
 * The fills are soft gradients from the same construction as `--accent-fill`,
 * not flat saturated icon colours. See `.stat-tile__mark--*` in index.css.
 *
 * ── AND THE SUB-NOTES ARE GONE ─────────────────────────────────────────────
 *
 * Two tiles used to carry a second line under the label — "Eng uzuni: 4" and
 * "1 240 harf oʻqildi". Both were true and neither was wanted here: this block
 * answers "how am I doing" at a glance, and a glance does not include a
 * lifetime-best sub-figure. The letters count still exists and is still what
 * hasanat is computed from — it is simply not narrated on Home.
 */
function Stat({
  mark,
  tone,
  value,
  label,
  empty,
}: {
  mark: React.ReactNode;
  tone: "flame" | "brass" | "jade" | "teal";
  value: string;
  label: string;
  empty: boolean;
}) {
  return (
    <li className={`stat-tile${empty ? " stat-tile--empty" : ""}`}>
      <span
        className={`stat-tile__mark stat-tile__mark--${tone}`}
        aria-hidden="true"
      >
        {mark}
      </span>
      <span className="stat-tile__value">{value}</span>
      <span className="stat-tile__label">{label}</span>
    </li>
  );
}

/**
 * The four gradient paint-servers the marks stroke themselves with.
 *
 * WHY A DEFS SPRITE AND NOT A CSS GRADIENT. `stroke` on an SVG cannot take a
 * CSS gradient — a gradient is a paint server, and a paint server has to live
 * in the document as an element with an id. So the four run once, hidden, and
 * every mark points at one by url(). The alternative was giving each icon its
 * own inline defs, which puts four duplicate gradients in the DOM per tile.
 *
 * THE STOPS ARE TOKENS, so the pair re-hues per theme without a second sprite:
 * the same amber has to be lighter on indigo than it is on paper to hold the
 * same weight. See `--tone-*` in index.css.
 *
 * Diagonal, top-left to bottom-right, which is the same light direction
 * `--accent-fill` uses on every filled shape in the app — that is what makes
 * these read as the same material rather than as four coloured icons.
 */
function ToneDefs() {
  const stop = (v: string) => ({ stopColor: `var(${v})` });
  return (
    <svg className="tone-defs" aria-hidden="true" focusable="false">
      <defs>
        {(["flame", "brass", "jade", "teal"] as const).map((tone) => (
          <linearGradient
            key={tone}
            id={`tone-${tone}`}
            x1="0.1"
            y1="0"
            x2="0.85"
            y2="1"
          >
            <stop offset="0" style={stop(`--tone-${tone}-1`)} />
            <stop offset="1" style={stop(`--tone-${tone}-2`)} />
          </linearGradient>
        ))}
      </defs>
    </svg>
  );
}

export function StatsRow({
  lang,
  totals,
}: {
  lang: Lang;
  totals: Totals;
}) {
  const blank = totals.xp === 0 && totals.hasanat === 0 && totals.ayat === 0;

  return (
    <section className="today__block">
      <ToneDefs />
      <header className="section-head">
        <div>
          <p className="section-label">{t(lang, "stats_kicker_home")}</p>
          <h2 className="section-title">{t(lang, "stats_title_home")}</h2>
        </div>
      </header>

      <ul className="stat-grid">
        <Stat
          mark={<Flame />}
          tone="flame"
          value={String(totals.streak.current)}
          label={t(lang, "stat_streak")}
          empty={totals.streak.current === 0}
        />
        <Stat
          mark={<Sparkle />}
          tone="brass"
          value={compact(totals.hasanat)}
          label={t(lang, "stat_hasanat")}
          empty={totals.hasanat === 0}
        />
        <Stat
          mark={<Leaf />}
          tone="jade"
          value={String(totals.ayat)}
          label={t(lang, "stat_ayat")}
          empty={totals.ayat === 0}
        />
        <Stat
          mark={<Dial />}
          tone="teal"
          value={hhmm(totals.seconds)}
          label={t(lang, "stat_time")}
          empty={totals.seconds === 0}
        />
      </ul>

      {/* Said once, under the grid, and only while it is all zero. */}
      {blank && <p className="stat-grid__note">{t(lang, "stats_empty_note")}</p>}
    </section>
  );
}

/* ══ the rank ═════════════════════════════════════════════════════════════ */

/**
 * The named stage, and how far through it the learner is.
 *
 * The bar is the app's one gold progress fill and it is honest about what it
 * measures: XP earned by reciting, against the next threshold. It does NOT
 * describe skill. Someone at "Qori" has recited a lot; the engine's opinion of
 * how well lives on the correction cards, where it belongs, and is not
 * summarised into a level here.
 */
export function RankCard({ lang, totals }: { lang: Lang; totals: Totals }) {
  const { rank, next, fraction, toNext, xp } = totals.standing;

  return (
    <article className="card rank">
      <div className="rank__head">
        <div>
          <p className="section-label">{t(lang, "rank_kicker")}</p>
          <h3 className="rank__name">{t(lang, rank.nameKey)}</h3>
        </div>
        <span className="rank__mark" aria-hidden="true">
          <StarOrnament size={40} />
        </span>
      </div>

      <p className="rank__note">{t(lang, rank.noteKey)}</p>

      <div className="progress" aria-hidden="true">
        <span
          className="progress__fill"
          style={{ width: `${Math.round(fraction * 100)}%` }}
        />
      </div>

      <div className="rank__foot">
        <span className="rank__xp">
          {t(lang, "rank_xp").replace("{n}", String(xp))}
        </span>
        <span className="rank__next">
          {next
            ? t(lang, "rank_to_next")
                .replace("{name}", t(lang, next.nameKey))
                .replace("{n}", String(toNext))
            : t(lang, "rank_top")}
        </span>
      </div>
    </article>
  );
}

/* ══ the week ═════════════════════════════════════════════════════════════ */

const DAY_KEYS: Key[] = [
  "day_mon",
  "day_tue",
  "day_wed",
  "day_thu",
  "day_fri",
  "day_sat",
  "day_sun",
];

const GLYPH: Record<DayState, React.ReactNode> = {
  done: <DayDone />,
  missed: <DayMissed />,
  pending: <DayPending />,
};

const STATE_LABEL: Record<DayState, Key> = {
  done: "day_state_done",
  missed: "day_state_missed",
  pending: "day_state_pending",
};

/**
 * Seven days, three shapes.
 *
 * THE SHAPES CARRY THE MEANING, not the colours: a filled tick, an open dashed
 * ring, a quiet dot. Read the strip in greyscale and it still says the same
 * thing, which is the test a seven-item status row has to pass.
 *
 * And no faces. The obvious move here is a row of little expressions — happy
 * for a day you practised, sad for one you did not — and it is the wrong one
 * twice over: it has the app pass comment on someone's week, and it does it in
 * a visual language borrowed wholesale from every habit tracker there is.
 */
export function WeekRow({
  lang,
  rows,
}: {
  lang: Lang;
  rows: Attempt[];
}) {
  const states = weekOf(rows);
  const todayIndex = (new Date().getDay() + 6) % 7;

  return (
    <section className="today__block">
      <header className="section-head">
        <div>
          <p className="section-label">{t(lang, "week_kicker")}</p>
          <h2 className="section-title">{t(lang, "week_title")}</h2>
        </div>
      </header>

      <article className="card week-strip">
        <ol className="week-strip__row">
          {states.map((state, i) => (
            <li
              key={DAY_KEYS[i]}
              className={`week-cell week-cell--${state}${
                i === todayIndex ? " week-cell--today" : ""
              }`}
              aria-current={i === todayIndex ? "date" : undefined}
            >
              <span className="week-cell__glyph">{GLYPH[state]}</span>
              <span className="week-cell__letter">{t(lang, DAY_KEYS[i])}</span>
              <span className="sr-only">{t(lang, STATE_LABEL[state])}</span>
            </li>
          ))}
        </ol>
      </article>
    </section>
  );
}

/* ══ formatting ═══════════════════════════════════════════════════════════ */

/** 12 400 → "12.4K". Hasanat runs into six figures fast and a tile is 80px. */
function compact(n: number): string {
  if (n < 1000) return String(n);
  if (n < 1_000_000) return `${trim(n / 1000)}K`;
  return `${trim(n / 1_000_000)}M`;
}

const trim = (n: number) => n.toFixed(n < 10 ? 1 : 0).replace(/\.0$/, "");

function hhmm(seconds: number): string {
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}
