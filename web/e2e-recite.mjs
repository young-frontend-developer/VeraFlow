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
const SHOTS = path.resolve(arg("out", "./e2e-shots"));

if (!fs.existsSync(WAV)) {
  console.error(`no such wav: ${WAV}`);
  process.exit(2);
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

  // Pick sura 112, ayah 3 — the clip is a recitation of al-Ikhlas 3.
  const search = page.getByPlaceholder(/Sura nomi|Название/);
  if (await search.isVisible().catch(() => false)) {
    await search.fill("112");
    await page.waitForTimeout(500);
    await page.locator(".row").first().click();
    // The picker hands off to <Reader>, which has no .row — wait for its own
    // chrome instead of guessing a timeout.
    await page.locator(".modes").waitFor({ timeout: 20000 });
  }

  // Verse-by-verse mode, then step to ayah 3 and start practising it.
  await page.getByRole("tab", { name: /Oyatma-oyat|По аятам/ }).click();
  await page.locator(".verse").waitFor({ timeout: 20000 });
  for (let i = 0; i < 2; i++) {
    await page.locator(".verse__arrow").last().click();
    await page.waitForTimeout(400);
  }
  const ref = await page.locator(".verse__ref").textContent();
  console.log(`on verse: ${ref?.trim()}`);
  await shot(page, "02-verse");

  await page.locator(".verse__actions .record").click();
  await page.locator(".ayah__text").first().waitFor({ timeout: 20000 });
  await shot(page, "02-selected");

  // Record. The fake device plays the WAV into getUserMedia in real time, so
  // this has to wait roughly the clip's length.
  const rec = page.getByRole("button", { name: /Oʻqishni boshlash|Начать чтение/ });
  await rec.waitFor({ timeout: 15000 });
  console.log("recording…");
  await rec.click();
  await page.waitForTimeout(6000);

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
      cards: document.querySelectorAll(".card").length,
      brokenCards: document.querySelectorAll(".card--broken").length,
      redLetters: document.querySelectorAll(".ayah__mark").length,
      hitTargets: document.querySelectorAll(".ayah__hit").length,
      selfPlayback: document.querySelectorAll(".selfplay__btn").length,
      // The four-slot card: the practice ladder replaced both the prose drill
      // and the single "re-record this word" button.
      ladders: document.querySelectorAll(".ladder").length,
      rungs: document.querySelectorAll(".rung").length,
      recordableRungs: document.querySelectorAll(".rung__btn").length,
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
    [...document.querySelectorAll(".card")].slice(0, 6).map((c) => ({
      kicker: c.querySelector(".card__kicker")?.innerText.trim() ?? "",
      headline: c.querySelector(".card__headline")?.innerText.trim() ?? "",
      where: c.querySelector(".where__words")?.innerText.trim() ?? "",
      correct: c.querySelector(".where__pair")?.innerText.replace(/
/g, " ").trim() ?? "",
      fix: c.querySelector(".card__body--fix")?.innerText.trim() ?? "",
      ladder: [...c.querySelectorAll(".rung")].map((r) =>
        r.innerText.replace(/
/g, " ").trim(),
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

  // The per-word retry control has to exist and be clickable.
  if (state.retryButtons > 0) {
    console.log("starting a per-word retry…");
    await page.locator(".card__retry-btn").first().click();
    await page.waitForTimeout(1500);
    await shot(page, "05-retry-recording");
    const live = await page.locator(".card__retry-btn--live").count();
    console.log(`  retry button live: ${live > 0}`);
    if (live === 0) problems.push("retry button did not enter the recording state");
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
