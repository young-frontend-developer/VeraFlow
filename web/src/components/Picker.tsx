import { useEffect, useMemo, useRef, useState } from "react";
import { AyahLine } from "./AyahText";
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

/**
 * Sura -> ayah -> segment, against the real catalogue: all 114 suras, all 6236
 * ayat, and the precomputed practice segments underneath them.
 *
 * Three panes rather than one long list. The Quran is not browsable as a flat
 * list of 6236 things, and a picker that pretends otherwise is the reason the
 * app shipped with a curated shortlist instead.
 */

export type Selection = {
  sura: Sura;
  ayah: AyahBrief;
  segment: PracticeSegment;
  /** True when the chosen segment is the entire ayah. */
  whole: boolean;
};

type Props = {
  lang: Lang;
  suras: Sura[];
  /** Reopens on the previous choice instead of resetting to al-Fatiha. */
  initial?: { sura: number; aya: number } | null;
  onPick: (s: Selection) => void;
};

const secs = (lang: Lang, s: number) =>
  `${s.toFixed(s < 10 ? 1 : 0)} ${t(lang, "seconds_short")}`;

export default function Picker({ lang, suras, initial, onPick }: Props) {
  const [query, setQuery] = useState("");
  const [sura, setSura] = useState<Sura | null>(null);
  const [ayat, setAyat] = useState<SuraAyat | null>(null);
  const [ayah, setAyah] = useState<AyahBrief | null>(null);
  const [segments, setSegments] = useState<PracticeSegment[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const ayahScroll = useRef<HTMLDivElement>(null);

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
    setAyah(null);
    setSegments(null);
    setAyat(null);
    setBusy(true);
    setFailed(false);
    try {
      const list = await suraAyat(s.number);
      setAyat(list);
      if (jumpToAya) {
        const found = list.ayat.find((a) => a.aya === jumpToAya);
        if (found) await openAyah(s, found);
      }
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  async function openAyah(s: Sura, a: AyahBrief) {
    setAyah(a);
    setSegments(null);
    setBusy(true);
    setFailed(false);
    try {
      const got = await ayahSegments(s.number, a.aya);
      setSegments(got.segments);
      // One segment means the whole ayah is the only range — nothing to choose,
      // so don't make the learner tap a list of one.
      if (got.segments.length === 1) {
        onPick({ sura: s, ayah: a, segment: got.segments[0], whole: true });
      }
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

  // ── ayah pane ──────────────────────────────────────────────────────────
  if (!ayah) {
    return (
      <>
        <button className="crumb" onClick={() => setSura(null)}>
          ← {t(lang, "pick_sura")}
        </button>
        <h2 className="section-head">
          {sura.number}. {sura.translit}
        </h2>
        <p className="section-sub">{t(lang, "pick_ayah")}</p>

        {failed && <p className="empty">{t(lang, "error_generic")}</p>}
        {!ayat ? (
          <p className="empty">{t(lang, "loading")}</p>
        ) : (
          <div className="list list--scroll" ref={ayahScroll}>
            <ul>
              {ayat.ayat.map((a) => (
                <li key={a.aya}>
                  <button className="row" onClick={() => openAyah(sura, a)}>
                    <span className="row__num">{a.aya}</span>
                    <span className="row__body">
                      <AyahLine uthmani={a.uthmani} />
                      <span className="row__meta">
                        {a.n_segments > 1
                          ? `${a.n_segments} ${t(lang, "parts")} · `
                          : ""}
                        {secs(lang, a.seconds)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </>
    );
  }

  // ── segment pane ───────────────────────────────────────────────────────
  return (
    <>
      <button className="crumb" onClick={() => setAyah(null)}>
        ← {sura.translit}
      </button>
      <h2 className="section-head">
        {sura.number}:{ayah.aya}
      </h2>
      <p className="section-sub">{t(lang, "pick_segment")}</p>

      {failed && <p className="empty">{t(lang, "error_generic")}</p>}
      {busy || !segments ? (
        <p className="empty">{t(lang, "loading")}</p>
      ) : (
        <ul className="list">
          {segments.map((seg) => (
            <li key={seg.index}>
              <button
                className="row"
                onClick={() =>
                  onPick({
                    sura,
                    ayah,
                    segment: seg,
                    whole: segments.length === 1,
                  })
                }
              >
                <span className="row__num">{seg.index + 1}</span>
                <span className="row__body">
                  <AyahLine uthmani={seg.uthmani} />
                  <span className="row__meta">
                    {t(lang, "words")} {seg.start_word + 1}–
                    {seg.start_word + seg.num_words} · {secs(lang, seg.seconds)}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
