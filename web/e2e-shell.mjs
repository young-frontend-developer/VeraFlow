/**
 * Verify this round's nine items against the RUNNING app.
 *
 * Item 3 was marked done last round on the strength of the source and was not
 * actually fixed, so everything here is read out of the rendered DOM or
 * measured off real geometry — including the icon, which is checked by
 * comparing its path data to what the running bundle actually serves.
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

const browser = await chromium.launch({
  channel: "chrome",
  args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
});
const ctx = await browser.newContext({
  viewport: { width: 430, height: 932 },
  deviceScaleFactor: 2,
  permissions: ["microphone"],
});
const page = await ctx.newPage();
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
page.on("console", (m) => {
  if (m.type() !== "error") return;
  if (/favicon|Failed to load resource/i.test(m.text())) return;
  problems.push(`console.error: ${m.text()}`);
});

const shot = async (n, full = false) => {
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(OUT, `${n}.png`), fullPage: full });
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
    veyraflow_theme: "dark",
    ...extra,
  });
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1800);
};

try {
  await seed();

  // ── the stale-server notice must NOT be showing against a fresh API ────
  ok("0 no version-skew notice", (await page.locator(".notice--stale").count()) === 0);

  // ── 4a. hasanat is non-zero from real seeded history ──────────────────
  const hasanat = await page
    .locator(".stat-tile", { hasText: /HASANAT/i })
    .locator(".stat-tile__value")
    .innerText();
  ok("4 hasanat reads a real total", hasanat.trim() !== "0", `"${hasanat.trim()}"`);
  await shot("r3-01-home");

  // ── 2. the filter pills ────────────────────────────────────────────────
  await page.locator(".tab--center").click();
  await page.locator(".picker").waitFor({ timeout: 25000 });
  const count = async () =>
    (await page.$$eval(".row--sura .sura-badge", (e) => e.map((x) => x.textContent.trim())));

  const all = await count();
  ok("2 all = 114", all.length === 114, `${all.length}`);

  await page.locator(".pill", { hasText: "Makkiy" }).first().click();
  await page.waitForTimeout(400);
  const makki = await count();
  ok("2 Makkiy filters", makki.length === 86, `${makki.length} rows`);
  ok("2 Makkiy list actually changed", makki.length !== all.length);
  await shot("r3-02-makki");

  await page.locator(".pill", { hasText: "Madaniy" }).first().click();
  await page.waitForTimeout(400);
  const madani = await count();
  ok("2 Madaniy filters", madani.length === 28, `${madani.length} rows`);
  ok("2 Madaniy differs from Makkiy", madani[0] !== makki[0], `${madani[0]} vs ${makki[0]}`);

  await page.locator(".pill", { hasText: "Barchasi" }).first().click();
  await page.waitForTimeout(300);

  // ── 3. the qalam, measured off the LIVE DOM ───────────────────────────
  const learnPath = await page.$eval(
    '.tab:nth-child(2) .tab__glyph svg',
    (svg) => [...svg.querySelectorAll("path")].map((p) => p.getAttribute("d")).join(" "),
  );
  // The chisel nib is a CLOSED wedge — the shape a cut reed has and a pencil
  // does not. Its presence in the live path data is the check.
  ok("3 qalam has a closed chisel nib", /z/i.test(learnPath), learnPath.slice(0, 60) + "…");
  ok("3 qalam is not the old pencil", !learnPath.includes("M16.2 2.9"), "old path absent");
  await page.locator(".tab").nth(1).scrollIntoViewIfNeeded();
  await shot("r3-03-nav-qalam");

  // ── 7 + 8. verse view: no practise button, pinned mic present ─────────
  await page.locator(".row--sura").first().click();
  await page.locator(".study").waitFor({ timeout: 25000 });
  await page.getByRole("tab", { name: /Oyatma-oyat/ }).click();
  await page.locator(".verse").waitFor({ timeout: 20000 });

  ok("8 no navigate-to-practice button", (await page.getByText("Bu oyatni oʻqish").count()) === 0);
  ok("8 verse view has a pinned mic", (await page.locator(".micbar__mic").count()) === 1);
  ok("6 no reciter picker in reader", (await page.locator(".reciter__select").count()) === 0);
  await shot("r3-04-verse-micbar");

  // The mic must be ON SCREEN without scrolling.
  const barBox = await page.locator(".micbar").boundingBox();
  const vh = page.viewportSize().height;
  const vwBar = page.viewportSize().width;
  ok(
    "5 verse mic is within the viewport",
    barBox && barBox.y > 0 && barBox.y + barBox.height <= vh,
    barBox ? `y=${Math.round(barBox.y)} h=${Math.round(barBox.height)} vh=${vh}` : "no box",
  );
  ok(
    "5 verse mic is centred horizontally",
    barBox && Math.abs(barBox.x - (vwBar - barBox.width) / 2) < 2,
    barBox ? `x=${Math.round(barBox.x)} w=${Math.round(barBox.width)} vw=${vwBar}` : "no box",
  );

  // ── 8. pressing it records inline ─────────────────────────────────────
  await page.locator(".micbar__mic").click();
  await page.locator(".studio--pinned").waitFor({ timeout: 25000 });
  await page.waitForTimeout(1500);
  const head = await page.locator(".studio__head").innerText();
  ok("8 mic starts recording immediately", /YOZILMOQDA|ЗАПИС/i.test(head), `head="${head.trim()}"`);
  await shot("r3-05-recording-pinned");

  // ── 5. the studio stays pinned in view on a long ayah ─────────────────
  const box1 = await page.locator(".studio--pinned").boundingBox();
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(400);
  const box2 = await page.locator(".studio--pinned").boundingBox();
  ok(
    "5 studio is fixed to the viewport",
    box1 && box2 && Math.abs(box1.y - box2.y) < 2,
    `y ${Math.round(box1?.y ?? -1)} -> ${Math.round(box2?.y ?? -1)}`,
  );
  ok(
    "5 studio sits above the tab bar",
    box2 && box2.y + box2.height <= vh,
    `bottom=${Math.round((box2?.y ?? 0) + (box2?.height ?? 0))} vh=${vh}`,
  );
  // HORIZONTAL TOO. The first version of this pinned card hung half off the
  // right edge and every vertical assertion still passed — a fixed element
  // needs both axes checked or the test agrees with a screenshot that is
  // obviously broken.
  const vw = page.viewportSize().width;
  ok(
    "5 studio is horizontally within the viewport",
    box2 && box2.x >= 0 && box2.x + box2.width <= vw + 1,
    `x=${Math.round(box2?.x ?? -1)} w=${Math.round(box2?.width ?? -1)} vw=${vw}`,
  );
  ok(
    "5 studio is centred",
    box2 && Math.abs(box2.x - (vw - box2.width) / 2) < 2,
    `left gap ${Math.round(box2?.x ?? -1)} vs right ${Math.round(vw - (box2?.x ?? 0) - (box2?.width ?? 0))}`,
  );
  // The nav's centre action breaks out ABOVE the bar, so "above the tab bar"
  // is not the same as "not touching the nav". Two gold discs in contact read
  // as one broken control.
  const navMic = await page.locator(".tab--center .tab__glyph").boundingBox();
  ok(
    "5 studio does not collide with the nav button",
    box2 && navMic && box2.y + box2.height < navMic.y,
    `studio bottom=${Math.round((box2?.y ?? 0) + (box2?.height ?? 0))} navMic top=${Math.round(navMic?.y ?? 0)}`,
  );

  // ── 6 + 7. practice screen carries neither control ────────────────────
  ok("6 no reciter picker on practice", (await page.locator(".reciter__select").count()) === 0);
  ok("7 no segment picker", (await page.locator(".list--parts").count()) === 0);
  ok("7 no 'practise part' link", (await page.getByText(/qismini oʻqish|Bir qismini/i).count()) === 0);

  // ── 1. light mode, structurally identical ─────────────────────────────
  // Probed on HOME, not on the recording screen: that screen has no `.card`
  // at all (the ayah is `.ayah` and the studio is `.studio`), so sampling a
  // card there measures nothing and reports it as a missing blur.
  await page.evaluate(() => {
    localStorage.setItem("veyraflow_theme", "light");
    document.documentElement.setAttribute("data-theme", "light");
  });
  await page.waitForTimeout(400);
  await shot("r3-06-light-recording");

  await page.locator(".ayah-nav__close").click().catch(() => {});
  await page.waitForTimeout(1200);
  await page.locator(".tab", { hasText: "Bosh sahifa" }).click();
  await page.locator(".card").first().waitFor({ timeout: 20000 });
  await page.waitForTimeout(800);

  const probe = await page.evaluate(() => {
    const cs = (sel, prop) => {
      const el = document.querySelector(sel);
      return el ? getComputedStyle(el)[prop] : "";
    };
    return {
      bodyBg: getComputedStyle(document.body).backgroundColor,
      groundImage: getComputedStyle(document.body, "::before").backgroundImage,
      patternOpacity: getComputedStyle(document.body, "::after").opacity,
      cardBlur: cs(".card", "backdropFilter"),
      cardImage: cs(".card", "backgroundImage"),
      navShadow: cs(".tab--center .tab__glyph", "boxShadow"),
      haloAnim: getComputedStyle(
        document.querySelector(".tab--center .tab__glyph"), "::after",
      ).animationName,
    };
  });
  ok("1 light ground is warm, not white", /247, 243, 236/.test(probe.bodyBg), probe.bodyBg);
  ok("1 ground keeps its gradient layers",
     (probe.groundImage.match(/radial-gradient/g) || []).length === 2,
     `${(probe.groundImage.match(/radial-gradient/g) || []).length} radial(s)`);
  ok("1 pattern layer still drawn", parseFloat(probe.patternOpacity) > 0, probe.patternOpacity);
  ok("1 cards keep the backdrop blur", /blur/.test(probe.cardBlur), probe.cardBlur);
  ok("1 cards keep the glass gradient", /gradient/.test(probe.cardImage), probe.cardImage.slice(0, 40) + "…");
  ok("1 centre button keeps its cast glow",
     (probe.navShadow.match(/rgba?\(/g) || []).length >= 4,
     `${(probe.navShadow.match(/rgba?\(/g) || []).length} shadow layers`);
  ok("1 halo animation retained", probe.haloAnim === "halo", probe.haloAnim);
  await shot("r3-07-light-home", true);
} catch (err) {
  problems.push(`driver: ${err.message}`);
  await shot("r3-99-failure").catch(() => {});
} finally {
  console.log("\n" + checks.join("\n"));
  console.log("\n====================================");
  console.log(problems.length ? `${problems.length} problem(s):\n  - ${problems.join("\n  - ")}` : "all checks passed");
  console.log("====================================");
  await browser.close();
  process.exit(problems.length ? 1 : 0);
}
