import { useEffect, useMemo, useRef, useState } from "react";
import Reader, { ReadMode } from "./Reader";
import {
  AyahBrief,
  PracticeSegment,
  Sura,
  SuraAyat,
  ayahSegments,
  foldQuery,
  suraAyat,
} from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { Blank, Failure, Loading } from "./States";

/**
 * Sura -> read -> practise, against the real catalogue: all 114 suras and all
 * 6236 ayat.
 *
 * Two panes. The Quran is not browsable as a flat list of 6236 things, and a
 * picker that pretends otherwise is the reason the app shipped with a curated
 * shortlist instead. The second pane is a READER (see Reader.tsx), in mushaf or
 * verse-by-verse form, because choosing an ayah and reading one are the same
 * act — the old flat row list was neither.
 *
 * THERE IS NO SEGMENT PANE. Choosing an ayah selects the WHOLE ayah, however
 * long it is. It used to land on a third pane asking which part you meant,
 * because segmentation had split 72% of the Quran into 12-second chunks — a
 * question nobody asked for, imposed on the majority of ayat. Practising part
 * of a long ayah is still available, but from inside Recite, as a choice.
 */

/**
 * ── THE LIST IS IN MUSHAF ORDER. THIS WAS A REAL BUG. ──────────────────────
 *
 * It used to be grouped into three bands by ayah count — short, medium, long —
 * on the reasoning that "can I read this in one sitting?" is the question a
 * learner is really asking, and that a flat index of 114 answers nothing.
 *
 * That reasoning was wrong in a way that is obvious the moment you look at the
 * screen instead of at the argument. Al-Fatiha has 7 ayat, so it opened the
 * short band; the next sura with 20 ayat or fewer is number 60. The list
 * therefore read 1, 60, 61, 62, 63… and every learner who has ever held a
 * mushaf reads that as broken, because it is. The Qur'an has an order. It is
 * not a database someone forgot to sort, and the app does not get to reindex
 * it for browsing convenience.
 *
 * The question the bands were trying to answer is real, and it is now answered
 * where it belongs — by the ayah count printed on every row, and by the filter
 * pills, which cut the list without reordering it.
 */

/** The pills above the list. `started` is computed from real attempts. */
type Filter = "all" | "makki" | "madani" | "started";

const FILTERS: { id: Filter; key: "filter_all" | "filter_makki"
  | "filter_madani" | "filter_started" }[] = [
  { id: "all", key: "filter_all" },
  { id: "makki", key: "filter_makki" },
  { id: "madani", key: "filter_madani" },
  { id: "started", key: "filter_started" },
];

export type Selection = {
  sura: Sura;
  ayah: AyahBrief;
  /** The range being recited. Defaults to the whole ayah, always. */
  segment: PracticeSegment;
  /** True when `segment` is the entire ayah. */
  whole: boolean;
  /**
   * The whole ayah, kept even while a part is selected, so returning to it is
   * a state change rather than another round trip.
   */
  wholeSegment: PracticeSegment;
  /**
   * The optional narrower ranges, carried along so Recite can offer "practise
   * part of this ayah" without a second round trip. Empty when the ayah has no
   * meaningful subdivision.
   */
  parts: PracticeSegment[];
  /**
   * Begin recording as soon as the practice screen mounts.
   *
   * Set only by the verse view's pinned mic. Choosing an ayah from the mushaf
   * or the picker leaves it unset, because those are acts of CHOOSING and
   * opening a microphone on someone who was browsing is a different thing
   * entirely from opening one on someone who just pressed record.
   */
  autoRecord?: boolean;
};

type Props = {
  lang: Lang;
  suras: Sura[];
  /** Reopens on the previous choice instead of resetting to al-Fatiha. */
  initial?: { sura: number; aya: number } | null;
  onPick: (s: Selection) => void;
  mode: ReadMode;
  onMode: (m: ReadMode) => void;
  /** Chosen once in Settings; passed through to the reader's listen button. */
  reciter: string;
  /**
   * Sura numbers the learner has actually recited from, for the "Started"
   * pill. Empty when retention is off — in which case the pill is not drawn at
   * all rather than drawn and always empty. There is no local guess at which
   * suras were started; that would be a fabricated history.
   */
  started: Set<number>;
};

export default function Picker({
  lang,
  suras,
  initial,
  onPick,
  mode,
  onMode,
  reciter,
  started,
}: Props) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [sura, setSura] = useState<Sura | null>(null);
  const [ayat, setAyat] = useState<SuraAyat | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  // Where the learner is in the sura: the marked ayah in the mushaf, and the
  // one shown in verse-by-verse. Only ever a position — never a selection.
  const [focusAya, setFocusAya] = useState<number | null>(null);

  // Reopen where the learner left off. Keyed on the place itself, not a
  // one-shot flag, so the Library shortcut can move the picker after mount —
  // but never twice for the same place, which would fight the learner's taps.
  const restoredKey = useRef<string | null>(null);
  useEffect(() => {
    if (!initial || suras.length === 0) return;
    const key = `${initial.sura}:${initial.aya}`;
    if (restoredKey.current === key) return;
    restoredKey.current = key;
    const found = suras.find((s) => s.number === initial.sura);
    if (found) openSura(found, initial.aya);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [suras, initial?.sura, initial?.aya]);

  /**
   * Search AND pill, in that order, and never a reorder.
   *
   * `suras` arrives from /api/suras in mushaf order and every step here
   * preserves it — `filter` keeps relative order by definition. That is the
   * whole fix for the ordering bug: there is no sort anywhere in this file,
   * because the correct order is the one the data already has.
   */
  const filtered = useMemo(() => {
    const q = foldQuery(query);
    return suras.filter((s) => {
      if (q && !s.search.includes(q)) return false;
      if (filter === "makki") return s.place === "makki";
      if (filter === "madani") return s.place === "madani";
      if (filter === "started") return started.has(s.number);
      return true;
    });
  }, [suras, query, filter, started]);

  async function openSura(s: Sura, jumpToAya?: number) {
    setSura(s);
    setAyat(null);
    setFocusAya(jumpToAya ?? null);
    setBusy(true);
    setFailed(false);
    try {
      // A restore stops here, at the reader. It deliberately does NOT open
      // `jumpToAya`: openAyah selects, so restoring through it re-selected the
      // ayah the learner had just backed out of and "Boshqa oyat tanlash"
      // bounced straight back to Recite. jumpToAya only says where to look, and
      // the learner still taps.
      setAyat(await suraAyat(s.number, lang));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  // The sura payload carries the translation, so switching language has to
  // refetch it — otherwise the reader keeps showing Uzbek under a Russian UI.
  useEffect(() => {
    if (sura) openSura(sura, focusAya ?? undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  async function openAyah(s: Sura, a: AyahBrief, record = false) {
    setBusy(true);
    setFailed(false);
    try {
      const got = await ayahSegments(s.number, a.aya);
      // Straight to the whole ayah. No length check and no branch on the number
      // of parts: the ayah the learner tapped is the ayah they get.
      onPick({
        sura: s,
        ayah: a,
        segment: got.whole,
        whole: true,
        wholeSegment: got.whole,
        parts: got.parts,
        // Carried through so the practice screen knows this came from the
        // verse view's mic and should start listening immediately.
        autoRecord: record,
      });
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  // ── sura pane ──────────────────────────────────────────────────────────
  // The full 114, in order, on a full screen. Not a sheet and not a popover:
  // this is the app's index and it gets the whole viewport, because choosing
  // what to recite is a real decision and 114 rows do not fit in a drawer.
  if (!sura) {
    // The pill is only offered when there is a history to filter against.
    // Drawn with retention off it would be a control that is permanently
    // empty and permanently unexplained.
    const pills = FILTERS.filter(
      (f) => f.id !== "started" || started.size > 0,
    );

    return (
      <section className="picker">
        <header className="picker__head">
          <h2 className="section-title section-title--hero">
            {t(lang, "pick_sura")}
          </h2>
          <p className="picker__count">
            {t(lang, "sura_count_n").replace("{n}", String(filtered.length))}
          </p>
        </header>

        {/* Matches the Arabic name, the standard transliteration and the Uzbek
            spelling at once — the haystack is prefolded server-side and the
            query is folded the same way, so "gofir", "Gʻofir" and غافر all
            land on sura 40. See foldQuery in lib/api.ts. */}
        <input
          className="search picker__search"
          type="search"
          inputMode="search"
          value={query}
          placeholder={t(lang, "search_sura")}
          aria-label={t(lang, "search_sura")}
          onChange={(e) => setQuery(e.target.value)}
        />

        <div className="pills" role="tablist" aria-label={t(lang, "filter_all")}>
          {pills.map((f) => (
            <button
              key={f.id}
              role="tab"
              aria-selected={filter === f.id}
              className={filter === f.id ? "pill pill--on" : "pill"}
              onClick={() => setFilter(f.id)}
            >
              {t(lang, f.key)}
            </button>
          ))}
        </div>

        {filtered.length === 0 ? (
          // NOT a line of grey text. The learner narrowed to nothing, so this
          // says what they searched and gives them the control that recovers.
          // Clearing resets the pill too — a "no results" they cannot explain
          // because a filter three taps ago is still on is worse than none.
          <Blank
            title={t(lang, "no_matches")}
            body={t(lang, "no_matches_body").replace("{q}", query.trim())}
            action={t(lang, "no_matches_clear")}
            onAction={() => {
              setQuery("");
              setFilter("all");
            }}
          />
        ) : (
          <ul className="list list--suras">
            {filtered.map((s) => (
              <SuraRow
                key={s.number}
                lang={lang}
                sura={s}
                started={started.has(s.number)}
                onOpen={openSura}
              />
            ))}
          </ul>
        )}
      </section>
    );
  }

  // ── reading pane ───────────────────────────────────────────────────────
  // The last pane. Choosing an ayah here resolves the whole ayah and hands it
  // to Recite — reading and choosing are the same act.
  if (failed && !ayat) {
    return (
      <>
        <button className="crumb" onClick={() => setSura(null)}>
          ← {t(lang, "pick_sura")}
        </button>
        <Failure
          lang={lang}
          title={t(lang, "sura_failed_title")}
          body={t(lang, "sura_failed_body")}
          onRetry={() => openSura(sura, focusAya ?? undefined)}
        />
      </>
    );
  }

  if (!ayat) {
    return (
      <>
        <button className="crumb" onClick={() => setSura(null)}>
          ← {t(lang, "pick_sura")}
        </button>
        <Loading rows={7} />
      </>
    );
  }

  return (
    <Reader
      lang={lang}
      sura={sura}
      suras={suras}
      ayat={ayat}
      mode={mode}
      onMode={onMode}
      focusAya={focusAya}
      onFocusAya={setFocusAya}
      onPractise={(a, record) => openAyah(sura, a, record)}
      onBack={() => setSura(null)}
      onOpenSura={(s, aya) => openSura(s, aya)}
      busy={busy}
      reciter={reciter}
    />
  );
}

/**
 * One sura: number in a lit badge, name, where it was revealed, how long it is,
 * and the Arabic name set large on the right.
 *
 * The revelation place is printed on the row and not only used by the pill —
 * a filter for a fact the rows themselves do not show is a filter people
 * cannot predict the result of. An unknown place prints nothing rather than a
 * guess; see the note on Sura.place.
 */
function SuraRow({
  lang,
  sura,
  started,
  onOpen,
}: {
  lang: Lang;
  sura: Sura;
  started: boolean;
  onOpen: (s: Sura) => void;
}) {
  return (
    <li>
      <button className="row row--sura" onClick={() => onOpen(sura)}>
        <span className={started ? "sura-badge sura-badge--on" : "sura-badge"}>
          {sura.number}
        </span>
        <span className="row__body">
          <span className="row__name">
            {sura.translit}
            <span className="row__alt"> · {sura.uz}</span>
          </span>
          <span className="row__meta">
            {sura.place === "makki" && t(lang, "place_makki")}
            {sura.place === "madani" && t(lang, "place_madani")}
            {sura.place ? " · " : ""}
            {sura.n_ayat} {t(lang, "ayat_count")}
          </span>
        </span>
        <span className="row__ar row__ar--name" dir="rtl" lang="ar">
          {sura.name_ar}
        </span>
      </button>
    </li>
  );
}
