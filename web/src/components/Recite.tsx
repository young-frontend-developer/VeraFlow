import { useEffect, useRef, useState } from "react";
import AyahText from "./AyahText";
import Feedback from "./Feedback";
import { Selection } from "./Picker";
import { Attempt, expertAudioUrl, submitAttempt } from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { RecorderHandle, startRecording } from "../lib/recorder";

type Phase = "idle" | "recording" | "waiting";

const mmss = (s: number) =>
  `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export default function Recite({
  lang,
  selection,
  onChange,
}: {
  lang: Lang;
  selection: Selection;
  onChange: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<Attempt | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [failed, setFailed] = useState(false);

  const handleRef = useRef<RecorderHandle | null>(null);
  const ringRef = useRef<HTMLSpanElement>(null);
  const ringOuterRef = useRef<HTMLSpanElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  const { sura, ayah, segment } = selection;
  // Identity of the exact range, so switching segments within one ayah resets
  // too — not just switching ayah.
  const key = `${sura.number}:${ayah.aya}:${segment.start_word}:${segment.num_words}`;

  useEffect(() => {
    handleRef.current?.cancel();
    handleRef.current = null;
    setPhase("idle");
    setResult(null);
    setElapsed(0);
    setFailed(false);
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

  const firstError = result?.status === "ok" ? result.errors[0] : undefined;
  const highlightUnit = firstError ? firstError.at : null;
  // text_segments are relative to the SELECTED RANGE, which is what the engine
  // diffed, so `at` indexes them directly.
  const letter =
    highlightUnit === null
      ? ""
      : (segment.text_segments.find((s) => s.units.includes(highlightUnit))
          ?.text ?? "");

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
        highlightUnit={highlightUnit}
        mode={
          phase === "recording"
            ? "listening"
            : phase === "waiting"
              ? "waiting"
              : "still"
        }
      />

      {/* What the learner is about to be measured against, before they commit
          to recording: how long this should take at a normal pace. */}
      <p className="estimate">
        {t(lang, "estimate")} ≈ {segment.seconds.toFixed(1)}{" "}
        {t(lang, "seconds_short")}
      </p>

      {/* Expert audio is per whole ayah, so it is only offered when the whole
          ayah is selected — playing a full ayah against a one-part selection
          would be teaching the wrong thing. */}
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
            src={expertAudioUrl(sura.number, ayah.aya)}
            preload="none"
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
        <Feedback
          lang={lang}
          attempt={result}
          letter={letter}
          onRetry={start}
          onReplay={() => audioRef.current?.play()}
        />
      )}
    </>
  );
}
