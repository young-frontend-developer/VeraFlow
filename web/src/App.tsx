import { useEffect, useState } from "react";
import Achievements from "./components/Achievements";
import Auth from "./components/Auth";
import Opening from "./components/Opening";
import Personalize from "./components/Personalize";
import LanguagePick from "./components/LanguagePick";
import Welcome from "./components/Welcome";
import { CreateJourney, JourneyReady } from "./components/JourneySetup";
import { BRAND } from "./lib/brand";
import { Journey, adjustJourney, hasJourney, storedJourney } from "./lib/journey";
import LangToggle from "./components/LangToggle";
import MailAction from "./components/MailAction";
import ConsentGate from "./components/ConsentGate";
import Onboarding, { Experience } from "./components/Onboarding";
import Picker, { Selection } from "./components/Picker";
import Profile from "./components/Profile";
import { ReadMode } from "./components/Reader";
import Recite from "./components/Recite";
import Review from "./components/Review";
import { Learn } from "./components/Soon";
import Progress from "./components/Progress";
import { Flame, Gear } from "./components/Ornament";
import GoalScreen, { GoalCard, goalSentence } from "./components/Goal";
import Notifications, { BellButton } from "./components/Notifications";
import { Goal, clearGoal, saveGoal, storedGoal } from "./lib/goals";
import {
  NotificationRecord,
  dropForGoal,
  markAllRead,
  push as pushNotification,
  read as readNotifications,
} from "./lib/notifications";
import TabBar, { Tab } from "./components/TabBar";
import Today from "./components/Today";
import { Failure, Loading } from "./components/States";
import {
  Attempt,
  Ayah,
  Meta,
  Reciter,
  Sura,
  apiPredatesContract,
  history,
  listAyat,
  listReciters,
  listSuras,
  meta,
  missingPayloadFields,
  setConsent,
  staleApiFields,
} from "./lib/api";
import { streak } from "./lib/progress";
import { Theme, applyTheme, storedTheme } from "./lib/theme";
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
/** The account screen has been shown and dismissed. See the gate in render. */
const AUTH_SEEN_KEY = "tilawah_auth_seen";
/**
 * ONE KEY FOR THE WHOLE ENTRY EXPERIENCE, not one per screen.
 *
 * The first-open flow is Basmala -> Welcome -> Personalize -> Create -> Ready
 * -> Account, and it is one journey rather than six gates. Storing a flag per
 * screen means a half-finished onboarding resumes in a different place than it
 * left, and a learner who backgrounds the app mid-flow comes back to a
 * fragment. This records only WHETHER the entry experience has been completed.
 */
const ENTRY_KEY = "veyraflow_entry_done";
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
  const path = window.location.pathname.replace(/\/+$/, "").toLowerCase();

  // WHERE A LINK FROM AN EMAIL LANDS. Both are one-shot screens with no tab
  // bar, no consent gate and no session assumed - see MailAction.tsx. They are
  // dispatched here for the same reason /review is: an early return inside
  // LearnerApp would call hooks conditionally and break the moment the path
  // changed.
  if (path === "/verify-email" || path === "/reset-password") {
    return <MailActionApp kind={path === "/verify-email" ? "verify" : "reset"} />;
  }
  return path === "/review" ? <ReviewApp /> : <LearnerApp />;
}

function MailActionApp({ kind }: { kind: "verify" | "reset" }) {
  // The learner arrives here from their inbox, possibly on a device that has
  // never opened the app - so the language comes from the same stored
  // preference the app uses, falling back to the browser's, and nothing here
  // needs a session.
  const [lang] = useState<Lang>(initialLang);
  return (
    <MailAction
      kind={kind}
      lang={lang}
      // Straight to the app's front door. A full navigation rather than a
      // state change, so the app boots normally instead of inheriting this
      // screen's assumptions - and the token is already out of the URL.
      onDone={() => window.location.assign("/")}
    />
  );
}

function ReviewApp() {
  return (
    <div className="app app--tool">
      <header className="app__header">
        <h1 className="wordmark">{BRAND}</h1>
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
  /**
   * Dark or light, CHOSEN IN SETTINGS.
   *
   * Read from storage on the first render rather than in an effect, so the very
   * first paint is already the chosen theme — setting it after mount is what
   * produces the flash of the wrong palette on every launch. The device's own
   * preference is deliberately not consulted; see lib/theme.ts.
   */
  const [theme, setTheme] = useState<Theme>(storedTheme);
  const [tab, setTab] = useState<Tab>("home");
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
  // Dismissed once, dismissed for good — see the gate below.
  const [authSeen, setAuthSeen] = useState(
    () => localStorage.getItem(AUTH_SEEN_KEY) === "1",
  );
  const [entryDone, setEntryDone] = useState(
    () => localStorage.getItem(ENTRY_KEY) === "1",
  );
  const [entry, setEntry] = useState<
    "basmala" | "language" | "welcome" | "personalize" | "create" | "ready"
    | "account" | "consent"
  >("basmala");
  /**
   * The journey being assembled during onboarding.
   *
   * Held in state, not written to storage, until the learner presses "Create My
   * Journey" - an abandoned onboarding should leave nothing behind, and a
   * half-filled journey in localStorage would make hasJourney() true for
   * someone who never finished.
   */
  const [draftJourney, setDraftJourney] = useState<Journey>(
    () => storedJourney() ?? {
      goal: null, stage: null, focus: null, minutes: null, when: null,
      weekly: 5, created: "",
    },
  );
  const [info, setInfo] = useState<Meta | null>(null);
  const [failed, setFailed] = useState(false);
  /**
   * The learner's attempt history, LIFTED OUT OF Today.
   *
   * It was fetched inside Today, which was correct while Today was the only
   * screen that counted anything. Three now read it — Home's figures, the
   * Progress tab, and the streak chip in the header that is on screen on every
   * tab — and three copies of the same fetch means three chances for them to
   * disagree about how long the streak is. One fetch, one answer, passed down.
   *
   * Null while loading; [] with retention declined, which is a real answer and
   * not a failure.
   */
  const [rows, setRows] = useState<Attempt[] | null>(null);

  /**
   * The goal, and the notification list.
   *
   * Both device-local, both read once on mount and held here rather than in
   * the screens that show them — the goal card is on Home, the goal screen is
   * a view of its own, and the bell is in the header on every tab, so a
   * per-screen copy would go stale the moment one of them wrote.
   */
  const [goal, setGoal] = useState<Goal | null>(storedGoal);
  const [notifications, setNotifications] = useState<NotificationRecord[]>(
    readNotifications,
  );
  const [bellOpen, setBellOpen] = useState(false);
  /** The goal editor is a SCREEN, not a tab — see the render. */
  const [goalOpen, setGoalOpen] = useState(false);

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

  /**
   * Bumped every time a recitation is stored, to re-run the fetch below.
   *
   * WITHOUT THIS, NOTHING ON HOME EVER MOVES. The history was fetched on mount
   * and on a consent change, and on nothing else — so a learner could recite
   * four ayat, walk back to Home, and find hasanat still reading 0, the streak
   * unchanged and the rank frozen. Every one of those numbers was correct for
   * the rows the app had; it just never asked for the new ones. Reported as
   * "hasanat not accumulating", and it was really "Home is showing you the
   * history it loaded when the app opened".
   */
  const [historyEpoch, setHistoryEpoch] = useState(0);

  useEffect(() => {
    // Declined retention means there is nothing stored to fetch, and asking
    // anyway would be a request for data the learner has said not to keep.
    if (!consented) return setRows([]);
    history(200)
      .then(setRows)
      .catch(() => setRows([]));
  }, [consented, historyEpoch]);

  useEffect(() => applyTheme(theme), [theme]);

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

  // ── THE ENTRY EXPERIENCE ──────────────────────────────────────────────
  // One continuous flow, in order, before anything else in the app renders:
  //
  //   Basmala -> LANGUAGE -> Welcome -> Personalization -> Create My Journey ->
  //   Journey Ready -> Account -> Consent
  //
  // LANGUAGE COMES FIRST, immediately after the Basmala, because every screen
  // after it is prose. It used to be settled near the END of this flow, on the
  // account screen, which meant the welcome and all five personalization
  // questions were put to the learner in whichever language the app happened to
  // default to. An answer given to a question you cannot read is not an answer.
  // See LanguagePick.tsx.
  //
  // Each stage hands to the next; nothing here is a dead end and every stage
  // after the Basmala can be skipped EXCEPT the language step, where skipping
  // would cost the learner every screen that follows. It runs ONCE - see
  // ENTRY_KEY - because a ceremonial opening on the fourth launch is an
  // obstacle, not a moment.
  if (!entryDone) {
    if (entry === "basmala") {
      return <Opening onDone={() => setEntry("language")} />;
    }
    if (entry === "language") {
      return (
        <LanguagePick
          lang={lang}
          onLang={setLang}
          onDone={() => setEntry("welcome")}
        />
      );
    }
    if (entry === "welcome") {
      return <Welcome lang={lang} onDone={() => setEntry("personalize")} />;
    }
    if (entry === "personalize") {
      return (
        <Personalize
          lang={lang}
          onDone={(a) => {
            setDraftJourney((j) => ({ ...j, ...a }));
            setEntry("create");
          }}
        />
      );
    }
    if (entry === "create") {
      return (
        <CreateJourney
          lang={lang}
          journey={draftJourney}
          onCreate={() => {
            // Written here and not before: the journey exists when the learner
            // says it does. That is what makes the button honest.
            setDraftJourney(adjustJourney(draftJourney));
            setEntry("ready");
          }}
          onBack={() => setEntry("personalize")}
        />
      );
    }
    if (entry === "ready") {
      return (
        <JourneyReady
          lang={lang}
          journey={draftJourney}
          onBegin={() => setEntry("account")}
        />
      );
    }
    // Account is skippable, so the learner experiences the beginning of the
    // app before being asked for anything. Their journey is already stored
    // locally and attaches to an account whenever accounts exist - see Auth.
    if (entry === "account") {
      return (
        <Auth
          lang={lang}
          onLang={setLang}
          onContinue={() => {
            localStorage.setItem(AUTH_SEEN_KEY, "1");
            setAuthSeen(true);
            setEntry("consent");
          }}
        />
      );
    }

    // CONSENT IS THE LAST STEP AND IT IS INSIDE THIS FLOW, not after it.
    // It used to be reached via the old Onboarding component, which meant the
    // learner finished the journey payoff, tapped through the account screen,
    // and landed on a bare consent page with no navigation - the one moment
    // the entry experience is supposed to hand them the app. It is also the
    // only step here that is a real decision rather than an introduction, so
    // it comes last, after they know what they are consenting for.
    return (
      <ConsentGate
        lang={lang}
        audioOffered={info?.collect_audio_offered ?? false}
        onDecide={(c, a) => {
          decide(c, a, null);
          setEntryDone(true);
          localStorage.setItem(ENTRY_KEY, "1");
        }}
      />
    );
  }

  // ── the account screen ────────────────────────────────────────────────
  // FIRST, AND SKIPPABLE. It comes before onboarding because that is where a
  // sign-in belongs, and it is skippable because Tilawah genuinely works
  // without an account — everything runs against an anonymous device id.
  //
  // Once dismissed it stays dismissed. There are real accounts now - email and
  // Google both work - but anonymous is still a first-class way to use this
  // app, not a trial of it, and re-presenting the screen every launch would be
  // nagging somebody towards a decision they have already made.
  if (!authSeen) {
    return (
      <Auth
        lang={lang}
        onLang={setLang}
        onContinue={() => {
          setAuthSeen(true);
          localStorage.setItem(AUTH_SEEN_KEY, "1");
        }}
      />
    );
  }

  // First run. Welcome, language, experience, then consent — asked once, before
  // anything is recorded, and never buried in a settings tab.
  if (!consentSeen) {
    return (
      <div className="app">
        <header className="app__header">
          <h1 className="wordmark">{BRAND}</h1>
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

  /**
   * The centre button: recite the thing you already chose, with nothing in
   * between.
   *
   * It resolves the ayah's practice range itself rather than routing through
   * the picker, because a "start reciting" button that lands on a chooser has
   * not started anything. With no stored place there is nothing to resolve and
   * it falls through to the chooser, which is the only honest thing it can do —
   * and if resolving fails it does the same, rather than sitting silent.
   */
  function startRecite() {
    // STRAIGHT TO THE ONE PRACTISING SCREEN, which is the reader's verse view.
    //
    // This used to resolve the practice range itself and drop the learner into
    // the recording screen with the mic idle — a THIRD way of looking at an
    // ayah, alongside the two the reading modes had. Now it lands exactly where
    // tapping an ayah in the mushaf lands: the verse view, at the stored place,
    // with the ayah, its translation, the reciter playback and the mic.
    //
    // Nothing is awaited any more. The Picker restores to `place` on mount and
    // the range is resolved when the mic is pressed, which is the only moment
    // it is actually needed. With no stored place there is nothing to restore
    // and it falls through to the sura list, as it always did.
    setSelection(null);
    setMode("verse");
    setTab("practice");
  }

  /**
   * Step to the ayah either side of the one just recorded.
   *
   * IT LANDS ON THE READER, not on another recording screen. This used to
   * resolve the next range and swap the selection in place, which meant the
   * arrows produced a recording screen with an idle mic — the same third view
   * of an ayah that `startRecite` used to produce, reachable one tap from a
   * result. Moving on to the next ayah now goes where moving on always goes:
   * the verse view, where you can read it and hear it before you recite it.
   *
   * No fetch and nothing to fail. Clearing the selection renders the Picker,
   * which restores to `place` — so "next" is one state update rather than two
   * network calls that could half-succeed.
   */
  function stepAyah(delta: -1 | 1) {
    if (!selection) return;
    const aya = selection.ayah.aya + delta;
    if (aya < 1 || aya > selection.sura.n_ayat) return;
    setPlace({ sura: selection.sura.number, aya });
    setSelection(null);
    setMode("verse");
  }

  const run = streak(rows ?? []);

  /**
   * Suras the learner has actually recited from, for the picker's "Started"
   * pill. Built from real attempt rows and nothing else — with retention off
   * this is empty and the pill is not offered.
   */
  const started = new Set((rows ?? []).map((r) => r.sura));

  return (
    // No per-screen bottom allowance. The recording card used to be fixed to
    // the viewport and the page had to reserve room under it; it is in the
    // normal flow now, so `.app`'s own clearance for the nav bar is all that
    // is needed and every screen gets the same one.
    <div className="app">
      {/* The top bar: wordmark left, streak right. That is all.
          THE STREAK CHIP IS NOT DECORATION AND NOT ALWAYS THERE. It appears
          only once there is a real run of days behind it — a flame showing "0"
          on a screen that has just told someone to start is a scold, and a
          flame that is always lit stops meaning anything. It is the one
          gamification element allowed outside Home, because it is the one that
          is about today.

          THE LANGUAGE TOGGLE IS GONE FROM HERE. It sat in this bar on every
          screen, which gave a once-a-year decision the same permanent real
          estate as the app's own name — and put a control that reloads all
          content one mis-tap from the streak. Language is chosen during
          onboarding and changed in Profile, which is now a tab rather than
          something behind a gear. The toggle itself is unchanged and still
          mounted there; only this instance was removed.

          The gear went with it. Profile is item five in the bar now, so a
          second route to the same screen would be two controls for one
          destination — the exact duplication the centre button just fixed. */}
      <header className="app__header">
        <h1 className="wordmark">{BRAND}</h1>
        {/* THE BELL IS ON EVERY SCREEN, the streak chip only when there is a
            streak. Both live in the same cluster on the right, and the bell is
            the outermost because it is the one that is always there — a row
            whose items shuffle position depending on whether you practised
            yesterday is a row you have to re-read every time. */}
        <div className="app__tools">
          {consented && run.current > 0 && (
            <span className="streak-chip" title={t(lang, "stat_streak")}>
              <Flame size={15} />
              {run.current}
            </span>
          )}
          <BellButton
            lang={lang}
            rows={notifications}
            onOpen={() => setBellOpen(true)}
          />
        </div>
      </header>

      {bellOpen && (
        <Notifications
          lang={lang}
          rows={notifications}
          // MARKED READ ON CLOSE, NOT ON OPEN. Marking on open is the obvious
          // move and it makes the unread marker unobservable: the state update
          // batches with the one that mounts the panel, so the list renders
          // with every row already read and the learner never finds out which
          // ones were new. Reading happens while the panel is up; the state
          // catches up when it comes down.
          onClose={() => {
            setBellOpen(false);
            setNotifications(markAllRead());
          }}
        />
      )}

      {/* VERSION SKEW, NAMED.
          A server process started before a field was added keeps answering
          200s, and from the browser that is indistinguishable from a client
          bug — every card throws and the error boundary quietly replaces all
          of them. This says which fields are missing and what to do, so the
          failure diagnoses itself instead of looking like broken cards. */}
      {(staleApiFields(info).length > 0 ||
        apiPredatesContract(info) ||
        missingPayloadFields(suras, rows).length > 0) && (
        <div className="notice notice--stale" role="alert">
          <p className="notice__title">{t(lang, "api_stale_title")}</p>
          <p className="notice__body">{t(lang, "api_stale_body")}</p>
          <p className="notice__body">
            <code>
              {[
                apiPredatesContract(info)
                  ? "error_fields: —"
                  : staleApiFields(info).join(", "),
                ...missingPayloadFields(suras, rows),
              ]
                .filter(Boolean)
                .join(", ")}
            </code>
          </p>
        </div>
      )}

      {/* THE PILOT BANNER IS GONE, and what it said is not.
          It stood above every screen for the whole session saying the tajweed
          corrections were unreviewed — true, and already said in the one place
          it can be acted on: the QORALAMA chip on each card, next to the
          specific sentence that has not been signed off. A standing banner
          repeats that claim on screens with no corrections on them at all, and
          a warning shown everywhere is one testers stop seeing exactly where it
          matters. The per-card chip is the same information at the point of
          use, which is where a caveat belongs. */}

      <main className="app__main" key={tab}>
        {failed ? (
          <Failure
            lang={lang}
            title={t(lang, "error_generic")}
            body={t(lang, "api_stale_body")}
            onRetry={() => window.location.reload()}
          />
        ) : goalOpen ? (
          /* ── THE GOAL EDITOR IS A SCREEN, NOT A SHEET AND NOT A TAB ──────
                It replaces the main region the way Recite does, checked before
                the tab switch so it opens over whatever the learner was on.
                Full-screen because it is one focused decision; not a tab
                because it is not a destination you return to. The nav bar
                stays mounted underneath — trapping someone inside a form is
                how a four-tap flow becomes a place people get stuck. */
          <GoalScreen
            lang={lang}
            goal={goal}
            onClose={() => setGoalOpen(false)}
            onSave={(next) => {
              const saved = saveGoal({ ...next, id: goal?.id, createdAt: goal?.createdAt });
              setGoal(saved);
              setGoalOpen(false);
              // A record of what was just set, so the bell has something true
              // in it from the first goal onward. NOT a fake reminder — see
              // the header of lib/notifications.ts.
              setNotifications(
                pushNotification({
                  kind: "goal_set",
                  goalId: saved.id,
                  title: t(lang, "goal_active_kicker"),
                  body:
                    goalSentence(lang, saved) +
                    (saved.remindAt
                      ? ` · ${t(lang, "goal_reminder_at").replace("{t}", saved.remindAt)}`
                      : ""),
                }),
              );
            }}
            onRemove={() => {
              if (goal) setNotifications(dropForGoal(goal.id));
              clearGoal();
              setGoal(null);
              setGoalOpen(false);
            }}
          />
        ) : tab === "home" ? (
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
              onOpenSura={(sura) => {
                setPlace({ sura, aya: 1 });
                setSelection(null);
                setTab("practice");
              }}
              onBrowse={() => {
                setSelection(null);
                setTab("practice");
              }}
              onViewAchievements={() => setTab("progress")}
              goal={goal}
              onOpenGoal={() => setGoalOpen(true)}
            />
          )
        ) : tab === "learn" ? (
          <Learn lang={lang} />
        ) : tab === "progress" ? (
          <Progress
            lang={lang}
            suras={suras}
            rows={rows}
            consented={consented}
            onBrowse={() => {
              setSelection(null);
              setTab("practice");
            }}
            onPick={(sura, aya) => {
              setPlace({ sura, aya });
              setSelection(null);
              setTab("practice");
            }}
          />
        ) : tab === "practice" ? (
          suras.length === 0 ? (
            <Loading rows={6} />
          ) : selection ? (
            <Recite
              lang={lang}
              selection={selection}
              // The X exits to the FULL SURA LIST, not to the reader for the
              // sura you were in. Clearing `place` as well as `selection` is
              // what makes that true: Picker restores to `initial` on mount,
              // so leaving it set would reopen the reader one step short of
              // the list the close button is supposed to reach.
              onChange={() => {
                setSelection(null);
                setPlace(null);
              }}
              onPart={(segment, whole) =>
                setSelection((s) => (s ? { ...s, segment, whole } : s))
              }
              onStep={stepAyah}
              // Every stored attempt invalidates the numbers on Home and
              // Progress. Fired on the analysed result rather than on the
              // upload, so the refetch sees the row the server actually wrote.
              onAttempt={() => setHistoryEpoch((n) => n + 1)}
              canStep={{
                prev: selection.ayah.aya > 1,
                next: selection.ayah.aya < selection.sura.n_ayat,
              }}
              maxAudioSeconds={info?.max_audio_seconds ?? 0}
              // The LIST and the setter are gone: choosing a reciter is a
              // Settings decision now. The id still comes through, because the
              // comparison playback has to resolve a file.
              reciter={reciter}
              showUnreviewed={info?.show_unreviewed ?? false}
            />
          ) : (
            <Picker
              lang={lang}
              suras={suras}
              initial={place}
              onPick={setSelection}
              mode={mode}
              onMode={setMode}
              reciter={reciter}
              started={started}
              showUnreviewed={info?.show_unreviewed ?? false}
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
            theme={theme}
            onTheme={setTheme}
          />
        )}
      </main>

      {/* The centre item is an ACTION, not a destination, so it is intercepted
          here rather than routed to a screen of its own. Everything else is a
          plain tab change. */}
      <TabBar
        tab={tab}
        onChange={(next) => {
          // THE GOAL EDITOR CLOSES ON ANY NAV. It renders ahead of the tab
          // switch, so without this a learner who opened it and then pressed
          // Profil would watch the bar's highlight move while the screen did
          // not — the definition of being stuck in a form.
          setGoalOpen(false);
          if (next === "tutor") startRecite();
          else setTab(next);
        }}
        lang={lang}
      />
    </div>
  );
}
