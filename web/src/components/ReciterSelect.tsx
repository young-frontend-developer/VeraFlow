import { Reciter } from "../lib/api";
import { Lang, t } from "../lib/i18n";

/**
 * Which reciter to hear. A native <select> on purpose: it is a list of sixteen
 * proper names, and every phone already knows how to present one of those
 * better than a hand-rolled dropdown does.
 *
 * Grouped by style, muallim first. That ordering is a teaching judgement, not
 * alphabetics — a muallim recording repeats each phrase for the listener, which
 * is what a beginner copying phrasing actually needs, and a mujawwad recitation
 * is the least useful thing to imitate however beautiful it is.
 */
const ORDER = ["muallim", "murattal", "mujawwad"] as const;

const GROUP_KEY = {
  muallim: "style_muallim",
  murattal: "style_murattal",
  mujawwad: "style_mujawwad",
} as const;

export default function ReciterSelect({
  lang,
  reciters,
  value,
  onChange,
  disabled = false,
}: {
  lang: Lang;
  reciters: Reciter[];
  value: string;
  onChange: (id: string) => void;
  disabled?: boolean;
}) {
  // Nothing to choose between until the list arrives, and a select with one
  // invisible option is worse than no select.
  if (reciters.length === 0) return null;

  return (
    <label className="reciter">
      <span className="reciter__label">{t(lang, "reciter")}</span>
      <select
        className="reciter__select"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {ORDER.map((style) => {
          const group = reciters.filter((r) => r.style === style);
          if (group.length === 0) return null;
          return (
            <optgroup key={style} label={t(lang, GROUP_KEY[style])}>
              {group.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </optgroup>
          );
        })}
        {/* Anything the server added under a style this build does not know
            about still has to be selectable, or a new group would silently
            vanish from the list. */}
        {reciters.some((r) => !ORDER.includes(r.style as never)) && (
          <optgroup label="—">
            {reciters
              .filter((r) => !ORDER.includes(r.style as never))
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
          </optgroup>
        )}
      </select>
    </label>
  );
}
