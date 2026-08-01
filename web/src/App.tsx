import { useEffect, useState } from "react";
import ConsentGate from "./components/ConsentGate";
import Library from "./components/Library";
import LangToggle from "./components/LangToggle";
import Log from "./components/Log";
import PilotBanner from "./components/PilotBanner";
import Picker, { Selection } from "./components/Picker";
import Recite from "./components/Recite";
import Review from "./components/Review";
import TabBar, { Tab } from "./components/TabBar";
import {
  Ayah,
  Meta,
  Sura,
  listAyat,
  listSuras,
  meta,
  setConsent,
} from "./lib/api";
import { Lang, t } from "./lib/i18n";

const LANG_KEY = "tilawah_lang";
const AYAH_KEY = "tilawah_ayah";
/** Where the learner was, as "sura:aya" — reopens the picker there. */
const PLACE_KEY = "tilawah_place";
const CONSENT_KEY = "tilawah_consent";
const AUDIO_CONSENT_KEY = "tilawah_consent_audio";
const CONSENT_SEEN_KEY = "tilawah_consent_seen";

function initialLang(): Lang {
  const saved = localStorage.getItem(LANG_KEY);
  if (saved === "uz" || saved === "ru") return saved;
  return navigator.language?.startsWith("ru") ? "ru" : "uz";
}

function initialPlace(): { sura: number; aya: number } | null {
  const raw = localStorage.getItem(PLACE_KEY);
  const [s, a] = (raw ?? "").split(":").map(Number);
  return s >= 1 && s <= 114 && a >= 1 ? { sura: s, aya: a } : null;
}

/**
 * /review is the qori content-review tool: a different audience, a different
 * language policy, no consent gate and no tab bar. It replaces the learner app
 * rather than living inside it as a fourth tab, which would put an operator
 * tool one mis-tap away from every learner.
 *
 * Split into its own component, not an early return inside LearnerApp — that
 * would call hooks conditionally and break the moment the path changed.
 */
export default function App() {
  const isReview =
    window.location.pathname.replace(/\/+$/, "").toLowerCase() === "/review";
  return isReview ? <ReviewApp /> : <LearnerApp />;
}

function ReviewApp() {
  return (
    <div className="app app--tool">
      <header className="app__header">
        <h1 className="wordmark">Tilawah</h1>
        <span className="app__tool-tag">qori review</span>
      </header>
      <main className="app__main">
        <Review />
      </main>
    </div>
  );
}

function LearnerApp() {
  const [lang, setLang] = useState<Lang>(initialLang);
  const [tab, setTab] = useState<Tab>("practice");
  const [ayat, setAyat] = useState<Ayah[]>([]);
  const [current, setCurrent] = useState<Ayah | null>(null);
  const [suras, setSuras] = useState<Sura[]>([]);
  // The practice range in play. Null means the picker is open, which is also
  // the first-run state — there is no default ayah any more, because there is
  // no shortlist to default into.
  const [selection, setSelection] = useState<Selection | null>(null);
  const [place, setPlace] = useState(initialPlace);
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
    // The catalogue is what Practice runs on; failing to load it is fatal to
    // the tab, so it is the one that sets `failed`.
    listSuras()
      .then(setSuras)
      .catch(() => setFailed(true));
    // The curated shortlist still backs the Library tab and the Log's ayah
    // names. It is no longer the source of what you can practise, so its
    // failure must not take the whole app down with it.
    listAyat()
      .then((list) => {
        setAyat(list);
        const saved = localStorage.getItem(AYAH_KEY);
        setCurrent(list.find((a) => a.slug === saved) ?? list[0] ?? null);
      })
      .catch(() => setAyat([]));
    // A failed /api/meta must not block the app, but it must not silently hide
    // the banner either — assume pilot until the server says otherwise.
    meta()
      .then(setInfo)
      .catch(() =>
        setInfo({
          pilot: true,
          unverified_codes: [],
          collect_audio_offered: false,
          show_unreviewed: false,
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

  useEffect(() => {
    if (selection)
      localStorage.setItem(
        PLACE_KEY,
        `${selection.sura.number}:${selection.ayah.aya}`,
      );
  }, [selection]);

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

      {info?.pilot && (
        <PilotBanner
          lang={lang}
          showUnreviewed={info?.show_unreviewed ?? false}
        />
      )}

      <main className="app__main">
        {failed ? (
          <div className="notice">
            <p className="notice__body">{t(lang, "error_generic")}</p>
          </div>
        ) : tab === "practice" ? (
          suras.length === 0 ? (
            <p className="empty">{t(lang, "loading")}</p>
          ) : selection ? (
            <Recite
              lang={lang}
              selection={selection}
              onChange={() => setSelection(null)}
            />
          ) : (
            <Picker
              lang={lang}
              suras={suras}
              initial={place}
              onPick={setSelection}
            />
          )
        ) : tab === "library" ? (
          <Library
            lang={lang}
            ayat={ayat}
            current={current}
            onPick={(a) => {
              setCurrent(a);
              // The shortlist is a shortcut into the real catalogue now, not a
              // parallel world: jump the picker to that ayah and let it resolve
              // the segments the same way as any other choice.
              setSelection(null);
              setPlace({ sura: a.sura, aya: a.aya });
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
