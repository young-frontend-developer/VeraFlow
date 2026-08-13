import { Attempt, Sura } from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { totals as totalsOf } from "../lib/progress";
import { RankCard, StatsRow, WeekRow } from "./Standing";
import WeekStats from "./WeekStats";
import Achievements from "./Achievements";
import { award, signalsFrom } from "../lib/achievements";
import { hasJourney, storedJourney } from "../lib/journey";
import { Blank, Loading } from "./States";
import { ArchOrnament } from "./Ornament";
import WeaknessBoard from "./WeaknessBoard";

/**
 * PROGRESS — the fourth tab, and the room everything countable moved into.
 *
 * ── WHY IT EXISTS ──────────────────────────────────────────────────────────
 *
 * The tab row gained a centre action and lost a slot, and Profile went behind
 * the settings gear. What Profile was actually being used for — the month grid,
 * the trend, the achievement wall — was never settings; it was a progress
 * dashboard living in a settings screen because there was nowhere else to put
 * it. Now there is.
 *
 * Home shows the FOUR headline figures and this shows the working: the same
 * counters, then the month, the trend and the full badge wall. Home answers
 * "how am I doing" in one glance; this answers "show me".
 *
 * ── ONE HONEST GAP, NAMED ──────────────────────────────────────────────────
 *
 * WeekStats below draws an accuracy figure, and it is the only number in this
 * app that is an average of the engine's own scores. It is kept because it is
 * real and because it is scoped to a week, but it is deliberately NOT promoted
 * to Home and NOT folded into the rank: a single percentage standing for how
 * well someone recites the Qur'an is a claim this engine is not good enough to
 * make, and putting it on the opening screen would make it the headline.
 *
 * With retention declined there is nothing here and the screen says so, rather
 * than showing empty scaffolding that implies numbers are coming. They are not;
 * the learner turned them off, and Profile is where that gets changed.
 */
export default function Progress({
  lang,
  suras,
  rows,
  consented,
  onBrowse,
  onPick,
}: {
  lang: Lang;
  suras: Sura[];
  /** Real attempts, newest first. Null while loading. */
  rows: Attempt[] | null;
  consented: boolean;
  onBrowse: () => void;
  onPick?: (sura: number, aya: number) => void;
}) {
  if (!consented) {
    return (
      <article className="card">
        {/* The copy that already exists for exactly this state, reused rather
            than reworded. Two strings saying the same thing in different words
            is how a product ends up sounding like two products. */}
        <Blank
          title={t(lang, "profile_off_title")}
          body={t(lang, "profile_off_body")}
          ornament={<ArchOrnament className="blank__ornament" size={40} />}
        />
      </article>
    );
  }

  if (rows === null) return <Loading rows={6} />;

  const totals = totalsOf(rows);
  const items = award(
    signalsFrom(
      rows,
      Object.fromEntries(suras.map((s) => [s.number, s.n_ayat])),
      { hasJourney: hasJourney(storedJourney()) },
    ),
  );

  return (
    <>
      <header className="section-head section-head--hero">
        <div>
          <p className="section-label">{t(lang, "stats_kicker")}</p>
          <h2 className="section-title section-title--hero">
            {t(lang, "stats_title")}
          </h2>
        </div>
      </header>

      <StatsRow lang={lang} totals={totals} />
      <RankCard lang={lang} totals={totals} />
      <WeekRow lang={lang} rows={rows} />

      {/* The month grid, the trend and the week's three figures. Unchanged
          logic — it was already counting only real rows — restyled by the
          shared system rather than rewritten. */}
      <section className="today__block">
        <WeekStats
          lang={lang}
          rows={rows}
          consented={consented}
          onBrowse={onBrowse}
        />
      </section>

      <section className="today__block">
        <WeaknessBoard lang={lang} rows={rows} onPractice={onPick} />
      </section>

      <section className="today__block">
        <Achievements lang={lang} items={items} />
      </section>
    </>
  );
}
