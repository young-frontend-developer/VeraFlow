import { useEffect, useMemo, useRef, useState } from "react";
import Reader, { ReadMode } from "./Reader";
import {
  AyahBrief,
  PracticeSegment,
  Reciter,
  Sura,
  SuraAyat,
  ayahSegments,
  foldQuery,
  suraAyat,
} from "../lib/api";
import { Lang, t } from "../lib/i18n";

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
};

type Props = {
  lang: Lang;
  suras: Sura[];
  /** Reopens on the previous choice instead of resetting to al-Fatiha. */
  initial?: { sura: number; aya: number } | null;
  onPick: (s: Selection) => void;
  mode: ReadMode;
  onMode: (m: ReadMode) => void;
  reciters: Reciter[];
  reciter: string;
  onReciter: (id: string) => void;
};

export default function Picker({
  lang,
  suras,
  initial,
  onPick,
  mode,
  onMode,
  reciters,
  reciter,
  onReciter,
}: Props) {
  const [query, setQuery] = useState("");
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

  const filtered = useMemo(() => {
    const q = foldQuery(query);
    if (!q) return suras;
    return suras.filter((s) => s.search.includes(q));
  }, [suras, query]);

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

  async function openAyah(s: Sura, a: AyahBrief) {
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
      });
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  // ── sura pane ──────────────────────────────────────────────────────────
  if (!sura) {
    return (
      <>
        <h2 className="section-head">{t(lang, "pick_sura")}</h2>
        <input
          className="search"
          type="search"
          inputMode="search"
          value={query}
          placeholder={t(lang, "search_sura")}
          aria-label={t(lang, "search_sura")}
          onChange={(e) => setQuery(e.target.value)}
        />
        {filtered.length === 0 ? (
          <p className="empty">{t(lang, "no_matches")}</p>
        ) : (
          <ul className="list list--scroll">
            {filtered.map((s) => (
              <li key={s.number}>
                <button className="row" onClick={() => openSura(s)}>
                  <span className="row__num">{s.number}</span>
                  <span className="row__body">
                    <span className="row__name">
                      {s.translit}
                      <span className="row__alt"> · {s.uz}</span>
                    </span>
                    <span className="row__meta">
                      {s.n_ayat} {t(lang, "ayat_count")}
                    </span>
                  </span>
                  <span className="row__ar row__ar--name" dir="rtl" lang="ar">
                    {s.name_ar}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </>
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
        <p className="empty">{t(lang, "error_generic")}</p>
      </>
    );
  }

  if (!ayat) {
    return (
      <>
        <button className="crumb" onClick={() => setSura(null)}>
          ← {t(lang, "pick_sura")}
        </button>
        <p className="empty">{t(lang, "loading")}</p>
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
      onPractise={(a) => openAyah(sura, a)}
      onBack={() => setSura(null)}
      onOpenSura={(s, aya) => openSura(s, aya)}
      busy={busy}
      reciters={reciters}
      reciter={reciter}
      onReciter={onReciter}
    />
  );
}
