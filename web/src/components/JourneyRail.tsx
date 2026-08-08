import { Sura } from "../lib/api";
import { Lang, t } from "../lib/i18n";

/**
 * YOUR JOURNEY — a horizontal rail of suras to go to next.
 *
 * ── WHAT MAKES THE LIST, AND WHY IT IS NOT A CURRICULUM ────────────────────
 *
 * The suras that FOLLOW the one being read, in mushaf order, starting with the
 * current one. That is the whole rule, and it is deliberately dumb.
 *
 * The tempting version of this card ranks suras by difficulty and calls itself
 * a path. This app has no model of ayah difficulty — only length — so a
 * difficulty ordering would be a length ordering with a pedagogy painted on
 * it, which is a fabricated curriculum in the same way an invented statistic
 * is a fabricated number. Mushaf order claims nothing it cannot back: these are
 * the suras that come next, because they come next.
 *
 * With no place stored there is nothing to be "next" to, so the rail is not
 * drawn at all rather than falling back to a hand-picked starter list — that
 * list would be exactly the recommendation this component has just declined to
 * make.
 *
 * Every card carries the real Arabic name, the transliteration and the real
 * ayah count from the catalogue. Nothing is decorative and nothing is invented.
 */
export default function JourneyRail({
  lang,
  suras,
  from,
  onOpen,
}: {
  lang: Lang;
  suras: Sura[];
  /** The sura currently being read. */
  from: number | null;
  onOpen: (sura: number) => void;
}) {
  if (!from) return null;
  const start = suras.findIndex((s) => s.number === from);
  if (start < 0) return null;

  const list = suras.slice(start, start + 6);
  if (list.length === 0) return null;

  return (
    <section className="today__block">
      <header className="section-head">
        <div>
          <p className="section-label">{t(lang, "journey_next_kicker")}</p>
          <h2 className="section-title">{t(lang, "journey_next_title")}</h2>
        </div>
      </header>

      {/* Overflowing its own scroller, not the page. The rail bleeds to the
          screen edge so the last card is visibly cut — the one honest signal
          that a horizontal list continues. */}
      <ul className="rail">
        {list.map((s) => (
          <li key={s.number}>
            <button className="rail__card" onClick={() => onOpen(s.number)}>
              <span className="rail__num">{s.number}</span>
              <span className="rail__ar" dir="rtl" lang="ar">
                {s.name_ar}
              </span>
              <span className="rail__name">{s.translit}</span>
              <span className="rail__meta">
                {t(lang, "journey_ayat_n").replace("{n}", String(s.n_ayat))}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
