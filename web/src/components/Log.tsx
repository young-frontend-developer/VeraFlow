import { useEffect, useState } from "react";
import { Attempt, Ayah, history, setConsent } from "../lib/api";
import { Lang, t } from "../lib/i18n";

/**
 * Past attempts, plus the consent control that governs whether there are any.
 *
 * A deliberately flat list: no streak, no chart, no score trend. Progress in
 * recitation is not a number going up, and implying it is would be its own kind
 * of dishonesty.
 */
export default function Log({
  lang,
  ayat,
  consented,
  onConsent,
}: {
  lang: Lang;
  ayat: Ayah[];
  consented: boolean;
  onConsent: (v: boolean) => void;
}) {
  const [rows, setRows] = useState<Attempt[] | null>(null);
  const [deleted, setDeleted] = useState(false);

  useEffect(() => {
    if (!consented) return setRows([]);
    history()
      .then(setRows)
      .catch(() => setRows([]));
  }, [consented]);

  const name = (a: Attempt) => {
    const found = ayat.find((x) => x.sura === a.sura && x.aya === a.aya);
    return found ? (lang === "uz" ? found.name_uz : found.name_ru) : `${a.sura}:${a.aya}`;
  };

  return (
    <>
      <h2 className="section-head">{t(lang, "log_title")}</h2>
      <p className="section-sub">{t(lang, "log_sub")}</p>

      {rows === null ? (
        <p className="empty">{t(lang, "loading")}</p>
      ) : rows.length === 0 ? (
        <p className="empty">{t(lang, "log_empty")}</p>
      ) : (
        <ul className="list">
          {rows.map((r, i) => (
            <li className="log" key={r.id ?? i}>
              <span
                className={r.clean ? "log__dot log__dot--clear" : "log__dot"}
                aria-hidden="true"
              />
              <span className="log__text">{name(r)}</span>
              <span className="log__meta">
                {r.status === "retry_recording"
                  ? t(lang, "log_retry")
                  : r.clean
                    ? t(lang, "log_clear")
                    : t(lang, "log_noted")}
              </span>
            </li>
          ))}
        </ul>
      )}

      <section className="consent">
        <h3 className="notice__title">{t(lang, "consent_title")}</h3>
        <p className="notice__body" style={{ marginBottom: "1rem" }}>
          {t(lang, "consent_body")}
        </p>
        <label className="consent__row">
          <input
            type="checkbox"
            checked={consented}
            onChange={(e) => {
              const next = e.target.checked;
              setConsent(next).catch(() => {});
              onConsent(next);
              if (!next) {
                setRows([]);
                setDeleted(true);
              }
            }}
          />
          <span>{t(lang, "consent_toggle")}</span>
        </label>
        {deleted && !consented && (
          <p className="notice__body" style={{ marginTop: "0.75rem" }}>
            {t(lang, "consent_delete")}
          </p>
        )}
      </section>
    </>
  );
}
