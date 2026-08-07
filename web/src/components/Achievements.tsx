import { Awarded } from "../lib/achievements";
import { Lang, t } from "../lib/i18n";
import { StarOrnament } from "./Ornament";

/**
 * The badge, and the two places it appears.
 *
 * ONE DESIGN, THREE STATES, and the third is the one most systems get wrong:
 *
 *   earned    gold rule + emerald mark. Restrained — it is a quiet mark of
 *             something done, not a trophy.
 *   locked    neutral ivory. Something to work toward.
 *   blocked   neutral ivory AND a plain line saying this part of the app is not
 *             built yet. See lib/achievements.ts: five of the fifteen measure
 *             memorization or a course path, neither of which exists, so nobody
 *             can earn them. Drawing those identically to an ordinary locked
 *             badge sends the learner hunting for a way to earn something
 *             unreachable, which is a worse experience than an honest gap.
 *
 * No rainbow, no tiers, no progress rings, no percentages, no confetti. The
 * iconography is the app's own eight-point star at three weights.
 */

function Badge({
  lang,
  item,
  compact = false,
}: {
  lang: Lang;
  item: Awarded;
  compact?: boolean;
}) {
  const state = item.earned ? "earned" : item.blocked ? "blocked" : "locked";
  return (
    <li className={`badge badge--${state}${compact ? " badge--compact" : ""}`}>
      <span className="badge__mark" aria-hidden="true">
        <StarOrnament size={compact ? 22 : 26} />
      </span>
      <span className="badge__text">
        <span className="badge__name">{t(lang, item.nameKey)}</span>
        {!compact && (
          <span className="badge__how">
            {t(lang, item.blocked ? "ach_not_built" : item.howKey)}
          </span>
        )}
      </span>
    </li>
  );
}

/**
 * The Home preview: earned badges only, at most three.
 *
 * A "recent achievements" row full of locked badges is a list of things you
 * have not done, sitting on the one screen whose job is to say what to do next.
 * With nothing earned yet the whole section is absent rather than showing three
 * grey placeholders — the same rule the stats card follows.
 */
export function RecentAchievements({
  lang,
  items,
  onViewAll,
}: {
  lang: Lang;
  items: Awarded[];
  onViewAll: () => void;
}) {
  if (items.length === 0) return null;
  return (
    <section className="today__block">
      <header className="section-head">
        <div>
          <p className="section-label">{t(lang, "ach_recent")}</p>
        </div>
        <button className="section-aside link" onClick={onViewAll}>
          {t(lang, "ach_view_all")}
        </button>
      </header>
      <ul className="badges badges--row">
        {items.map((a) => (
          <Badge key={a.id} lang={lang} item={a} compact />
        ))}
      </ul>
    </section>
  );
}

/** The full wall. Lives in Profile — Home only ever gets the preview. */
export default function Achievements({
  lang,
  items,
}: {
  lang: Lang;
  items: Awarded[];
}) {
  const earned = items.filter((a) => a.earned).length;
  const earnable = items.filter((a) => !a.blocked).length;

  return (
    <section>
      <p className="section-label" style={{ margin: "0 0 4px" }}>
        {t(lang, "ach_all")}
      </p>
      {/* Counted against what can actually be earned, not against fifteen.
          "3 of 15" would be measuring the learner against features nobody has
          built. */}
      <p className="profile__note" style={{ marginBottom: 14 }}>
        {t(lang, "ach_count")
          .replace("{n}", String(earned))
          .replace("{of}", String(earnable))}
      </p>
      <ul className="badges">
        {items.map((a) => (
          <Badge key={a.id} lang={lang} item={a} />
        ))}
      </ul>
    </section>
  );
}
