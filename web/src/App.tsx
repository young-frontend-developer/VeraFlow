import { useEffect, useState } from "react";
import LangToggle from "./components/LangToggle";
import Onboarding, { Experience } from "./components/Onboarding";
import PilotBanner from "./components/PilotBanner";
import Picker, { Selection } from "./components/Picker";
import Profile from "./components/Profile";
import { ReadMode } from "./components/Reader";
import Recite from "./components/Recite";
import Review from "./components/Review";
import { Learn, Memorize } from "./components/Soon";
import TabBar, { Tab } from "./components/TabBar";
import Today from "./components/Today";
import { Failure, Loading } from "./components/States";
import {
  Ayah,
  Meta,
  Reciter,
  Sura,
  apiPredatesContract,
  listAyat,
  listReciters,
  listSuras,
  meta,
  setConsent,
  staleApiFields,
} from "./lib/api";
import { Lang, t } from "./lib/i18n";

const LANG_KEY = "tilawah_lang";
const AYAH_KEY = "tilawah_ayah";
/** Where the learner was, as "sura:aya" — reopens the picker there. */
const PLACE_KEY = "tilawah_place";
/** mushaf | verse — how they prefer to read. */
const MODE_KEY = "tilawah_read_mode";
/** everyayah folder of the chosen reciter. */
const RECITER_KEY = "tilawah_reciter";
const CONSENT_KEY = "tilawah_consent";
const AUDIO_CONSENT_KEY = "tilawah_consent_audio";
const CONSENT_SEEN_KEY = "tilawah_consent_seen";
/**
 * How much Qur'an reading the learner said they had done, at onboarding.
 *
 * It exists to pick a DEFAULT RECITER and nothing else: a muallim recording
 * repeats each phrase and is genuinely easier to follow when you are starting,
 * a murattal is not. Storing an answer nothing reads would be a survey
 * pretending to be personalisation, so the one thing it decides is the one
 * thing it is asked for.
 */
const EXPERIENCE_KEY = "tilawah_experience";

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

function initialMode(): ReadMode {
  const saved = localStorage.getItem(MODE_KEY);
  // Mushaf by default: it is the shape people already know the Quran in, and
  // the one that shows where an ayah sits among its neighbours.
  return saved === "verse" ? "verse" : "mushaf";
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
  const [tab, setTab] = useState<Tab>("today");
  const [ayat, setAyat] = useState<Ayah[]>([]);
  const [current, setCurrent] = useState<Ayah | null>(null);
  const [suras, setSuras] = useState<Sura[]>([]);
  // The practice range in play. Null means the picker is open, which is also
  // the first-run state — there is no default ayah any more, because there is
  // no shortlist to default into.
  const [selection, setSelection] = useState<Selection | null>(null);
  const [place, setPlace] = useState(initialPlace);
  const [mode, setMode] = useState<ReadMode>(initialMode);
  const [reciters, setReciters] = useState<Reciter[]>([]);
  // Empty until /api/reciters answers. The saved id is NOT trusted until it is
  // checked against that list — a reciter folder can be dropped by a rebuild
  // when it stops serving files, and a stale id would 404 on every play.
  const [reciter, setReciter] = useState(
    () => localStorage.getItem(RECITER_KEY) ?? "",
  );
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
    // Reciters. A failure here costs playback, not practice, so it degrades to
    // an empty list and the select simply does not render.
    listReciters()
      .then((got) => {
        setReciters(got.reciters);
        setReciter((saved) =>
          got.reciters.some((r) => r.id === saved) ? saved : got.default,
        );
      })
      .catch(() => setReciters([]));
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
          max_audio_seconds: 0,
          missing_registries: [],
          missing_audio: [],
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

  useEffect(() => localStorage.setItem(MODE_KEY, mode), [mode]);

  useEffect(() => {
    // Only persist a validated id, so a dropped reciter cannot be written back
    // and resurrected on the next load.
    if (reciter) localStorage.setItem(RECITER_KEY, reciter);
  }, [reciter]);

  useEffect(() => {
    if (!selection) return;
    const next = {
      sura: selection.sura.number,
      aya: selection.ayah.aya,
    };
    localStorage.setItem(PLACE_KEY, `${next.sura}:${next.aya}`);
    // Track the live choice, not just the one restored at page load, so the
    // picker reopens on the ayah actually being recited. Safe to set on every
    // selection: Picker's restore effect keys on the sura/aya numbers, so a
    // fresh object with unchanged numbers does not re-trigger it.
    setPlace(next);
  }, [selection]);

  // Mirror both flags to the server whenever they change, so the two cannot
  // drift. Nothing is retained until these say so.
  useEffect(() => {
    localStorage.setItem(CONSENT_KEY, consented ? "1" : "0");
    localStorage.setItem(AUDIO_CONSENT_KEY, audioConsented ? "1" : "0");
    if (consentSeen) setConsent(consented, audioConsented).catch(() => {});
  }, [consented, audioConsented, consentSeen]);

  function decide(
    next: boolean,
    nextAudio: boolean,
    experience: Experience | null = null,
  ) {
    setConsented(next);
    setAudioConsented(nextAudio);
    setConsentSeen(true);
    localStorage.setItem(CONSENT_SEEN_KEY, "1");
    // The experience answer spends itself here and nowhere else: a beginner
    // gets the muallim recording, which repeats each phrase. If no muallim is
    // in the list the server's default stands — never a guessed folder name.
    if (experience) {
      localStorage.setItem(EXPERIENCE_KEY, experience);
      if (experience === "new") {
        const muallim = reciters.find((r) => r.style === "muallim");
        if (muallim) setReciter(muallim.id);
      }
    }
    // Deliberately does NOT call setConsent here. The effect above already
    // mirrors the flags to the server, and calling it from both places fired
    // two concurrent writes - the decline path deletes rows, so the two
    // collided on SQLite and one connection died before CORS headers were
    // written, surfacing in the browser as an unexplained CORS error.
  }

  // First run. Welcome, language, experience, then consent — asked once, before
  // anything is recorded, and never buried in a settings tab.
  if (!consentSeen) {
    return (
      <div className="app">
        <header className="app__header">
          <h1 className="wordmark">Tilawah</h1>
          <LangToggle lang={lang} onChange={setLang} />
        </header>
        <Onboarding
          lang={lang}
          audioOffered={info?.collect_audio_offered ?? false}
          onLang={setLang}
          onDone={decide}
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

      {/* VERSION SKEW, NAMED.
          A server process started before a field was added keeps answering
          200s, and from the browser that is indistinguishable from a client
          bug — every card throws and the error boundary quietly replaces all
          of them. This says which fields are missing and what to do, so the
          failure diagnoses itself instead of looking like broken cards. */}
      {(staleApiFields(info).length > 0 || apiPredatesContract(info)) && (
        <div className="notice notice--stale" role="alert">
          <p className="notice__title">{t(lang, "api_stale_title")}</p>
          <p className="notice__body">{t(lang, "api_stale_body")}</p>
          <p className="notice__body">
            <code>
              {apiPredatesContract(info)
                ? "error_fields: —"
                : staleApiFields(info).join(", ")}
            </code>
          </p>
        </div>
      )}

      {info?.pilot && (
        <PilotBanner
          lang={lang}
          showUnreviewed={info?.show_unreviewed ?? false}
        />
      )}

      <main className="app__main" key={tab}>
        {failed ? (
          <Failure
            lang={lang}
            title={t(lang, "error_generic")}
            body={t(lang, "api_stale_body")}
            onRetry={() => window.location.reload()}
          />
        ) : tab === "today" ? (
          suras.length === 0 ? (
            <Loading rows={5} />
          ) : (
            <Today
              lang={lang}
              suras={suras}
              place={place}
              consented={consented}
              onResume={(sura, aya) => {
                setPlace({ sura, aya });
                setSelection(null);
                setTab("practice");
              }}
              onPick={(sura, aya) => {
                setPlace({ sura, aya });
                setSelection(null);
                setTab("practice");
              }}
              onBrowse={() => {
                setSelection(null);
                setTab("practice");
              }}
            />
          )
        ) : tab === "learn" ? (
          <Learn lang={lang} />
        ) : tab === "memorize" ? (
          <Memorize lang={lang} />
        ) : tab === "practice" ? (
          suras.length === 0 ? (
            <Loading rows={6} />
          ) : selection ? (
            <Recite
              lang={lang}
              selection={selection}
              onChange={() => setSelection(null)}
              onPart={(segment, whole) =>
                setSelection((s) => (s ? { ...s, segment, whole } : s))
              }
              maxAudioSeconds={info?.max_audio_seconds ?? 0}
              reciters={reciters}
              reciter={reciter}
              onReciter={setReciter}
            />
          ) : (
            <Picker
              lang={lang}
              suras={suras}
              initial={place}
              onPick={setSelection}
              mode={mode}
              onMode={setMode}
              reciters={reciters}
              reciter={reciter}
              onReciter={setReciter}
            />
          )
        ) : (
          <Profile
            lang={lang}
            suras={suras}
            reciters={reciters}
            reciter={reciter}
            consented={consented}
            audioConsented={audioConsented}
            audioOffered={info?.collect_audio_offered ?? false}
            onReciter={setReciter}
            onLang={setLang}
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
