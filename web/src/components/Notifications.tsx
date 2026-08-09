import { useEffect, useRef } from "react";
import { Lang, t } from "../lib/i18n";
import { NotificationRecord, unreadCount } from "../lib/notifications";
import { Bell, Close } from "./Ornament";

/**
 * THE BELL, AND THE LIST BEHIND IT.
 *
 * ── THE COUNT IS THE POINT OF THE BELL ─────────────────────────────────────
 *
 * A bell with no badge is a button whose whole job is to be pressed on the
 * off-chance. The badge appears only when something is unread and disappears
 * the moment the list is opened — which is also why opening marks everything
 * read rather than requiring a per-row tap: this list is three lines long on a
 * busy week, and asking someone to dismiss each one is inventing housework.
 *
 * ── AND IT SAYS WHAT IT CANNOT DO ──────────────────────────────────────────
 *
 * The footer states that reminders only appear here, in the app, and that
 * phone notifications are not connected yet. That sentence is not an apology
 * and it is not optional: a bell icon is a promise that the app will tell you
 * when something happens while you are away, and this one cannot keep that
 * promise yet. Saying so is cheaper than a learner missing a reminder and
 * concluding the goal feature is broken. See lib/notifications.ts for what
 * delivery still needs.
 */

export function BellButton({
  lang,
  rows,
  onOpen,
}: {
  lang: Lang;
  rows: NotificationRecord[];
  onOpen: () => void;
}) {
  const unread = unreadCount(rows);
  return (
    <button
      className="bell"
      onClick={onOpen}
      aria-label={
        unread > 0
          ? `${t(lang, "notif_open")} (${unread})`
          : t(lang, "notif_open")
      }
    >
      <Bell />
      {/* The number, not just a dot: "three things happened" and "something
          happened" are different messages, and the count is already known. */}
      {unread > 0 && (
        <span className="bell__badge" aria-hidden="true">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </button>
  );
}

export default function Notifications({
  lang,
  rows,
  onClose,
}: {
  lang: Lang;
  rows: NotificationRecord[];
  onClose: () => void;
}) {
  const panel = useRef<HTMLDivElement>(null);

  // Escape closes, and focus moves into the panel on open. A sheet that traps
  // neither is a sheet a keyboard user cannot leave.
  useEffect(() => {
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="sheet" role="presentation" onClick={onClose}>
      <div
        className="sheet__panel"
        role="dialog"
        aria-modal="true"
        aria-label={t(lang, "notif_title")}
        tabIndex={-1}
        ref={panel}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="sheet__head">
          <h2 className="sheet__title">{t(lang, "notif_title")}</h2>
          <button
            className="sheet__close"
            aria-label={t(lang, "notif_close")}
            onClick={onClose}
          >
            <Close />
          </button>
        </header>

        {rows.length === 0 ? (
          <div className="notif-empty">
            <span className="notif-empty__mark" aria-hidden="true">
              <Bell size={30} />
            </span>
            <p className="notif-empty__title">{t(lang, "notif_empty_title")}</p>
            <p className="notif-empty__body">{t(lang, "notif_empty_body")}</p>
          </div>
        ) : (
          <ul className="notif-list">
            {rows.map((n) => (
              <li
                key={n.id}
                className={`notif${n.readAt === null ? " notif--unread" : ""}`}
              >
                <p className="notif__title">{n.title}</p>
                <p className="notif__body">{n.body}</p>
                <p className="notif__when">{ago(lang, n.createdAt)}</p>
              </li>
            ))}
          </ul>
        )}

        <p className="sheet__note">{t(lang, "notif_delivery_note")}</p>
      </div>
    </div>
  );
}

/**
 * "12 daqiqa oldin". Relative, because the absolute time of a notification is
 * almost never what you want to know about it, and because a list of clock
 * times all reading 09:00 tells you nothing about which arrived today.
 */
function ago(lang: Lang, at: number): string {
  const mins = Math.max(0, Math.round((Date.now() - at) / 60000));
  if (mins < 1) return t(lang, "notif_now");
  if (mins < 60) return t(lang, "notif_min").replace("{n}", String(mins));
  const hours = Math.round(mins / 60);
  if (hours < 24) return t(lang, "notif_hour").replace("{n}", String(hours));
  return t(lang, "notif_day").replace("{n}", String(Math.round(hours / 24)));
}
