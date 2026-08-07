const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/**
 * One letter-group of the ayah. `start`/`end` index the Uthmani string; the UI
 * measures a Range over them rather than slicing the text, because splitting
 * cursive Arabic into separate elements breaks the joining forms.
 */
export type Segment = {
  text: string;
  start: number;
  end: number;
  units: number[];
};

export type Ayah = {
  sura: number;
  aya: number;
  slug: string;
  level: number;
  uthmani: string;
  name_uz: string;
  name_ru: string;
  segments: Segment[];
};

/**
 * The authored half of a card. TWO sentences of text, and no more:
 *
 *   headline  what went wrong, in this word, with this letter
 *   fix       the ONE thing to do about it
 *
 * `rule` and `drill` USED TO BE HERE and are deliberately gone. `rule` was the
 * ruling and why it matters — tajweed theory behind a "Why" disclosure, which
 * a beginner cannot use and did not ask for. `drill` was a paragraph
 * describing an exercise, which the practice ladder now replaces with
 * something tappable. Both are still authored and still in the registries; the
 * review tool reads them there. They are simply not part of a learner's card.
 *
 * Templates are substituted server-side and validated there: a string that
 * still contains a brace never leaves the API.
 */
export type ErrorContent = {
  headline: string;
  fix: string;
  severity: string;
  /** Whether a qori has signed this text off. Almost never true today. */
  reviewed?: boolean;
  /** The registry entry's own short title. Never the error code. */
  label?: string;
  /**
   * URL of the isolated LETTER recording for this confusion — the sound of
   * «ص» against «س», not the ayah. Empty when no file exists, and empty is the
   * signal to render no button at all rather than a dead one.
   */
  audio_pair?: string;
  /** Nothing is authored for this code; only the location is known. */
  unauthored?: boolean;
};

/**
 * The learner-facing category. The client turns this into a title; the raw
 * `code` is never printed. Closed set — see engine/cards.py.
 */
export type ErrorKind =
  | "extra_letter"
  | "missing_letter"
  | "wrong_letter"
  | "pronunciation"
  | "tajweed"
  | "madd"
  | "ghunna"
  | "haraka"
  /**
   * Length on a DOUBLED CONSONANT. Its own kind because it is not madd: madd
   * lengthens a vowel on ا و ي, shadda holds a consonant, and they are
   * different rulings with different corrections. SHADDA_* used to be titled
   * as madd, which pointed the learner at the wrong rule entirely.
   */
  | "shadda";

/**
 * One rung of the practice ladder — see engine/practice.py, which builds them.
 *
 * THE SHAPE DEPENDS ON THE ERROR. There are four ladders, not one, and the
 * server picks between them:
 *
 *   articulation  letter → syllables → word → ayah
 *   omission      word_include → word → ayah
 *   insertion     word_omit → word → ayah
 *   duration      word_hold → word → ayah
 *
 * The isolated-letter opening belongs only to the first. A letter that was
 * DROPPED was never mispronounced, a letter that was ADDED needs un-saying
 * rather than saying, and a bare letter has no duration at all — so for those
 * three the ladder opens on the word, said slowly with the thing to attend to
 * named. Every rung is still derived from the error, so one exists even for
 * codes with no coaching text.
 */
export type PracticeRung = {
  /** Position on the ladder, 1-based and gapless. */
  level: number;
  /**
   * What this rung is, and therefore what the learner is being asked to do.
   * `ayah` carries no items — it is already on screen.
   *
   *   letter        the sound alone
   *   syllables     that sound under each haraka
   *   word_include  the word, slowly, sounding the letter that went missing
   *   word_omit     the word, slowly, without the sound that was added
   *   word_hold     the word, holding the letter for `hold` harakat
   *   word          the word at normal pace
   *   ayah          back to the test
   */
  focus:
    | "letter"
    | "syllables"
    | "word_include"
    | "word_omit"
    | "word_hold"
    | "word"
    | "ayah";
  items: string[];
  /**
   * Whether this rung can be RECORDED AND SCORED. False for the letter and
   * syllable rungs: the engine scores against a word range of an ayah and has
   * no target for a bare letter, so offering a record button there would be a
   * control that cannot do what it says. Those two rungs are listen-and-say.
   */
  recordable: boolean;
  /**
   * How this rung is judged, and therefore which control it gets.
   *
   *   score  recorded and diffed against a real target — word and ayah
   *   self   the learner confirms they said it — letter and syllables
   *
   * Both gate the next rung, so the ladder is climbed in order either way.
   * What differs is who judges, and the UI has to be honest about which:
   * a `self` rung that displayed a percentage would be inventing one.
   */
  check: "score" | "self";
  /** Ayah-relative word to re-record, for the `word` rung. -1 otherwise. */
  word_index: number;
  /**
   * Playable URL for this rung, or "" for none — and "" means render NO
   * control, never a dead one.
   */
  audio: string;
  /**
   * Where this rung's audio comes from. `ayah` is resolved CLIENT-SIDE from
   * the reciter the learner picked, which the server does not know; `letter`
   * arrives as a ready URL in `audio`. Empty means there is no recording for
   * this rung and none is claimed — today that is every word rung, because
   * everyayah serves whole-ayah files with no word timings to clip.
   */
  audio_source: "letter" | "ayah" | "";
  /**
   * Harakat to hold for on a `word_hold` rung, 0 on every other rung.
   *
   * It is the reference's own expected count, and when the reference does not
   * supply one the server omits the rung rather than sending 0 with a rung that
   * needs a number — so a `word_hold` rung always has a real count to count to.
   */
  hold: number;
};

/** One place this error happened. A merged card has several. */
export type Occurrence = {
  at: number;
  word: string;
  /** Index of that word WITHIN THE AYAH — feeds `start_word` on re-record. */
  word_index: number;
  /**
   * The Uthmani character range to paint, narrowed to THE SOUND rather than
   * the letter-group containing it. For a madd this is the lengthening mark
   * alone, not the consonant it sits after — so "2 harakat kerak" points at
   * the thing it is about. Absent on attempts replayed from before this
   * existed, in which case the caller falls back to the segment.
   */
  span?: [number, number];
  /** Which instance of this letter within its word, 1-based, and how many. */
  ordinal?: number;
  of?: number;
};

export type TajweedError = {
  /**
   * Internal. Kept for the "this assessment is wrong" report and for logs.
   * MUST NOT be rendered — use `kind` for the title. See Part B.
   */
  code: string;
  kind: ErrorKind;
  /** Run-length unit index of the FIRST occurrence. */
  at: number;
  letter: string;
  /**
   * What should have been said. A LETTER for a substitution, a haraka NAME
   * ("fatha") for a vowel error, and empty for duration and ṣifa errors — so
   * a caller showing it in an Arabic-script chip must check it is one
   * character first.
   */
  expected?: string;
  /** What we heard, on the same terms as `expected`. */
  heard?: string;
  /**
   * The Uthmani word the error falls in. Present even when nothing is authored
   * for the code — locating the mistake never depends on having text for it.
   */
  word?: string;
  /** Ayah-relative index of that word, for re-recording just it. -1 if unknown. */
  word_index?: number;
  /** How many times this (code, letter) occurred. 1 for most cards. */
  count: number;
  /** Every occurrence, so the ayah can mark all of them — not just the first. */
  occurrences: Occurrence[];
  /** The distinct words it touched, in reading order. */
  words: string[];
  /**
   * The name of the ruling this card is about — the registry entry's own short
   * title, or the ṣifa's name. Empty when neither exists, and empty means fall
   * back to the `kind` title, which is also a real name. Never the code.
   */
  rule_name?: string;
  /** Which ṣifa property was wrong, named. Empty for non-ṣifa errors. */
  sifa_name?: string;
  /**
   * Where the tongue, throat or lips go to make this sound. Answers "which
   * articulation point" and "which mouth position" — the two questions a card
   * saying only "the ṣifa was wrong" could never answer.
   */
  articulation?: string;
  /**
   * WHERE THE CORRECT LETTER COMES FROM, and what it is like — one sentence,
   * rendered above the fix instruction.
   *
   * Always about the TARGET letter, never the one that was heard: the card
   * exists to move the learner toward the right sound, and describing the
   * wrong one describes the mistake. Empty on cards that are not about
   * producing a letter — a skipped letter was never mispronounced, and a madd
   * error is about a length rather than a place — which is the same scope rule
   * the isolated-letter practice rung uses.
   */
  makhraj?: string;
  /**
   * Teaching tier: 1 wrong letter, 2 articulation, 3 ruling, 4 timing. The
   * server ranks by this, so the client does not re-sort — it renders in the
   * order it was sent.
   */
  tier?: number;
  /**
   * Position in the reveal chain, dense from 0. The client opens the lowest
   * unresolved one and unlocks forward, so the learner meets one correction at
   * a time while the engine still reports everything it found.
   */
  reveal_order?: number;
  /** Which ṣifa field the detector compared. Internal; never rendered raw. */
  sifa?: string;
  /** Reference and heard length, in harakat. 0 when not a duration error. */
  expected_count?: number;
  heard_count?: number;
  needs_teacher?: boolean;
  /**
   * No qori has signed this off. Outside production that is the normal case,
   * not an exception — the UI MUST render a visible marker on every one of
   * them. That obligation is the whole reason the server sends the flag rather
   * than just the content.
   */
  draft?: boolean;
  content: ErrorContent;
  /**
   * The practice ladder for this card, narrowest rung first. Always at least
   * one rung — derived, not authored, so it never depends on a qori having
   * written anything for this code.
   */
  practice: PracticeRung[];
};

export type Attempt = {
  id: number | null;
  sura: number;
  aya: number;
  status: "ok" | "retry_recording" | "error";
  reason: string;
  /** Nothing was detected — the only case where praise is honest. */
  clean: boolean;
  /**
   * Something WAS detected and every correction was withheld by the production
   * content gate. A judgement exists; we are not allowed to show it.
   */
  suppressed: boolean;
  /**
   * The model returned nothing to compare against, so no judgement was formed.
   * Distinct from `suppressed` on purpose — these are different failures and
   * they must not print the same sentence.
   */
  analysable: boolean;
  errors: TajweedError[];
  snr_db: number;
  duration_s: number;
  /**
   * Fraction of the recited range's sounds with no error against them, and the
   * mark a practice rung has to clear before the next unlocks.
   *
   * `pass_score` is SENT rather than hard-coded here on purpose: it is a guess
   * made before any learner has used the ladder, and it is meant to be tuned
   * from real attempts. A threshold compiled into the bundle would need a
   * release to move.
   */
  score?: number;
  pass_score?: number;
  /**
   * ISO timestamp of when this attempt was recorded, or null on rows written
   * before the server sent it.
   *
   * It is the only reason the Today screen's week strip and its "last
   * practiced" line can exist: without a real date the alternatives were to
   * draw a week of invented days or to drop the section. A null leaves that
   * day unmarked — never guessed.
   */
  created_at?: string | null;
};

// Anonymous until there is a reason to have accounts. Stored locally so the
// learner can revoke consent and have the server actually delete their data.
export function deviceId(): string {
  let id = localStorage.getItem("tilawah_device_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("tilawah_device_id", id);
  }
  return id;
}

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export const listAyat = () => fetch(`${BASE}/api/ayat`).then(json<Ayah[]>);

/** One row of the sura picker. All 114 come down in a single small response. */
export type Sura = {
  number: number;
  name_ar: string;
  /** Standard Latin form — "Al-Fatiha". */
  translit: string;
  /** Uzbek form — "Fotiha". Different enough that search needs both. */
  uz: string;
  n_ayat: number;
  /**
   * Prefolded haystack: number, both transliterations and the Arabic name,
   * lowercased with apostrophes and hyphens stripped. Filter with a plain
   * `includes` against the query folded the same way — see `foldQuery`.
   */
  search: string;
};

export const listSuras = () => fetch(`${BASE}/api/suras`).then(json<Sura[]>);

/** Strip what a learner will not type: "Ali 'Imran" gets typed "ali imran". */
export const foldQuery = (q: string) =>
  q.toLowerCase().replace(/['’`\-–—]/g, "").trim();

export type AyahBrief = {
  aya: number;
  uthmani: string;
  n_words: number;
  n_segments: number;
  seconds: number;
  /** Translation in the language this sura was requested in. */
  translation: string;
};

export type SuraAyat = {
  sura: number;
  name_ar: string;
  translit: string;
  n_ayat: number;
  ayat: AyahBrief[];
  /**
   * Whether the mushaf prints the basmala as an opening line for this sura.
   * False for al-Fatiha (it IS ayah 1) and at-Tawba (there is none), so it
   * cannot be assumed — the server decides and the reader obeys.
   */
  has_basmala: boolean;
  bismillah: string;
};

export const suraAyat = (sura: number, lang: string) =>
  fetch(`${BASE}/api/suras/${sura}/ayat?lang=${lang}`).then(json<SuraAyat>);

/* ── reciters ─────────────────────────────────────────────────────────── */

export type Reciter = {
  /** everyayah folder name; also the persisted key. */
  id: string;
  name: string;
  /** muallim (repeats phrases, best for beginners) | murattal | mujawwad */
  style: "muallim" | "murattal" | "mujawwad" | string;
  bitrate_kbps: number;
};

export type Reciters = {
  default: string;
  base_url: string;
  reciters: Reciter[];
};

export const listReciters = () =>
  fetch(`${BASE}/api/reciters`).then(json<Reciters>);

export const history = (limit = 20) =>
  fetch(
    `${BASE}/api/attempts?device_id=${encodeURIComponent(deviceId())}&limit=${limit}`,
  ).then(json<Attempt[]>);

/** A practice range, indexed RELATIVE TO THE AYAH (never encoded indices). */
export type PracticeRange = {
  start_word: number;
  num_words: number;
  include_bismillah?: boolean;
};

export type PracticeSegment = PracticeRange & {
  index: number;
  n_phonemes: number;
  /** Median-reciter estimate. The slow rate used for capping is never sent. */
  seconds: number;
  uthmani: string;
  /**
   * Letter-groups for THIS range, with unit indices relative to the range —
   * which is what the engine diffs, so it is what `TajweedError.at` counts
   * against. Using the whole ayah's segments for a sub-range would put every
   * highlight on the wrong letter.
   */
  text_segments: Segment[];
};

export type AyahSegments = {
  sura: number;
  aya: number;
  n_words: number;
  /** Boundaries that do not split an Uthmani word — the only legal cuts. */
  legal_cuts: number[];
  /**
   * THE practice range: the entire ayah, whatever its length. Always present.
   * This is what gets selected unless the learner deliberately asks for less.
   */
  whole: PracticeSegment;
  /**
   * Optional "practise part of this ayah" ranges. Empty when the ayah is a
   * single part anyway, so a non-empty list is exactly when to offer the
   * control — never a forced split.
   */
  parts: PracticeSegment[];
};

export const ayahSegments = (sura: number, aya: number) =>
  fetch(`${BASE}/api/segments/${sura}/${aya}`).then(json<AyahSegments>);

export async function submitAttempt(
  audio: Blob,
  sura: number,
  aya: number,
  lang: string,
  range?: PracticeRange,
): Promise<Attempt> {
  const fd = new FormData();
  fd.append("audio", audio, "recitation.wav");
  fd.append("sura", String(sura));
  fd.append("aya", String(aya));
  fd.append("lang", lang);
  fd.append("device_id", deviceId());
  // Omitted or 0 means the whole ayah, so existing callers are unaffected.
  fd.append("start_word", String(range?.start_word ?? 0));
  fd.append("num_words", String(range?.num_words ?? 0));
  fd.append("include_bismillah", String(range?.include_bismillah ?? false));
  return fetch(`${BASE}/api/attempts`, { method: "POST", body: fd }).then(
    json<Attempt>,
  );
}

export async function flagWrong(attemptId: number): Promise<void> {
  await fetch(`${BASE}/api/attempts/${attemptId}/wrong`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note: null }),
  });
}

/* ── qori review tool ─────────────────────────────────────────────────────
   Operator-facing, not learner-facing. Unauthenticated by design and refused
   outright by the server in production. */

/** The Uzbek block of a registry entry, as a learner would eventually read it. */
export type ReviewUz = {
  name?: string;
  short?: string;
  nima_xato?: string;
  qoida?: string;
  nega_muhim?: string;
  tuzatish?: string;
  mashq?: string;
};

export const UZ_FIELDS: (keyof ReviewUz)[] = [
  "name",
  "short",
  "nima_xato",
  "qoida",
  "nega_muhim",
  "tuzatish",
  "mashq",
];

export type ReviewEntry = {
  code: string;
  group: string;
  severity: string;
  detection_confidence: string;
  source_ref: string;
  status: "draft" | "reviewed" | "rejected";
  reviewed_by: string;
  reviewed_at: string;
  review_note: string;
  /** Fields a reviewer has edited away from the generated registry. */
  uz_edited_fields: string[];
  uz: ReviewUz;
  review_order: number;
  beginner_pct: number;
  all_pct: number;
};

export type ReviewQueue = {
  total: number;
  reviewed: number;
  rejected: number;
  remaining: number;
  entries: ReviewEntry[];
  ranking_stale: boolean;
};

export const reviewQueue = () =>
  fetch(`${BASE}/api/review/queue`).then(json<ReviewQueue>);

export async function reviewDecide(
  code: string,
  action: "approve" | "reject" | "edit" | "reset",
  opts: { reviewed_by?: string; note?: string; uz?: ReviewUz } = {},
): Promise<ReviewEntry> {
  const r = await fetch(`${BASE}/api/review/${encodeURIComponent(code)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action,
      reviewed_by: opts.reviewed_by ?? "",
      note: opts.note ?? "",
      uz: opts.uz ?? {},
    }),
  });
  if (!r.ok) {
    // The server explains itself here — "reviewed_by is required to approve",
    // "not a reviewable entry" — so surface it rather than a bare status code.
    let detail = String(r.status);
    try {
      detail = (await r.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return r.json();
}

export type Meta = {
  pilot: boolean;
  unverified_codes: string[];
  collect_audio_offered: boolean;
  /** The server's content review gate is open — true outside production. */
  show_unreviewed: boolean;
  /**
   * Longest recitation the engine will attempt, in seconds. A memory limit,
   * quadratic in length, not a preference. Used to warn BEFORE recording:
   * inference runs ~10x realtime, so finding out afterwards costs minutes.
   */
  max_audio_seconds: number;
  /** Coaching registries the server could not find. Non-empty = a known gap. */
  missing_registries: string[];
  /**
   * Entries naming an isolated letter recording that is not on disk. Each is a
   * practice button being hidden — the gap stays countable rather than just
   * invisible.
   */
  missing_audio: string[];
  /** Every field this server puts on an error object. See staleApiFields(). */
  error_fields?: string[];
  version: string;
};

/**
 * Fields <Correction> dereferences without a fallback. If the API does not send
 * one of these, every card throws.
 *
 * Kept as data so the mismatch can be DETECTED rather than discovered from a
 * broken screen: a server process started before a field was added keeps
 * answering 200s, and from the browser that is indistinguishable from a bug in
 * the client. api/tests/test_client_contract.py enforces the same list on the
 * server side by reading it out of the component.
 */
export const REQUIRED_ERROR_FIELDS = [
  "kind",
  "letter",
  "count",
  "words",
  "occurrences",
  "content",
] as const;

/**
 * Which required fields the connected API does not send — empty when in sync.
 *
 * Returns [] for a server too old to declare `error_fields` at all; that case
 * is reported separately, because "declares nothing" and "declares an
 * incomplete set" want different sentences.
 */
export function staleApiFields(info: Meta | null): string[] {
  if (!info?.error_fields?.length) return [];
  const sent = new Set(info.error_fields);
  return REQUIRED_ERROR_FIELDS.filter((f) => !sent.has(f));
}

/** True when the API is old enough that it does not describe its own payload. */
export function apiPredatesContract(info: Meta | null): boolean {
  return !!info && !info.error_fields?.length;
}

export const meta = () => fetch(`${BASE}/api/meta`).then(json<Meta>);

/**
 * Two separate permissions. Storing a record of what you recited is not the
 * same as storing a recording of your voice, so audio is asked for separately
 * and defaults to off. Revoking either one deletes what it covered.
 */
export async function setConsent(
  consented: boolean,
  audioConsented = false,
): Promise<void> {
  const fd = new FormData();
  fd.append("device_id", deviceId());
  fd.append("consented", String(consented));
  fd.append("audio_consented", String(audioConsented));
  await fetch(`${BASE}/api/consent`, { method: "POST", body: fd });
}

/**
 * everyayah serves ONE FILE PER WHOLE AYAH — there is no file for a fragment,
 * which is why playback died while long ayat were being force-split.
 *
 * `reciter` is an everyayah folder name from /api/reciters, each probed at
 * build time against 1:1, 2:282, 36:1 and 114:6.
 */
/**
 * The isolated letter-pair recording a card's practice section plays.
 *
 * `content.audio_pair` is a server path ("/audio/sad_zay.mp3") that the API
 * only sends when the file really exists, so an empty string here means "no
 * recording" and the caller must render no control at all.
 */
export function letterAudioUrl(audioPair: string): string {
  return audioPair ? `${BASE}${audioPair}` : "";
}

export function expertAudioUrl(
  sura: number,
  aya: number,
  reciter: string,
): string {
  const s = String(sura).padStart(3, "0");
  const a = String(aya).padStart(3, "0");
  return `https://everyayah.com/data/${reciter}/${s}${a}.mp3`;
}


/**
 * The day's hadith, or null.
 *
 * NULL IS A REAL ANSWER — in production only qori-reviewed entries are
 * eligible, and none are yet, so the card is simply not drawn there. Never
 * substitute a fallback: a fallback is where an unreviewed attribution would
 * end up. See api/tilawah/content/hadith.py.
 */
export type Hadith = {
  id: string;
  /** The Arabic text of the hadith. */
  ar: string;
  /** A rendering of the meaning — labelled as such on the card, never as the hadith. */
  text: string;
  collection: string;
  ref: string;
  grading: string;
  /** No qori has checked the wording OR the citation. The client must mark it. */
  draft: boolean;
};

export const hadithToday = (lang: string) =>
  fetch(`${BASE}/api/hadith/today?lang=${lang}`).then(json<Hadith | null>);
