import { Lang, t } from "../lib/i18n";

export type Tab = "practice" | "library" | "log";

/* Hand-drawn rather than an icon pack: three glyphs is not worth a dependency,
 * and these are drawn to match the hairline weight of the rules on the page. */
const glyph = {
  // a niche — the place you stand to recite
  practice: (
    <path d="M4 17V9a6 6 0 0 1 12 0v8" />
  ),
  // a folded sheet
  library: (
    <>
      <path d="M10 5v12" />
      <path d="M10 5c-1.6-1-3.4-1.4-6-1.3v11.6c2.6-.1 4.4.3 6 1.3" />
      <path d="M10 5c1.6-1 3.4-1.4 6-1.3v11.6c-2.6-.1-4.4.3-6 1.3" />
    </>
  ),
  // a quiet dial
  log: (
    <>
      <circle cx="10" cy="10" r="6.6" />
      <path d="M10 6.4V10l2.6 1.6" />
    </>
  ),
} as const;

const LABEL: Record<Tab, Parameters<typeof t>[1]> = {
  practice: "nav_practice",
  library: "nav_library",
  log: "nav_log",
};

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
    <nav className="tabbar">
      {(Object.keys(LABEL) as Tab[]).map((key) => (
        <button
          key={key}
          className="tab"
          aria-current={tab === key ? "page" : undefined}
          onClick={() => onChange(key)}
        >
          <span className="tab__glyph">
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              {glyph[key]}
            </svg>
          </span>
          {t(lang, LABEL[key])}
        </button>
      ))}
    </nav>
  );
}
