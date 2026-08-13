import { Attempt } from "../lib/api";
import { Key, Lang, t } from "../lib/i18n";
import { weaknesses, todaysFocus } from "../lib/weakness";

const KIND_KEY: Record<string, Key> = {
  extra_letter: "kind_extra_letter",
  missing_letter: "kind_missing_letter",
  wrong_letter: "kind_wrong_letter",
  pronunciation: "kind_pronunciation",
  tajweed: "kind_tajweed",
  madd: "kind_madd",
  ghunna: "kind_ghunna",
  haraka: "kind_haraka",
  shadda: "kind_shadda",
};

export default function FocusCard({
  lang,
  rows,
  onPractice,
}: {
  lang: Lang;
  rows: Attempt[];
  onPractice: (sura: number, aya: number) => void;
}) {
  const focus = todaysFocus(weaknesses(rows));
  if (!focus) return null;

  const kindTitle = t(lang, KIND_KEY[focus.kind] ?? "kind_pronunciation");

  return (
    <div className="focus-card">
      <p className="focus-card__kicker">{t(lang, "focus_kicker")}</p>
      <div className="focus-card__body">
        <span className="focus-card__letter" lang="ar">{focus.letter}</span>
        <div className="focus-card__info">
          <p className="focus-card__kind">{kindTitle}</p>
          {focus.content.headline && (
            <p className="focus-card__headline">{focus.content.headline}</p>
          )}
          <p className="focus-card__meta">
            {t(lang, "focus_recent_n").replace("{n}", String(focus.recentCount))}
          </p>
          {focus.makhraj && (
            <p className="focus-card__makhraj">
              {t(lang, "weak_makhraj")}: {focus.makhraj}
            </p>
          )}
        </div>
      </div>
      <div className="focus-card__actions">
        {focus.content.audio_pair && (
          <button
            className="btn-quiet"
            onClick={() => new Audio(focus.content.audio_pair!).play()}
          >
            {t(lang, "weak_listen")}
          </button>
        )}
        <button
          className="btn-primary focus-card__cta"
          onClick={() => onPractice(focus.sura, focus.aya)}
        >
          {t(lang, "focus_cta")}
        </button>
      </div>
    </div>
  );
}
