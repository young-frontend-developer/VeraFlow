/**
 * NOTIFICATION RECORDS — the store and the read/unread state.
 *
 * ══ WHAT THIS IS NOT ═══════════════════════════════════════════════════════
 *
 * THERE IS NO DELIVERY HERE. Nothing in this file rings a phone, raises a
 * system banner, wakes a service worker or talks to a push service. It is the
 * record layer only: notifications exist, they are stored, they are read, and
 * the bell shows how many have not been.
 *
 * That boundary is deliberate and it is the honest one to ship first. Real
 * delivery needs, in this order: a permission prompt the learner can decline
 * and never be asked again; a service worker; either the browser Push API with
 * VAPID keys or platform tokens if this is ever wrapped for a store; and a
 * server-side scheduler, because a web page that is closed cannot fire its own
 * reminder — the whole point of a reminder is that it arrives when you are not
 * already in the app. None of that is built.
 *
 * WHAT IS NOT DONE INSTEAD: a `setTimeout` that raises a toast while the tab
 * happens to be open, and a bell that fills up with it. That would look like a
 * working reminder system to everyone including the next person to read this,
 * and it would silently do nothing for the case reminders exist for. A goal's
 * reminder time is STORED (see lib/goals.ts) so the scheduler can be attached
 * later without touching the goal feature; until then the panel says plainly
 * that reminders only appear inside the app.
 *
 * ══ WHERE RECORDS COME FROM ════════════════════════════════════════════════
 *
 * `push()` is the only writer, and it is called from app code when something
 * has genuinely happened — a goal saved, a goal reached. It is NOT called on a
 * timer to make the panel look inhabited. An empty bell on a new device is the
 * true state and it is drawn as one.
 *
 * ══ STORAGE ════════════════════════════════════════════════════════════════
 *
 * localStorage, device-local, same as the journey and the level. No consent
 * question attached: these are the learner's own actions reflected back at
 * them, they never leave the device, and nothing here is recitation data.
 */

const KEY = "tilawah_notifications";

/**
 * How many to keep. A notification list is not a log — past about twenty the
 * oldest entries are never read again, and an unbounded array in localStorage
 * is a quota error waiting for the learner who uses the app for a year.
 */
const CAP = 40;

export type NotificationKind = "goal_set" | "goal_reminder" | "goal_reached";

export type NotificationRecord = {
  id: string;
  kind: NotificationKind;
  /** Already-resolved display text. See the note below on why. */
  title: string;
  body: string;
  /** Epoch ms. Absolute, so a stored record does not drift with the clock. */
  createdAt: number;
  /** Epoch ms when it was read, or null while unread. */
  readAt: number | null;
  /** The goal this came from, when it came from one. */
  goalId?: string;
};

/**
 * WHY THE TEXT IS STORED RESOLVED RATHER THAN AS A KEY PLUS ARGUMENTS.
 *
 * The alternative is tidier: store `{kind, goalId}` and render through i18n at
 * display time, so switching language re-labels the history. It is also wrong
 * here — a record says what the app told you at the time, and a goal that has
 * since been edited or deleted would re-render its old notification with the
 * new goal's wording, or with a blank where the goal used to be. The text is
 * part of the record.
 *
 * The cost is real and accepted: notifications received in Uzbek stay in Uzbek
 * after a switch to Russian. New ones arrive in the new language.
 */
export function read(): NotificationRecord[] {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    if (!Array.isArray(raw)) return [];
    return raw.filter(isRecord).sort((a, b) => b.createdAt - a.createdAt);
  } catch {
    // A corrupt store is not worth a crash on the first screen. The learner
    // loses a list they were not relying on; the app keeps working.
    return [];
  }
}

function isRecord(v: unknown): v is NotificationRecord {
  const r = v as NotificationRecord;
  return (
    !!r &&
    typeof r.id === "string" &&
    typeof r.title === "string" &&
    typeof r.body === "string" &&
    typeof r.createdAt === "number" &&
    (r.readAt === null || typeof r.readAt === "number")
  );
}

function write(rows: NotificationRecord[]): NotificationRecord[] {
  const kept = rows.slice(0, CAP);
  try {
    localStorage.setItem(KEY, JSON.stringify(kept));
  } catch {
    // Quota, or storage disabled. Nothing to recover and nothing to say — the
    // list is a convenience, not a record the learner is owed.
  }
  return kept;
}

/** Record something that has happened. Returns the new list. */
export function push(
  n: Omit<NotificationRecord, "id" | "createdAt" | "readAt">,
): NotificationRecord[] {
  return write([
    { ...n, id: newId(), createdAt: Date.now(), readAt: null },
    ...read(),
  ]);
}

export function markAllRead(): NotificationRecord[] {
  const now = Date.now();
  return write(read().map((n) => (n.readAt ? n : { ...n, readAt: now })));
}

export function markRead(id: string): NotificationRecord[] {
  const now = Date.now();
  return write(read().map((n) => (n.id === id || n.readAt ? n : { ...n, readAt: now })));
}

/** Every notification a given goal produced, dropped with the goal. */
export function dropForGoal(goalId: string): NotificationRecord[] {
  return write(read().filter((n) => n.goalId !== goalId));
}

export const unreadCount = (rows: NotificationRecord[]) =>
  rows.filter((n) => n.readAt === null).length;

const newId = () =>
  `n_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
