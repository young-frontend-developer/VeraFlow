import { useEffect, useMemo, useState } from "react";
import { Attempt, Reciter, Sura, history, setConsent } from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { Blank, Loading } from "./States";
import { StarOrnament } from "./Ornament";

/**
 * PROFILE — who this device is, what it has kept, and how to stop keeping it.
 *
 * THE AVATAR IS NOT A PHOTOGRAPH AND NEVER WILL BE. Initials in serif inside a
 * sage ring. The imagery rule that bans scholar headshots applies here too: a
 * Quran app should not attach a face to a person's recitation, and a stock
 * portrait standing in for the learner is the same category of mistake made
 * about them instead of about a teacher.
 *
 * THE DATA CONTROLS ARE THE POINT OF THE SCREEN, not a footer under it.
 * Consent is a plain-language toggle, audio is a separate one because storing
 * a record of what you recited is not the same as storing your voice, and
 * "delete everything" is a real action that really deletes — it is the same
 * call as revoking consent, which the server honours by dropping the rows.
 *
 * ADVANCED TAJWEED CONFIG IS COLLAPSED BY DEFAULT and, today, is honest about
 * being nearly empty: the only setting the engine truly has is which script the
 * text is in, and there is exactly one. See the Mushaf row.
 */

export default function Profile({
  lang,
  suras,
  reciters,
  reciter,
  consented,
  audioConsented,
  audioOffered,
  onReciter,
  onConsent,
  onLang,
}: {
  lang: Lang;
  suras: Sura[];
  reciters: Reciter[];
  reciter: string;
  consented: boolean;
  audioConsented: boolean;
  audioOffered: boolean;
  onReciter: (id: string) => void;
  onConsent: (v: boolean, audio: boolean) => void;
  onLang: (l: Lang) => void;
}) {
  const [rows, setRows] = useState<Attempt[] | null>(null);
  const [filter, setFilter] = useState<number | "all">("all");
  const [deleted, setDeleted] = useState(false);

  useEffect(() => {
    if (!consented) return setRows([]);
    history(60)
      .then(setRows)
      .catch(() => setRows(null));
  }, [consented]);

  /** Suras that actually appear in the history — never the whole catalogue. */
  const practised = useMemo(() => {
    const seen = new Set((rows ?? []).map((r) => r.sura));
    return suras.filter((s) => seen.has(s.number));
  }, [rows, suras]);

  const shown = (rows ?? []).filter(
    (r) => filter === "all" || r.sura === filter,
  );

  return (
    <>
      <div className="profile__head">
        {/* No image. Initials, or the app's own mark when there is no name —
            there are no accounts, so most of the time there is no name. */}
        <span className="avatar" aria-hidden="true">
          {t(lang, "profile_initials")}
        </span>
        <div>
          <p className="profile__name">{t(lang, "profile_name")}</p>
          <p className="profile__sub">{t(lang, "profile_sub")}</p>
        </div>
      </div>

      {/* ── history ──────────────────────────────────────────────────── */}
      <p className="section-label" style={{ margin: "0 0 12px" }}>
        {t(lang, "profile_history")}
      </p>

      {practised.length > 1 && (
        <div className="lang" style={{ marginBottom: 16, flexWrap: "wrap" }}>
          <button
            className="lang__btn"
            aria-current={filter === "all"}
            onClick={() => setFilter("all")}
          >
            {t(lang, "profile_all")}
          </button>
          {practised.map((s) => (
            <button
              key={s.number}
              className="lang__btn"
              aria-current={filter === s.number}
              onClick={() => setFilter(s.number)}
            >
              {s.translit}
            </button>
          ))}
        </div>
      )}

      {rows === null ? (
        <Loading rows={4} />
      ) : !consented ? (
        <Blank
          title={t(lang, "profile_off_title")}
          body={t(lang, "profile_off_body")}
        />
      ) : shown.length === 0 ? (
        <Blank
          title={t(lang, "profile_empty_title")}
          body={t(lang, "profile_empty_body")}
          ornament={<StarOrnament className="blank__ornament" size={40} />}
        />
      ) : (
        <ul className="list">
          {shown.map((r, i) => (
            <li className="log" key={r.id ?? i}>
              <span
                className={r.clean ? "log__dot log__dot--clear" : "log__dot"}
                aria-hidden="true"
              />
              <span className="log__text">
                {suras.find((s) => s.number === r.sura)?.translit ?? r.sura}{" "}
                {r.sura}:{r.aya}
              </span>
              <span className="log__meta">
                {r.status === "retry_recording"
                  ? t(lang, "log_retry")
                  : !r.analysable
                    ? t(lang, "log_unassessed")
                    : r.clean
                      ? t(lang, "log_clear")
                      : t(lang, "log_noted")}
              </span>
            </li>
          ))}
        </ul>
      )}

      {/* ── settings ─────────────────────────────────────────────────── */}
      <p className="section-label" style={{ margin: "38px 0 4px" }}>
        {t(lang, "profile_settings")}
      </p>

      <div className="setting">
        <span className="setting__label">{t(lang, "profile_lang")}</span>
        <span className="lang">
          {(["uz", "ru"] as const).map((code) => (
            <button
              key={code}
              className="lang__btn"
              aria-current={lang === code}
              onClick={() => onLang(code)}
            >
              {code === "uz" ? "Oʻz" : "Ру"}
            </button>
          ))}
        </span>
      </div>

      {reciters.length > 0 && (
        <div className="setting">
          <span className="setting__label">
            {t(lang, "reciter")}
            <span className="setting__help">{t(lang, "profile_reciter_help")}</span>
          </span>
          <select
            className="reciter__select"
            style={{ flex: "0 0 auto", maxWidth: 190 }}
            value={reciter}
            onChange={(e) => onReciter(e.target.value)}
          >
            {reciters.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* THE SCRIPT ROW NAMES WHAT IS IN USE RATHER THAN OFFERING A CHOICE.
          The engine computes its target, its segment offsets and every letter
          highlight from the Uthmani text; there is no second script in the
          data. A picker listing IndoPak or Warsh would either mis-place every
          mark or be a dead control, so this states the script plainly and says
          the others are not available yet. */}
      <div className="setting">
        <span className="setting__label">
          {t(lang, "profile_script")}
          <span className="setting__help">{t(lang, "profile_script_help")}</span>
        </span>
        <span className="setting__value">{t(lang, "profile_script_value")}</span>
      </div>

      <details className="disclosure">
        <summary className="disclosure__summary">
          {t(lang, "profile_advanced")}
          <span className="setting__value">+</span>
        </summary>
        <div className="disclosure__body">
          <p className="notice__body">{t(lang, "profile_advanced_body")}</p>
        </div>
      </details>

      {/* ── data ─────────────────────────────────────────────────────── */}
      <p className="section-label" style={{ margin: "38px 0 4px" }}>
        {t(lang, "profile_data")}
      </p>

      <label className="consent__row">
        <input
          type="checkbox"
          checked={consented}
          onChange={(e) => {
            const next = e.target.checked;
            // Revoking attempt consent revokes audio with it: there is no
            // coherent state where we keep the voice but not the record.
            const nextAudio = next && audioConsented;
            setConsent(next, nextAudio).catch(() => {});
            onConsent(next, nextAudio);
            if (!next) {
              setRows([]);
              setDeleted(true);
            }
          }}
        />
        <span>
          {t(lang, "consent_toggle")}
          <span className="consent__help">{t(lang, "consent_body")}</span>
        </span>
      </label>

      {audioOffered && (
        <label
          className={consented ? "consent__row" : "consent__row consent__row--off"}
        >
          <input
            type="checkbox"
            checked={audioConsented}
            disabled={!consented}
            onChange={(e) => {
              setConsent(consented, e.target.checked).catch(() => {});
              onConsent(consented, e.target.checked);
            }}
          />
          <span>
            {t(lang, "consent_audio_label")}
            <span className="consent__help">{t(lang, "consent_audio_help")}</span>
          </span>
        </label>
      )}

      <button
        className="setting setting__danger"
        onClick={() => {
          setConsent(false, false).catch(() => {});
          onConsent(false, false);
          setRows([]);
          setDeleted(true);
        }}
      >
        <span className="setting__label setting__danger">
          {t(lang, "profile_delete")}
          <span className="setting__help">{t(lang, "profile_delete_help")}</span>
        </span>
      </button>

      {deleted && !consented && (
        <p className="notice__body" style={{ marginTop: 14 }}>
          {t(lang, "consent_delete")}
        </p>
      )}
    </>
  );
}
