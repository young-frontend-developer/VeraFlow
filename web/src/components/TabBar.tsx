import { Lang, t } from "../lib/i18n";
import { TabIcon } from "./Ornament";

/**
 * The five destinations.
 *
 * `practice` is still a Tab because it is still a SCREEN — the sura list and
 * the recite flow both live under it — but it is no longer an item in the bar.
 * The centre button goes there directly, which is what made the separate tab
 * redundant: two controls, side by side, that opened the same thing.
 *
 * `memorize` is gone and stays gone as a tab. Memorisation now appears where it
 * actually belongs — as a study mode on a sura, marked "Tez orada" — rather
 * than as a whole tab leading to an apology.
 */
export type Tab = "home" | "practice" | "tutor" | "progress" | "learn" | "profile";

/**
 * A glass capsule floating clear of the device edge, with the centre action
 * BREAKING OUT of it — see the `.tabbar` block in index.css for the visual
 * construction.
 *
 * ── THE ORDER IS THE DESIGN, and the previous one had a duplicate ──────────
 *
 * The bar used to carry both a "Mashq" tab and a centre mic, and they did the
 * same thing: open practice. Two controls one thumb-width apart, leading to the
 * same place, one of them shaped like the app's primary action. The separate
 * tab is gone and the centre keeps the job AND the name — it is Mashq now, not
 * "Ustoz", because that is what pressing it does. Naming the button after the
 * feature behind it rather than after what it opens is how you get a nav item
 * nobody can predict.
 *
 * That freed a slot, and the two moves after it are consequences: Oʻrganish
 * takes the empty second position, and Profil takes the fifth. Profil had been
 * hiding behind a gear in the top bar, which is a fine place for settings right
 * up until settings is also where the language lives — and language is not a
 * setting people find by hunting for a gear.
 *
 *   Bosh sahifa · Oʻrganish · [ Mashq ] · Natijalar · Profil
 */

const LABEL: Record<Exclude<Tab, "practice">, Parameters<typeof t>[1]> = {
  home: "nav_home",
  learn: "nav_learn",
  tutor: "nav_practice",
  progress: "nav_progress",
  profile: "nav_profile",
};

const ORDER: Exclude<Tab, "practice">[] = [
  "home",
  "learn",
  "tutor",
  "progress",
  "profile",
];

/** The centre item, rendered as the bar's primary action. */
const CENTER: Tab = "tutor";

export default function TabBar({
  tab,
  onChange,
  lang,
}: {
  tab: Tab;
  onChange: (t: Tab) => void;
  lang: Lang;
}) {
  return (
    <nav className="tabbar" aria-label={t(lang, "nav_label")}>
      {ORDER.map((key) => {
        // The practice SCREEN has no item of its own any more, so the centre
        // stays lit while you are on it — that is the button you pressed to
        // get there, and a bar with nothing marked leaves you unsure which
        // part of the app you are standing in.
        const current = tab === key || (key === CENTER && tab === "practice");
        return (
          <button
            key={key}
            className={key === CENTER ? "tab tab--center" : "tab"}
            aria-current={current ? "page" : undefined}
            onClick={() => onChange(key)}
          >
            <span className="tab__glyph">{TabIcon[key]}</span>
            {t(lang, LABEL[key])}
          </button>
        );
      })}
    </nav>
  );
}
