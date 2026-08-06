import { useEffect, useState } from "react";
import { Attempt, AyahBrief, Sura, history, suraAyat } from "../lib/api";
import { Lang, dateline, t } from "../lib/i18n";
import { Blank, Loading } from "./States";
import { ArchOrnament, Chevron } from "./Ornament";

/**
 * TODAY — the screen the app opens on.
 *
 * One editorial greeting, one hero card that resumes where the learner left
 * off, their recent activity, and one suggestion. Nothing else. It is a place
 * to start from, not a dashboard: no streak, no chart, no score trend. Progress
 * in recitation is not a number going up, and drawing one would be this app's
 * most convincing lie.
 *
 * EVERY MODULE HERE IS BACKED BY REAL DATA OR IT IS NOT DRAWN.
 *
 *   hero      the place stored when they last chose an ayah. With no stored
 *             place there is nothing to "continue", so the card becomes an
 *             invitation to choose one — designed, not a grey box.
 *   recent    real attempts, and only if they consented to storing them.
 *             Declining consent is a legitimate choice, so its empty state
 *             explains itself rather than looking broken.
 *   suggested the NEXT ayah in the same sura. Derived from where they are,
 *             which is the only recommendation this app can honestly make —
 *             there is no model of difficulty here, and inventing one would
 *             mean inventing the reasons too.
 */

export default function Today({
  lang,
  suras,
  place,
  consented,
  onResume,
  onPick,
  onBrowse,
}: {
  lang: Lang;
  suras: Sura[];
  /** Where they left off, or null on a first run. */
  place: { sura: number; aya: number } | null;
  consented: boolean;
  onResume: (sura: number, aya: number) => void;
  onPick: (sura: number, aya: number) => void;
  onBrowse: () => void;
}) {
  const [ayah, setAyah] = useState<AyahBrief | null>(null);
  const [next, setNext] = useState<AyahBrief | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<Attempt[] | null>(null);

  const sura = suras.find((s) => s.number === place?.sura) ?? null;

  useEffect(() => {
    if (!place) {
      setLoading(false);
      return;
    }
    let alive = true;
    setLoading(true);
    suraAyat(place.sura, lang)
      .then((got) => {
        if (!alive) return;
        setTotal(got.n_ayat);
        setAyah(got.ayat.find((a) => a.aya === place.aya) ?? null);
        setNext(got.ayat.find((a) => a.aya === place.aya + 1) ?? null);
      })
      .catch(() => alive && setAyah(null))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [place?.sura, place?.aya, lang]);

  useEffect(() => {
    if (!consented) return setRows([]);
    history(4)
      .then(setRows)
      .catch(() => setRows([]));
  }, [consented]);

  return (
    <>
      <h2 className="today__greet">{t(lang, "today_greeting")}</h2>
      <p className="today__date">{dateline(lang)}</p>

      {/* ── hero ─────────────────────────────────────────────────────── */}
      {loading ? (
        <div className="card">
          <Loading rows={3} />
        </div>
      ) : place && sura && ayah ? (
        <article className="card hero">
          <p className="card__kicker">{t(lang, "today_continue")}</p>
          <div className="hero__label">
            <span>
              <span className="hero__sura">{sura.translit}</span>
              <span className="hero__meaning"> · {sura.uz}</span>
            </span>
            <span className="row__ar row__ar--name" dir="rtl" lang="ar">
              {sura.name_ar}
            </span>
          </div>

          <p className="hero__ar" dir="rtl" lang="ar">
            {ayah.uthmani}
          </p>
          <p className="hero__ref">
            {sura.number}:{ayah.aya}
          </p>

          <div className="progress" aria-hidden="true">
            <span
              className="progress__fill"
              style={{ width: `${Math.round((ayah.aya / Math.max(total, 1)) * 100)}%` }}
            />
          </div>
          <p className="progress__text">
            {t(lang, "today_progress")
              .replace("{n}", String(ayah.aya))
              .replace("{of}", String(total))}
            {" · ≈ "}
            {secs(lang, ayah.seconds)}
          </p>

          <button
            className="btn-primary"
            onClick={() => onResume(place.sura, place.aya)}
          >
            {t(lang, "today_resume")}
          </button>
        </article>
      ) : (
        <article className="card">
          <Blank
            title={t(lang, "today_first_title")}
            body={t(lang, "today_first_body")}
            action={t(lang, "today_first_action")}
            onAction={onBrowse}
            ornament={<ArchOrnament className="blank__ornament" size={40} />}
          />
        </article>
      )}

      {/* ── recent ───────────────────────────────────────────────────── */}
      <p className="section-label" style={{ margin: "34px 0 12px" }}>
        {t(lang, "today_recent")}
      </p>
      {rows === null ? (
        <Loading rows={3} />
      ) : rows.length === 0 ? (
        <p className="empty">
          {consented ? t(lang, "today_recent_none") : t(lang, "today_recent_off")}
        </p>
      ) : (
        <ul className="list">
          {rows.map((r, i) => (
            <li className="log" key={r.id ?? i}>
              <span
                className={r.clean ? "log__dot log__dot--clear" : "log__dot"}
                aria-hidden="true"
              />
              <span className="log__text">
                {suras.find((s) => s.number === r.sura)?.translit ?? r.sura}{" "}
                {r.sura}:{r.aya}
              </span>
              <span className="log__meta">
                {r.status === "retry_recording"
                  ? t(lang, "log_retry")
                  : !r.analysable
                    ? t(lang, "log_unassessed")
                    : r.clean
                      ? t(lang, "log_clear")
                      : t(lang, "log_noted")}
              </span>
            </li>
          ))}
        </ul>
      )}

      {/* ── suggested next ───────────────────────────────────────────── */}
      {next && sura && (
        <>
          <p className="section-label" style={{ margin: "34px 0 12px" }}>
            {t(lang, "today_next")}
          </p>
          <article className="card">
            <button
              className="suggest"
              onClick={() => onPick(sura.number, next.aya)}
            >
              <span>
                <span className="suggest__name">
                  {sura.translit} {sura.number}:{next.aya}
                </span>
                <span className="suggest__why">
                  {t(lang, "today_next_why")} · ≈ {secs(lang, next.seconds)}
                </span>
              </span>
              <span className="row__mark" aria-hidden="true">
                <Chevron />
              </span>
            </button>
          </article>
        </>
      )}
    </>
  );
}

const secs = (lang: Lang, s: number) =>
  s >= 60
    ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`
    : `${s.toFixed(0)} ${t(lang, "seconds_short")}`;

