import { useEffect, useState } from "react";
import {
  Attempt,
  AyahBrief,
  Hadith,
  Sura,
  hadithToday,
  history,
  suraAyat,
} from "../lib/api";
import { Lang, dateline, greeting, sinceLabel, t } from "../lib/i18n";
import DailyHadith from "./DailyHadith";
import JourneyRail from "./JourneyRail";
import TutorCard from "./TutorCard";
import { RankCard, StatsRow, WeekRow } from "./Standing";
import { RecentAchievements } from "./Achievements";
import { recent, signalsFrom } from "../lib/achievements";
import { totals as totalsOf } from "../lib/progress";
import { hasJourney, storedJourney } from "../lib/journey";
import { Blank, Loading } from "./States";
import { ArchOrnament, Chevron } from "./Ornament";

/**
 * HOME — the screen the app opens on.
 *
 * ── THE ORDER, AND WHY IT IS THIS ORDER ────────────────────────────────────
 *
 *   greeting     who you are and when it is. One line, no card.
 *   continue     the ONE lit card on the screen: the ayah you were on, set
 *                large enough to actually read, and the button that resumes it
 *   figures      streak, hasanat, ayat, time — four counters, real or zero
 *   rank         the named stage and the distance to the next
 *   week         seven days, three shapes
 *   journey      the suras that come next, as a rail
 *   hadith       the day's narration, cited, or nothing at all
 *   tutor        what the guidance is, with no face on it
 *   badges       earned only
 *
 * It descends from the specific to the general, and the descent is the design:
 * one thing to do now, then the shape of your practice, then the wider path.
 * A learner who reads only the first card has still been given the answer to
 * the question they opened the app with.
 *
 * ── EVERY MODULE IS BACKED BY REAL DATA OR IT IS NOT DRAWN ─────────────────
 *
 * This was the rule here before the visual overhaul and the overhaul does not
 * relax it. It is now the rule under MORE pressure, not less: a gamification
 * layer is the easiest place in a product to draw a number that looks finished
 * the instant it is drawn. Where a section can be built from real rows it is;
 * where it cannot, it is absent:
 *
 *   continue   the stored place, with progress and remaining time from the
 *              engine's own per-ayah estimate. With nothing stored the card
 *              becomes a designed invitation, not a grey box.
 *   figures    counted in lib/progress.ts from attempts. Zeroes are DRAWN and
 *              styled — see the note in Standing.tsx for why these show zero
 *              where the week card hides itself.
 *   rank       a band of that same XP. Nothing awards XP for opening the app.
 *   journey    mushaf order from where you are. Absent with no place stored,
 *              because there is nothing for a suggestion to be relative to.
 *   hadith     reviewed entries only; null is a real answer and draws nothing.
 *   badges     earned only, from real history.
 *
 * THE LEARNING CARD IS GONE FROM THIS SCREEN. It used to sit here as an honest
 * empty state saying no course exists. That was the right call while Home had
 * five sections; with nine it became a paragraph of apology in the middle of
 * the screen. The same refusal still lives in the Learn tab, in the same words,
 * which is where someone looking for a course will go.
 *
 * "Last practiced N ago" is read off the newest attempt's real timestamp and
 * omitted entirely when there is none.
 */

export default function Today({
  lang,
  suras,
  place,
  consented,
  onResume,
  onPick,
  onOpenSura,
  onBrowse,
  onViewAchievements,
}: {
  lang: Lang;
  suras: Sura[];
  /** Where they left off, or null on a first run. */
  place: { sura: number; aya: number } | null;
  consented: boolean;
  onResume: (sura: number, aya: number) => void;
  onPick: (sura: number, aya: number) => void;
  onOpenSura: (sura: number) => void;
  onBrowse: () => void;
  /** Open the full achievement wall, which lives in Profile. */
  onViewAchievements: () => void;
}) {
  const [ayah, setAyah] = useState<AyahBrief | null>(null);
  const [next, setNext] = useState<AyahBrief | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<Attempt[] | null>(null);
  /**
   * Whether there IS a hadith today. Fetched here as well as inside the card so
   * the section HEADING can be suppressed with it — a "Hadis" title sitting
   * over nothing reads as a card that failed to load, which is exactly what the
   * null answer is not.
   */
  const [hadith, setHadith] = useState<Hadith | null>(null);

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
    let alive = true;
    hadithToday(lang)
      .then((got) => alive && setHadith(got))
      .catch(() => alive && setHadith(null));
    return () => {
      alive = false;
    };
  }, [lang]);

  useEffect(() => {
    if (!consented) return setRows([]);
    history(200)
      .then(setRows)
      .catch(() => setRows([]));
  }, [consented]);

  // The newest attempt carrying a real timestamp. Undated rows are skipped
  // rather than treated as recent.
  const lastDated = (rows ?? []).find((r) => Boolean(r.created_at));
  const since = lastDated?.created_at
    ? sinceLabel(lang, new Date(lastDated.created_at))
    : "";

  const percent = ayah && total > 0 ? Math.round((ayah.aya / total) * 100) : 0;
  const totals = totalsOf(rows ?? []);

  return (
    <>
      {/* ── GREETING ─────────────────────────────────────────────────────
             Not in a card. The one piece of type on this screen that sits
             directly on the atmosphere, which is what makes the first card
             below it read as the first LAYER rather than as the first item. */}
      <header className="greet">
        <h2 className="greet__line">{greeting(lang)}</h2>
        <p className="greet__meta">
          {dateline(lang)}
          {since && <span className="greet__since"> · {since}</span>}
        </p>
      </header>

      {/* ── 1. CONTINUE ─────────────────────────────────────────────────── */}
      {loading ? (
        <div className="card">
          <Loading rows={3} />
        </div>
      ) : place && sura && ayah ? (
        <article className="card card--hero hero">
          <div className="hero__label">
            <div>
              <p className="section-label">{t(lang, "home_continue_kicker")}</p>
              <h3 className="hero__name">{sura.translit}</h3>
              <p className="hero__meaning">{sura.uz}</p>
            </div>
            {/* The sura's own name, in Arabic, at display size. It is the
                card's mark — which is why it is set as type and not as an
                icon. */}
            <span className="hero__sura-ar" dir="rtl" lang="ar">
              {sura.name_ar}
            </span>
          </div>

          <p className="hero__ar" dir="rtl" lang="ar">
            {ayah.uthmani}
          </p>

          <div className="progress-row">
            <span className="progress__end">{ayah.aya}</span>
            <div className="progress" aria-hidden="true">
              <span
                className="progress__fill"
                style={{ width: `${percent}%` }}
              />
            </div>
            <span className="progress__end">{total}</span>
          </div>
          <p className="progress__text">
            {t(lang, "hero_verse_of")
              .replace("{n}", String(ayah.aya))
              .replace("{of}", String(total))}
            {" · "}
            {t(lang, "hero_remaining").replace("{t}", secs(lang, ayah.seconds))}
          </p>

          <button
            className="btn-primary hero__go"
            onClick={() => onResume(place.sura, place.aya)}
          >
            {t(lang, "home_continue_cta")}
            <span className="hero__go-mark" aria-hidden="true">
              <Chevron size={15} />
            </span>
          </button>
        </article>
      ) : (
        <article className="card card--hero">
          <Blank
            title={t(lang, "today_first_title")}
            body={t(lang, "today_first_body")}
            action={t(lang, "home_begin_cta")}
            onAction={onBrowse}
            ornament={<ArchOrnament className="blank__ornament" size={40} />}
          />
        </article>
      )}

      {/* ── 2. THE FIGURES ──────────────────────────────────────────────
             Only where there is history to count, or the possibility of any.
             With retention declined there is no history and never will be, so
             the whole block is absent rather than showing four permanent
             zeroes that the learner has no way to move. Profile is where that
             gets changed. */}
      {consented && rows !== null && (
        <>
          <StatsRow lang={lang} totals={totals} />
          <RankCard lang={lang} totals={totals} />
          <WeekRow lang={lang} rows={rows} />
        </>
      )}

      {/* ── 3. YOUR JOURNEY ─────────────────────────────────────────────── */}
      <JourneyRail
        lang={lang}
        suras={suras}
        from={place?.sura ?? null}
        onOpen={onOpenSura}
      />

      {/* ── 4. THE DAY'S HADITH ──────────────────────────────────────────
             Every entry is authenticated and carries its collection and
             reference number; nothing is generated and nothing is attributed
             loosely. The card draws nothing at all when the server has nothing
             reviewed to give it, which in production is currently always — see
             DailyHadith and content/hadith.py. The heading goes with it, so an
             absent hadith does not leave a section title over empty space. */}
      {hadith && (
        <section className="today__block">
          <header className="section-head">
            <div>
              <p className="section-label">{t(lang, "hadith_kicker_section")}</p>
              <h2 className="section-title">{t(lang, "hadith_title")}</h2>
            </div>
          </header>
          <DailyHadith lang={lang} />
        </section>
      )}

      {/* ── 5. THE TUTOR ────────────────────────────────────────────────── */}
      <TutorCard
        lang={lang}
        onStart={() =>
          place ? onResume(place.sura, place.aya) : onBrowse()
        }
      />

      {/* ── 6. BADGES ────────────────────────────────────────────────────
             A preview of three EARNED badges and a way to the full wall, which
             lives in Profile. Absent entirely until something has been earned:
             a row of grey placeholders on the screen that answers "what do I do
             now" is three things you have not done. */}
      <RecentAchievements
        lang={lang}
        items={recent(
          signalsFrom(
            rows ?? [],
            Object.fromEntries(suras.map((s) => [s.number, s.n_ayat])),
            { hasJourney: hasJourney(storedJourney()) },
          ),
        )}
        onViewAll={onViewAchievements}
      />

      {/* ── suggested next ayah ─────────────────────────────────────────── */}
      {next && sura && (
        <section className="today__block">
          <p className="section-label">{t(lang, "today_next")}</p>
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
        </section>
      )}
    </>
  );
}

const secs = (lang: Lang, s: number) =>
  s >= 60
    ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`
    : `${s.toFixed(0)} ${t(lang, "seconds_short")}`;
