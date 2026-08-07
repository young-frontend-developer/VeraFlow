import { useEffect, useRef, useState } from "react";
import AyahText, { AyahLine, Mark } from "./AyahText";
import ErrorBoundary from "./ErrorBoundary";
import Feedback, {
  EMPTY_RUNGS,
  RetryState,
  SelfPlayback,
  cardId,
} from "./Feedback";
import { Selection } from "./Picker";
import { decideRetry } from "../lib/retry";
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
import Studio from "./Studio";
import { Failure } from "./States";
import { Play } from "./Ornament";

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
  /**
   * WHY the last action failed, not merely THAT it did.
   *
   *   mic      the browser refused the microphone. Nothing was recorded, and
   *            the fix is a permission the app cannot grant itself.
   *   network  the recording was made and the upload or analysis died. The
   *            learner has already waited, possibly a long time, and their
   *            audio is still in memory — so this state offers to send it
   *            again rather than asking them to recite from scratch.
   *
   * A single boolean printed one sentence for both, which told the learner
   * nothing about which of the two very different things had happened.
   */
  const [failure, setFailure] = useState<"mic" | "network" | null>(null);
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
    rungs: {},
    tries: {},
    accepted: [],
  });

  /**
   * The live retry state, for reading inside an async handler.
   *
   * stopRecordRung awaits a network round trip and then needs the CURRENT try
   * count to decide whether the cap has been reached. Closing over `retry` from
   * render would read the count as it was when recording STARTED, so the cap
   * would always be one behind and the third attempt would not fire it.
   */
  const retryRef = useRef(retry);
  useEffect(() => {
    retryRef.current = retry;
  }, [retry]);

  const handleRef = useRef<RecorderHandle | null>(null);
  /**
   * The range the in-flight rung recording will be submitted against, captured
   * when recording STARTS. A ref rather than state because the stop handler
   * reads it synchronously, and because it must be the range of the rung that
   * was tapped — not whatever the ladder happens to look like by the time the
   * learner stops.
   */
  const rangeRef = useRef<{ start_word: number; num_words: number } | null>(null);
  /** The rung level being recorded, captured for the same reason as the range. */
  const levelRef = useRef<number | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const cardRefs = useRef<Record<string, HTMLElement | null>>({});

  /**
   * The two figures on the dark card's stats row: how long the last take ran
   * and what it scored.
   *
   * Taken from the last COMPLETED attempt in this session and nowhere else. Not
   * from history — that would need consent the learner may not have given — and
   * never invented. Both start empty, and Studio omits the whole row until
   * there is something true to put in it, because a stat slot showing a dash
   * is an invitation for someone to fill it later with a plausible number.
   */
  const [lastSeconds, setLastSeconds] = useState(0);
  const [lastScore, setLastScore] = useState<number | null>(null);

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
    setFailure(null);
    setPickingPart(false);
    setOwnRecording(null);
    setActiveCardId(null);
    setRetry({ cardId: null, level: null, phase: null, fixed: [],
               stillWrong: null, rungs: {}, tries: {}, accepted: [] });
  }, [key]);

  useEffect(() => () => handleRef.current?.cancel(), []);

  // The elapsed clock. Studio draws the waveform itself from the same handle,
  // at frame rate and straight to the DOM — this only has to keep the timer
  // honest, so it ticks four times a second rather than sixty.
  useEffect(() => {
    if (phase !== "recording") return;
    const id = window.setInterval(() => {
      const h = handleRef.current;
      if (h) setElapsed((Date.now() - h.startedAt) / 1000);
    }, 250);
    return () => window.clearInterval(id);
  }, [phase]);

  async function start() {
    setResult(null);
    setFailure(null);
    setActiveCardId(null);
    setRetry({ cardId: null, level: null, phase: null, fixed: [],
               stillWrong: null, rungs: {}, tries: {}, accepted: [] });
    audioRef.current?.pause();
    try {
      handleRef.current = await startRecording();
      setElapsed(0);
      setPhase("recording");
    } catch {
      // getUserMedia rejects for a denied permission, a missing device and a
      // non-secure origin alike. All three land the learner in the same place:
      // no microphone, and no amount of retrying inside the app fixes it.
      setFailure("mic");
    }
  }

  async function stop() {
    const h = handleRef.current;
    if (!h) return;
    setPhase("waiting");
    try {
      const blob = await h.stop();
      setOwnRecording(blob);
      const out = await send(blob);
      setResult(out);
      remember(out);
    } catch {
      setFailure("network");
    } finally {
      handleRef.current = null;
      setPhase("idle");
    }
  }

  const send = (blob: Blob) =>
    submitAttempt(blob, sura.number, ayah.aya, lang, {
      start_word: segment.start_word,
      num_words: segment.num_words,
    });

  /**
   * Send the recording we already have, again.
   *
   * THE RECOVERY THAT MATTERS. A network failure during analysis arrives after
   * the learner has recited and then waited — sometimes half a minute. Asking
   * them to record the whole ayah again to recover from OUR failure is the
   * least forgivable moment in the app. The blob is still in memory for
   * playback, so it can simply be resent, and the retry costs them nothing.
   */
  async function resend() {
    if (!ownRecording) return;
    setFailure(null);
    setPhase("waiting");
    try {
      const out = await send(ownRecording);
      setResult(out);
      remember(out);
    } catch {
      setFailure("network");
    } finally {
      setPhase("idle");
    }
  }

  /** Keep the last real figures for the dark card. Only from a judged take. */
  function remember(out: Attempt) {
    if (out.status !== "ok" || !out.analysable) return;
    setLastSeconds(out.duration_s);
    setLastScore(out.score ?? null);
  }

  /* ── the recovery loop ──────────────────────────────────────────────────
     Re-record ONE RUNG of a card's practice ladder and re-check only the error
     that card is about. Rungs submit one of two ranges:

       word*  just that word          start_word = word_index, num_words = 1
       ayah   the range on screen     whatever the learner selected

     `word*` is every word-focused rung, not only `word`. The omission,
     insertion and duration ladders open on the word too — said slowly, with
     the thing to attend to named — and those rungs are the same word range as
     the normal-pace one, so they record and score identically. Matching on the
     `word` prefix rather than listing them keeps a new word rung on the server
     from silently falling through to the ayah branch and re-recording the
     whole verse.

     The range machinery is the same one the practice segments use, and
     `word_index` is ayah-relative precisely so it can be handed straight to
     `start_word`. The letter and syllable rungs are not recordable at all —
     the engine has no target for a bare letter — and the server says so on the
     rung itself, so this never has to guess. */

  /** The range one rung submits, or null if it cannot be recorded. */
  function rungRange(rung: PracticeRung) {
    if (!rung.recordable) return null;
    if (rung.focus.startsWith("word")) {
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
      levelRef.current = rung.level;
      setRetry((r) => ({ ...r, cardId: cardId(e), level: rung.level,
                         phase: "recording", stillWrong: null }));
    } catch {
      setFailure("network");
    }
  }

  async function stopRecordRung(e: TajweedError) {
    const h = handleRef.current;
    const range = rangeRef.current;
    const level = levelRef.current;
    if (!h || !range || level === null) return;
    const id = cardId(e);
    setRetry((r) => ({ ...r, phase: "checking" }));
    try {
      const blob = await h.stop();
      const out = await submitAttempt(blob, sura.number, ayah.aya, lang, range);
      const judged = out.status === "ok" && out.analysable;
      const score = out.score ?? 0;
      // Counted BEFORE the decision, so this re-read is the nth try and the cap
      // can fire on it. An unjudged read does not count — see decideRetry.
      const tried = (retryRef.current.tries[id] ?? 0) + (judged ? 1 : 0);
      // The whole decision lives in lib/retry.ts. It used to be inline here and
      // it deadlocked on any ayah with more than one error: the last rung is
      // the AYAH, so its score covers other cards' mistakes too, and a learner
      // who fixed this card perfectly was held shut by a mistake the app had
      // not shown them yet. See that module for the full account.
      const verdict = decideRetry({ out, error: e, attempt: tried });
      const cleared = verdict.cleared;
      const isLast = level >= (e.practice?.length ?? 0);

      setRetry((r) => {
        const prev = r.rungs[id] ?? EMPTY_RUNGS;
        return {
          ...r,
          cardId: null,
          level: null,
          phase: null,
          // The card itself closes only when the LAST rung is cleared — the
          // ayah, which is the test. Clearing the word rung is progress, not a
          // finish, and closing there would send the learner away one rung
          // short of putting it back in context.
          fixed: cleared && isLast ? [...r.fixed, id] : r.fixed,
          accepted:
            verdict.accepted && isLast ? [...r.accepted, id] : r.accepted,
          tries: { ...r.tries, [id]: tried },
          stillWrong: cleared ? null : id,
          rungs: {
            ...r.rungs,
            [id]: {
              done: cleared && !prev.done.includes(level)
                ? [...prev.done, level]
                : prev.done,
              failed: cleared ? null : level,
              score: judged ? score : null,
            },
          },
        };
      });
    } catch {
      setRetry((r) => ({ ...r, cardId: null, level: null, phase: null }));
      setFailure("network");
    } finally {
      handleRef.current = null;
      rangeRef.current = null;
      levelRef.current = null;
    }
  }

  /**
   * A listen-and-say rung the learner says they have done.
   *
   * SELF-ATTESTED, AND LABELLED AS SUCH. The engine has no target for a bare
   * letter — see engine/practice.py — so there is nothing to score here and
   * nothing is claimed. It still advances the ladder, because the ladder is an
   * ORDER and the narrow rungs are the part a learner most needs to do before
   * the wide ones. The alternative was leaving these rungs with no way to be
   * cleared at all, which would have made the unlock chain stop at rung one.
   */
  function selfCheck(e: TajweedError, rung: PracticeRung) {
    const id = cardId(e);
    setRetry((r) => {
      const prev = r.rungs[id] ?? EMPTY_RUNGS;
      if (prev.done.includes(rung.level)) return r;
      return {
        ...r,
        rungs: {
          ...r.rungs,
          [id]: { ...prev, done: [...prev.done, rung.level], failed: null },
        },
      };
    });
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
        // The exact character range for THIS sound. For a madd that is the
        // lengthening mark alone rather than the consonant it follows, which
        // is what lets the note below sit on the thing it is about.
        span: o.span,
        // RULE 2: the requirement the length in the card, next to the mark.
        // Only duration errors carry one — everything else is a red letter
        // with nothing hanging off it.
        note:
          (e.expected_count ?? 0) > 0
            ? `${e.expected_count} ${t(lang, "harakat")}`
            : undefined,
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
              <Play size={12} />
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

      {/* THE ONE DARK SURFACE IN THE APP. It carries the whole recording and
          analysing experience — waveform, stats, button, copy — and disappears
          the moment a result arrives. The learner goes into it to recite and
          comes straight back out to the ivory; that is what makes it read as a
          moment of focus rather than as a second theme. */}
      <Studio
        lang={lang}
        phase={
          phase === "recording"
            ? "recording"
            : phase === "waiting"
              ? "analyzing"
              : "idle"
        }
        elapsed={elapsed}
        level={() => handleRef.current?.level() ?? 0}
        lastSeconds={lastSeconds}
        lastScore={lastScore}
        disabled={failure === "mic"}
        onStart={start}
        onStop={stop}
      />

      {/* NO MICROPHONE. Not a toast: the app cannot fix this itself, so the
          state has to say what happened and what the learner must do in their
          browser — and it must not pretend a retry button will help. */}
      {failure === "mic" && (
        <Failure
          lang={lang}
          tone="warm"
          title={t(lang, "mic_denied_title")}
          body={t(lang, "mic_denied_body")}
          onRetry={start}
        />
      )}

      {/* THE FAILURE THAT DESERVES THE MOST CARE. The learner has already
          recited and waited, and the recording is still in memory — so this
          offers to send THAT audio again rather than asking them to perform
          the whole ayah a second time for our sake. */}
      {failure === "network" && (
        <Failure
          lang={lang}
          tone="warm"
          title={t(lang, "net_failed_title")}
          body={
            ownRecording
              ? t(lang, "net_failed_body_kept")
              : t(lang, "net_failed_body")
          }
          retryKey={ownRecording ? "net_failed_resend" : "retry_again"}
          onRetry={ownRecording ? resend : start}
        />
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
            // The ladder's top rung plays the real recitation of this ayah, at
            // normal speed and slowed. Resolved here because it depends on the
            // reciter the learner picked, which the server does not hold — and
            // empty for a partial range, since everyayah has no file for one.
            ayahAudio={
              selection.whole
                ? expertAudioUrl(sura.number, ayah.aya, reciter)
                : ""
            }
            onRecordRung={recordRung}
            onStopRetry={() => {
              const e = errors.find((x) => cardId(x) === retry.cardId);
              if (e) stopRecordRung(e);
            }}
            onSelfCheck={selfCheck}
            onFocusLetter={setActiveCardId}
            onRetry={start}
            cardRefs={cardRefs}
          />
        </ErrorBoundary>
      )}
    </>
  );
}
