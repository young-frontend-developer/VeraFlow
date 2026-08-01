import { useEffect, useMemo, useState } from "react";
import {
  ReviewEntry,
  ReviewQueue,
  ReviewUz,
  UZ_FIELDS,
  reviewDecide,
  reviewQueue,
} from "../lib/api";

/**
 * Qori review tool, served at /review.
 *
 * One entry per screen, deliberately. A reviewer signing off rulings about the
 * Quran should be reading one thing at a time; a scrolling table invites
 * skimming, and skimming is exactly the failure this gate exists to prevent.
 *
 * The Uzbek is rendered in the learner's own card, not as form fields, because
 * what is being approved is what a learner will actually read. Edit mode swaps
 * to textareas and back.
 *
 * Not translated. The reviewer is an Uzbek-speaking qori and the chrome is
 * Uzbek; this screen never reaches a learner and has no language toggle.
 */

const REVIEWER_KEY = "tilawah_reviewer";

const LABELS: Record<string, string> = {
  name: "Nomi",
  short: "Qisqacha",
  nima_xato: "Nima xato",
  qoida: "Qoida",
  nega_muhim: "Nega muhim",
  tuzatish: "Tuzatish",
  mashq: "Mashq",
};

export default function Review() {
  const [queue, setQueue] = useState<ReviewQueue | null>(null);
  const [at, setAt] = useState(0);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<ReviewUz>({});
  const [reviewer, setReviewer] = useState(
    () => localStorage.getItem(REVIEWER_KEY) ?? "",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    reviewQueue()
      .then((q) => {
        setQueue(q);
        // Open on the first entry still needing a decision, so reopening the
        // tool resumes rather than restarting.
        const next = q.entries.findIndex((e) => e.status === "draft");
        setAt(next === -1 ? 0 : next);
      })
      .catch(() =>
        setLoadError(
          "Ro'yxatni yuklab bo'lmadi. Server ishlayotganini tekshiring " +
            "(review tool production'da o'chirilgan).",
        ),
      );
  }, []);

  useEffect(() => {
    localStorage.setItem(REVIEWER_KEY, reviewer);
  }, [reviewer]);

  const entry: ReviewEntry | undefined = queue?.entries[at];

  // Reset the editor whenever the entry changes, or an unsaved edit would leak
  // onto the next code.
  useEffect(() => {
    setEditing(false);
    setDraft({});
    setError("");
  }, [entry?.code]);

  const progress = useMemo(() => {
    if (!queue) return "";
    return `${queue.reviewed} / ${queue.total} ko'rib chiqildi`;
  }, [queue]);

  function replace(updated: ReviewEntry) {
    setQueue((q) => {
      if (!q) return q;
      const entries = q.entries.map((e) =>
        e.code === updated.code ? updated : e,
      );
      return {
        ...q,
        entries,
        reviewed: entries.filter((e) => e.status === "reviewed").length,
        rejected: entries.filter((e) => e.status === "rejected").length,
        remaining: entries.filter((e) => e.status === "draft").length,
      };
    });
  }

  async function decide(action: "approve" | "reject" | "edit" | "reset") {
    if (!entry) return;
    setBusy(true);
    setError("");
    try {
      const updated = await reviewDecide(entry.code, action, {
        reviewed_by: reviewer,
        uz: action === "edit" ? draft : {},
      });
      replace(updated);
      if (action === "edit") {
        setEditing(false);
        setDraft({});
      } else if (action !== "reset") {
        // Advance only on a decision. Staying put after approving would make
        // the reviewer click twice for every entry.
        setAt((i) => Math.min(i + 1, (queue?.entries.length ?? 1) - 1));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <div className="review">
        <p className="review__error">{loadError}</p>
      </div>
    );
  }
  if (!queue || !entry) {
    return (
      <div className="review">
        <p className="empty">Yuklanmoqda</p>
      </div>
    );
  }

  const uz = entry.uz ?? {};
  const edited = new Set(entry.uz_edited_fields ?? []);

  return (
    <div className="review">
      <header className="review__bar">
        <span className="review__progress">{progress}</span>
        <span className="review__counts">
          {entry.status === "rejected" || queue.rejected > 0
            ? `${queue.rejected} rad etildi · `
            : ""}
          {queue.remaining} qoldi
        </span>
        <input
          className="review__who"
          value={reviewer}
          placeholder="Ismingiz"
          aria-label="Ko'rib chiquvchi ismi"
          onChange={(e) => setReviewer(e.target.value)}
        />
      </header>

      <div
        className="review__meter"
        role="progressbar"
        aria-valuenow={queue.reviewed}
        aria-valuemin={0}
        aria-valuemax={queue.total}
      >
        <span
          className="review__meter-fill"
          style={{ width: `${(queue.reviewed / queue.total) * 100}%` }}
        />
      </div>

      {queue.ranking_stale && (
        <p className="review__warn">
          Chastota reytingi eskirgan — ba'zi yozuvlar tartibda yo'q.
          <code> tools/rank_error_frequency.py </code> ni qayta ishga tushiring.
        </p>
      )}

      <nav className="review__nav">
        <button disabled={at === 0} onClick={() => setAt((i) => i - 1)}>
          ← Oldingi
        </button>
        <span className="review__pos">
          #{entry.review_order} · {at + 1} / {queue.entries.length}
        </span>
        <button
          disabled={at >= queue.entries.length - 1}
          onClick={() => setAt((i) => i + 1)}
        >
          Keyingi →
        </button>
      </nav>

      <p className="review__reach">
        <code>{entry.code}</code> · {entry.group} · {entry.severity} ·
        boshlovchilarda {entry.beginner_pct}% · umumiy {entry.all_pct}%
      </p>

      {entry.source_ref ? (
        <p className="review__source">Manba: {entry.source_ref}</p>
      ) : (
        <p className="review__source review__source--missing">
          Manba ko'rsatilmagan
        </p>
      )}

      <StatusChip entry={entry} />

      {editing ? (
        <div className="review__edit">
          {UZ_FIELDS.map((f) => (
            <label key={f} className="review__field">
              <span className="review__field-label">{LABELS[f]}</span>
              <textarea
                rows={f === "name" || f === "short" ? 2 : 4}
                value={draft[f] ?? uz[f] ?? ""}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, [f]: e.target.value }))
                }
              />
            </label>
          ))}
          <div className="review__actions">
            <button
              className="btn-primary"
              disabled={busy}
              onClick={() => decide("edit")}
            >
              Saqlash
            </button>
            <button
              className="btn-quiet"
              disabled={busy}
              onClick={() => {
                setEditing(false);
                setDraft({});
              }}
            >
              Bekor qilish
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* The learner's own card. This is the thing being approved. */}
          <article className="card card--lit review__preview">
            <h3 className="card__rule">{uz.name || entry.code}</h3>
            {uz.short && <p className="card__said">{uz.short}</p>}
            {(["nima_xato", "qoida", "nega_muhim", "tuzatish", "mashq"] as const).map(
              (f) =>
                uz[f] ? (
                  <div key={f}>
                    <p className="card__label">
                      {LABELS[f]}
                      {edited.has(f) && (
                        <span className="review__edited"> tahrirlangan</span>
                      )}
                    </p>
                    <p className="card__body">{uz[f]}</p>
                  </div>
                ) : null,
            )}
          </article>

          {error && <p className="review__error">{error}</p>}

          <div className="review__actions">
            <button
              className="btn-primary"
              disabled={busy}
              onClick={() => decide("approve")}
            >
              Tasdiqlash
            </button>
            <button
              className="btn-quiet"
              disabled={busy}
              onClick={() => {
                setDraft({ ...uz });
                setEditing(true);
              }}
            >
              Tahrirlash
            </button>
            <button
              className="btn-quiet review__reject"
              disabled={busy}
              onClick={() => decide("reject")}
            >
              Rad etish
            </button>
          </div>

          {entry.status !== "draft" && (
            <button
              className="linkish"
              disabled={busy}
              onClick={() => decide("reset")}
            >
              Qarorni bekor qilish
            </button>
          )}
        </>
      )}
    </div>
  );
}

function StatusChip({ entry }: { entry: ReviewEntry }) {
  if (entry.status === "draft") {
    return <p className="review__status">Hali ko'rib chiqilmagan</p>;
  }
  const word = entry.status === "reviewed" ? "Tasdiqlangan" : "Rad etilgan";
  return (
    <p
      className={
        entry.status === "reviewed"
          ? "review__status review__status--ok"
          : "review__status review__status--no"
      }
    >
      {word}
      {entry.reviewed_by && ` — ${entry.reviewed_by}`}
      {entry.reviewed_at && ` · ${entry.reviewed_at.slice(0, 10)}`}
    </p>
  );
}
