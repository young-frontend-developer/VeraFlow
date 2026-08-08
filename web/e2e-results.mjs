/**
 * The two things that only exist AFTER an analysis: the playback comparison
 * (item 9) and the hasanat refetch (item 4).
 *
 * The acoustic model does not fit in memory on this machine, so the POST is
 * answered from a payload built by the REAL card pipeline — real capture, real
 * error code, real locate()/present()/practice.ladder(). Only the model is
 * substituted. That makes this a genuine test of the CLIENT, which is what
 * both items are about.
 *
 * The GET is served from a list that GROWS when the POST is made, which is
 * exactly the condition the hasanat bug was hiding in: the numbers were right
 * for the rows the app held and it never asked for new ones.
 */
import { chromium } from "playwright";
import path from "node:path";
import fs from "node:fs";

const URL = "http://localhost:5199";
const OUT = path.resolve("./shots");
const SCRATCH =
  "C:/Users/Rahmatulloh/AppData/Local/Temp/claude/C--Users-Rahmatulloh-Desktop-Tilawah/3c0d3642-d899-4867-9888-003502a34945/scratchpad";
const CARD = JSON.parse(fs.readFileSync(`${SCRATCH}/attempt.json`, "utf8"));
fs.mkdirSync(OUT, { recursive: true });

const problems = [];
const checks = [];
const ok = (n, pass, d = "") => {
  checks.push(`${pass ? "PASS" : "FAIL"}  ${n}${d ? ` — ${d}` : ""}`);
  if (!pass) problems.push(n);
};

// The history the fake server holds. Starts with one row; the POST appends.
const LETTERS_PER_ROW = 30;
let history = [
  { id: 1, sura: 110, aya: 1, status: "ok", clean: true, suppressed: false,
    analysable: true, errors: [], snr_db: 24, duration_s: 8, score: 0.9,
    pass_score: 0.9, created_at: new Date().toISOString(),
    letters: LETTERS_PER_ROW },
];

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

await page.route("**/api/attempts*", async (route) => {
  const req = route.request();
  if (req.method() === "POST") {
    history = [
      { ...history[0], id: history.length + 1, sura: 103, aya: 1 },
      ...history,
    ];
    return route.fulfill({
      status: 200, contentType: "application/json", body: JSON.stringify(CARD),
    });
  }
  return route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify(history),
  });
});
// everyayah is not reachable from here; answer the reciter file so the
// comparison button has a src that resolves.
await page.route("**/*.mp3", (r) =>
  r.fulfill({ status: 200, contentType: "audio/mpeg", body: Buffer.alloc(64) }));

const shot = async (n, full = false) => {
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(OUT, `${n}.png`), fullPage: full });
};

try {
  await page.goto(URL);
  await page.evaluate(() => {
    localStorage.clear();
    const s = {
      veyraflow_entry_done: "1", tilawah_auth_seen: "1",
      tilawah_consent_seen: "1", tilawah_consent: "1", tilawah_lang: "uz",
      tilawah_device_id: "verify-results", tilawah_place: "103:1",
      veyraflow_theme: "dark",
    };
    for (const [k, v] of Object.entries(s)) localStorage.setItem(k, v);
  });
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1800);

  // ── 4. the total BEFORE reciting ──────────────────────────────────────
  const readHasanat = async () =>
    (await page.locator(".stat-tile", { hasText: /HASANAT/i })
      .locator(".stat-tile__value").innerText()).trim();
  const before = await readHasanat();
  ok("4 baseline hasanat", before === "300", `${before} (1 row x 30 letters x 10)`);

  // ── recite ────────────────────────────────────────────────────────────
  await page.locator(".tab--center").click();
  await page.locator(".ayah-nav").waitFor({ timeout: 25000 });
  const rec = page.getByRole("button", { name: /Oʻqishni boshlash/ });
  await rec.waitFor({ timeout: 15000 });
  await rec.click();
  await page.waitForTimeout(2200);
  await page.getByRole("button", { name: /^Toʻxtatish/ }).first().click();
  await page.waitForFunction(
    () => document.querySelector("article.card") !== null &&
          !document.querySelector(".waiting"),
    null, { timeout: 60000 },
  );
  await page.waitForTimeout(900);

  // ── 9. the comparison pair ────────────────────────────────────────────
  const pair = page.locator(".compare__btn");
  ok("9 two playback buttons", (await pair.count()) === 2, `${await pair.count()}`);
  const labels = (await pair.allInnerTexts()).map((s) => s.trim());
  ok("9 labelled mine + reciter",
     /Mening oʻqishim/.test(labels[0]) && /Qori oʻqishi/.test(labels[1]),
     labels.join(" | "));

  // Equal weight: same box, side by side on one row.
  const b0 = await pair.nth(0).boundingBox();
  const b1 = await pair.nth(1).boundingBox();
  ok("9 equal width", Math.abs(b0.width - b1.width) < 2,
     `${Math.round(b0.width)} vs ${Math.round(b1.width)}`);
  ok("9 equal height", Math.abs(b0.height - b1.height) < 2,
     `${Math.round(b0.height)} vs ${Math.round(b1.height)}`);
  ok("9 same row", Math.abs(b0.y - b1.y) < 2, `y ${Math.round(b0.y)} / ${Math.round(b1.y)}`);
  ok("9 left is mine, right is reciter", b0.x < b1.x);
  ok("9 old standalone listen control gone",
     (await page.locator(".selfplay").count()) === 0);

  // THE COMPARISON MUST NOT BE UNDER THE RECORDER. The studio unpins once a
  // result is on screen precisely so it stops covering this row — the first
  // version pinned it always and the two overlapped exactly here.
  ok("5 studio unpins once results are shown",
     (await page.locator(".studio--pinned").count()) === 0);
  const studioBox = await page.locator(".studio").boundingBox();
  ok(
    "9 comparison is not covered by the recorder",
    !studioBox || b0.y >= studioBox.y + studioBox.height - 1 ||
      b0.y + b0.height <= studioBox.y + 1,
    `compare y=${Math.round(b0.y)}, studio ${Math.round(studioBox?.y ?? -1)}–${Math.round((studioBox?.y ?? 0) + (studioBox?.height ?? 0))}`,
  );
  await shot("r3-08-compare");

  // ── 4. the total AFTER, without a reload ──────────────────────────────
  await page.locator(".tab", { hasText: "Bosh sahifa" }).click();
  await page.locator(".stat-grid").waitFor({ timeout: 20000 });
  await page.waitForTimeout(1200);
  const after = await readHasanat();
  ok("4 hasanat increased with no reload", after === "600",
     `${before} -> ${after} (2 rows x 30 x 10)`);
  await shot("r3-09-hasanat-after");
} catch (err) {
  problems.push(`driver: ${err.message}`);
  await shot("r3-99-results-failure").catch(() => {});
} finally {
  console.log("\n" + checks.join("\n"));
  console.log("\n====================================");
  console.log(problems.length ? `${problems.length} problem(s):\n  - ${problems.join("\n  - ")}` : "all checks passed");
  console.log("====================================");
  await browser.close();
  process.exit(problems.length ? 1 : 0);
}
