import { useEffect, useRef, useState } from "react";
import AyahText, { AyahLine, Mark } from "./AyahText";
import ErrorBoundary from "./ErrorBoundary";
import Feedback, { RetryState, SelfPlayback, cardId } from "./Feedback";
import { Selection } from "./Picker";
import ReciterSelect from "./ReciterSelect";
import {
  Attempt,
  PracticeRung,
  PracticeSegment,
  Reciter,
  TajweedError,
  expertAudioUrl,
  submitAttempt,
} from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { RecorderHandle, startRecording } from "../lib/recorder";

type Phase = "idle" | "recording" | "waiting";

const mmss = (s: number) =>
  `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export default function Recite({
  lang,
  selection,
  onChange,
  onPart,
  maxAudioSeconds,
  reciters,
  reciter,
  onReciter,
}: {
  lang: Lang;
  selection: Selection;
  onChange: () => void;
  /** Narrow the practice range to one part of this ayah, or back to the whole. */
  onPart: (segment: PracticeSegment, whole: boolean) => void;
  /** Engine ceiling in seconds; 0 while /api/meta is still in flight. */
  maxAudioSeconds: number;
  reciters: Reciter[];
  reciter: string;
  onReciter: (id: string) => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<Attempt | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [failed, setFailed] = useState(false);
  const [pickingPart, setPickingPart] = useState(false);

  // The learner's own recording, kept only for as long as this result is on
  // screen. Never uploaded beyond the attempt itself and never persisted —
  // hearing yourself back must not require consenting to retention.
  const [ownRecording, setOwnRecording] = useState<Blob | null>(null);

  // Which card the learner is reading, so the ayah can strengthen its letters.
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [retry, setRetry] = useState<RetryState>({
    cardId: null,
    level: null,
    phase: null,
    fixed: [],
    stillWrong: null,
  });

  const handleRef = useRef<RecorderHandle | null>(null);
  /**
   * The range the in-flight rung recording will be submitted against, captured
   * when recording STARTS. A ref rather than state because the stop handler
   * reads it synchronously, and because it must be the range of the rung that
   * was tapped — not whatever the ladder happens to look like by the time the
   * learner stops.
   */
  const rangeRef = useRef<{ start_word: number; num_words: number } | null>(null);
  const ringRef = useRef<HTMLSpanElement>(null);
  const ringOuterRef = useRef<HTMLSpanElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const cardRefs = useRef<Record<string, HTMLElement | null>>({});

  // Whole ayat run to nearly four minutes, and "193.9 s" is not a duration a
  // person can feel. Past a minute, read it as minutes.
  const estimate = (s: number) =>
    s >= 60 ? mmss(s) : `${s.toFixed(1)} ${t(lang, "seconds_short")}`;

  const { sura, ayah, segment, parts } = selection;
  // `seconds` is the median-reciter estimate and the gate is on real recorded
  // duration, so warn with headroom rather than exactly at the line.
  const tooLong =
    maxAudioSeconds > 0 && segment.seconds > maxAudioSeconds * 0.8;
  // Identity of the exact range, so switching parts within one ayah resets
  // too — not just switching ayah.
  const key = `${sura.number}:${ayah.aya}:${segment.start_word}:${segment.num_words}`;

  useEffect(() => {
    handleRef.current?.cancel();
    handleRef.current = null;
    setPhase("idle");
    setResult(null);
    setElapsed(0);
    setFailed(false);
    setPickingPart(false);
    setOwnRecording(null);
    setActiveCardId(null);
    setRetry({ cardId: null, level: null, phase: null, fixed: [],
               stillWrong: null });
  }, [key]);

  useEffect(() => () => handleRef.current?.cancel(), []);

  // Drive the breathing ring from the live mic level. Written straight to the
  // DOM rather than through state: this runs at 60fps and React does not need
  // to know about any of it.
  useEffect(() => {
    if (phase !== "recording") return;
    let raf = 0;
    const tick = () => {
      const h = handleRef.current;
      if (h) {
        const level = h.level();
        if (ringRef.current)
          ringRef.current.style.transform = `scale(${1 + level * 0.34})`;
        if (ringOuterRef.current)
          ringOuterRef.current.style.transform = `scale(${1.25 + level * 0.6})`;
        setElapsed((Date.now() - h.startedAt) / 1000);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase]);

  async function start() {
    setResult(null);
    setFailed(false);
    setActiveCardId(null);
    setRetry({ cardId: null, level: null, phase: null, fixed: [],
               stillWrong: null });
    audioRef.current?.pause();
    try {
      handleRef.current = await startRecording();
      setElapsed(0);
      setPhase("recording");
    } catch {
      setFailed(true);
    }
  }

  async function stop() {
    const h = handleRef.current;
    if (!h) return;
    setPhase("waiting");
    try {
      const blob = await h.stop();
      setOwnRecording(blob);
      setResult(
        await submitAttempt(blob, sura.number, ayah.aya, lang, {
          start_word: segment.start_word,
          num_words: segment.num_words,
        }),
      );
    } catch {
      setFailed(true);
    } finally {
      handleRef.current = null;
      setPhase("idle");
    }
  }

  /* ── the recovery loop ──────────────────────────────────────────────────
     Re-record ONE RUNG of a card's practice ladder and re-check only the error
     that card is about. Two rungs are recordable and they submit different
     ranges:

       word  just that word          start_word = word_index, num_words = 1
       ayah  the range on screen     whatever the learner selected

     The range machinery is the same one the practice segments use, and
     `word_index` is ayah-relative precisely so it can be handed straight to
     `start_word`. The letter and syllable rungs are not recordable at all —
     the engine has no target for a bare letter — and the server says so on the
     rung itself, so this never has to guess. */

  /** The range one rung submits, or null if it cannot be recorded. */
  function rungRange(rung: PracticeRung) {
    if (!rung.recordable) return null;
    if (rung.focus === "word") {
      if (rung.word_index < 0) return null;
      return { start_word: rung.word_index, num_words: 1 };
    }
    // The ayah rung re-reads exactly what is on screen, which may itself be a
    // part of the ayah if the learner narrowed the selection.
    return { start_word: segment.start_word, num_words: segment.num_words };
  }

  async function recordRung(e: TajweedError, rung: PracticeRung) {
    const range = rungRange(rung);
    if (!range) return;
    try {
      handleRef.current = await startRecording();
      rangeRef.current = range;
      setRetry((r) => ({ ...r, cardId: cardId(e), level: rung.level,
                         phase: "recording", stillWrong: null }));
    } catch {
      setFailed(true);
    }
  }

  async function stopRecordRung(e: TajweedError) {
    const h = handleRef.current;
    const range = rangeRef.current;
    if (!h || !range) return;
    const id = cardId(e);
    setRetry((r) => ({ ...r, phase: "checking" }));
    try {
      const blob = await h.stop();
      const out = await submitAttempt(blob, sura.number, ayah.aya, lang, range);
      // SCOPED to this error. The re-read covers one word, so anything else it
      // turns up belongs to a different card and must not silently close this
      // one — or, worse, open new cards for a word the learner was drilling.
      const stillThere =
        out.status === "ok" &&
        out.errors.some((x) => x.code === e.code && x.letter === e.letter);
      // A re-read we could not judge is NOT a fix. Only a clean, analysable
      // result closes the card; anything else leaves it exactly as it was.
      const judged = out.status === "ok" && out.analysable;
      setRetry((r) => ({
        cardId: null,
        level: null,
        phase: null,
        fixed: judged && !stillThere ? [...r.fixed, id] : r.fixed,
        stillWrong: judged && stillThere ? id : null,
      }));
    } catch {
      setRetry((r) => ({ ...r, cardId: null, level: null, phase: null }));
      setFailed(true);
    } finally {
      handleRef.current = null;
      rangeRef.current = null;
    }
  }

  const errors = result?.status === "ok" ? result.errors : [];

  // EVERY errored letter, not just the first — one mark per occurrence, each
  // tagged with the card that explains it. Cards the learner has already fixed
  // drop out, so the ayah clears as they work through it.
  const marks: Mark[] = errors
    .filter((e) => !retry.fixed.includes(cardId(e)))
    .flatMap((e) =>
      (e.occurrences ?? []).map((o) => ({
        at: o.at,
        cardId: cardId(e),
        letter: e.letter,
      })),
    );

  function scrollToCard(id: string) {
    setActiveCardId(id);
    cardRefs.current[id]?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }

  return (
    <>
      <div className="eyebrow">
        <h2 className="eyebrow__name">
          {sura.number}. {sura.translit}
        </h2>
        <span className="eyebrow__meta">
          {sura.number}:{ayah.aya}
          {!selection.whole &&
            ` · ${t(lang, "words")} ${segment.start_word + 1}–${
              segment.start_word + segment.num_words
            }`}
        </span>
      </div>

      <button className="crumb crumb--change" onClick={onChange}>
        {t(lang, "change_selection")}
      </button>

      <AyahText
        uthmani={segment.uthmani}
        segments={segment.text_segments}
        marks={marks}
        activeCardId={activeCardId}
        onPick={scrollToCard}
        mode={
          phase === "recording"
            ? "listening"
            : phase === "waiting"
              ? "waiting"
              : "still"
        }
      />

      {/* What the learner is about to be measured against, before they commit
          to recording: how long this should take at a normal pace. A long ayah
          is slow, not broken — this is the number that lets them decide. */}
      <p className="estimate">
        {t(lang, "estimate")} ≈ {estimate(segment.seconds)}
      </p>

      {/* Said BEFORE recording. Inference runs ~10x realtime, so learning this
          from the result would mean waiting minutes for a rejection. The
          ceiling is the engine's memory limit, not a judgement about the
          learner, so the wording blames the length and offers the way out. */}
      {tooLong && (
        <p className="estimate estimate--warn">{t(lang, "too_long_hint")}</p>
      )}

      {/* Practising part of an ayah is a CHOICE, offered only where the ayah
          genuinely divides. It is never taken for the learner, and the whole
          ayah is always one tap away again. */}
      {parts.length > 1 && (
        <div className="parts">
          {selection.whole ? (
            <button
              className="linkish"
              disabled={phase !== "idle"}
              onClick={() => setPickingPart((v) => !v)}
            >
              {t(lang, "practise_part")}
            </button>
          ) : (
            <button
              className="linkish"
              disabled={phase !== "idle"}
              onClick={() => {
                setPickingPart(false);
                onPart(selection.wholeSegment, true);
              }}
            >
              {t(lang, "practise_whole")}
            </button>
          )}

          {pickingPart && (
            <ul className="list list--parts">
              {parts.map((p) => (
                <li key={p.index}>
                  <button
                    className="row"
                    aria-current={
                      p.start_word === segment.start_word &&
                      p.num_words === segment.num_words
                    }
                    onClick={() => {
                      setPickingPart(false);
                      onPart(p, false);
                    }}
                  >
                    <span className="row__num">{p.index + 1}</span>
                    <span className="row__body">
                      <AyahLine uthmani={p.uthmani} />
                      <span className="row__meta">
                        {t(lang, "words")} {p.start_word + 1}–
                        {p.start_word + p.num_words} · {estimate(p.seconds)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* everyayah serves whole-ayah files only. Offering playback against a
          part would request a file that does not exist — which is exactly why
          reciter audio "died on long suras" while they were force-split. */}
      {selection.whole && (
        <>
          <button
            className="listen"
            disabled={phase !== "idle"}
            onClick={() => audioRef.current?.play()}
          >
            <span className="listen__glyph" aria-hidden="true">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                <path d="M3 1.6 10 6 3 10.4Z" />
              </svg>
            </span>
            {t(lang, "listen")}
          </button>
          <audio
            ref={audioRef}
            src={expertAudioUrl(sura.number, ayah.aya, reciter)}
            preload="none"
          />
          {/* Offered next to the thing it changes. Switching reciter mid-drill
              is a normal thing to want — one voice is easier to follow than
              another, and a muallim recording repeats each phrase. */}
          <ReciterSelect
            lang={lang}
            reciters={reciters}
            value={reciter}
            onChange={onReciter}
            disabled={phase !== "idle"}
          />
        </>
      )}

      {phase === "recording" && (
        <>
          <div className="breath">
            <span
              className="breath__ring breath__ring--outer"
              ref={ringOuterRef}
              aria-hidden="true"
            />
            <span className="breath__ring" ref={ringRef} aria-hidden="true" />
            <span className="breath__timer">{mmss(elapsed)}</span>
          </div>
          <p className="breath__hint">{t(lang, "recording_hint")}</p>
        </>
      )}

      {phase === "waiting" && (
        <p className="waiting" role="status">
          {t(lang, "waiting")}
          <br />
          <span className="waiting__hint">{t(lang, "waiting_hint")}</span>
        </p>
      )}

      <button
        className={phase === "recording" ? "record record--stop" : "record"}
        disabled={phase === "waiting"}
        onClick={phase === "recording" ? stop : start}
      >
        <span className="record__dot" aria-hidden="true" />
        {phase === "recording" ? t(lang, "stop") : t(lang, "record")}
      </button>

      {failed && (
        <div className="notice">
          <p className="notice__body">{t(lang, "error_generic")}</p>
        </div>
      )}

      {result && phase === "idle" && (
        // The outer net. Per-card boundaries inside Feedback catch the common
        // case; this catches anything in the results view ITSELF — the merge
        // logic, the playback control, an unexpected attempt shape — so a
        // learner who has just waited minutes for inference always gets
        // something back rather than a white page.
        <ErrorBoundary
          label="results"
          resetKey={result.id}
          fallback={
            <div className="notice">
              <p className="notice__body">{t(lang, "results_broken")}</p>
              <div className="actions">
                <button className="btn-quiet" onClick={start}>
                  {t(lang, "retry_again")}
                </button>
              </div>
            </div>
          }
        >
          {/* Hearing yourself back is how a learner judges whether a flagged
              error is real. Session-only: the blob lives in memory until the
              next take replaces it. */}
          <SelfPlayback lang={lang} blob={ownRecording} />
          <Feedback
            lang={lang}
            attempt={result}
            activeCardId={activeCardId}
            retry={retry}
            onRecordRung={recordRung}
            onStopRetry={() => {
              const e = errors.find((x) => cardId(x) === retry.cardId);
              if (e) stopRecordRung(e);
            }}
            onFocusLetter={setActiveCardId}
            onRetry={start}
            cardRefs={cardRefs}
          />
        </ErrorBoundary>
      )}
    </>
  );
}
