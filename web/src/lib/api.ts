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

export type ErrorContent = {
  rule: string;
  you_did: string;
  fix: string;
  drill: string;
  severity: string;
  /** No qori has authored this code at all; `rule` holds the raw code. */
  unauthored?: boolean;
};

export type TajweedError = {
  code: string;
  /** Run-length unit index — join to Segment.units to find the letter. */
  at: number;
  letter: string;
  needs_teacher?: boolean;
  /**
   * Reached the screen only because TILAWAH_SHOW_UNREVIEWED is on — no qori has
   * signed this off. The UI MUST render a visible marker; that obligation is
   * the whole reason the server sends the flag rather than just the content.
   */
  draft?: boolean;
  content: ErrorContent;
};

export type Attempt = {
  id: number | null;
  sura: number;
  aya: number;
  status: "ok" | "retry_recording" | "error";
  reason: string;
  clean: boolean;
  suppressed: boolean;
  errors: TajweedError[];
  snr_db: number;
  duration_s: number;
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
};

export type SuraAyat = {
  sura: number;
  name_ar: string;
  translit: string;
  n_ayat: number;
  ayat: AyahBrief[];
};

export const suraAyat = (sura: number) =>
  fetch(`${BASE}/api/suras/${sura}/ayat`).then(json<SuraAyat>);

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
  segments: PracticeSegment[];
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
  /** The server's content review gate is bypassed. Dev boxes only. */
  show_unreviewed: boolean;
  version: string;
};

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

export function expertAudioUrl(sura: number, aya: number): string {
  const s = String(sura).padStart(3, "0");
  const a = String(aya).padStart(3, "0");
  return `https://everyayah.com/data/Alafasy_128kbps/${s}${a}.mp3`;
}
