import { useState } from "react";
import { RuleBadge } from "../lib/api";
import { Lang, t } from "../lib/i18n";

/**
 * THE RULES THIS PASSAGE CONTAINS.
 *
 * A row of small pills under the ayah, one per tajweed rule that structurally
 * occurs in it, each expanding to the rule in plain Uzbek.
 *
 * ── WHY THIS IS NOT THE ERROR CARDS ────────────────────────────────────────
 *
 * Every entry in the error registry describes a MISTAKE, so it can only ever
 * appear after a bad take. A learner who recited well was told "nothing found"
 * and learned nothing about what they had just done correctly. These fire on
 * PRESENCE: al-Baqara 1 contains a madd lozim whether or not anyone reads it,
 * and the badge says so before, during and after the recording.
 *
 * ── ONE PANEL AT A TIME ────────────────────────────────────────────────────
 *
 * Opening a badge closes whatever else was open. Two open panels on a phone
 * push the second one off-screen the moment it appears, so the learner taps a
 * rule and watches the page jump — and with eight badges on a long ayah, a
 * free-for-all accordion turns into a wall. The open panel is tracked as ONE
 * code rather than as a set, which makes the rule structural instead of
 * something the handlers have to remember to enforce.
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
  const [open, setOpen] = useState<string | null>(null);

  const shown = rules.filter((r) => r.reviewed || showUnreviewed);
  if (shown.length === 0) return null;

  return (
    <section className="rules" aria-label={t(lang, "rules_title")}>
      <p className="rules__kicker">{t(lang, "rules_title")}</p>

      <ul className="rules__row">
        {shown.map((r) => {
          const isOpen = open === r.code;
          return (
            <li key={r.code}>
              <button
                className={`rule-pill rule-pill--${r.color}${
                  isOpen ? " rule-pill--open" : ""
                }`}
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : r.code)}
              >
                <span className="rule-pill__dot" aria-hidden="true" />
                {r.name}
                {/* Plus becomes minus. A rotated plus rather than two glyphs,
                    so the transition is the state change rather than a swap. */}
                <span className="rule-pill__toggle" aria-hidden="true">
                  <span className="rule-pill__bar" />
                  <span className="rule-pill__bar rule-pill__bar--v" />
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {/* ONE PANEL, BELOW THE WHOLE ROW — not inside the pill that opened it.
          The pills wrap onto two or three lines, and a panel opening inside the
          row would shove the remaining pills down and re-flow the ones beside
          it. Below the row, the row never moves. */}
      {shown
        .filter((r) => r.code === open)
        .map((r) => (
          <div className="rule-panel" key={r.code}>
            <p className="rule-panel__rule">{r.rule}</p>

            {r.target && (
              <p className="rule-panel__target">
                {t(lang, "rules_target")}: <strong>{r.target}</strong>{" "}
                {t(lang, "harakat")}
              </p>
            )}

            {/* dir="ltr", and neither "rtl" nor "auto".
                The authored examples are Arabic words inside an UZBEK sentence:
                "…, va الٓمٓ kabi sura boshidagi yakka harflar". `rtl` reversed the
                Latin half. `auto` was no better - it takes the base direction
                from the first strong character, which is Arabic, so it landed
                on rtl too and moved "kabi sura boshidagi" to the left of the
                examples it describes. The sentence is Uzbek, so the paragraph
                is LTR and the bidi algorithm lays each Arabic run out
                right-to-left inside it, in the order they were written. */}
            {r.example && (
              <p className="rule-panel__example" dir="ltr">
                {r.example}
              </p>
            )}

            <p className="rule-panel__source">
              {r.source}
              {!r.reviewed && (
                <span className="rule-panel__draft">{t(lang, "draft_chip")}</span>
              )}
            </p>

            {/* SAID ONCE, WHERE IT MATTERS. The content was transcribed in
                Uzbek only; no Russian was authored and none was invented, so a
                Russian UI is reading Uzbek here and is told so rather than left
                to wonder whether the app is broken. */}
            {lang !== "uz" && (
              <p className="rule-panel__lang">{t(lang, "rules_uz_only")}</p>
            )}
          </div>
        ))}
    </section>
  );
}
