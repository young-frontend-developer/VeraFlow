import { useEffect, useMemo, useRef, useState } from "react";
import {
  AyahBrief,
  RuleBadge,
  Sura,
  SuraAyat,
  ayahSegments,
  expertAudioUrl,
} from "../lib/api";
import { Lang, t } from "../lib/i18n";
import AyahBadge from "./AyahBadge";
import RuleBadges from "./RuleBadges";
import Recorder, { useElapsed } from "./Recorder";
import {
  RecorderHandle,
  cancelShared,
  startShared,
} from "../lib/recorder";

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
  showUnreviewed,
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
  /** Pilot builds show draft rule content, labelled. Production shows none. */
  showUnreviewed: boolean;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);

  /**
   * RECORDING BEGAN ON THIS SCREEN, and the disc says so before the app has
   * finished working out which range it will be submitted against.
   *
   * `arming` is set synchronously in the tap handler, so the control goes live
   * in the same frame as the press. The recording itself is genuinely running
   * by then — `startShared()` has already been called — and this component is
   * usually replaced by the practice screen a moment later, which continues the
   * same recording and the same clock.
   *
   * It is NOT a fake "recording" state waiting for a real one: if the microphone
   * is refused, the promise rejects and this resets, and the practice screen
   * shows the permission failure it was always going to show.
   */
  const [arming, setArming] = useState(false);
  const live = useRef<RecorderHandle | null>(null);
  const elapsed = useElapsed(arming, live.current?.startedAt);

  /**
   * The rules this ayah contains, for the badge strip.
   *
   * Fetched from the SAME endpoint the mic press needs, one ayah at a time, so
   * it is not a new cost so much as a moved one: by the time the learner
   * presses record the range is already resolved and cached. Adding `rules` to
   * the sura payload instead would mean two phonetizer runs per ayah for all
   * 286 of al-Baqara on every open, to draw pills for one of them.
   *
   * Null while loading and on failure. Badges are worth a fetch and not worth
   * an error state — the ayah is readable either way.
   */
  const [rules, setRules] = useState<RuleBadge[] | null>(null);

  // Leaving the reader with a recording still parked and no practice screen to
  // adopt it would leave the microphone open behind a screen that is gone.
  useEffect(
    () => () => {
      if (!live.current) cancelShared();
    },
    [],
  );

  const current =
    ayat.ayat.find((a) => a.aya === focusAya) ?? ayat.ayat[0] ?? null;

  /**
   * THE PRESS DOES BOTH THINGS AT ONCE.
   *
   * The microphone opens first and the app works out where to send the audio
   * second — in parallel, not in sequence. The old order fetched the practice
   * range, swapped screens, and only then asked for the mic, so the gap between
   * "I pressed record" and "it is recording" was a network round trip plus a
   * mount. Neither of those is something the learner should have to recite
   * through or wait out.
   */
  function startHere() {
    if (!current || arming) return;
    setArming(true);
    startShared()
      .then((h) => {
        live.current = h;
      })
      .catch(() => {
        // Denied, or no device. Drop back to idle here; the practice screen
        // owns the explanation, because that is where the retry lives.
        setArming(false);
      });
    onPractise(current, true);
  }

  // One fetch per focused ayah, and only in the verse view — the mushaf shows
  // a page of them and a strip of pills under continuous text would be the one
  // thing that view exists to avoid.
  useEffect(() => {
    if (mode !== "verse" || !current) return setRules(null);
    let alive = true;
    setRules(null);
    ayahSegments(sura.number, current.aya)
      .then((got) => alive && setRules(got.whole.rules ?? []))
      .catch(() => alive && setRules(null));
    return () => {
      alive = false;
    };
  }, [mode, sura.number, current?.aya]);

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

  /**
   * The mushaf, cut into pages of five ayat.
   *
   * FIVE, not a measured height. A real mushaf page holds a fixed number of
   * LINES and the ayat that fall on it vary; matching that would mean laying
   * out the Arabic and measuring it, and the result would still differ from
   * the printed page the learner knows. A fixed ayah count is honest about
   * being the app's own pagination rather than pretending to be the mushaf's,
   * and it keeps every page a comfortable read: al-Baqara 282 alone is longer
   * than five short ayat put together, so the range is uneven either way.
   */
  const PAGE = 5;
  const pages = useMemo(() => {
    const out: AyahBrief[][] = [];
    for (let i = 0; i < ayat.ayat.length; i += PAGE)
      out.push(ayat.ayat.slice(i, i + PAGE));
    return out.length ? out : [[]];
  }, [ayat.ayat]);

  // Derived, never stored — see the note at the arrows.
  const page = Math.max(
    0,
    Math.min(
      pages.length - 1,
      pages.findIndex((p) => p.some((a) => a.aya === focusAya)),
    ),
  );

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

        {/* ── A PAGE AT A TIME, NOT A SCROLL ────────────────────────────
               286 ayat in one scrolling column has no sense of place: you
               cannot tell how far in you are, returning means hunting, and on
               a phone the thumb travels the length of al-Baqara. A mushaf is
               PAGED, and this is the same arrows-at-the-top pattern the verse
               view already uses — so the two reading modes are navigated
               identically instead of by two different gestures.

               The page is derived from `focusAya` rather than held in state of
               its own. Tapping an ayah, stepping in the verse view and coming
               back, or restoring a saved place all move the focus; a second
               page number would have to be kept in step with it and would
               eventually disagree. */}
        <div className="ayah-nav">
          <button
            className="ayah-nav__close"
            aria-label={t(lang, "prev_ayah")}
            disabled={page === 0}
            onClick={() => onFocusAya(pages[page - 1][0].aya)}
          >
            <span aria-hidden="true">‹</span>
          </button>

          <span className="mushaf__page-of">
            {page + 1} / {pages.length}
          </span>

          <div className="ayah-nav__steps">
            <button
              className="ayah-nav__arrow ayah-nav__arrow--next"
              aria-label={t(lang, "next_ayah")}
              disabled={page >= pages.length - 1}
              onClick={() => onFocusAya(pages[page + 1][0].aya)}
            >
              <span aria-hidden="true">›</span>
            </button>
          </div>
        </div>

        {/* ── TAPPING AN AYAH OPENS IT IN THE VERSE VIEW ─────────────────
               and NOT straight into the recording screen, which is what it used
               to do. That was the whole defect: the same ayah reached from here
               and from Oyatma-oyat landed on two different screens — this one
               skipped the translation, the reciter playback and the prominent
               ayah number, because it skipped the reader entirely.

               `onMode("verse")` is the fix, and the reason it is the right one
               is that there is now nothing to build: the verse view already IS
               the screen for looking at one ayah and reciting it. Mushaf is a
               way of FINDING an ayah; tapping one says "this is where I am",
               and where you are is shown in exactly one place. */}
        <div className="mushaf mushaf--paged" ref={scrollRef} dir="rtl" lang="ar">
          {/* The basmala heads the SURA, so it belongs on the first page and
              nowhere else — reprinting it above page four would be a claim
              about the text that is not true. */}
          {ayat.has_basmala && page === 0 && (
            <p className="mushaf__bismillah">{ayat.bismillah}</p>
          )}
          <p className="mushaf__body">
            {(pages[page] ?? []).map((a) => (
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
                  onMode("verse");
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onFocusAya(a.aya);
                    onMode("verse");
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

      <div className="verse">
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
          {/* THE SAME BADGE THE RECORDING SCREEN SHOWS, in the same slot: the
              centre of the arrow row. This was a 12px tracked-out "112:1" — the
              treatment the app gives a timestamp — while the recording screen
              carried a prominent plate, and the mismatch was half of why the
              two screens did not read as one. */}
          <AyahBadge lang={lang} aya={current.aya} />
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

        {/* ── RECORD, ON THIS SCREEN, AT THE PRESS ───────────────────────
               THE SAME `Recorder` THE PRACTICE SCREEN USES. Not a lookalike —
               the same component, so the disc, its size, its label and the
               space around it cannot drift apart again.

               AND THE PRESS IS THE START. `startShared()` issues getUserMedia
               in the tap handler, so the microphone opens on this screen, in
               this frame. The range fetch and the screen change run beside it
               and the practice screen adopts the recording already in
               progress — see claimShared() in lib/recorder.ts. Previously the
               order was the other way round: fetch, navigate, and only then
               open the mic, which is a second or more of a button that looks
               pressed and is not yet listening.

               IT IS PART OF THE CARD, in the normal flow, directly below the
               Arabic. An earlier version pinned it to the bottom of the
               viewport and it floated over the translation.

               MUSHAF VIEW IS UNTOUCHED: tapping an ayah in continuous text
               still selects it exactly as before. That flow was never the
               complaint, and a mushaf page with a mic welded into it would
               break the one thing it is for, which is uninterrupted reading. */}
        <Recorder
          lang={lang}
          phase={arming ? "recording" : "idle"}
          elapsed={elapsed}
          level={() => live.current?.level() ?? 0}
          onStart={startHere}
          // Unreachable: this screen hands the recording over the instant the
          // range resolves, so the stop button belongs to the practice screen.
          // Present because the component demands it, and because a Recorder
          // that could reach a live state with no way out would be a trap.
          onStop={() => {}}
        />

        {current.translation ? (
          <p className="verse__tr">{current.translation}</p>
        ) : (
          <p className="verse__tr verse__tr--none">
            {t(lang, "no_translation")}
          </p>
        )}

        {/* WHAT THIS AYAH CONTAINS. Under the translation rather than under
            the Arabic: the pills are about the text, and putting them between
            the verse and its meaning would break the one pairing the verse
            view exists for. */}
        {rules && rules.length > 0 && (
          <RuleBadges lang={lang} rules={rules} showUnreviewed={showUnreviewed} />
        )}

        {/* NO DURATION ESTIMATE HERE. "Taxminiy davomiylik ≈ 4.5 s" was a
            number about the ENGINE's budget wearing the costume of a reading
            aid, and it sat under every ayah in the app. Removed from the
            learner-facing view; the figure itself is still computed and still
            drives the auto-narrowing on the ~60 ayat the engine cannot hold. */}

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
    </>
  );
}
