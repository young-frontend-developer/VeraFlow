import { useEffect, useState } from "react";
import Library from "./components/Library";
import LangToggle from "./components/LangToggle";
import Log from "./components/Log";
import Recite from "./components/Recite";
import TabBar, { Tab } from "./components/TabBar";
import { Ayah, listAyat, setConsent } from "./lib/api";
import { Lang, t } from "./lib/i18n";

const LANG_KEY = "tilawah_lang";
const AYAH_KEY = "tilawah_ayah";
const CONSENT_KEY = "tilawah_consent";

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
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    listAyat()
      .then((list) => {
        setAyat(list);
        const saved = localStorage.getItem(AYAH_KEY);
        setCurrent(list.find((a) => a.slug === saved) ?? list[0] ?? null);
      })
      .catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    localStorage.setItem(LANG_KEY, lang);
    document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    if (current) localStorage.setItem(AYAH_KEY, current.slug);
  }, [current]);

  // Consent defaults to off, so nothing is retained until it is granted. Mirror
  // the local flag to the server on first load so the two cannot drift.
  useEffect(() => {
    localStorage.setItem(CONSENT_KEY, consented ? "1" : "0");
    setConsent(consented).catch(() => {});
  }, [consented]);

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="wordmark">Tilawah</h1>
        <LangToggle lang={lang} onChange={setLang} />
      </header>

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
            onConsent={setConsented}
          />
        )}
      </main>

      <TabBar tab={tab} onChange={setTab} lang={lang} />
    </div>
  );
}
