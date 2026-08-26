import { ReactNode, useEffect, useMemo, useState } from "react";
import { Attempt, Me, Reciter, Sura, history } from "../lib/api";
import { Key, Lang, t } from "../lib/i18n";
import { LEVEL_LABEL, Level, storeLevel, storedLevel } from "../lib/level";
import { Theme } from "../lib/theme";
import Achievements from "./Achievements";
import { award, signalsFrom } from "../lib/achievements";
import { hasJourney, storedJourney } from "../lib/journey";
import { Blank, Loading } from "./States";
import {
  Bin,
  Contrast,
  Globe,
  Info,
  Log,
  Script,
  Shield,
  StarOrnament,
  Target,
  Voice,
} from "./Ornament";

/**
 * PROFILE — who this device is, what it has kept, and how to stop keeping it.
 *
 * ── GROUPED, THE WAY EVERY PHONE ALREADY DOES IT ───────────────────────────
 *
 * This screen was one continuous scroll: avatar, achievement wall, level
 * picker, history, then eight settings and two consent checkboxes in a single
 * run, held apart by inline margins. Nothing was grouped, so nothing could be
 * scanned — finding "delete everything" meant reading past the reciter picker.
 *
 * It is now four named groups, each a card of rows, each row a leading mark, a
 * label and a trailing value or control:
 *
 *   Hisob        the device's standing, the practice log, the level setting
 *   Sozlamalar   language, appearance, reciter
 *   Maxfiylik    the two consents, and the deletion
 *   Ilova haqida the script in use, and what is not configurable yet
 *
 * The pattern is deliberately the system-settings one. It is worth copying
 * PRECISELY BECAUSE IT IS NOT NOVEL: a learner has used it in every app on
 * their phone, so the organisation costs them nothing to read. Only the shape
 * is borrowed — the glass card, the brass hairline, the serif and the emerald
 * selection state are all this app's own and unchanged.
 *
 * A ROW WITH A CHEVRON OPENS SOMETHING. A row that merely reports a value does
 * not get one. That is the one rule in this pattern people break, and a chevron
 * pointing at nothing is a control that lies.
 *
 * THE AVATAR IS NOT A PHOTOGRAPH AND NEVER WILL BE. Initials in serif inside a
 * sage ring. The imagery rule that bans scholar headshots applies here too: a
 * Quran app should not attach a face to a person's recitation, and a stock
 * portrait standing in for the learner is the same category of mistake made
 * about them instead of about a teacher.
 *
 * THE DATA CONTROLS ARE THE POINT OF THE SCREEN, not a footer under it. That is
 * why Privacy is its own named group rather than a run of checkboxes: consent
 * is a plain-language toggle, audio is a separate one because storing a record
 * of what you recited is not the same as storing your voice, and "delete
 * everything" is a real action that really deletes — the same call as revoking
 * consent, which the server honours by dropping the rows.
 */

/** One group: a header, then a card of rows. */
function Group({
  lang,
  title,
  children,
}: {
  lang: Lang;
  title: Key;
  children: ReactNode;
}) {
  return (
    <section className="settings-group">
      <p className="section-label settings-group__head">{t(lang, title)}</p>
      <div className="card settings-card">{children}</div>
    </section>
  );
}

/**
 * One row. `control` is the trailing element — a segmented picker, a select, or
 * a plain value. There is no chevron prop: nothing on this screen navigates
 * anywhere yet, and a decorative one would be the lie described above.
 */
function Row({
  mark,
  label,
  help,
  control,
  danger,
}: {
  mark: ReactNode;
  label: string;
  help?: string;
  control?: ReactNode;
  danger?: boolean;
}) {
  return (
    <div className="setting">
      <span className={danger ? "setting__mark setting__mark--danger" : "setting__mark"}>
        {mark}
      </span>
      <span className="setting__body">
        <span className={danger ? "setting__label setting__danger" : "setting__label"}>
          {label}
        </span>
        {help && <span className="setting__help">{help}</span>}
      </span>
      {control}
    </div>
  );
}

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
  theme,
  onTheme,
  meData,
  onLogout,
  onSignIn,
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
  theme: Theme;
  onTheme: (t: Theme) => void;
  /** Current user identity from /api/auth/me. Null while loading or on error. */
  meData: Me | null;
  /** Revoke the current session and return to the auth screen. */
  onLogout: () => Promise<void>;
  /** Navigate to the auth screen to sign in or register. */
  onSignIn: () => void;
}) {
  const [rows, setRows] = useState<Attempt[] | null>(null);
  const [level, setLevel] = useState<Level | null>(() => storedLevel());
  const [filter, setFilter] = useState<number | "all">("all");
  const [deleted, setDeleted] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

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
        {/* If the user has a profile picture from Google, show it. Otherwise fallback to the initials mark. */}
        {meData && !meData.is_anonymous && meData.picture ? (
          <img src={meData.picture} alt="" className="avatar" style={{ objectFit: "cover" }} />
        ) : (
          <span className="avatar" aria-hidden="true">
            {t(lang, "profile_initials")}
          </span>
        )}
        <div>
          <p className="profile__name">
            {meData && !meData.is_anonymous && meData.display_name
              ? meData.display_name
              : t(lang, "profile_name")}
          </p>
          <p className="profile__sub">
            {meData && !meData.is_anonymous
              ? meData.email ?? (meData.providers.includes("google")
                ? t(lang, "profile_provider_google")
                : t(lang, "profile_provider_email"))
              : t(lang, "profile_sub")}
          </p>
        </div>
      </div>

      {/* ── the full achievement wall ────────────────────────────────────
             HOME ONLY EVER GETS A PREVIEW. The complete set lives here, where
             looking at it is a thing the learner chose to do rather than
             something waiting on the screen they open every day.

             ABOVE THE GROUPS, NOT IN ONE. It is not a setting and it is not a
             row; putting it in a card of rows would make it look adjustable. */}
      <div style={{ marginBottom: 30 }}>
        <Achievements
          lang={lang}
          items={award(
            signalsFrom(
              rows ?? [],
              Object.fromEntries(suras.map((s) => [s.number, s.n_ayat])),
              { hasJourney: hasJourney(storedJourney()) },
            ),
          )}
        />
      </div>

      {/* ── ACCOUNT ─────────────────────────────────────────────────────
             The level setting lives here rather than under Preferences
             because it describes the person, not the app's behaviour. It is a
             SETTING, not a status: it appears on this screen and nowhere else.
             A learner told daily that they are a "beginner" is being handed an
             identity by software that has heard them recite once. */}
      <Group lang={lang} title="profile_group_account">
        {/* ── AUTH STATUS. Shows who is signed in, or a prompt to sign in. ─
               This is the primary purpose of the Account group now that real
               auth exists. The level setting follows it as a secondary item. */}
        {meData && !meData.is_anonymous ? (
          <>
            {/* Signed-in state: show email/provider + logout button */}
            <Row
              mark={<Shield size={18} />}
              label={t(lang, "profile_signed_in_as")}
              help={
                meData.email ??
                (meData.providers.includes("google")
                  ? t(lang, "profile_provider_google")
                  : meData.providers.includes("email")
                    ? t(lang, "profile_provider_email")
                    : meData.providers[0] ?? "")
              }
            />
            <button
              className="setting"
              disabled={loggingOut}
              onClick={async () => {
                setLoggingOut(true);
                try {
                  await onLogout();
                } finally {
                  setLoggingOut(false);
                }
              }}
            >
              <span className="setting__mark setting__mark--danger">
                <Shield size={18} />
              </span>
              <span className="setting__body">
                <span className="setting__label setting__danger">
                  {loggingOut ? t(lang, "auth_working") : t(lang, "profile_logout")}
                </span>
                <span className="setting__help">{t(lang, "profile_logout_help")}</span>
              </span>
            </button>
          </>
        ) : (
          /* Anonymous or not yet loaded — show sign-in button */
          <>
            <Row
              mark={<Shield size={18} />}
              label={t(lang, "profile_anon_label")}
              help={t(lang, "profile_anon_help")}
            />
            <button
              className="setting"
              style={{ borderBottom: "none" }}
              onClick={onSignIn}
            >
              <span className="setting__mark">
                <Shield size={18} />
              </span>
              <span className="setting__body">
                <span className="setting__label">{t(lang, "profile_sign_in")}</span>
                <span className="setting__help">{t(lang, "profile_sign_in_help")}</span>
              </span>
            </button>
          </>
        )}
        <Row
          mark={<Target size={18} />}
          label={t(lang, "level_setting")}
          help={t(lang, "level_setting_note")}
          control={
            <span className="lang setting__control">
              {(["beginner", "intermediate", "advanced"] as Level[]).map((lv) => (
                <button
                  key={lv}
                  className="lang__btn"
                  aria-current={level === lv}
                  onClick={() => {
                    storeLevel(lv);
                    setLevel(lv);
                  }}
                >
                  {t(lang, LEVEL_LABEL[lv] as never)}
                </button>
              ))}
            </span>
          }
        />
      </Group>

      {/* ── PREFERENCES ─────────────────────────────────────────────────── */}
      <Group lang={lang} title="profile_group_prefs">
        {/* LANGUAGE LIVES HERE AND ONLY HERE once the app is running. It is
            also the first question of the entry flow, which is a different
            moment: asked once when it decides every screen that follows, and
            changeable ever after from exactly one place. */}
        <Row
          mark={<Globe size={18} />}
          label={t(lang, "profile_lang")}
          control={
            <span className="lang setting__control">
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
          }
        />

        {/* APPEARANCE. Two named times of day rather than a "dark mode"
            switch: both are designed systems and neither is the other one
            dimmed, so neither gets to be the off position of the other.
            THE LEARNER DECIDES, NOT THE PHONE — what is chosen here holds
            whatever the device is set to, and holds across launches. */}
        <Row
          mark={<Contrast size={18} />}
          label={t(lang, "theme_label")}
          help={t(lang, "theme_help")}
          control={
            <span className="lang setting__control">
              {(["dark", "light"] as const).map((mode) => (
                <button
                  key={mode}
                  className="lang__btn"
                  aria-current={theme === mode}
                  onClick={() => onTheme(mode)}
                >
                  {t(lang, mode === "dark" ? "theme_dark" : "theme_light")}
                </button>
              ))}
            </span>
          }
        />

        {reciters.length > 0 && (
          <Row
            mark={<Voice size={18} />}
            label={t(lang, "reciter")}
            help={t(lang, "profile_reciter_help")}
            control={
              <select
                className="reciter__select"
                style={{ flex: "0 0 auto", maxWidth: 170 }}
                value={reciter}
                onChange={(e) => onReciter(e.target.value)}
              >
                {reciters.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            }
          />
        )}
      </Group>

      {/* ── PRIVACY ─────────────────────────────────────────────────────
             Its own named group, at the same weight as everything else rather
             than buried at the bottom of a scroll. */}
      <Group lang={lang} title="profile_group_privacy">
        <label className="consent__row">
          <input
            type="checkbox"
            checked={consented}
            onChange={(e) => {
              const next = e.target.checked;
              const nextAudio = next && audioConsented;
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
            className={
              consented ? "consent__row" : "consent__row consent__row--off"
            }
          >
            <input
              type="checkbox"
              checked={audioConsented}
              disabled={!consented}
              onChange={(e) => {
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
          className="setting"
          style={{ borderBottom: "none" }}
          onClick={() => {
            if (!confirm(t(lang, "profile_delete_confirm" as Key) || "Delete all practice data? This cannot be undone.")) return;
            onConsent(false, false);
            setRows([]);
            setDeleted(true);
          }}
        >
          <span className="setting__mark setting__mark--danger">
            <Bin size={18} />
          </span>
          <span className="setting__body">
            <span className="setting__label setting__danger">
              {t(lang, "profile_delete")}
            </span>
            <span className="setting__help">{t(lang, "profile_delete_help")}</span>
          </span>
        </button>
      </Group>

      {deleted && !consented && (
        <p className="notice__body" style={{ margin: "-14px 0 26px" }}>
          {t(lang, "consent_delete")}
        </p>
      )}

      {/* ── ABOUT ───────────────────────────────────────────────────────
             THE SCRIPT ROW NAMES WHAT IS IN USE RATHER THAN OFFERING A CHOICE.
             The engine computes its target, its segment offsets and every
             letter highlight from the Uthmani text; there is no second script
             in the data. A picker listing IndoPak or Warsh would either
             mis-place every mark or be a dead control — so this states the
             script plainly, with no chevron, because it goes nowhere. */}
      <Group lang={lang} title="profile_group_about">
        <Row
          mark={<Script size={18} />}
          label={t(lang, "profile_script")}
          help={t(lang, "profile_script_help")}
          control={
            <span className="setting__value">{t(lang, "profile_script_value")}</span>
          }
        />
        <Row
          mark={<Info size={18} />}
          label={t(lang, "profile_advanced")}
          help={t(lang, "profile_advanced_body")}
        />
      </Group>

      {/* ── the practice log ─────────────────────────────────────────────
             LAST, AND OUTSIDE THE GROUPS. It is a list of events, not a set of
             controls, and it is the one thing on this screen that grows without
             limit — a settings card that is sixty rows long is not a settings
             card. */}
      <section className="settings-group">
        <p className="section-label settings-group__head">
          <Log size={15} /> {t(lang, "profile_history")}
        </p>

        {practised.length > 1 && (
          <div className="lang" style={{ marginBottom: 14, flexWrap: "wrap" }}>
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
      </section>
    </>
  );
}
