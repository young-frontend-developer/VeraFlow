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
};

export type TajweedError = {
  code: string;
  /** Run-length unit index — join to Segment.units to find the letter. */
  at: number;
  letter: string;
  needs_teacher?: boolean;
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

export type Meta = {
  pilot: boolean;
  unverified_codes: string[];
  collect_audio_offered: boolean;
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
