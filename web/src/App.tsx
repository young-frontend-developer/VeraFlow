import { useEffect, useState } from "react";
import ConsentGate from "./components/ConsentGate";
import Library from "./components/Library";
import LangToggle from "./components/LangToggle";
import Log from "./components/Log";
import PilotBanner from "./components/PilotBanner";
import Recite from "./components/Recite";
import TabBar, { Tab } from "./components/TabBar";
import { Ayah, Meta, listAyat, meta, setConsent } from "./lib/api";
import { Lang, t } from "./lib/i18n";

const LANG_KEY = "tilawah_lang";
const AYAH_KEY = "tilawah_ayah";
const CONSENT_KEY = "tilawah_consent";
const AUDIO_CONSENT_KEY = "tilawah_consent_audio";
const CONSENT_SEEN_KEY = "tilawah_consent_seen";

function initialLang(): Lang {
  const saved = localStorage.getItem(LANG_KEY);
  if (saved === "uz" || saved === "ru") return saved;
  return navigator.language?.startsWith("ru") ? "ru" : "uz";
}

export default function App() {
  const [lang, setLang] = useState<Lang>(initialLang);
  const [tab, setTab] = useState<Tab>("practice");
  const [ayat, setAyat] = useState<Ayah[]>([]);
  const [current, setCurrent] = useState<Ayah | null>(null);
  const [consented, setConsented] = useState(
    () => localStorage.getItem(CONSENT_KEY) === "1",
  );
  const [audioConsented, setAudioConsented] = useState(
    () => localStorage.getItem(AUDIO_CONSENT_KEY) === "1",
  );
  const [consentSeen, setConsentSeen] = useState(
    () => localStorage.getItem(CONSENT_SEEN_KEY) === "1",
  );
  const [info, setInfo] = useState<Meta | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    listAyat()
      .then((list) => {
        setAyat(list);
        const saved = localStorage.getItem(AYAH_KEY);
        setCurrent(list.find((a) => a.slug === saved) ?? list[0] ?? null);
      })
      .catch(() => setFailed(true));
    // A failed /api/meta must not block the app, but it must not silently hide
    // the banner either — assume pilot until the server says otherwise.
    meta()
      .then(setInfo)
      .catch(() =>
        setInfo({
          pilot: true,
          unverified_codes: [],
          collect_audio_offered: false,
          version: "?",
        }),
      );
  }, []);

  useEffect(() => {
    localStorage.setItem(LANG_KEY, lang);
    document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    if (current) localStorage.setItem(AYAH_KEY, current.slug);
  }, [current]);

  // Mirror both flags to the server whenever they change, so the two cannot
  // drift. Nothing is retained until these say so.
  useEffect(() => {
    localStorage.setItem(CONSENT_KEY, consented ? "1" : "0");
    localStorage.setItem(AUDIO_CONSENT_KEY, audioConsented ? "1" : "0");
    if (consentSeen) setConsent(consented, audioConsented).catch(() => {});
  }, [consented, audioConsented, consentSeen]);

  function decide(next: boolean, nextAudio: boolean) {
    setConsented(next);
    setAudioConsented(nextAudio);
    setConsentSeen(true);
    localStorage.setItem(CONSENT_SEEN_KEY, "1");
    // Deliberately does NOT call setConsent here. The effect above already
    // mirrors the flags to the server, and calling it from both places fired
    // two concurrent writes - the decline path deletes rows, so the two
    // collided on SQLite and one connection died before CORS headers were
    // written, surfacing in the browser as an unexplained CORS error.
  }

  // Asked once, before anything is recorded — not buried in a settings tab.
  if (!consentSeen) {
    return (
      <div className="app">
        <header className="app__header">
          <h1 className="wordmark">Tilawah</h1>
          <LangToggle lang={lang} onChange={setLang} />
        </header>
        <ConsentGate
          lang={lang}
          audioOffered={info?.collect_audio_offered ?? false}
          onDecide={decide}
        />
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="wordmark">Tilawah</h1>
        <LangToggle lang={lang} onChange={setLang} />
      </header>

      {info?.pilot && <PilotBanner lang={lang} />}

      <main className="app__main">
        {failed ? (
          <div className="notice">
            <p className="notice__body">{t(lang, "error_generic")}</p>
          </div>
        ) : tab === "practice" ? (
          current ? (
            <Recite lang={lang} ayah={current} />
          ) : (
            <p className="empty">{t(lang, "loading")}</p>
          )
        ) : tab === "library" ? (
          <Library
            lang={lang}
            ayat={ayat}
            current={current}
            onPick={(a) => {
              setCurrent(a);
              setTab("practice");
            }}
          />
        ) : (
          <Log
            lang={lang}
            ayat={ayat}
            consented={consented}
            audioConsented={audioConsented}
            audioOffered={info?.collect_audio_offered ?? false}
            onConsent={(v, a) => {
              setConsented(v);
              setAudioConsented(a);
            }}
          />
        )}
      </main>

      <TabBar tab={tab} onChange={setTab} lang={lang} />
    </div>
  );
}
