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
import { Lang, sinceLabel, t } from "../lib/i18n";
import DailyPlan, { PlanStep, buildPlan } from "./DailyPlan";
import DailyHadith from "./DailyHadith";
import WeekStats from "./WeekStats";
import { RecentAchievements } from "./Achievements";
import { recent, signalsFrom } from "../lib/achievements";
import { hasJourney, storedJourney } from "../lib/journey";
import { Blank, Loading } from "./States";
import { ArchOrnament, BookOrnament, Chevron } from "./Ornament";

/**
 * TODAY — the screen the app opens on.
 *
 * Five sections, top to bottom: where you left off, a plan for the day, the
 * daily verse, learning, and the week. That is the reference design's order and
 * it is a good one — it moves from the specific thing to resume, out to the
 * shape of the day, then to something to sit with, and only then to anything
 * resembling a number.
 *
 * EVERY MODULE IS BACKED BY REAL DATA OR IT IS NOT DRAWN. This was already the
 * rule here before the restyle and the restyle does not get to relax it — the
 * new sections are the ones most exposed to it, because a plan, a course card
 * and a statistics panel are all things that look complete the instant they are
 * drawn with invented contents.
 *
 *   hero      the place stored when they last chose an ayah. Progress and
 *             minutes-remaining come from the engine's own per-ayah estimate.
 *             With no stored place there is nothing to continue, so the card
 *             becomes an invitation — designed, not a grey box.
 *   plan      derived from that same place. See DailyPlan.
 *   verse     a real ayah, cited. See Reflection.
 *   learning  THERE IS NO COURSE CONTENT. The card is an honest empty state at
 *             the same visual weight, with no modules, hours, percentage or
 *             difficulty label attached to nothing.
 *   week      counted from real attempts, or a designed empty state. See
 *             WeekStats.
 *
 * "Last practiced N ago" is read off the newest attempt's real timestamp, and
 * omitted entirely when there is none rather than defaulted to something
 * plausible.
 */

export default function Today({
  lang,
  suras,
  place,
  consented,
  onResume,
  onPick,
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
  onBrowse: () => void;
  /** Open the full achievement wall, which lives in Profile. */
  onViewAchievements: () => void;
}) {
  const [ayah, setAyah] = useState<AyahBrief | null>(null);
  const [prev, setPrev] = useState<AyahBrief | null>(null);
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
        setPrev(got.ayat.find((a) => a.aya === place.aya - 1) ?? null);
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
    history(60)
      .then(setRows)
      .catch(() => setRows([]));
  }, [consented]);

  // The newest attempt carrying a real timestamp. Undated rows are skipped
  // rather than treated as recent.
  const lastDated = (rows ?? []).find((r) => Boolean(r.created_at));
  const since = lastDated?.created_at
    ? sinceLabel(lang, new Date(lastDated.created_at))
    : "";

  const percent =
    ayah && total > 0 ? Math.round((ayah.aya / total) * 100) : 0;

  const plan: PlanStep[] =
    sura && ayah ? buildPlan(lang, sura, ayah, prev) : [];

  return (
    <>
      {/* ── 1. HERO ──────────────────────────────────────────────────── */}
      <header className="section-head section-head--hero">
        <div>
          <p className="section-label">{t(lang, "today_kicker")}</p>
          <h2 className="section-title section-title--hero">
            {t(lang, "today_title")}
          </h2>
        </div>
        {/* Only when there is a real timestamp behind it. */}
        {since && <p className="section-aside">{since}</p>}
      </header>

      {loading ? (
        <div className="card">
          <Loading rows={3} />
        </div>
      ) : place && sura && ayah ? (
        <article className="card hero">
          <p className="hero__caps">
            {t(lang, "hero_surah")
              .replace("{n}", String(sura.number))
              .replace("{name}", sura.translit)}
          </p>
          <h3 className="hero__name">{sura.uz}</h3>
          <p className="hero__sub">
            {t(lang, "hero_verse_of")
              .replace("{n}", String(ayah.aya))
              .replace("{of}", String(total))}
            {" · "}
            {t(lang, "hero_remaining").replace("{t}", secs(lang, ayah.seconds))}
          </p>

          <p className="hero__ar" dir="rtl" lang="ar">
            {ayah.uthmani}
          </p>

          <p className="progress__pct">{percent}%</p>
          <div className="progress-row">
            <span className="progress__end">{ayah.aya}</span>
            <div className="progress" aria-hidden="true">
              <span className="progress__fill" style={{ width: `${percent}%` }} />
            </div>
            <span className="progress__end">{total}</span>
          </div>

          <div className="hero__foot">
            <button
              className="btn-primary hero__go"
              onClick={() => onResume(place.sura, place.aya)}
            >
              <span className="hero__go-mark" aria-hidden="true">
                <Chevron size={14} />
              </span>
              {t(lang, "today_resume")}
            </button>
            {/* Unattributed by design. It is the app's own aside, not a
                quotation, so there is no one to credit and nothing to
                misattribute. */}
            <p className="hero__aside">{t(lang, "today_aside")}</p>
          </div>
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

      {/* ── 2. THE DAY ───────────────────────────────────────────────── */}
      <DailyPlan lang={lang} steps={plan} onOpen={onPick} />

      {/* ── 3. THE DAY'S HADITH ──────────────────────────────────────────
             Replaced the daily verse card. Every entry is authenticated and
             carries its collection and reference number; nothing is generated
             and nothing is attributed loosely. The card draws nothing at all
             when the server has nothing reviewed to give it, which in
             production is currently always — see DailyHadith and
             content/hadith.py. The heading goes with it, so an absent hadith
             does not leave a section title over empty space. */}
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

      {/* ── 4. LEARNING ──────────────────────────────────────────────────
             NO COURSE EXISTS, so no course card is drawn. The reference puts a
             progress bar, a percentage, a difficulty label and a module count
             here; every one of those would be describing something that has not
             been made. It gets the section heading and a card of the same
             weight saying plainly that the work is not done — the same refusal
             Soon.tsx already makes for the Learn tab, in the same words. */}
      <section className="today__block">
        <header className="section-head">
          <div>
            <p className="section-label">{t(lang, "learning_kicker")}</p>
            <h2 className="section-title">{t(lang, "learning_title")}</h2>
          </div>
        </header>
        <article className="card">
          <Blank
            title={t(lang, "learn_title")}
            body={t(lang, "learn_body")}
            ornament={<BookOrnament className="blank__ornament" size={40} />}
          />
        </article>
      </section>

      {/* ── 5. THE WEEK ──────────────────────────────────────────────── */}
      {consented && (
        <section className="today__block">
          <header className="section-head">
            <div>
              <p className="section-label">{t(lang, "stats_kicker")}</p>
              <h2 className="section-title">{t(lang, "stats_title")}</h2>
            </div>
          </header>
          <WeekStats
            lang={lang}
            rows={rows}
            consented={consented}
            onBrowse={onBrowse}
          />
        </section>
      )}

      {/* ── RECENT ACHIEVEMENTS ──────────────────────────────────────────
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

      {/* ── suggested next ───────────────────────────────────────────── */}
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
