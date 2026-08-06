import { Lang, t, Key } from "../lib/i18n";
import { StarOrnament } from "./Ornament";

/**
 * Loading, empty and error — designed once, used on every screen.
 *
 * These are the states a product shows most often and designs last, which is
 * how an otherwise careful app ends up with a spinner from one era and a toast
 * from another. Sharing them is what keeps the system honest at the edges:
 * there is no way to add a screen and forget what it looks like with no data.
 *
 * NONE OF THEM APOLOGISE OR ALARM. An empty list is not a failure, a wait is
 * not a hang, and a network error after a long analysis is a thing that
 * happened rather than something the learner did.
 */

/**
 * A loading list, shaped like the content it stands in for.
 *
 * Skeleton lines rather than a spinner: a spinner says "something is
 * happening", a skeleton says "this is what is coming, and roughly how much" —
 * and the layout does not jump when the real rows land.
 */
export function Loading({ rows = 5 }: { rows?: number }) {
  return (
    <div className="skeleton" role="status" aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <span
          key={i}
          className="skeleton__line"
          // Ragged widths. Equal bars read as a progress chart rather than as
          // text that has not arrived.
          style={{ width: `${[92, 74, 86, 62, 80, 70][i % 6]}%` }}
        />
      ))}
    </div>
  );
}

/**
 * Nothing here yet — and that is a legitimate state, given the same care as a
 * full screen. An ornament, one serif line, one quiet sentence, and only the
 * action that actually resolves it.
 */
export function Blank({
  title,
  body,
  action,
  onAction,
  ornament,
}: {
  title: string;
  body: string;
  action?: string;
  onAction?: () => void;
  ornament?: React.ReactNode;
}) {
  return (
    <div className="blank">
      {ornament ?? <StarOrnament className="blank__ornament" size={40} />}
      <p className="blank__title">{title}</p>
      <p className="blank__body">{body}</p>
      {action && onAction && (
        <div className="blank__actions">
          <button className="btn-quiet" onClick={onAction}>
            {action}
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Something went wrong. Says what, says what to do, and offers the one control
 * that might fix it.
 *
 * `retryKey`/`onRetry` are optional because not every failure is retryable, and
 * offering a retry that cannot help is worse than offering none.
 */
export function Failure({
  lang,
  title,
  body,
  retryKey = "retry_again",
  onRetry,
  tone = "plain",
}: {
  lang: Lang;
  title: string;
  body: string;
  retryKey?: Key;
  onRetry?: () => void;
  /** `warm` for a failure the learner should not read as their fault. */
  tone?: "plain" | "warm";
}) {
  return (
    <div className={tone === "warm" ? "notice notice--warm" : "notice"} role="alert">
      <p className="notice__title">{title}</p>
      <p className="notice__body">{body}</p>
      {onRetry && (
        <div className="actions">
          <button className="btn-quiet" onClick={onRetry}>
            {t(lang, retryKey)}
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * THE LONG WAIT, when it is not happening inside the dark recording card.
 *
 * Inference runs around ten times realtime, so this can sit past fifteen
 * seconds. What that length needs is not a faster-looking spinner but a
 * sentence that sets the expectation, so the wait reads as work rather than as
 * a stall.
 */
export function Waiting({ lang }: { lang: Lang }) {
  return (
    <p className="waiting" role="status" aria-live="polite">
      {t(lang, "waiting")}
      <span className="waiting__hint">{t(lang, "waiting_hint")}</span>
    </p>
  );
}
