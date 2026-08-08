import { useEffect, useRef, useState } from "react";
import {
  AyahBrief,
  Sura,
  SuraAyat,
  expertAudioUrl,
} from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { Mic } from "./Ornament";

/**
 * Reading a sura, in the two shapes people actually read one.
 *
 *   MUSHAF          continuous text with ayah markers, the way a printed page
 *                   reads. For finding your place and reading in flow.
 *   VERSE BY VERSE  one ayah, its translation, and arrows. For studying.
 *
 * Both are readers, and in both, choosing an ayah starts practising it — the
 * app has one job and reading is the way into it, not a detour from it.
 *
 * The two are deliberately not one view with a toggle on the translation:
 * continuous text with a translation under every ayah is neither of the things
 * anyone wanted, and the mushaf's whole value is the uninterrupted Arabic.
 */

export type ReadMode = "mushaf" | "verse";

/** Western digits -> Arabic-Indic, for the ayah markers only. */
const arabicNum = (n: number) =>
  String(n).replace(/\d/g, (d) => "٠١٢٣٤٥٦٧٨٩"[Number(d)]);

const secs = (lang: Lang, s: number) =>
  s >= 60
    ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`
    : `${s.toFixed(s < 10 ? 1 : 0)} ${t(lang, "seconds_short")}`;

export default function Reader({
  lang,
  sura,
  suras,
  ayat,
  mode,
  onMode,
  focusAya,
  onFocusAya,
  onPractise,
  onBack,
  onOpenSura,
  busy,
  reciter,
}: {
  lang: Lang;
  sura: Sura;
  /** All 114, so verse-by-verse can step across a sura boundary. */
  suras: Sura[];
  ayat: SuraAyat;
  mode: ReadMode;
  onMode: (m: ReadMode) => void;
  /** Where the learner is. Drives both the marker and the verse pane. */
  focusAya: number | null;
  onFocusAya: (aya: number) => void;
  /**
   * Practise this ayah. `record` asks the practice screen to begin recording
   * as soon as it has resolved the range — that is what makes the verse view's
   * mic feel inline rather than like a link to somewhere else.
   */
  onPractise: (a: AyahBrief, record?: boolean) => void;
  onBack: () => void;
  /** Cross a sura boundary: load another sura and land on `aya`. */
  onOpenSura: (sura: Sura, aya: number) => void;
  busy: boolean;
  /** Chosen once in Settings. Resolves the listen button's audio only. */
  reciter: string;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);

  const current =
    ayat.ayat.find((a) => a.aya === focusAya) ?? ayat.ayat[0] ?? null;

  // Changing ayah or reciter must stop whatever is playing: the <audio> src
  // swaps underneath and would otherwise keep going with the old recitation,
  // or leave the button stuck showing "pause".
  useEffect(() => {
    const el = audioRef.current;
    if (el) {
      el.pause();
      el.currentTime = 0;
    }
    setPlaying(false);
  }, [current?.aya, sura.number, reciter]);

  // Keep the focused ayah visible in the mushaf when arrows or a restore move
  // it. Scrolls the reading box, not the page.
  useEffect(() => {
    if (mode !== "mushaf") return;
    const box = scrollRef.current;
    if (!box || focusAya === null) return;
    const el = box.querySelector<HTMLElement>(`[data-aya="${focusAya}"]`);
    if (!el) return;
    const b = box.getBoundingClientRect();
    const r = el.getBoundingClientRect();
    box.scrollTop += r.top - b.top - (b.height - r.height) / 2;
  }, [mode, focusAya, ayat.sura]);

  // ── moving between ayat, across sura boundaries ──────────────────────────
  const idx = current ? ayat.ayat.findIndex((a) => a.aya === current.aya) : -1;
  const prevSura = suras.find((s) => s.number === sura.number - 1) ?? null;
  const nextSura = suras.find((s) => s.number === sura.number + 1) ?? null;
  // 2:286 -> 3:1 and 3:1 -> 2:286. The Quran does not stop at a sura boundary
  // and neither should the arrows; only the first and last ayah of the whole
  // mushaf are genuinely ends.
  const canPrev = idx > 0 || prevSura !== null;
  const canNext = idx >= 0 ? idx < ayat.ayat.length - 1 || nextSura !== null : false;

  function step(delta: -1 | 1) {
    if (idx < 0) return;
    const target = idx + delta;
    if (target >= 0 && target < ayat.ayat.length) {
      onFocusAya(ayat.ayat[target].aya);
      return;
    }
    if (delta < 0 && prevSura) onOpenSura(prevSura, prevSura.n_ayat);
    if (delta > 0 && nextSura) onOpenSura(nextSura, 1);
  }

  function togglePlay() {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
      setPlaying(false);
    } else {
      el.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
    }
  }

  const header = (
    <>
      <button className="crumb" onClick={onBack}>
        ← {t(lang, "pick_sura")}
      </button>
      <div className="reader__head">
        <h2 className="section-head">
          {sura.number}. {sura.translit}
        </h2>
        <span className="reader__ar" dir="rtl" lang="ar">
          {ayat.name_ar}
        </span>
      </div>

      {/* ── STUDY MODE ──────────────────────────────────────────────────
             Two ways to work on a sura, and only one of them is built.

             Yodlash is drawn, disabled, and labelled "Tez orada". That is the
             deliberate middle between the two bad options: hiding it entirely
             hides a planned direction from the person using the app, and
             wiring it to an empty screen is the fabricated-feature failure the
             Learn tab already refuses to commit. A tab you can see, cannot
             press, and which says why is honest about both the plan and the
             state of it.

             It is a BUTTON with `disabled`, not a div — so it is reachable by
             keyboard and announced as unavailable rather than being invisible
             to a screen reader. */}
      <div className="study" role="tablist" aria-label={t(lang, "study_mode")}>
        <button
          role="tab"
          aria-selected={true}
          className="study__tab study__tab--on"
        >
          {t(lang, "study_read")}
        </button>
        <button
          role="tab"
          aria-selected={false}
          className="study__tab study__tab--soon"
          disabled
          title={t(lang, "coming_soon")}
        >
          {t(lang, "study_memorize")}
          <span className="study__soon">{t(lang, "coming_soon")}</span>
        </button>
      </div>

      <div className="modes" role="tablist" aria-label={t(lang, "read_mode")}>
        <button
          role="tab"
          aria-selected={mode === "mushaf"}
          className={mode === "mushaf" ? "modes__tab is-on" : "modes__tab"}
          onClick={() => onMode("mushaf")}
        >
          {t(lang, "mode_mushaf")}
        </button>
        <button
          role="tab"
          aria-selected={mode === "verse"}
          className={mode === "verse" ? "modes__tab is-on" : "modes__tab"}
          onClick={() => onMode("verse")}
        >
          {t(lang, "mode_verse")}
        </button>
      </div>
    </>
  );

  // ── mushaf ───────────────────────────────────────────────────────────────
  if (mode === "mushaf") {
    return (
      <>
        {header}
        <p className="section-sub">{t(lang, "mushaf_hint")}</p>
        <div className="mushaf" ref={scrollRef} dir="rtl" lang="ar">
          {ayat.has_basmala && (
            <p className="mushaf__bismillah">{ayat.bismillah}</p>
          )}
          <p className="mushaf__body">
            {ayat.ayat.map((a) => (
              // A span, not a button: buttons do not reflow as inline text, and
              // the whole point of this view is one continuous paragraph. Keyed
              // to keyboard as well as tap so it stays reachable.
              <span
                key={a.aya}
                data-aya={a.aya}
                role="button"
                tabIndex={0}
                aria-label={`${sura.number}:${a.aya}`}
                className={
                  a.aya === focusAya ? "mushaf__aya is-on" : "mushaf__aya"
                }
                onClick={() => {
                  onFocusAya(a.aya);
                  onPractise(a);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onFocusAya(a.aya);
                    onPractise(a);
                  }
                }}
              >
                {a.uthmani}
                <span className="mushaf__mark" aria-hidden="true">
                  {arabicNum(a.aya)}
                </span>{" "}
              </span>
            ))}
          </p>
        </div>
        {busy && <p className="empty">{t(lang, "loading")}</p>}
      </>
    );
  }

  // ── verse by verse ───────────────────────────────────────────────────────
  if (!current) return <>{header}</>;

  return (
    <>
      {header}

      <div className="verse reader--verse">
        <div className="verse__nav">
          {/* RTL text, LTR controls: previous is on the left because the whole
              interface around it is Latin. Arrows point the way the LEARNER
              reads the app, not the way the Arabic runs. */}
          <button
            className="verse__arrow"
            disabled={!canPrev}
            aria-label={t(lang, "prev_ayah")}
            onClick={() => step(-1)}
          >
            ‹
          </button>
          <span className="verse__ref">
            {sura.number}:{current.aya}
          </span>
          <button
            className="verse__arrow"
            disabled={!canNext}
            aria-label={t(lang, "next_ayah")}
            onClick={() => step(1)}
          >
            ›
          </button>
        </div>

        {ayat.has_basmala && current.aya === 1 && (
          <p className="mushaf__bismillah" dir="rtl" lang="ar">
            {ayat.bismillah}
          </p>
        )}

        <p className="verse__ar" dir="rtl" lang="ar">
          {current.uthmani}
        </p>

        {current.translation ? (
          <p className="verse__tr">{current.translation}</p>
        ) : (
          <p className="verse__tr verse__tr--none">
            {t(lang, "no_translation")}
          </p>
        )}

        <p className="estimate">
          {t(lang, "estimate")} ≈ {secs(lang, current.seconds)}
        </p>

        <div className="verse__actions">
          <button className="listen" onClick={togglePlay}>
            <span className="listen__glyph" aria-hidden="true">
              {playing ? (
                <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                  <rect x="2" y="1.5" width="3" height="9" />
                  <rect x="7" y="1.5" width="3" height="9" />
                </svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                  <path d="M3 1.6 10 6 3 10.4Z" />
                </svg>
              )}
            </span>
            {playing ? t(lang, "pause") : t(lang, "listen")}
          </button>
        </div>

        {/* THE RECITER PICKER IS GONE FROM HERE. It is one choice, made once,
            and it now lives in Settings beside the language — it does not need
            to be on the screen you read from. The play button above stays: that
            is a reading aid, not a preference. */}

        <audio
          ref={audioRef}
          src={expertAudioUrl(sura.number, current.aya, reciter)}
          preload="none"
          onEnded={() => setPlaying(false)}
          onError={() => setPlaying(false)}
        />
      </div>

      {/* ── RECORD, WITHOUT LEAVING THE VERSE ────────────────────────────
             There used to be a "Bu oyatni oʻqish" button down here that took
             the learner to a different screen, where they then pressed a
             second button to start recording. Two taps and a screen change
             between reading a verse and reciting it.

             This is the same pinned control the recording screen uses, in the
             same place on the viewport, and it starts recording on the first
             press. The screen behind it does change — the analysis needs the
             practice range resolved — but the learner does not experience a
             step, because the button they pressed does not move and the ayah
             they were reading is still the ayah on screen.

             MUSHAF VIEW IS UNTOUCHED: tapping an ayah in continuous text still
             selects it exactly as before. That flow was never the complaint,
             and a mushaf page with a mic welded to the bottom would break the
             one thing it is for, which is uninterrupted reading. */}
      <MicBar lang={lang} onStart={() => onPractise(current, true)} />
    </>
  );
}

/**
 * The pinned mic, in its pre-recording state, for a screen that does not own
 * the recorder.
 *
 * It draws the same disc as Studio's and sits in the same place, so pressing it
 * and finding the real one there afterwards reads as one continuous control
 * rather than as a handoff. It records nothing itself — see onStart.
 */
function MicBar({ lang, onStart }: { lang: Lang; onStart: () => void }) {
  return (
    <div className="micbar">
      <button
        className="mic micbar__mic"
        onClick={onStart}
        aria-label={t(lang, "record")}
      >
        <span className="mic__ring" aria-hidden="true" />
        <Mic />
      </button>
      <p className="micbar__copy">{t(lang, "studio_idle_primary")}</p>
    </div>
  );
}
