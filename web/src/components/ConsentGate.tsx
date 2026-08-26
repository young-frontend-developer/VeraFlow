import { useState } from "react";
import { Lang, t } from "../lib/i18n";

/**
 * First-run data choice. Shown before the app is usable, once per device.
 *
 * Both boxes start UNCHECKED and the decline path is a real, equally weighted
 * option — declining costs the learner nothing but history. Retention is not
 * the price of using the app, and a consent screen that nudges is not consent.
 *
 * Audio is asked separately from attempt history because they are different
 * things: one keeps a record of what you recited, the other keeps a recording
 * of your voice. Granting the first must never imply the second.
 */
export default function ConsentGate({
  lang,
  audioOffered,
  onDecide,
}: {
  lang: Lang;
  /** Whether the server is collecting audio at all (TILAWAH_COLLECT_AUDIO). */
  audioOffered: boolean;
  onDecide: (consented: boolean, audioConsented: boolean) => void;
}) {
  const [attempts, setAttempts] = useState(false);
  const [audio, setAudio] = useState(false);

  return (
    <div className="gate" role="dialog" aria-modal="true">
      <div className="gate__panel">
        <h2 className="gate__title">{t(lang, "consent_gate_title")}</h2>
        <p className="gate__intro">{t(lang, "consent_gate_intro")}</p>

        <div className="gate__none">
          <p className="gate__none-title">{t(lang, "consent_gate_none_title")}</p>
          <p className="gate__none-body">{t(lang, "consent_gate_none_body")}</p>
        </div>

        <label className="gate__opt">
          <input
            type="checkbox"
            checked={attempts}
            onChange={(e) => {
              setAttempts(e.target.checked);
              // Audio consent cannot outlive attempt consent, so untick it too
              // rather than leave an impossible combination selected.
              if (!e.target.checked) setAudio(false);
            }}
          />
          <span>
            <span className="gate__opt-label">
              {t(lang, "consent_attempts_label")}
            </span>
            <span className="gate__opt-help">
              {t(lang, "consent_attempts_help")}
            </span>
          </span>
        </label>

        {audioOffered && (
          <label className={attempts ? "gate__opt" : "gate__opt gate__opt--off"}>
            <input
              type="checkbox"
              checked={audio}
              disabled={!attempts}
              onChange={(e) => setAudio(e.target.checked)}
            />
            <span>
              <span className="gate__opt-label">
                {t(lang, "consent_audio_label")}
              </span>
              <span className="gate__opt-help">
                {t(lang, "consent_audio_help")}
              </span>
            </span>
          </label>
        )}

        <div className="gate__actions">
          <button
            className={attempts ? "gate__primary" : "gate__primary gate__primary--muted"}
            onClick={() => onDecide(attempts, audio)}
          >
            {t(lang, attempts ? "consent_gate_accept" : "consent_gate_skip")}
          </button>
          <button className="gate__quiet" onClick={() => onDecide(false, false)}>
            {t(lang, "consent_gate_skip")}
          </button>
        </div>

        <p className="gate__footer">{t(lang, "consent_gate_footer")}</p>
      </div>
    </div>
  );
}
