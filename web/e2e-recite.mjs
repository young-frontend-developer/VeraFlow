/**
 * One real recitation, through a real browser, end to end.
 *
 * Drives Chrome with a fake microphone fed from an actual recording in
 * api/debug_audio, so getUserMedia -> Web Audio -> WAV -> POST /api/attempts ->
 * the results screen is the genuine path. This exists because the white-screen
 * crash was shipped twice after verifying the payload by hand: a payload does
 * not render, a browser does.
 *
 * Fails loudly on ANY page error or console error, which is precisely what the
 * TypeError in <Correction> would have tripped.
 *
 *   node e2e-recite.mjs [--url http://localhost:5199] [--wav <path>]
 *                       [--sura 112] [--aya 3]
 */
import { chromium } from "playwright";
import path from "node:path";
import fs from "node:fs";

const arg = (name, dflt) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : dflt;
};

const URL = arg("url", "http://localhost:5199");
const WAV = path.resolve(
  arg("wav", "../api/debug_audio/20260731-121116-112_003-4cb1a6.16k.wav"),
);
const SURA = Number(arg("sura", 112));
const AYA = Number(arg("aya", 3));
const SHOTS = path.resolve(arg("out", "./e2e-shots"));

if (!fs.existsSync(WAV)) {
  console.error(`no such wav: ${WAV}`);
  process.exit(2);
}

/**
 * How long the clip actually runs, from its own header.
 *
 * THE RECORDING WINDOW HAS TO MATCH THE CLIP, and missing in EITHER direction
 * ruins the run in a way that looks like a product fault:
 *
 *   too short   the read is truncated, and every letter past the cut comes back
 *               as a dropped letter. A 6-second window on a 20-second ayah
 *               produced 32 cards of entirely correct feedback about a
 *               recitation the harness had chopped up.
 *   too long    the fake device goes silent once the file ends, and the trailing
 *               silence trips the collapse gate — "we could not hear that
 *               clearly", with no cards at all.
 *
 * So it is read rather than guessed. Canonical 44-byte PCM WAV, which is what
 * debug_capture writes; anything else falls back to the caller's estimate.
 */
function wavSeconds(path) {
  const b = fs.readFileSync(path, { start: 0, end: 44 });
  if (b.length < 44 || b.toString("ascii", 0, 4) !== "RIFF") return 0;
  const byteRate = b.readUInt32LE(28);
  const bytes = fs.statSync(path).size - 44;
  return byteRate > 0 ? bytes / byteRate : 0;
}
fs.mkdirSync(SHOTS, { recursive: true });

const problems = [];
const shot = async (page, name) => {
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
  console.log(`  [shot] ${name}.png`);
};

const browser = await chromium.launch({
  channel: "chrome",
  args: [
    "--use-fake-ui-for-media-stream", // auto-grant the mic prompt
    "--use-fake-device-for-media-stream",
    `--use-file-for-fake-audio-capture=${WAV}`,
    "--autoplay-policy=no-user-gesture-required",
  ],
});

const ctx = await browser.newContext({ permissions: ["microphone"] });

// SEED THE APP'S OWN PERSISTENCE INSTEAD OF CLICKING THROUGH TO THE AYAH.
// The picker restores `tilawah_place` on mount, so writing it lands the reader
// directly on the ayah under test. The previous version searched for the sura
// and then stepped with the arrows, which does the wrong thing the moment any
// state survives — a restored place hides the search box, the search branch is
// skipped, and the arrows then step relative to whatever ayah was restored. One
// run ended up reciting into sura 108 in Russian for exactly that reason.
await ctx.addInitScript(
  ([sura, aya]) => {
    localStorage.setItem("tilawah_place", `${sura}:${aya}`);
    localStorage.setItem("tilawah_read_mode", "verse");
    localStorage.setItem("tilawah_lang", "uz");
    // Consent is answered, and answered the stingy way: seen, but nothing
    // stored. That is the path a learner who consents to nothing takes, and the
    // one that must keep working.
    localStorage.setItem("tilawah_consent_seen", "1");
    localStorage.setItem("tilawah_consent", "0");
    localStorage.setItem("tilawah_consent_audio", "0");
  },
  [SURA, AYA],
);

const page = await ctx.newPage();

// Any console error or uncaught exception is a failure. The crash we are
// hunting surfaced exactly here.
// The app declares no favicon, so Chrome requests /favicon.ico and logs a 404
// on every page load. Pre-existing, unrelated to rendering, and it would mask
// the signal this script exists for.
const IGNORE = [/favicon/i];

page.on("console", (m) => {
  if (m.type() !== "error") return;
  const text = m.text();
  if (IGNORE.some((re) => re.test(text))) return;
  // "Failed to load resource" carries no URL and is always a duplicate of a
  // response event, which does carry one. Judged there instead so a favicon
  // can be ignored without also ignoring a real 404.
  if (/Failed to load resource/.test(text)) return;
  problems.push(`console.error: ${text}`);
  console.log(`  [console.error] ${text}`);
});

page.on("response", (r) => {
  if (r.status() < 400) return;
  const url = r.url();
  if (IGNORE.some((re) => re.test(url))) return;
  problems.push(`HTTP ${r.status()} ${url}`);
  console.log(`  [http ${r.status()}] ${url}`);
});
page.on("pageerror", (e) => {
  problems.push(`pageerror: ${e.message}`);
  console.log(`  [pageerror] ${e.message}`);
});

try {
  console.log(`opening ${URL}`);
  await page.goto(URL, { waitUntil: "networkidle" });

  // First-run consent gate. Continue without storing anything — the default,
  // and the path that must work for a learner who consents to nothing.
  const skip = page.getByRole("button", { name: /Hech narsa saqlamasdan|Продолжить, ничего/ });
  if (await skip.isVisible().catch(() => false)) {
    console.log("consent gate: continuing without storage");
    await skip.click();
  }
  await shot(page, "01-home");

  // The app opens on TODAY now, not on the picker. Practice is a tab, so get
  // there first — the seeded place then restores inside it.
  const practiceTab = page.locator(".tab", { hasText: /Mashq|Практика/ });
  if (await practiceTab.count()) {
    await practiceTab.click();
    await page.waitForTimeout(900);
  }

  // The seeded place has already opened the sura in verse-by-verse mode. Only
  // fall back to searching if that restore did not happen.
  if (!(await page.locator(".modes").count())) {
    console.log("no restore — falling back to the search box");
    const search = page.getByPlaceholder(/Sura nomi|Название/);
    await search.fill(String(SURA));
    await page.waitForTimeout(500);
    await page.locator(".row").first().click();
    await page.locator(".modes").waitFor({ timeout: 20000 });
  }
  await page.getByRole("tab", { name: /Oyatma-oyat|По аятам/ }).click();
  await page.locator(".verse").waitFor({ timeout: 20000 });

  // Step to the ayah under test. Seeding lands it there already, so this is a
  // correction, not the route — and if it cannot get there, that is a failure
  // rather than "recite whatever is on screen", which is how a previous run
  // silently recited into the wrong sura.
  const currentAya = async () =>
    Number((await page.locator(".verse__ref").textContent())?.match(/(\d+)\s*$/)?.[1] ?? 0);
  for (let i = 0; i < 40 && (await currentAya()) !== AYA; i++) {
    const at = await currentAya();
    await page.locator(".verse__arrow").nth(at < AYA ? 1 : 0).click();
    await page.waitForTimeout(250);
  }
  const ref = await page.locator(".verse__ref").textContent();
  console.log(`on verse: ${ref?.trim()}  (want ${SURA}:${AYA})`);
  if ((await currentAya()) !== AYA) {
    throw new Error(`could not reach ayah ${AYA}; stuck on "${ref?.trim()}"`);
  }
  await shot(page, "02-verse");

  await page.locator(".verse__actions .record").click();
  await page.locator(".ayah__text").first().waitFor({ timeout: 20000 });
  await shot(page, "02-selected");

  // Record. The fake device plays the WAV into getUserMedia in REAL TIME, so
  // this must wait at least as long as the clip.
  //
  // Timed from the CLIP, not from the ayah's estimate — see wavSeconds(). A
  // small tail lets the last phoneme land without adding enough silence to
  // trip the collapse gate.
  const clip = wavSeconds(WAV);
  const waitMs = Math.round((clip > 0 ? clip : 6) * 1000) + 600;

  const rec = page.getByRole("button", { name: /Oʻqishni boshlash|Начать чтение/ });
  await rec.waitFor({ timeout: 15000 });
  console.log(`recording… (clip ${clip.toFixed(1)}s, waiting ${waitMs}ms)`);
  await rec.click();
  await page.waitForTimeout(waitMs);

  const stop = page.getByRole("button", { name: /^Toʻxtatish|^Остановить/ });
  await stop.first().click();
  console.log("stopped; waiting for inference (model load can take ~30 s)…");

  // Results, or a retry notice, or the crash.
  // NOTE the `null`: waitForFunction is (fn, arg, options). Passing the
  // options object as `arg` silently leaves the 30 s default in place, which
  // is far shorter than a cold model load.
  await page.waitForFunction(
    () =>
      document.querySelector(".card, .clear, .notice") !== null &&
      !document.querySelector(".waiting"),
    null,
    { timeout: 300000 },
  );
  await page.waitForTimeout(1200);
  await shot(page, "03-results");

  // What actually rendered?
  const state = await page.evaluate(() => {
    const txt = (el) => (el ? el.textContent.trim().slice(0, 160) : null);
    return {
      rootChildren: document.getElementById("root")?.childElementCount ?? 0,
      bodyChars: document.body.innerText.trim().length,
      // CORRECTION cards specifically. The results screen also opens with a
      // verdict card — one sentence saying how many places to look at — which
      // is a `section`, not an `article`, and has no headline, no fix and no
      // ladder by design. Counting it as a correction made the first-card
      // checks below fail on a screen that was rendering perfectly.
      cards: document.querySelectorAll("article.card").length,
      brokenCards: document.querySelectorAll(".card--broken").length,
      redLetters: document.querySelectorAll(".ayah__mark").length,
      hitTargets: document.querySelectorAll(".ayah__hit").length,
      selfPlayback: document.querySelectorAll(".selfplay__btn").length,
      // The four-slot card: the practice ladder replaced both the prose drill
      // and the single "re-record this word" button.
      ladders: document.querySelectorAll(".ladder").length,
      rungs: document.querySelectorAll(".rung").length,
      // The quiet button plays the isolated-letter audio and carries the same
      // base class, so it has to be excluded — it is not a record control.
      recordableRungs: document.querySelectorAll(
        ".rung__btn:not(.rung__btn--quiet)",
      ).length,
      letterAudioButtons: document.querySelectorAll(".rung__btn--quiet").length,
      // Must be ZERO: the collapsed "Why" and "Practice" disclosures are gone.
      disclosures: document.querySelectorAll(".card__more").length,
      kickers: [...document.querySelectorAll(".card__kicker")].map((e) =>
        e.textContent.trim(),
      ),
      counts: [...document.querySelectorAll(".card__count")].map((e) =>
        e.textContent.trim(),
      ),
      notice: txt(document.querySelector(".notice")),
      clear: txt(document.querySelector(".clear")),
    };
  });
  console.log("\n--- rendered state ---");
  console.log(JSON.stringify(state, null, 2));

  // THE ACTUAL SENTENCES A LEARNER READS. The point of driving a browser is to
  // see this, not to count elements.
  const cardText = await page.evaluate(() =>
    [...document.querySelectorAll("article.card")].slice(0, 6).map((c) => ({
      kicker: c.querySelector(".card__kicker")?.innerText.trim() ?? "",
      headline: c.querySelector(".card__headline")?.innerText.trim() ?? "",
      where: c.querySelector(".where__words")?.innerText.trim() ?? "",
      correct:
        c.querySelector(".where__pair")?.innerText.replace(/\s+/g, " ").trim() ??
        "",
      fix: c.querySelector(".card__body--fix")?.innerText.trim() ?? "",
      ladder: [...c.querySelectorAll(".rung")].map((r) =>
        r.innerText.replace(/\s+/g, " ").trim(),
      ),
      broken: c.classList.contains("card--broken"),
    })),
  );
  console.log("\n--- what the learner actually reads ---");
  for (const [i, c] of cardText.entries()) {
    console.log(`\n[card ${i + 1}]${c.broken ? "  ** BROKEN **" : ""}`);
    console.log(`  kicker   : ${c.kicker}`);
    console.log(`  headline : ${c.headline}`);
    console.log(`  where    : ${c.where}`);
    if (c.correct) console.log(`  correct  : ${c.correct}`);
    console.log(`  fix      : ${c.fix || "(none shown)"}`);
    for (const [j, r] of c.ladder.entries())
      console.log(`  rung ${j + 1}   : ${r}`);
  }
  if (cardText.some((c) => c.broken)) {
    problems.push("at least one card rendered the broken-card fallback");
  }
  if (cardText.length && !cardText[0].headline && !cardText[0].fix) {
    problems.push("first card has neither a headline nor a fix — empty card");
  }

  // The stale-API banner must NOT be showing when client and server agree.
  if (await page.locator(".notice--stale").count()) {
    const txt = await page.locator(".notice--stale").innerText();
    problems.push(`stale-API banner is showing: ${txt.replace(/\n/g, " ")}`);
  }

  if (state.rootChildren === 0 || state.bodyChars < 20) {
    problems.push("WHITE SCREEN: React root is empty");
  }

  // Internal codes must never reach the screen.
  const leaked = await page.evaluate(() => {
    const text = document.body.innerText;
    return [
      "LETTER_ADDED", "LETTER_DROPPED", "GENERIC_SIFAT_MISMATCH",
      "GENERIC_LETTER_SUBSTITUTED", "SUB_SAD_SEEN", "MADD_SHORT",
      "QALQALA_DROP", "GHUNNA_LONG", "SHADDA_LONG", "TAFKHEEM_LOST",
      "QALQALAH_MISSING", "MAKHARIJ_TA_TO_DAL",
      // QPS notation symbols. Not codes, but the same rule: a learner must
      // never be shown a character that is not in the text in front of them.
      // ۥ and ۦ are excluded — the mushaf writes both as real superscripts.
      "ڇ", "ں", "۾",
    ].filter((c) => text.includes(c));
  });
  if (leaked.length)
    problems.push(`internal codes or QPS marks on screen: ${leaked.join(", ")}`);

  // Tap a red letter -> should focus its card.
  if (state.hitTargets > 0) {
    console.log("\ntapping a red letter…");
    await page.locator(".ayah__hit").first().click();
    await page.waitForTimeout(900);
    const active = await page.locator(".card--active").count();
    console.log(`  active cards after tap: ${active}`);
    if (active === 0) problems.push("tapping a red letter focused no card");
    await shot(page, "04-letter-tapped");
  } else if (state.cards > 0) {
    problems.push("cards rendered but no red letters marked in the ayah");
  }

  // THE UNLOCK CHAIN. The ladder is an order, so the word rung starts locked
  // and the only live control is the self-check on rung 1. Clearing the narrow
  // rungs in turn is what opens the recorded one — which is the behaviour to
  // verify, not a step to skip past.
  // Always the first rung NOT yet cleared. A cleared rung keeps its self-check
  // button (relabelled "yana aytdim"), so taking `.rung__btn--self` first()
  // clicks rung 1 over and over and rung 2 never opens — which reads exactly
  // like the unlock chain being broken.
  const nextSelf = () =>
    page
      .locator("article.card")
      .first()
      .locator(".rung:not(.rung--done) .rung__btn--self");
  for (let i = 0; i < 4; i++) {
    if ((await nextSelf().count()) === 0) break;
    console.log("  clearing a self-check rung…");
    await nextSelf().first().click();
    await page.waitForTimeout(350);
  }
  await shot(page, "05-unlocked");

  const recBtn = page
    .locator("article.card")
    .first()
    .locator(".rung__btn:not(.rung__btn--quiet):not(.rung__btn--self)");
  if ((await recBtn.count()) > 0) {
    console.log("starting a rung recording…");
    await recBtn.first().click();
    await page.waitForTimeout(1500);
    await shot(page, "06-rung-recording");
    const live = await page.locator(".rung__btn--live").count();
    console.log(`  rung record button live: ${live > 0}`);
    if (live === 0)
      problems.push("rung record button did not enter the recording state");
  } else {
    problems.push("no recordable rung ever unlocked on the first card");
  }
} catch (err) {
  problems.push(`driver: ${err.message}`);
  await shot(page, "99-failure").catch(() => {});
} finally {
  console.log("\n=====================================");
  if (problems.length) {
    console.log(`FAILED — ${problems.length} problem(s):`);
    for (const p of problems) console.log(`  - ${p}`);
  } else {
    console.log("PASSED — real recitation rendered with no console errors");
  }
  console.log("=====================================");
  await browser.close();
  process.exit(problems.length ? 1 : 0);
}
