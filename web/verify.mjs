/**
 * In-browser proof of the progressive-reveal advance path.
 *
 * Drives the REAL built app in Chromium with a FAKE MICROPHONE (Chromium's own
 * --use-fake-device-for-media-stream), so the real recorder, the real Recite
 * handlers and the real Feedback component all run. Only the API is stubbed,
 * because the bug is in the client's advance logic and the 2.4 GB model has
 * nothing to do with it.
 *
 * THE CASE THAT MATTERS: three errors in one ayah, and a re-read that clears
 * only the first. That is what deadlocked, and it is what no component test
 * produced.
 */
import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join } from "node:path";

const DIST = new URL("./dist/", import.meta.url).pathname.slice(1);
const MIME = {
  ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".woff": "font/woff", ".woff2": "font/woff2", ".svg": "image/svg+xml",
};

const server = createServer(async (req, res) => {
  const p = req.url.split("?")[0];
  const file = p === "/" ? "index.html" : p;
  try {
    const body = await readFile(join(DIST, file));
    res.writeHead(200, { "content-type": MIME[extname(file)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(200, { "content-type": "text/html" });
    res.end(await readFile(join(DIST, "index.html")));
  }
});
await new Promise((r) => server.listen(4319, r));

const card = (code, letter, at, kind, tier, order) => ({
  code, kind, at, letter, expected: letter, heard: "س",
  expected_count: 0, heard_count: 0, sifa: "",
  word: "ٱللَّهُ", word_index: 1, words: ["ٱللَّهُ"], count: 1,
  occurrences: [{ at, word: "ٱللَّهُ", word_index: 1 }],
  status: "collect", draft: true, needs_teacher: false,
  content: { headline: `H-${code}`, fix: `F-${code}`, severity: "high",
             reviewed: true, label: "", audio_pair: "", unauthored: false },
  practice: [
    { level: 1, focus: "word", items: ["ٱللَّهُ"], recordable: true, check: "score",
      word_index: 1, audio: "", audio_source: "", hold: 0 },
    { level: 2, focus: "ayah", items: [], recordable: true, check: "score",
      word_index: -1, audio: "", audio_source: "ayah", hold: 0 },
  ],
  rule_name: "", sifa_name: "", articulation: "", makhraj: "",
  tier, reveal_order: order,
});

const A = card("SUB_SAD_SEEN", "ص", 3, "wrong_letter", 1, 0);
const B = card("TAFKHEEM_LOST", "ط", 7, "pronunciation", 2, 1);
const C = card("MADD_TOO_LONG", "ا", 11, "madd", 4, 2);

const result = (errors, score) => ({
  id: 1, sura: 112, aya: 2, status: "ok", reason: "", clean: false,
  suppressed: false, analysable: true, errors,
  snr_db: 30, duration_s: 5, score, pass_score: 0.8, created_at: null,
});

let posts = 0;
const browser = await chromium.launch({
  args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
         "--autoplay-policy=no-user-gesture-required"],
});
const ctx = await browser.newContext({ permissions: ["microphone"] });
const page = await ctx.newPage();

await page.route("**/api/**", async (route) => {
  const url = route.request().url();
  const j = (b) => route.fulfill({ status: 200, contentType: "application/json",
                                   body: JSON.stringify(b) });
  if (url.includes("/api/meta")) {
    return j({ pilot: false, show_unreviewed: true, collect_audio_offered: false,
               max_audio_seconds: 120,
               error_fields: ["makhraj", "tier", "reveal_order"] });
  }
  if (url.includes("/api/suras/112/ayat")) {
    return j({ sura: 112, name_ar: "الإخلاص", translit: "Al-Ikhlas", n_ayat: 4,
      has_basmala: true, bismillah: "بِسْمِ ٱللَّهِ",
      ayat: [1, 2, 3, 4].map((a) => ({ aya: a, uthmani: "ٱللَّهُ ٱلصَّمَدُ",
        n_words: 2, n_segments: 2, seconds: 4, translation: "" })) });
  }
  if (url.includes("/api/suras")) {
    return j([{ number: 112, name_ar: "الإخلاص", translit: "Al-Ikhlas",
                uz: "Ixlos", n_ayat: 4, search: "112 ixlos" }]);
  }
  if (url.includes("/api/segments")) {
    const whole = { index: 0, start_word: 0, num_words: 2, n_phonemes: 10,
                    seconds: 4, uthmani: "ٱللَّهُ ٱلصَّمَدُ", text_segments: [] };
    return j({ sura: 112, aya: 2, n_words: 2, legal_cuts: [], whole, parts: [] });
  }
  if (url.includes("/api/reciters")) {
    return j({ default: "x", base_url: "http://localhost:4319/",
               reciters: [{ id: "x", name: "R", style: "murattal", bitrate_kbps: 64 }] });
  }
  if (url.includes("/api/hadith")) return j(null);
  if (url.includes("/api/attempts") && route.request().method() === "POST") {
    posts += 1;
    if (posts === 1) return j(result([A, B, C], 0.55));   // first read
    // EVERY re-read after this: card A is GONE but B and C remain, so the
    // whole-ayah score stays BELOW pass_score (0.8). This is the exact input
    // the old rule deadlocked on.
    return j(result([B, C], 0.62));
  }
  if (url.includes("/api/attempts")) return j([]);
  if (url.includes("/api/consent")) return j({ ok: true });
  return j({});
});

await page.addInitScript(() => {
  localStorage.setItem("tilawah_lang", "uz");
  localStorage.setItem("tilawah_place", "112:2");
});

const errs = [];
page.on("pageerror", (e) => errs.push(String(e)));

await page.goto("http://localhost:4319/");
await page.waitForTimeout(500);

const text = async (sel) => (await page.$$eval(sel, (e) => e.map((x) => x.textContent.trim())))[0] ?? "";

console.log("1. BASMALA   :", await text(".opening__basmala"));
console.log("   brand mark:", await text(".opening__brand"));
await page.waitForTimeout(2600);

console.log("2. WELCOME   :", await text(".onboard__display"));
for (let i = 0; i < 3; i++) { await page.click(".btn-primary"); await page.waitForTimeout(320); }

console.log("3. PERSONALIZE:", await text(".onboard__display"), "|", await text(".onboard__count"));
for (let i = 0; i < 5; i++) {
  const opts = await page.$$(".choice__item");
  if (opts.length) await opts[0].click();
  await page.waitForTimeout(150);
  await page.click(".btn-primary");
  await page.waitForTimeout(320);
}

console.log("4. CREATE    :", await text(".onboard__display"));
const rows = await page.$$eval(".journey__row", (rs) =>
  rs.map((r) => r.querySelector(".journey__key").textContent.trim() + ": " +
                r.querySelector(".journey__val").textContent.trim()));
console.log("   MY JOURNEY:", rows.join(" | "));
await page.click(".btn-primary");
await page.waitForTimeout(400);

console.log("5. READY     :", await text(".onboard__display"));
const steps = await page.$$eval(".ready__step", (ss) =>
  ss.map((x) => x.textContent.trim().replace(/\s+/g, " ")));
console.log("   TODAY     :", steps.join(" | "));
console.log("   PATH      :", await text(".ready__path"));
await page.click(".btn-primary");
await page.waitForTimeout(400);

console.log("6. ACCOUNT   :", await text(".auth__wordmark"), "|", await text(".auth__pending"));
await page.click(".auth__skip");
await page.waitForTimeout(500);

console.log("7. CONSENT   :", (await page.$$(".gate__quiet")).length ? "shown" : "MISSING");
const gate = await page.$(".gate__quiet");
if (gate) await gate.click();
await page.waitForTimeout(1100);

console.log("8. HOME      : nav =", (await page.$$eval(".tabbar .tab", (e) => e.map((x) => x.textContent.trim()))).join(" | "));
console.log("   home CTA  :", await text(".btn-primary"));
console.log("   journey stored:", await page.evaluate(() => localStorage.getItem("veyraflow_journey")));

console.log("PAGE ERRORS:", errs.slice(0, 3));
await browser.close();
server.close();
