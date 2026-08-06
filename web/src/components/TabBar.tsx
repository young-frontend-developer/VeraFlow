import { Lang, t } from "../lib/i18n";
import { TabIcon } from "./Ornament";

export type Tab = "today" | "practice" | "learn" | "memorize" | "profile";

/**
 * The floating pill. A dark charcoal capsule that sits ABOVE the page with real
 * space beneath it, rather than a bar welded to the bottom edge.
 *
 * That gap is the whole idea: a bar flush to the edge belongs to the device, a
 * capsule floating clear of it belongs to the app. The page reserves room for
 * it (`.app` bottom padding) so nothing ever scrolls underneath and hides.
 *
 * DARK, WHILE EVERY PAGE IS IVORY — and this is the one exception to the "one
 * dark surface" rule that the recording card otherwise owns. It is legitimate
 * because the nav is chrome rather than content: it never sits inside the
 * reading column, it never changes, and a light pill on a light ground would
 * need a border heavy enough to fight the hairlines everywhere else.
 *
 * Icons are hairline and 20px, labels are 10.5px — small enough that the
 * capsule reads as one object rather than as five buttons.
 */

const LABEL: Record<Tab, Parameters<typeof t>[1]> = {
  today: "nav_today",
  practice: "nav_practice",
  learn: "nav_learn",
  memorize: "nav_memorize",
  profile: "nav_profile",
};

const ORDER: Tab[] = ["today", "practice", "learn", "memorize", "profile"];

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
      {ORDER.map((key) => (
        <button
          key={key}
          className="tab"
          aria-current={tab === key ? "page" : undefined}
          onClick={() => onChange(key)}
        >
          <span className="tab__glyph">{TabIcon[key]}</span>
          {t(lang, LABEL[key])}
        </button>
      ))}
    </nav>
  );
}
