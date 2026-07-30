import { AyahLine } from "./AyahText";
import { Ayah } from "../lib/api";
import { Lang, t } from "../lib/i18n";

export default function Library({
  lang,
  ayat,
  current,
  onPick,
}: {
  lang: Lang;
  ayat: Ayah[];
  current: Ayah | null;
  onPick: (a: Ayah) => void;
}) {
  return (
    <>
      <h2 className="section-head">{t(lang, "library_title")}</h2>
      <p className="section-sub">{t(lang, "library_sub")}</p>

      <ul className="list">
        {ayat.map((a) => (
          <li key={a.slug}>
            <button
              className="row"
              aria-current={current?.slug === a.slug}
              onClick={() => onPick(a)}
            >
              <span className="row__mark" aria-hidden="true" />
              <span className="row__body">
                <span className="row__name">
                  {lang === "uz" ? a.name_uz : a.name_ru}
                </span>
                <AyahLine uthmani={a.uthmani} />
              </span>
              <span className="level">
                {t(lang, "level")} {a.level}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
