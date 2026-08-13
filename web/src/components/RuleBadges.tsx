import { RuleBadge } from "../lib/api";
import { Lang, t } from "../lib/i18n";

/**
 * THE RULES THIS PASSAGE CONTAINS — a LEGEND, not a content surface.
 *
 * A row of names under the ayah, one per tajweed rule that structurally occurs
 * in it, each carrying the colour those letters are painted in above. That is
 * the whole job: it tells you what the colours mean.
 *
 * ── WHY THIS IS NOT THE ERROR CARDS ────────────────────────────────────────
 *
 * Every entry in the error registry describes a MISTAKE, so it can only ever
 * appear after a bad take. A learner who recited well was told "nothing found"
 * and learned nothing about what they had just done correctly. These fire on
 * PRESENCE: al-Baqara 1 contains a madd lozim whether or not anyone reads it,
 * and the label says so before, during and after the recording.
 *
 * ── WHY NOTHING HERE OPENS ─────────────────────────────────────────────────
 *
 * It used to. Each name was a button with a plus sign that expanded a panel
 * carrying the ruling, a worked example, the citation and a draft chip — an
 * encyclopedia entry per rule, sitting under an ayah the learner had opened in
 * order to recite it.
 *
 * That content has exactly one home now, and it is the feedback card: behind
 * the ❔ toggle on a Kind 1 correction, at the moment a learner got that
 * specific rule wrong and has a reason to read about it. Teaching the ruling to
 * someone who just executed it correctly is an interruption; teaching it to
 * someone who just missed it is a lesson.
 *
 * So there is no button, no chevron, no plus, no panel and nothing tappable.
 * A name that looks pressable and does nothing is worse than plain text, and
 * plain text is what a legend is.
 *
 * ── GATED, LIKE EVERYTHING ELSE ────────────────────────────────────────────
 *
 * `reviewed` comes from the server and the whole strip is dropped when the
 * build is not showing unreviewed content. Nothing here has a qori's signature
 * yet; see rule_badges.json.
 */
export default function RuleBadges({
  lang,
  rules,
  showUnreviewed,
}: {
  lang: Lang;
  rules: RuleBadge[];
  /** Pilot builds show draft content, labelled. Production shows none. */
  showUnreviewed: boolean;
}) {
  // ONE ENTRY PER RULE. The server sends a sorted set, so duplicates should not
  // arrive — but a legend that printed "Ixfo · Ixfo" because a rule fired twice
  // in one ayah would read as a bug, and the cost of being certain here is one
  // Set.
  const seen = new Set<string>();
  const shown = rules.filter((r) => {
    if (!(r.reviewed || showUnreviewed)) return false;
    if (seen.has(r.code)) return false;
    seen.add(r.code);
    return true;
  });
  if (shown.length === 0) return null;

  return (
    <section className="rules" aria-label={t(lang, "rules_title")}>
      <p className="rules__kicker">{t(lang, "rules_title")}</p>

      {/* A list, not a row of controls. The dot carries the colour tie back to
          the painted letters; the name carries the meaning. */}
      <ul className="rules__row">
        {shown.map((r) => (
          <li key={r.code} className={`rule-name rule-name--${r.color}`}>
            <span className="rule-name__dot" aria-hidden="true" />
            {r.name}
          </li>
        ))}
      </ul>
    </section>
  );
}
