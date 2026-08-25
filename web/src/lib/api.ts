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

  /**
   * ── the v7 restructure ───────────────────────────────────────────────────
   *
   * `card_kind` decides which of two card shapes this renders as, and 0 means
   * NEITHER — the entry has not been converted yet and keeps the old
   * headline+fix card. 56 of 61 are still 0, so this is the common case and
   * not an error state.
   *
   *   1  RULE VIOLATION      the letters were right, a ruling was not applied.
   *                          Gets the ❔ Qoida toggle and, where authored, the
   *                          💡 simplified level.
   *   2  PRONUNCIATION       a sound came out wrong. No rule toggle: §4 is
   *                          explicit that theory does not help here.
   */
  card_kind?: 0 | 1 | 2;
  /** "What happened", split out of the headline so each says one thing. */
  explanation?: string;
  /** The one physical instruction. Same slot `fix` filled, renamed by §14. */
  correction?: string;
  /** The phrase to re-record, e.g. «الٓمٓ» ni qayta o'qing. */
  retry?: string;
  /**
   * The ruling, condensed to a sentence, for the ❔ toggle on Kind 1 cards.
   * NOT the old `rule` field — that was two paragraphs of theory rendered
   * unconditionally on every card, which is why it was removed. This is
   * shorter, collapsed by default, and Kind 1 only.
   */
  rule_text?: string;
  /**
   * The 💡 "Explain simply" level. NULL, not empty strings, when nobody has
   * authored one — the button must not appear rather than opening onto
   * nothing. §10: it may never contradict or replace the standard text.
   */
  simplified?: { explanation: string; correction: string } | null;
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
  /**
   * The rule code actually PLACED at this error's position by
   * engine/rule_presence, e.g. "RULE_MADD_LOZIM". Empty when the engine could
   * not place one — which must be rendered as no rule colour and no rule name,
   * never as a default. It is what lets a card be tinted to match the same
   * ruling's colour in the ayah above it.
   */
  rule_code?: string;
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
  /**
   * Arabic letters in the range that was recited, counted BY THE SERVER from
   * the Uthmani text — see api/tilawah/content/letters.py, which documents
   * what counts as a letter against the wording of the hadith the hasanat
   * total rests on.
   *
   * Not computed here, and it must not be: the client holds one sura's text at
   * a time while history spans many, so deriving it in the browser would mean
   * estimating — and an estimate with a hadith attached to it is exactly the
   * thing this app does not ship. Absent on rows from a server that predates
   * the field, and absent means 0, not "about this many".
   */
  letters?: number;
  wrong_flag?: boolean;
};

/**
 * THE DEVICE ID IS NO LONGER A CREDENTIAL. It used to be the whole of identity:
 * every learner-data request carried it and the server took the caller's word
 * for it, which meant anyone who knew one could read that person's history or
 * delete their account. The server stopped accepting it as proof; this file
 * stopped sending it as proof.
 *
 * What it still does, exactly once, is claim an account. An install that
 * predates sign-in has practice history filed under this id, so it is handed to
 * POST /api/auth/anonymous to say "this is who I was" and a real session comes
 * back. After that it is never sent again.
 *
 * Keep it stable. Losing it does not lose the account while a session survives,
 * but it is the only way back to the old history if the session is ever lost.
 */
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

/* ── sessions ─────────────────────────────────────────────────────────────

   The server issues an opaque token and ALSO sets it as an httpOnly cookie.
   Both are the same session; which one travels is a transport detail.

   WHY THE TOKEN IS KEPT IN localStorage ANYWAY, despite the cookie being the
   safer store: the dev client runs on :5173 and the api on :8000, which is
   CROSS-SITE, and the cookie is SameSite=lax - so the browser will not attach
   it. The same is true of any split-origin deployment, which is where the
   Android plan points. A bearer header works in every arrangement, so it is
   the one this client relies on, with `credentials: "include"` alongside it so
   a same-origin deployment gets the cookie for free.

   THE TRADE-OFF IS REAL AND IT IS NOT FREE: a token in localStorage is
   readable by any script that gets injected, which an httpOnly cookie is not.
   The mitigation available today is that the token is revocable server-side.
   The real fix is to serve the client and the api from ONE origin and delete
   the localStorage half of this - at which point the cookie alone suffices. */

const SESSION_KEY = "tilawah_session_token";

/** In-flight bootstrap, so ten simultaneous calls mint one session, not ten. */
let bootstrapping: Promise<string> | null = null;

function storedToken(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY);
  } catch {
    return null; // private mode, disabled storage - treat as "no session yet"
  }
}

function keepToken(token: string): void {
  try {
    localStorage.setItem(SESSION_KEY, token);
  } catch {
    /* the session still works for this page load; it just will not survive it */
  }
}

/** Forget the local session. Does NOT revoke it server-side - see logout(). */
export function clearSession(): void {
  bootstrapping = null;
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch {
    /* nothing to do */
  }
}

/**
 * Forget the session ONLY if it is still the one the caller was using.
 *
 * COMPARE-AND-CLEAR, because 401s arrive in parallel. The app fires several
 * learner-data requests at once, so an expired token produces several 401s at
 * once. With an unconditional clear, the second one wipes the fresh token the
 * first one just obtained, and each request bootstraps again - measured as two
 * sessions minted per reload in e2e-session.mjs, with the losers left live on
 * the server. Checking first means the first 401 replaces the token and the
 * rest simply use it.
 */
function clearSessionIf(token: string): void {
  if (storedToken() === token) clearSession();
}

export function hasSession(): boolean {
  return Boolean(storedToken());
}

/** Exchange the device id for a session. The only place device_id is sent. */
async function bootstrapSession(): Promise<string> {
  const r = await fetch(`${BASE}/api/auth/anonymous`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ device_id: deviceId() }),
  });
  if (!r.ok) throw new Error(String(r.status));
  const body = (await r.json()) as { token: string };
  keepToken(body.token);
  return body.token;
}

/**
 * A usable token, minting one if needed.
 *
 * SINGLE-FLIGHT. The app opens by firing several requests at once; without the
 * shared promise each would bootstrap its own session, leaving a pile of live
 * tokens for one learner and a race over which one localStorage kept. The
 * promise is cleared on failure so a later call retries rather than
 * re-throwing a stale rejection forever.
 */
export async function ensureSession(): Promise<string> {
  const existing = storedToken();
  if (existing) return existing;
  if (!bootstrapping) {
    bootstrapping = bootstrapSession().finally(() => {
      bootstrapping = null;
    });
  }
  return bootstrapping;
}

/**
 * Rotate the session. The old token stops working the moment this returns, so
 * the new one is stored before anything else can use it.
 */
export async function refreshSession(): Promise<void> {
  const token = await ensureSession();
  const r = await fetch(`${BASE}/api/auth/refresh`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    credentials: "include",
  });
  if (!r.ok) {
    // Refresh failing means the session is already dead; drop it so the next
    // call bootstraps cleanly instead of retrying a corpse.
    clearSession();
    throw new Error(String(r.status));
  }
  const body = (await r.json()) as { token: string };
  keepToken(body.token);
}

/** Revoke this session server-side, then forget it locally. */
export async function logout(): Promise<void> {
  const token = storedToken();
  if (token) {
    try {
      await fetch(`${BASE}/api/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        credentials: "include",
      });
    } catch {
      /* the network can fail; the local half of logout must still happen */
    }
  }
  clearSession();
}

/* ── Google sign-in ───────────────────────────────────────────────────── */

export type GoogleStart = {
  nonce: string;
  /** The OAuth client id, served BY THE BACKEND so there is one source of
   *  truth. Deliberately not a VITE_ env var: two copies of a client id drift,
   *  and the failure ("wrong audience") names neither of them. */
  client_id: string;
  expires_in: number;
};

export type GoogleSession = {
  token: string;
  user_id: string;
  expires_at: string;
  /** True when Google was just attached to the anonymous account in hand -
   *  i.e. the learner kept their history rather than starting over. */
  linked_now: boolean;
  providers: string[];
  email: string | null;
  display_name: string | null;
};

/** Distinguishable so the UI can say something true about what went wrong. */
export class GoogleSignInError extends Error {
  constructor(readonly status: number) {
    super(`google_sign_in_${status}`);
  }
  /** This Google account already belongs to a different Tilawah account. */
  get isConflict() {
    return this.status === 409;
  }
  /** The server has no Google client configured. */
  get isUnavailable() {
    return this.status === 503;
  }
}

/** Ask for a single-use nonce. 503 means Google is not configured here. */
export async function googleStart(): Promise<GoogleStart> {
  const r = await fetch(`${BASE}/api/auth/google/start`, {
    method: "POST",
    credentials: "include",
  });
  if (!r.ok) throw new GoogleSignInError(r.status);
  return r.json();
}

/**
 * Hand Google's ID token to the server, which links or signs in.
 *
 * DELIBERATELY NOT authedFetch. That wrapper reacts to a 401 by discarding the
 * session and bootstrapping a new one - which here would throw away the very
 * anonymous account we are trying to attach Google TO, and silently create a
 * fresh empty one instead. The current token is sent as-is or not at all.
 */
export async function googleSignIn(
  credential: string,
  nonce: string,
): Promise<GoogleSession> {
  const current = storedToken();
  const r = await fetch(`${BASE}/api/auth/google`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(current ? { Authorization: `Bearer ${current}` } : {}),
    },
    body: JSON.stringify({ credential, nonce }),
  });
  if (!r.ok) throw new GoogleSignInError(r.status);
  const body = (await r.json()) as GoogleSession;
  // The server rotated the session; the old token is already dead.
  keepToken(body.token);
  return body;
}

/* ── email / password sign-in ─────────────────────────────────────────────

   THE SAME SESSION SYSTEM AS GOOGLE. The server hands back the same opaque
   token from the same table, so everything below stores it with keepToken()
   and the rest of the app cannot tell which provider produced it.

   NO PASSWORD IS EVER STORED, LOGGED OR RETRIED HERE. It goes into one fetch
   body and out of scope. In particular it is never kept in order to "retry
   after refresh" — a stored password waiting for a second attempt is a
   password sitting in memory for as long as the tab is open. */

export type EmailSession = {
  token: string;
  user_id: string;
  expires_at: string;
  /** True when email was just attached to the anonymous account in hand —
   *  i.e. the learner kept their history rather than starting over. */
  linked_now: boolean;
  providers: string[];
  email: string | null;
  display_name: string | null;
  email_verified: boolean;
};

/** Registration that produced no session because the address needs confirming
 *  first. Distinguished from EmailSession by `verification_required`. */
export type Registered = {
  verification_required: true;
  email: string;
  /** Whether a message actually went out. False means no mail provider is
   *  wired on the server yet — see api/tilawah/mailer.py. */
  sent: boolean;
};

/**
 * A refused email-auth request, carrying the server's machine codes.
 *
 * CODES AND NOT SENTENCES. The server does not write the learner's error
 * message — it cannot, because the message has to arrive in Uzbek or Russian
 * depending on a preference this client owns. `code` and `problems` are stable
 * strings that i18n maps to real wording; nothing from the API is ever
 * rendered to a learner verbatim.
 */
export class EmailAuthError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly problems: string[] = [],
    readonly retryAfter = 0,
  ) {
    super(`email_auth_${code}`);
  }
}

async function emailAuth<T>(path: string, body: unknown): Promise<T> {
  // DELIBERATELY NOT authedFetch, for the same reason googleSignIn is not:
  // that wrapper reacts to a 401 by discarding the session and bootstrapping a
  // new one, which here would throw away the very anonymous account we are
  // trying to attach an email TO — and silently replace it with a fresh empty
  // one. The current token is sent as-is or not at all.
  const current = storedToken();
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(current ? { Authorization: `Bearer ${current}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!r.ok) {
    // The server's shape is {detail: {code, problems, retry_after}}. A 500 or
    // a proxy error page has neither, so anything unparseable becomes one
    // honest "something went wrong" rather than a crash inside a form.
    let code = "unknown";
    let problems: string[] = [];
    let retryAfter = 0;
    try {
      const d = (await r.json())?.detail;
      if (d && typeof d === "object") {
        code = String(d.code ?? "unknown");
        problems = Array.isArray(d.problems) ? d.problems.map(String) : [];
        retryAfter = Number(d.retry_after ?? 0);
      }
    } catch {
      /* keep the defaults */
    }
    throw new EmailAuthError(r.status, code, problems, retryAfter);
  }
  return r.json();
}

/**
 * Create an account, or attach email to the anonymous one already in hand.
 *
 * TWO POSSIBLE SUCCESS SHAPES and the caller must check which. With
 * verification required the server mints NO session and returns `Registered`;
 * otherwise it returns a full `EmailSession`. Reading `.token` off the first
 * would store `undefined` and log the learner out on the next request.
 */
export async function register(
  email: string,
  password: string,
  // A plain string, not the Lang union: this module imports NOTHING, and
  // pulling i18n in for one type would couple the wire layer to the copy
  // layer. The value is passed straight through to the server.
  lang: string,
): Promise<EmailSession | Registered> {
  const body = await emailAuth<EmailSession | Registered>("/api/auth/register", {
    email,
    password,
    lang,
  });
  if ("token" in body && body.token) keepToken(body.token);
  return body;
}

export async function login(
  email: string,
  password: string,
): Promise<EmailSession> {
  const body = await emailAuth<EmailSession>("/api/auth/login", {
    email,
    password,
  });
  // The server rotated the session; whatever token was held is already dead.
  keepToken(body.token);
  return body;
}

/**
 * Ask for a password reset link. ALWAYS RESOLVES on a reachable server, for
 * registered and unregistered addresses alike — the server deliberately gives
 * the same answer either way, so the UI must not imply it learned anything.
 */
export async function forgotPassword(email: string, lang: string): Promise<void> {
  await emailAuth<{ ok: boolean }>("/api/auth/forgot-password", { email, lang });
}

/** Send the confirmation link again. Same constant-response rule as above. */
export async function resendVerification(
  email: string,
  lang: string,
): Promise<void> {
  await emailAuth<{ ok: boolean }>("/api/auth/verification/resend", {
    email,
    lang,
  });
}

/** Confirm an address from a mailed link. Mints no session by design. */
export async function verifyEmail(token: string): Promise<void> {
  await emailAuth<{ ok: boolean }>("/api/auth/verify-email", { token });
}

/**
 * Set a new password from a mailed link.
 *
 * EVERY SESSION DIES WHEN THIS SUCCEEDS, including this browser's — that is
 * the point of a reset, and the reason the local token is dropped here rather
 * than left to fail on the next request.
 */
export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<void> {
  await emailAuth<{ ok: boolean }>("/api/auth/reset-password", {
    token,
    new_password: newPassword,
  });
  clearSession();
}

/** Who the current session belongs to. Shape mirrors MeOut on the server. */
export type Me = {
  user_id: string;
  lang: string;
  consented: boolean;
  audio_consented: boolean;
  consent_seen: boolean;
  is_anonymous: boolean;
  email: string | null;
  display_name: string | null;
  picture?: string;
  providers: string[];
  session_expires_at: string;
};

export const me = () => authedFetch(`/api/auth/me`).then(json<Me>);

/**
 * A request carrying the session, with ONE retry on 401.
 *
 * `makeInit` IS A FACTORY, NOT AN OBJECT, and that is not fussiness: a retry
 * has to build a fresh body. A FormData holding an audio Blob cannot reliably
 * be sent twice, and reusing a consumed body fails in a way that looks like the
 * upload silently vanishing.
 *
 * The 401 path is the whole point. A session expires after 30 days, is revoked
 * when the learner deletes their data, and dies if the server forgets it. In
 * every one of those cases the honest response is to get a new session and
 * carry on - the learner did nothing wrong and there is nothing to tell them.
 * Exactly one retry: if a fresh session is also refused, something is actually
 * broken and looping would only hide it.
 */
async function authedFetch(
  path: string,
  makeInit: () => RequestInit = () => ({}),
): Promise<Response> {
  const send = (token: string) => {
    const init = makeInit();
    return fetch(`${BASE}${path}`, {
      ...init,
      credentials: "include",
      headers: { ...(init.headers ?? {}), Authorization: `Bearer ${token}` },
    });
  };

  const used = await ensureSession();
  let r = await send(used);
  if (r.status === 401) {
    clearSessionIf(used);
    r = await send(await ensureSession());
  }
  return r;
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
  /**
   * "makki" | "madani" — where the sura was revealed, for the picker's filter
   * pills. Follows the designation printed in the standard Cairo mushaf; see
   * the provenance note in suras.json's `_meta`.
   *
   * MAY BE ABSENT OR EMPTY, from a server built before the column existed.
   * Treat that as unknown: such a sura matches neither Meccan nor Medinan and
   * is never sorted into one on a guess.
   */
  place?: string;
};

export const listSuras = () => fetch(`${BASE}/api/suras`).then(json<Sura[]>);

/**
 * Strip what a learner will not type: "Ali 'Imran" gets typed "ali imran".
 *
 * ʻ (U+02BB) and ʼ (U+02BC) are in this set because the Uzbek sura names use
 * the correct Uzbek letters — "Gʻofir", "Aʼrof" — and nobody has those on a
 * keyboard. THIS LIST MUST MATCH `STRIP` in api/tools/build_suras.py: that one
 * folds the haystack, this one folds the query, and if they disagree the two
 * are normalised differently and nine suras quietly stop being findable.
 */
export const foldQuery = (q: string) =>
  q.toLowerCase().replace(/['’`ʻʼ\-–—]/g, "").trim();

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

/**
 * This learner's recent attempts.
 *
 * `device_id` IS GONE FROM THE QUERY STRING and that is the single biggest
 * privacy win in this change. It used to be the authorization for this call,
 * which meant the credential was written into access logs, browser history,
 * referrer headers and every proxy on the path - by design, on every load. The
 * server now scopes the response to the session; there is nothing to send.
 */
export const history = (limit = 20) =>
  authedFetch(`/api/attempts?limit=${limit}`).then(json<Attempt[]>);

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
  /**
   * Tajweed rules that are STRUCTURALLY PRESENT in this range.
   *
   * Not errors. These say what the passage CONTAINS — a madd lozim is in
   * al-Baqara 1 whether or not the learner held it — so a flawless recitation
   * still shows what it just executed. Every entry in the error registry
   * describes a mistake and could only ever appear after a bad take; this is
   * the other half.
   */
  rules: RuleBadge[];
};

/**
 * One rule badge. Content is transcribed from the printed Uzbek Tajweed text
 * (see api/tilawah/content/rule_badges.json) — never generated.
 *
 * `reviewed` is the SERVER's decision and the only thing that may gate
 * display. A client that inferred the gate for itself would eventually infer
 * it wrong, which for religious instruction is the expensive direction.
 */
export type RuleBadge = {
  code: string;
  /** A palette token name, not a CSS colour. Resolved in index.css. */
  color: string;
  name: string;
  rule: string;
  example: string;
  /** Harakat count, as authored: "6", "4-5", "2, 4, 5". Free text on purpose. */
  target: string;
  source: string;
  reviewed: boolean;
  /**
   * Uthmani character ranges this rule governs, so the glyphs themselves can
   * be coloured rather than only named in the strip below the ayah.
   *
   * EMPTY IS A REAL ANSWER and means "present in this passage but not placed":
   * the idgham token-count proxy can tell that an assimilation happened but
   * not which letter did it. Draw nothing for those — never fall back to
   * colouring the whole word, which would claim a position the engine refused
   * to claim.
   */
  spans?: [number, number][];
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
  // Rebuilt per attempt, because a 401 retry needs a fresh body - the audio
  // Blob cannot be re-sent from a consumed FormData.
  const build = (): RequestInit => {
    const fd = new FormData();
    fd.append("audio", audio, "recitation.wav");
    fd.append("sura", String(sura));
    fd.append("aya", String(aya));
    fd.append("lang", lang);
    // No device_id. The attempt is filed for the session's user; naming an
    // account in a form field is what let anyone record against anyone.
    // Omitted or 0 means the whole ayah, so existing callers are unaffected.
    fd.append("start_word", String(range?.start_word ?? 0));
    fd.append("num_words", String(range?.num_words ?? 0));
    fd.append("include_bismillah", String(range?.include_bismillah ?? false));
    return { method: "POST", body: fd };
  };
  return authedFetch(`/api/attempts`, build).then(json<Attempt>);
}

export async function flagWrong(attemptId: number): Promise<void> {
  // The server now refuses an attempt that is not this learner's, with a 404
  // that is deliberately indistinguishable from "no such attempt".
  await authedFetch(`/api/attempts/${attemptId}/wrong`, () => ({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note: null }),
  }));
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

/**
 * FIELDS A STALE SERVER SILENTLY DROPS, detected from the payloads themselves.
 *
 * ── WHY THIS EXISTS, AND WHAT IT COST TO LEARN ────────────────────────────
 *
 * `staleApiFields` above only inspects what /api/meta DECLARES, and it only
 * covers the error object. That leaves a whole class of skew invisible: a
 * server process started before a column was added keeps answering 200s with a
 * well-formed payload that is simply missing a field, and every feature built
 * on that field degrades into looking broken rather than looking stale.
 *
 * Both of these were reported as bugs and neither was one:
 *
 *   suras.place      the Meccan/Medinan pills "did not filter". They filtered
 *                    perfectly against a field the running server had never
 *                    heard of.
 *   attempts.letters the hasanat counter "stayed at 0" after four recitations.
 *                    It summed a field that was not being sent.
 *
 * In both cases the fix was to restart the API, and in both cases the app gave
 * no hint of that. It does now.
 *
 * DETECTED FROM THE DATA, NOT FROM A VERSION STRING. A version number is a
 * promise about the payload; the payload is the payload. `some` rather than
 * `every` because one resolvable row is enough to prove the server knows the
 * field — a legitimately absent value on a single row is not skew.
 */
export function missingPayloadFields(
  suras: Sura[],
  rows: Attempt[] | null,
): string[] {
  const missing: string[] = [];
  if (suras.length > 0 && !suras.some((s) => s.place)) {
    missing.push("suras.place");
  }
  // `typeof === "number"` and not truthiness: a range that could not be
  // resolved contributes a real 0, and that must not read as a missing field.
  if (rows?.length && !rows.some((r) => typeof r.letters === "number")) {
    missing.push("attempts.letters");
  }
  return missing;
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
  await authedFetch(`/api/consent`, () => {
    const fd = new FormData();
    // No device_id: the server acts on the session's own account and nothing
    // else. This call can DESTROY every attempt and every stored recording,
    // and until now a form field chose whose.
    fd.append("consented", String(consented));
    fd.append("audio_consented", String(audioConsented));
    return { method: "POST", body: fd };
  });

  if (!consented) {
    // Declining consent hard-deletes the account, and the session cascades
    // away with it - the token in hand is already dead. Dropping it here means
    // the next call bootstraps a fresh anonymous session instead of spending a
    // round trip discovering the 401. The learner keeps using the app; there
    // is simply nothing left of what they asked to be forgotten.
    clearSession();
  }
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

/**
 * One named hadith, or null.
 *
 * For features that rest on a SPECIFIC narration rather than on the daily
 * rotation — the hasanat counter and its reward-per-letter claim. The claim and
 * its source travel together or neither is drawn: null here means the card
 * shows letters recited and makes no claim about reward, which needs no
 * citation because it asserts nothing.
 */
export const hadithById = (id: string, lang: string) =>
  fetch(`${BASE}/api/hadith/${encodeURIComponent(id)}?lang=${lang}`).then(
    json<Hadith | null>,
  );


// ── academy ─────────────────────────────────────────────────────────────

export type LessonSummary = {
  id: number;
  order: number;
  slug: string;
  difficulty: string;
  title_uz: string;
  title_ru: string;
  practice_sura: number;
  practice_aya: number;
  video_url: string | null;
  rule_codes: string[];
  status: "locked" | "available" | "completed";
  quiz_score: number | null;
  practice_done: boolean;
};

export type QuizQuestion = {
  id: number;
  order: number;
  question_uz: string;
  question_ru: string;
  options_uz: string[];
  options_ru: string[];
};

export type LessonDetail = {
  id: number;
  order: number;
  slug: string;
  difficulty: string;
  title_uz: string;
  title_ru: string;
  body_uz: string;
  body_ru: string;
  practice_sura: number;
  practice_aya: number;
  video_url: string | null;
  rule_codes: string[];
  pass_score: number;
  quiz: QuizQuestion[];
  status: "locked" | "available" | "completed";
  quiz_score: number | null;
  practice_done: boolean;
};

export type QuizResult = {
  score: number;
  passed: boolean;
  total: number;
  correct_count: number;
  results: {
    question_id: number;
    given: number;
    correct: number;
    is_correct: boolean;
    explanation_uz: string | null;
    explanation_ru: string | null;
  }[];
};

export const listLessons = () =>
  authedFetch("/api/lessons").then(json<LessonSummary[]>);

export const getLesson = (id: number) =>
  authedFetch(`/api/lessons/${id}`).then(json<LessonDetail>);

export async function submitQuiz(
  lessonId: number,
  answers: number[],
): Promise<QuizResult> {
  return authedFetch(`/api/lessons/${lessonId}/quiz`, () => ({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  })).then(json<QuizResult>);
}

export async function markPractice(lessonId: number): Promise<void> {
  await authedFetch(`/api/lessons/${lessonId}/practice`, () => ({
    method: "POST",
  }));
}
