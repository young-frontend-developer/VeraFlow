import { useEffect, useRef, useState } from "react";
import AyahText, { Mark, RuleSpan } from "./AyahText";
import ErrorBoundary from "./ErrorBoundary";
import Feedback, {
  EMPTY_RUNGS,
  RetryState,
  PlaybackPair,
  cardId,
} from "./Feedback";
import { Selection } from "./Picker";
import { decideRetry } from "../lib/retry";
import {
  Attempt,
  PracticeRung,
  PracticeSegment,
  TajweedError,
  expertAudioUrl,
  submitAttempt,
} from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { ruleLayers } from "../lib/rules";
import AyahBadge from "./AyahBadge";
import RuleBadges from "./RuleBadges";
import { Chevron, Close } from "./Ornament";
import {
  RecorderHandle,
  claimShared,
  startRecording,
} from "../lib/recorder";
import Recorder, { useElapsed } from "./Recorder";
import { Failure } from "./States";

type Phase = "idle" | "recording" | "waiting";


const mmss = (s: number) =>
  `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export default function Recite({
  lang,
  selection,
  onChange,
  onPart,
  onStep,
  onAttempt,
  canStep,
  maxAudioSeconds,
  reciter,
  showUnreviewed,
}: {
  lang: Lang;
  selection: Selection;
  /** Leave practice entirely, straight out to the full sura list. */
  onChange: () => void;
  /** Narrow the practice range to one part of this ayah, or back to the whole. */
  onPart: (segment: PracticeSegment, whole: boolean) => void;
  /**
   * Move to the adjacent ayah of the same sura, -1 or +1.
   *
   * The caller resolves the new ayah's practice range and swaps the selection;
   * this component only says which way. Null at either end of the sura, which
   * is what disables the arrow — an arrow that is present and does nothing is
   * worse than one that is visibly unavailable.
   */
  onStep: (delta: -1 | 1) => void;
  /**
   * A recitation was stored. The caller refetches the attempt history on this,
   * which is what makes hasanat, the streak and the rank move without a reload.
   */
  onAttempt?: () => void;
  /** Whether stepping is possible in each direction, from the caller's data. */
  canStep: { prev: boolean; next: boolean };
  /** Engine ceiling in seconds; 0 while /api/meta is still in flight. */
  maxAudioSeconds: number;
  /** Chosen once in Settings. Used to resolve the comparison audio only. */
  reciter: string;
  /** Pilot builds show draft rule content, labelled. Production shows none. */
  showUnreviewed: boolean;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<Attempt | null>(null);
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

  /**
   * ADOPT the recording that is already running, when the reader's mic sent us
   * here.
   *
   * The press on the previous screen called `startShared()` — getUserMedia was
   * issued at that instant, and audio has been arriving ever since, through the
   * range fetch and through this component mounting. Claiming it continues that
   * one recording. Calling `start()` here instead would throw the learner's
   * first second away and open a second microphone stream to replace it.
   *
   * `startRecording()` is the fallback for the case where nothing was parked,
   * which should not happen on this path but must not leave a live-looking
   * screen with no recorder behind it.
   *
   * A ref guard rather than an empty dep array: the effect must not re-fire
   * when the selection object is replaced by a re-render, and it must not fire
   * at all for an ayah opened by tapping the mushaf or the picker — those are
   * acts of choosing, and turning on a microphone because someone browsed to a
   * verse is not something an app gets to do.
   */
  const autoStarted = useRef(false);
  useEffect(() => {
    if (!selection.autoRecord || autoStarted.current) return;
    autoStarted.current = true;
    (async () => {
      try {
        const inFlight = claimShared();
        handleRef.current = inFlight ? await inFlight : await startRecording();
        setPhase("recording");
      } catch {
        setFailure("mic");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selection.autoRecord]);

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
  const cardRefs = useRef<Record<string, HTMLElement | null>>({});

  /**
   * The clock under the disc, ticking from the handle's own start time.
   *
   * Reads `startedAt` rather than counting from when this screen mounted, which
   * is what makes the timer continuous across the handoff: a recording begun on
   * the reader's mic shows the seconds it has actually been running, not the
   * seconds since the practice screen appeared.
   *
   * THE LAST-TAKE STATS ARE GONE with the card that held them. "Last: 0:14 ·
   * 92%" filled the dark panel's spare width, and the results screen states
   * both properly the moment analysis lands.
   */
  const elapsed = useElapsed(phase === "recording", handleRef.current?.startedAt);

  const { sura, ayah, segment, parts } = selection;
  // `seconds` is the median-reciter estimate and the gate is on real recorded
  // duration, so warn with headroom rather than exactly at the line.
  const tooLong =
    maxAudioSeconds > 0 && segment.seconds > maxAudioSeconds * 0.8;

  /**
   * THE SILENT FALLBACK FOR AYAT THE ENGINE CANNOT HOLD.
   *
   * A handful of ayat — 2:282 is the famous one — run to several minutes. The
   * engine's ceiling is a MEMORY limit, not a preference: attention allocates a
   * [frames, frames, 64] tensor, so cost is quadratic in length and a long ayah
   * does not run slowly, it fails. See Settings.max_audio_seconds.
   *
   * The old answer was to ask the learner which chunk they wanted. This one
   * narrows to the opening section automatically, and then SAYS SO. That
   * sentence is not optional and it is the whole reason this is not the thing
   * the brief warned against: scoring a fragment while presenting it as the
   * whole ayah would be a fabricated result, which is a worse failure than the
   * picker ever was. The learner never chooses a chunk; they are simply told
   * when one is in play.
   *
   * Null on every ayah that fits, which is 99% of them.
   */
  const autoNarrowed =
    maxAudioSeconds > 0 &&
    selection.wholeSegment.seconds > maxAudioSeconds * 0.8 &&
    !selection.whole
      ? segment
      : null;

  /**
   * Narrow to the opening section as soon as an over-long ayah is opened.
   *
   * Runs on the SELECTION, not on a tap, because the learner never asked for
   * this — it is the app arranging what it can actually analyse. `parts[0]`
   * rather than a computed slice: the segmentation is precomputed and legal at
   * those boundaries, and cutting anywhere else raises PartOfUthmaniWord.
   */
  useEffect(() => {
    if (maxAudioSeconds <= 0) return;
    if (!selection.whole) return;
    if (selection.wholeSegment.seconds <= maxAudioSeconds * 0.8) return;
    const first = parts[0];
    if (first) onPart(first, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selection.sura.number, selection.ayah.aya, maxAudioSeconds, parts.length]);
  // Identity of the exact range, so switching parts within one ayah resets
  // too — not just switching ayah.
  const key = `${sura.number}:${ayah.aya}:${segment.start_word}:${segment.num_words}`;

  useEffect(() => {
    handleRef.current?.cancel();
    handleRef.current = null;
    setPhase("idle");
    setResult(null);
    setFailure(null);
    setOwnRecording(null);
    setActiveCardId(null);
    setRetry({ cardId: null, level: null, phase: null, fixed: [],
               stillWrong: null, rungs: {}, tries: {}, accepted: [] });
  }, [key]);

  useEffect(() => () => handleRef.current?.cancel(), []);

  async function start() {
    setResult(null);
    setFailure(null);
    setActiveCardId(null);
    setRetry({ cardId: null, level: null, phase: null, fixed: [],
               stillWrong: null, rungs: {}, tries: {}, accepted: [] });
    try {
      handleRef.current = await startRecording();
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

  /**
   * Tell the app a recording was stored.
   *
   * It used to also stash the take's duration and score for the recording
   * card's stats row. That row went with the card — the results the learner is
   * about to read state both properly, and a second copy of them under the mic
   * was the panel filling its own spare width.
   */
  function remember(out: Attempt) {
    // TELL THE APP FIRST, and tell it about every stored attempt. The counters
    // on Home are built from the attempt history, and the history is only
    // refetched when something says it changed. This is that something.
    //
    // Deliberately OUTSIDE the guard below: a retry-worthy recording is still a
    // row on the server, and the streak counts days practised rather than days
    // practised well. Gating this on `analysable` would mean a learner whose
    // takes were all too noisy to judge kept a streak that never advanced.
    onAttempt?.();
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
      setFailure("mic");
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

  /**
   * The results are open and there is nothing left to correct on this ayah.
   *
   * Computed the SAME WAY Feedback computes it — a filter over the resolved
   * SET, not a counter — so the two cannot drift out of step and leave the
   * screen showing both the arrows and the completion bar, or neither. It is
   * false while a recording or a check is in flight, because the bar offering
   * the next ayah must not appear over a take that has not landed yet.
   */
  const correctionsDone =
    !!result &&
    phase === "idle" &&
    errors.length > 0 &&
    errors.every((e) => retry.fixed.includes(cardId(e)));

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

  /**
   * The rules to paint onto the glyphs.
   *
   * TWO FILTERS, AND BOTH ARE REFUSALS. `reviewed || showUnreviewed` is the
   * same content gate the strip uses — production shows nothing a qori has not
   * signed. `spans.length` drops any rule the engine found but could not
   * PLACE: the idgham token-count proxy knows an assimilation happened without
   * knowing which letter did it, and a colour has to land on a specific glyph
   * or it is a claim nobody made.
   */
  // Gating, placement filter and precedence all live in lib/rules, shared with
  // the reader — the same ayah must not be coloured two different ways
  // depending on which screen the learner reached it from.
  const ruleSpans: RuleSpan[] = ruleLayers(segment.rules, showUnreviewed);

  function scrollToCard(id: string) {
    setActiveCardId(id);
    cardRefs.current[id]?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }

  return (
    <>
      {/* The sura, in the serif, exactly as the reader's own head shows it —
          and the ayah number is NOT here. It sits in the centre of the arrow
          row below, which is where the reader puts it, so the two screens
          carry the same fact in the same slot. */}
      <div className="eyebrow">
        <div className="eyebrow__where">
          <h2 className="eyebrow__name">
            {sura.number}. {sura.translit}
          </h2>
          {/* The partial range, when one is in play. It qualifies the ayah, so
              it sits under the sura name rather than inside the badge — the
              badge answers "which ayah", and it must keep answering only that
              however narrow the range gets. */}
          {!selection.whole && (
            <p className="eyebrow__range">
              {t(lang, "words")} {segment.start_word + 1}–
              {segment.start_word + segment.num_words}
            </p>
          )}
        </div>
      </div>

      {/* ── LEAVING, AND MOVING ALONG ────────────────────────────────────
             Two different intentions that used to share one control.

             "Boshqa oyat tanlash" was a text link that dropped you back into
             the picker at the sura you were already in — so getting to the
             next ayah meant leaving practice, finding your place in the
             reader, and tapping the ayah below the one you just did. Three
             steps to go one verse forward.

             Now the two are separate and shaped like what they do: one control
             that LEAVES, straight out to the full 114-sura list, and arrows
             that MOVE, to the ayah either side without unwinding anything.

             ── THE LEAVE CONTROL IS A LABELLED BUTTON, NOT AN X ─────────────

             It was a 36px circle carrying a close glyph and an aria-label, and
             an aria-label is not a label — nobody looking at the screen can
             read it. "Choose a different sura" is a thing learners genuinely
             want early and often, and it was the least visible control on the
             screen: an unnamed icon, at icon size, in the muted ink. So it now
             says what it does, in words, in a contained shape at the top of the
             screen where the decision is actually made. The glyph stays beside
             the text, because the icon was never the problem. */}
      <div className="ayah-nav ayah-nav--stacked">
        <button className="btn-switch" onClick={onChange}>
          <Close />
          {t(lang, "exit_practice")}
        </button>

        {/* THE AYAH NUMBER, BETWEEN THE CONTROLS. An early draft put
            "Al-Fatiha · 1:1" here and it repeated the heading two lines above
            it, which is why it was removed. The badge is not that: it carries
            the one fact the heading does NOT — which ayah of the sura — and it
            sits here because this is where the reader's verse view puts it, in
            the middle of its own arrow row. Same component, same slot, so the
            number does not move when the recording starts. */}
        <div className="ayah-nav__place">
        <AyahBadge lang={lang} aya={ayah.aya} />

        {/* REPLACED, NOT DUPLICATED. Once the results are open and every
            correction on this ayah is resolved, the completion bar at the foot
            of the results carries the named move instead - see Feedback's
            `donebar`. Two ways to do the same thing, one of them silent
            chevrons at the far end of the screen, is how the learner ends up
            using neither. */}
        {!correctionsDone && (
        <div className="ayah-nav__steps">
          <button
            className="ayah-nav__arrow"
            aria-label={t(lang, "prev_ayah")}
            disabled={!canStep.prev || phase !== "idle"}
            onClick={() => onStep(-1)}
          >
            <Chevron size={16} />
          </button>
          <button
            className="ayah-nav__arrow ayah-nav__arrow--next"
            aria-label={t(lang, "next_ayah")}
            disabled={!canStep.next || phase !== "idle"}
            onClick={() => onStep(1)}
          >
            <Chevron size={16} />
          </button>
        </div>
        )}
        </div>
      </div>

      <AyahText
        uthmani={segment.uthmani}
        segments={segment.text_segments}
        marks={marks}
        // The rules governing these glyphs, coloured onto the text. Gated the
        // same way the strip below is — nothing here has a qori's signature —
        // and filtered to the ones the engine could actually PLACE, so a rule
        // it found but could not locate is named in the strip and painted
        // nowhere. See RuleBadge.spans.
        rules={ruleSpans}
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

      {/* NO DURATION ESTIMATE HERE. "Taxminiy davomiylik ≈ 4.5 s" under every
          ayah was a figure about the ENGINE's budget dressed as a reading aid.
          The two warnings below stay, because they are not measurements — they
          are the app explaining something it has already done to the range. */}

      {/* THE ONE SENTENCE THE FALLBACK OWES THE LEARNER. Shown when the app
          has narrowed a long ayah on its own, so the range on screen is
          explained rather than merely different from the ayah they chose.
          Blames the length, never the learner, and does not ask anything. */}
      {autoNarrowed && (
        <p className="estimate estimate--warn">{t(lang, "long_ayah_note")}</p>
      )}

      {/* Said BEFORE recording. Inference runs ~10x realtime, so learning this
          from the result would mean waiting minutes for a rejection. The
          ceiling is the engine's memory limit, not a judgement about the
          learner, so the wording blames the length. */}
      {tooLong && !autoNarrowed && (
        <p className="estimate estimate--warn">{t(lang, "too_long_hint")}</p>
      )}

      {/* ── THE SEGMENT PICKER IS GONE, AND SO IS THE CONCEPT ────────────
             There used to be a "practise part of this ayah" control here that
             opened a list of numbered chunks. It is removed: a learner opening
             an ayah should record the ayah, and "which 12-second slice of this
             verse would you like" is a question about the engine's memory
             budget wearing the costume of a feature.

             The segmentation itself is NOT gone — see `autoNarrowed` above and
             ranges.py. It still runs, silently, on the ~60 ayat whose full
             length exceeds what the engine can hold, and it says so in one
             plain sentence instead of asking. Everywhere else, which is 99% of
             the Qur'an, the whole ayah is simply what gets recorded.

             THE RECITER CONTROLS ARE GONE FROM HERE TOO. The picker and the
             "listen first" button both moved: the choice is one setting in
             Profile, and the listening now happens AFTER the result, next to
             the learner's own recording, where the two can be compared. Before
             recording, hearing a perfect reading is as likely to be a thing to
             imitate from memory as a thing to learn from. */}

      {/* THE SAME STRIP THE READER SHOWS, from the same `rules` on the same
          segment — so what the ayah contains does not change on the way into
          the recording. It sits ABOVE the mic here, because below it is where
          the result lands. */}
      <RuleBadges
        lang={lang}
        rules={selection.segment.rules ?? []}
        showUnreviewed={showUnreviewed}
      />

      {/* THE SAME CONTROL THE READER SHOWS. Not a similar one — the same
          component, the same props, the same disc floating on the same
          background with no card around it. There used to be a deep navy panel
          here carrying a header, a stats row and a small horizontal mic, and it
          made this moment look like equipment being operated. */}
      <Recorder
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
        disabled={failure === "mic"}
        longWait={tooLong}
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
          {/* YOUR READING AND THE RECITER'S, SIDE BY SIDE. Hearing yourself
              back is how a learner judges whether a flagged error is real, and
              hearing it against the reciter is how they judge what to do about
              it. Session-only on our side: the blob lives in memory until the
              next take replaces it.
              The reciter file is whole-ayah only on everyayah, so a range that
              was auto-narrowed offers no comparison rather than requesting a
              file that does not exist. */}
          <PlaybackPair
            lang={lang}
            blob={ownRecording}
            reciterUrl={
              selection.whole
                ? expertAudioUrl(sura.number, ayah.aya, reciter)
                : ""
            }
          />
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
            // The ayah-to-ayah move, handed to the results view so it can end
            // on a named action instead of sending the learner back up to a
            // pair of chevrons. Same handler the arrows used.
            onStep={onStep}
            canStep={canStep}
            cardRefs={cardRefs}
          />
        </ErrorBoundary>
      )}
    </>
  );
}
