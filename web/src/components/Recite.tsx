import { useEffect, useRef, useState } from "react";
import AyahText, { AyahLine } from "./AyahText";
import Feedback from "./Feedback";
import { Selection } from "./Picker";
import ReciterSelect from "./ReciterSelect";
import {
  Attempt,
  PracticeSegment,
  Reciter,
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

  const handleRef = useRef<RecorderHandle | null>(null);
  const ringRef = useRef<HTMLSpanElement>(null);
  const ringOuterRef = useRef<HTMLSpanElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

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
