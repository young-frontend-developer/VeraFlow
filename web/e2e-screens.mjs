/**
 * Walk every screen and state, and photograph each one.
 *
 * This exists because a design system is a claim about CONSISTENCY, and
 * consistency is the one property you cannot check by reading the code that
 * produces it. Ten screens each look right in isolation; whether they look like
 * the same product is only visible side by side.
 *
 * It also fails loudly on any console error, so a screen cannot look finished
 * in a screenshot while throwing underneath.
 *
 *   node e2e-screens.mjs [--url http://localhost:5199]
 */
import { chromium } from "playwright";
import path from "node:path";
import fs from "node:fs";

const arg = (name, dflt) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : dflt;
};

const URL = arg("url", "http://localhost:5199");
const OUT = path.resolve(arg("out", "./screens"));
fs.mkdirSync(OUT, { recursive: true });

const problems = [];
const browser = await chromium.launch({
  channel: "chrome",
  args: [
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    "--autoplay-policy=no-user-gesture-required",
  ],
});

// A tall phone. The system is designed mobile-first and the floating nav needs
// real estate below the fold to prove it clears the content.
const ctx = await browser.newContext({
  viewport: { width: 430, height: 932 },
  deviceScaleFactor: 2,
  permissions: ["microphone"],
});
const page = await ctx.newPage();

page.on("console", (m) => {
  if (m.type() !== "error") return;
  const text = m.text();
  if (/favicon|Failed to load resource/i.test(text)) return;
  problems.push(`console.error: ${text}`);
});
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));

/**
 * `full` captures the whole scroll height, which is what you want for judging a
 * screen's composition. It is NOT usable past ~16000px: Chrome stitches tall
 * captures and a 114-row list comes back duplicated and misaligned, which reads
 * as a rendering bug in the app rather than in the camera. Long screens are
 * therefore shot at viewport height, the way a phone actually shows them.
 */
const shot = async (name, { full = true } = {}) => {
  await page.waitForTimeout(450);
  const h = await page.evaluate(() => document.body.scrollHeight);
  await page.screenshot({
    path: path.join(OUT, `${name}.png`),
    fullPage: full && h < 15000,
  });
  console.log(`  · ${name}${full && h >= 15000 ? " (viewport — page too tall)" : ""}`);
};

/** Reset to a first-run device. */
const fresh = async (seed = {}) => {
  await ctx.clearCookies();
  await page.goto(URL);
  await page.evaluate((s) => {
    localStorage.clear();
    for (const [k, v] of Object.entries(s)) localStorage.setItem(k, v);
  }, seed);
  await page.reload({ waitUntil: "networkidle" });
};

const SETTLED = {
  tilawah_consent_seen: "1",
  tilawah_consent: "0",
  tilawah_consent_audio: "0",
  tilawah_lang: "uz",
};

try {
  // ── 1. onboarding, all four steps ──────────────────────────────────────
  console.log("onboarding");
  await fresh();
  await shot("01-onboard-welcome");
  await page.getByRole("button", { name: /Boshlash/ }).click();
  await shot("02-onboard-language");
  await page.getByRole("button", { name: /Davom etish/ }).click();
  await shot("03-onboard-level");
  await page.locator(".choice__item").first().click();
  await page.getByRole("button", { name: /Davom etish/ }).click();
  await shot("04-onboard-consent");

  // ── 2. today, first run (no place stored) ──────────────────────────────
  console.log("today");
  await page.getByRole("button", { name: /Hech narsa saqlamasdan|Davom/ }).first().click();
  await page.waitForTimeout(900);
  await shot("05-today-firstrun");

  // ── today with a place and a suggestion ────────────────────────────────
  await fresh({ ...SETTLED, tilawah_place: "112:3" });
  await page.waitForTimeout(1600);
  await shot("06-today-resume");

  // ── 3+5. practice picker: grouped browse, search, no results ───────────
  console.log("picker");
  await fresh(SETTLED);
  await page.locator(".tab", { hasText: "Mashq" }).click();
  await page.waitForTimeout(1200);
  await shot("07-picker-grouped");
  await page.getByPlaceholder(/Sura nomi/).fill("nasr");
  await shot("08-picker-search");
  await page.getByPlaceholder(/Sura nomi/).fill("zzzz");
  await shot("09-picker-no-results");
  await page.getByPlaceholder(/Sura nomi/).fill("110");
  await page.locator(".row").first().click();
  await page.locator(".modes").waitFor({ timeout: 20000 });

  // ── 3. mushaf ──────────────────────────────────────────────────────────
  console.log("reader");
  await shot("10-mushaf");

  // ── 4. verse by verse ──────────────────────────────────────────────────
  await page.getByRole("tab", { name: /Oyatma-oyat/ }).click();
  await page.locator(".verse").waitFor({ timeout: 20000 });
  await shot("11-verse");

  // ── 6. the dark recording card ─────────────────────────────────────────
  console.log("studio");
  await page.locator(".verse__actions .record").click();
  await page.locator(".ayah__text").first().waitFor({ timeout: 20000 });
  await shot("12-studio-idle");

  await page.locator(".mic").click();
  await page.waitForTimeout(2200);
  await shot("13-studio-recording");
  await page.locator(".mic").click();
  await page.waitForTimeout(1200);
  await shot("14-studio-analyzing");

  // ── 7. results ─────────────────────────────────────────────────────────
  console.log("results (waiting on inference)");
  await page
    .waitForFunction(
      () =>
        document.querySelector(".card, .clear, .notice") !== null &&
        !document.querySelector(".waiting"),
      null,
      { timeout: 300000 },
    )
    .catch(() => problems.push("results never rendered"));
  await page.waitForTimeout(1200);
  await shot("15-results");

  // ── 9 + 10. learn and memorize ─────────────────────────────────────────
  console.log("learn / memorize / profile");
  await page.locator(".tab", { hasText: "Oʻrganish" }).click();
  await shot("16-learn");
  await page.locator(".tab", { hasText: "Yodlash" }).click();
  await shot("17-memorize");

  // ── 8. profile ─────────────────────────────────────────────────────────
  await page.locator(".tab", { hasText: "Profil" }).click();
  await page.waitForTimeout(700);
  await shot("18-profile-no-consent");

  await page.locator(".consent__row input").first().check();
  await page.waitForTimeout(900);
  await shot("19-profile-consented");
} catch (err) {
  problems.push(`driver: ${err.message}`);
  await shot("99-failure").catch(() => {});
} finally {
  console.log("\n=====================================");
  if (problems.length) {
    console.log(`${problems.length} problem(s):`);
    for (const p of problems) console.log(`  - ${p}`);
  } else {
    console.log("every screen rendered with no console errors");
  }
  console.log("=====================================");
  await browser.close();
  process.exit(problems.length ? 1 : 0);
}
