import { useEffect, useRef, useState } from "react";
import AyahText from "./AyahText";
import Feedback from "./Feedback";
import { Attempt, Ayah, expertAudioUrl, submitAttempt } from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { RecorderHandle, startRecording } from "../lib/recorder";

type Phase = "idle" | "recording" | "waiting";

const mmss = (s: number) =>
  `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export default function Recite({ lang, ayah }: { lang: Lang; ayah: Ayah }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<Attempt | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [failed, setFailed] = useState(false);

  const handleRef = useRef<RecorderHandle | null>(null);
  const ringRef = useRef<HTMLSpanElement>(null);
  const ringOuterRef = useRef<HTMLSpanElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Reset when the learner moves to another ayah.
  useEffect(() => {
    handleRef.current?.cancel();
    handleRef.current = null;
    setPhase("idle");
    setResult(null);
    setElapsed(0);
    setFailed(false);
  }, [ayah.slug]);

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
      setResult(await submitAttempt(blob, ayah.sura, ayah.aya, lang));
    } catch {
      setFailed(true);
    } finally {
      handleRef.current = null;
      setPhase("idle");
    }
  }

  const firstError = result?.status === "ok" ? result.errors[0] : undefined;
  const highlightUnit = firstError ? firstError.at : null;
  const letter =
    highlightUnit === null
      ? ""
      : (ayah.segments.find((s) => s.units.includes(highlightUnit))?.text ?? "");

  return (
    <>
      <div className="eyebrow">
        <h2 className="eyebrow__name">
          {lang === "uz" ? ayah.name_uz : ayah.name_ru}
        </h2>
        <span className="eyebrow__meta">
          {ayah.sura}:{ayah.aya}
        </span>
      </div>

      <AyahText
        uthmani={ayah.uthmani}
        segments={ayah.segments}
        highlightUnit={highlightUnit}
        mode={
          phase === "recording"
            ? "listening"
            : phase === "waiting"
              ? "waiting"
              : "still"
        }
      />

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
      <audio ref={audioRef} src={expertAudioUrl(ayah.sura, ayah.aya)} preload="none" />

      {phase === "recording" && (
        <>
          <div className="breath">
            <span className="breath__ring breath__ring--outer" ref={ringOuterRef} aria-hidden="true" />
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
