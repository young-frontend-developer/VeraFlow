/**
 * The picker, the sura data, and the practice flow — checked against the
 * RUNNING app rather than against the source.
 *
 * ── WHY THIS EXISTS ────────────────────────────────────────────────────────
 *
 * The sura list once rendered 1, 60, 61, 62… because it was grouped into
 * ayah-count bands rather than left in mushaf order, and nothing caught it:
 * the code had no sort to be wrong, the tests asserted on the data, and the
 * data was fine. The bug lived entirely in what the browser painted.
 *
 * So this reads the rendered DOM — every row, in order — and asserts on the
 * list a learner actually sees. Same for the corrected transliteration, which
 * is checked off the row rather than off the JSON.
 *
 *   node e2e-picker.mjs        (needs the app on :5199 and an API behind it)
 */
import { chromium } from "playwright";
import path from "node:path";
import fs from "node:fs";

const URL = "http://localhost:5199";
const OUT = path.resolve("./shots");
fs.mkdirSync(OUT, { recursive: true });

const problems = [];
const checks = [];
const ok = (name, pass, detail = "") => {
  checks.push(`${pass ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`);
  if (!pass) problems.push(name);
};

const browser = await chromium.launch({ channel: "chrome" });
const ctx = await browser.newContext({
  viewport: { width: 430, height: 932 },
  deviceScaleFactor: 2,
});
const page = await ctx.newPage();
page.on("console", (m) => {
  if (m.type() !== "error") return;
  if (/favicon|Failed to load resource/i.test(m.text())) return;
  problems.push(`console.error: ${m.text()}`);
});
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));

const shot = async (name, full = false) => {
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: full });
};

const seed = async (extra = {}) => {
  await page.goto(URL);
  await page.evaluate((v) => {
    localStorage.clear();
    for (const [k, val] of Object.entries(v)) localStorage.setItem(k, val);
  }, {
    veyraflow_entry_done: "1",
    tilawah_auth_seen: "1",
    tilawah_consent_seen: "1",
    tilawah_consent: "1",
    tilawah_lang: "uz",
    tilawah_device_id: "screenshot-device-0001",
    ...extra,
  });
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1600);
};

try {
  await seed();

  // ── 3. the nav row ─────────────────────────────────────────────────────
  const labels = await page.locator(".tabbar .tab").allInnerTexts();
  ok(
    "3 nav order",
    JSON.stringify(labels.map((s) => s.trim())) ===
      JSON.stringify(["Bosh sahifa", "Oʻrganish", "Mashq", "Natijalar", "Profil"]),
    labels.map((s) => s.trim()).join(" | "),
  );

  // ── 2. no language toggle on a main screen ─────────────────────────────
  ok("2 no lang toggle on Home", (await page.locator(".app__header .lang").count()) === 0);
  await shot("fix-01-home");

  // ── 6 + 7. the picker ──────────────────────────────────────────────────
  await page.locator(".tab--center").click();
  await page.waitForTimeout(2500);
  // Nothing was stored, so the centre falls through to the chooser.
  await page.locator(".picker").waitFor({ timeout: 20000 });
  await shot("fix-02-picker-top");

  // THE WHOLE LIST, in the order the browser painted it.
  const nums = await page.$$eval(".row--sura .sura-badge", (els) =>
    els.map((e) => Number(e.textContent.trim())),
  );
  const expected = Array.from({ length: 114 }, (_, i) => i + 1);
  ok("6 all 114 rendered", nums.length === 114, `got ${nums.length}`);
  ok(
    "6 strict mushaf order",
    JSON.stringify(nums) === JSON.stringify(expected),
    `first 8: ${nums.slice(0, 8).join(", ")}`,
  );

  // ── 5. the corrected name, read off the row ────────────────────────────
  const s60 = await page
    .locator(".row--sura", { has: page.locator(".sura-badge", { hasText: /^60$/ }) })
    .first()
    .innerText();
  ok("5 sura 60 name", /Al-Mumtahana/.test(s60) && !/Mumtahina/.test(s60),
     s60.replace(/\n/g, " · "));

  // scroll the whole list to be sure nothing breaks further down
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(400);
  await shot("fix-03-picker-bottom");
  const lastNum = (await page.$$eval(".row--sura .sura-badge", (els) =>
    els.map((e) => e.textContent.trim()),
  )).at(-1);
  ok("6 list ends at 114", lastNum === "114", `last = ${lastNum}`);
  await page.evaluate(() => window.scrollTo(0, 0));

  // ── 7. search matches all three name forms ─────────────────────────────
  const search = page.getByPlaceholder(/Sura nomi|sura/i).first();
  for (const [q, want] of [["gofir", 40], ["Ixlos", 112], ["الناس", 114], ["60", 60]]) {
    await search.fill(String(q));
    await page.waitForTimeout(350);
    const got = await page.$$eval(".row--sura .sura-badge", (els) =>
      els.map((e) => Number(e.textContent.trim())),
    );
    ok(`7 search "${q}"`, got.includes(want), `matched ${got.slice(0, 6).join(",")}`);
  }
  await search.fill("");
  await page.waitForTimeout(300);

  // ── 7. filter pills ────────────────────────────────────────────────────
  const pillNames = (await page.locator(".pill").allInnerTexts()).map((s) => s.trim());
  ok("7 pills present", pillNames.length >= 3, pillNames.join(" | "));

  await page.locator(".pill", { hasText: "Madaniy" }).first().click();
  await page.waitForTimeout(350);
  const madani = await page.$$eval(".row--sura .sura-badge", (els) =>
    els.map((e) => Number(e.textContent.trim())),
  );
  ok("7 madani filter", madani.length === 28, `${madani.length} rows`);
  ok("7 madani ordered", JSON.stringify(madani) === JSON.stringify([...madani].sort((a, b) => a - b)));
  await shot("fix-04-picker-madani");

  await page.locator(".pill", { hasText: "Makkiy" }).first().click();
  await page.waitForTimeout(350);
  const makki = await page.$$eval(".row--sura .sura-badge", (e) => e.length);
  ok("7 makki filter", makki === 86, `${makki} rows`);

  const started = page.locator(".pill", { hasText: "Boshlangan" });
  if (await started.count()) {
    await started.first().click();
    await page.waitForTimeout(350);
    const st = await page.$$eval(".row--sura .sura-badge", (els) =>
      els.map((e) => Number(e.textContent.trim())),
    );
    ok("7 started filter", st.length > 0 && st.length < 114, `${st.length} rows: ${st.join(",")}`);
  } else {
    ok("7 started pill hidden with no history", true, "(no rows for this device)");
  }
  await page.locator(".pill", { hasText: "Barchasi" }).first().click();
  await page.waitForTimeout(300);

  // ── 8. study mode tabs ─────────────────────────────────────────────────
  await page.locator(".row--sura").first().click();
  await page.locator(".study").waitFor({ timeout: 20000 });
  const study = (await page.locator(".study__tab").allInnerTexts()).map((s) =>
    s.replace(/\s+/g, " ").trim(),
  );
  ok("8 study tabs", study.length === 2 && /Oʻqish/.test(study[0]) && /Yodlash/.test(study[1]),
     study.join(" | "));
  ok("8 memorize disabled", await page.locator(".study__tab--soon").isDisabled());
  // Case-insensitive: the chip is uppercased by CSS, so innerText comes back
  // "TEZ ORADA" while the string in i18n is "Tez orada".
  ok("8 memorize says coming soon", /tez orada/i.test(study[1]), study[1]);
  await shot("fix-05-study-tabs");

  // ── 9. practice header: X and arrows ───────────────────────────────────
  await page.getByRole("tab", { name: /Oyatma-oyat/ }).click();
  await page.locator(".verse").waitFor({ timeout: 20000 });
  await page.locator(".verse__actions .record").click();
  await page.locator(".ayah-nav").waitFor({ timeout: 20000 });
  ok("9 close button present", (await page.locator(".ayah-nav__close").count()) === 1);
  ok("9 arrows present", (await page.locator(".ayah-nav__arrow").count()) === 2);
  ok("9 old text link gone", (await page.getByText("Boshqa oyat tanlash").count()) === 0);
  // Position is read off the heading, which is the one place it is printed.
  const where = await page.locator(".eyebrow__meta").first().innerText();
  await shot("fix-06-practice-nav");

  // step forward and confirm the ayah actually changed
  await page.locator(".ayah-nav__arrow--next").click();
  await page.waitForTimeout(2200);
  const where2 = await page.locator(".eyebrow__meta").first().innerText();
  ok("9 next arrow moves ayah", where2 !== where, `${where} -> ${where2}`);

  // the X exits straight to the full list
  await page.locator(".ayah-nav__close").click();
  await page.waitForTimeout(1800);
  const backToList = await page.locator(".row--sura").count();
  ok("9 X exits to full sura list", backToList === 114, `${backToList} rows`);
  await shot("fix-07-after-close");

  // ── 1. light mode ──────────────────────────────────────────────────────
  await page.locator(".tab", { hasText: "Profil" }).click();
  await page.waitForTimeout(1400);
  await shot("fix-08-profile-dark");
  await page.getByRole("button", { name: /Kunduzgi/ }).click();
  await page.waitForTimeout(600);
  const themeAttr = await page.evaluate(() =>
    document.documentElement.getAttribute("data-theme"),
  );
  ok("1 light theme applies", themeAttr === "light", `data-theme=${themeAttr}`);
  const bg = await page.evaluate(() =>
    getComputedStyle(document.body).backgroundColor,
  );
  ok("1 ground is ivory", /250, 248, 244/.test(bg), bg);
  await shot("fix-09-profile-light");

  await page.locator(".tab", { hasText: "Bosh sahifa" }).click();
  await page.waitForTimeout(1600);
  await shot("fix-10-home-light", true);

  await page.locator(".tab--center").click();
  await page.waitForTimeout(2200);
  await shot("fix-11-picker-light");

  // persists across a reload
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  const after = await page.evaluate(() =>
    document.documentElement.getAttribute("data-theme"),
  );
  ok("1 light theme persists", after === "light", `data-theme=${after}`);

  // ── 10. the qalam, in the nav ──────────────────────────────────────────
  await shot("fix-12-nav-light");
} catch (err) {
  problems.push(`driver: ${err.message}`);
  await shot("99-failure").catch(() => {});
} finally {
  console.log("\n" + checks.join("\n"));
  console.log("\n====================================");
  const fails = problems.length;
  console.log(fails ? `${fails} problem(s):\n  - ${problems.join("\n  - ")}` : "all checks passed");
  console.log("====================================");
  await browser.close();
  process.exit(fails ? 1 : 0);
}
