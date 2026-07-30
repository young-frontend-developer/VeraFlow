import { Lang } from "../lib/i18n";

const ORDER: Lang[] = ["uz", "ru"];

/**
 * Two languages, equal weight. A sunken well with a paper chip that slides —
 * so it reads as part of the page rather than a control set on top of it.
 */
export default function LangToggle({
  lang,
  onChange,
}: {
  lang: Lang;
  onChange: (l: Lang) => void;
}) {
  return (
    <div className="lang" role="group" aria-label="Til / Язык">
      <span
        className="lang__chip"
        aria-hidden="true"
        style={{
          transform: `translateX(${ORDER.indexOf(lang) * 100}%)`,
        }}
      />
      {ORDER.map((l) => (
        <button
          key={l}
          className="lang__btn"
          aria-pressed={lang === l}
          onClick={() => onChange(l)}
        >
          {l === "uz" ? "OʻZ" : "RU"}
        </button>
      ))}
    </div>
  );
}
