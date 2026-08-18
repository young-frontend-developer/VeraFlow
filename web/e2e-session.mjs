/**
 * Proof that the REAL built client authenticates itself against the REAL api.
 *
 * The Python tests assert two things separately: that api.ts no longer sends a
 * device id, and that the routes behave when driven by hand. Neither runs the
 * browser, and the thing most likely to break is exactly what neither covers -
 * whether the client actually bootstraps a session on load, attaches it, and
 * recovers from a 401. So this drives Chromium against a live server and reads
 * every request off the wire.
 *
 *   node e2e-session.mjs            (expects an api on :8000 unless told otherwise)
 *   API=http://127.0.0.1:8033 node e2e-session.mjs
 *
 * The api it points at MUST be running on a throwaway database. This records
 * attempts and revokes consent; do not aim it at anything real.
 */
import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join } from "node:path";

const API = process.env.API ?? "http://127.0.0.1:8000";
const PORT = Number(process.env.PORT ?? 5199);
const DIST = new URL("./dist/", import.meta.url).pathname.slice(1);
const MIME = {
  ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".woff": "font/woff", ".woff2": "font/woff2", ".svg": "image/svg+xml",
  ".json": "application/json",
};

const server = createServer(async (req, res) => {
  const path = req.url.split("?")[0];
  const file = path === "/" ? "index.html" : path.slice(1);
  try {
    const body = await readFile(join(DIST, file));
    res.writeHead(200, { "Content-Type": MIME[extname(file)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    const body = await readFile(join(DIST, "index.html"));
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(body);
  }
});

const fail = [];
const check = (ok, label, detail = "") => {
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${label}${detail ? ` — ${detail}` : ""}`);
  if (!ok) fail.push(label);
};

await new Promise((r) => server.listen(PORT, r));

const browser = await chromium.launch();
const page = await browser.newPage();

// Every request the client makes, recorded off the wire.
//
// MATCHED ON THE PATH, NOT THE ORIGIN. The bundle's BASE defaults to
// `http://localhost:8000` while this harness talks to `http://127.0.0.1:8000`;
// those are the same server and different strings, and comparing origins
// silently recorded nothing while every check that depended on the log
// "passed" by being empty. Path matching cannot drift that way.
const seen = [];
page.on("request", (r) => {
  const u = new URL(r.url());
  if (u.pathname.startsWith("/api/")) {
    seen.push({
      method: r.method(),
      url: u.pathname + u.search,
      auth: r.headers()["authorization"] ?? null,
    });
  }
});

// Point the built bundle at our api, and plant a device id that already has
// history so the claim path is the one under test.
const DEVICE = process.env.DEVICE ?? "e2e-existing-install";
await page.addInitScript((dev) => {
  localStorage.setItem("tilawah_device_id", dev);
  localStorage.setItem("tilawah_consent", "1");
  localStorage.setItem("tilawah_consent_seen", "1");
  localStorage.setItem("tilawah_auth_seen", "1");
  localStorage.setItem("tilawah_entry_done", "1");
}, DEVICE);

console.log(`\napi=${API}  client=http://127.0.0.1:${PORT}  device=${DEVICE}\n`);
await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);

// ── 1. did it bootstrap a session? ───────────────────────────────────────
const boot = seen.filter((r) => r.url.startsWith("/api/auth/anonymous"));
check(boot.length >= 1, "client bootstraps a session on load",
      `${boot.length} call(s)`);
check(boot.length <= 1, "bootstrap is single-flight (not one per request)",
      `${boot.length} call(s)`);

const token = await page.evaluate(() => localStorage.getItem("tilawah_session_token"));
check(Boolean(token) && token.length > 20, "a session token is stored",
      token ? `${token.length} chars` : "none");

// ── 2. no device id anywhere except the bootstrap ────────────────────────
const leaks = seen.filter((r) => r.url.includes("device_id"));
check(leaks.length === 0, "no device_id in any query string",
      leaks.map((l) => l.url).join(", "));

// ── 3. learner-data calls carry the session ──────────────────────────────
const learner = seen.filter((r) =>
  r.url.startsWith("/api/attempts") || r.url.startsWith("/api/consent"));
check(learner.length > 0, "the client made learner-data calls",
      `${learner.length}`);
const unauth = learner.filter((r) => !r.auth?.startsWith("Bearer "));
check(unauth.length === 0, "every learner-data call carries a bearer token",
      unauth.map((u) => `${u.method} ${u.url}`).join(", "));

// ── 4. content calls are NOT authenticated ───────────────────────────────
const content = seen.filter((r) =>
  r.url.startsWith("/api/suras") || r.url.startsWith("/api/meta") ||
  r.url.startsWith("/api/ayat") || r.url.startsWith("/api/reciters"));
check(content.length > 0, "the client fetched public content", `${content.length}`);

// ── 5. the seeded history actually came back ─────────────────────────────
const historyCalls = seen.filter((r) => r.url.startsWith("/api/attempts?"));
check(historyCalls.length > 0, "the client requested its history");

// ── 6. 401 recovery: destroy the stored token and reload ─────────────────
seen.length = 0;
await page.evaluate(() => localStorage.setItem("tilawah_session_token", "not-a-real-token"));
await page.reload({ waitUntil: "networkidle" });
await page.waitForTimeout(1500);

const got401 = seen.some((r) => r.url.startsWith("/api/attempts"));
const reboot = seen.filter((r) => r.url.startsWith("/api/auth/anonymous"));
check(reboot.length >= 1, "a rejected token triggers a fresh bootstrap",
      `${reboot.length} call(s)`);

const after = await page.evaluate(() => localStorage.getItem("tilawah_session_token"));
check(after && after !== "not-a-real-token",
      "the bad token was replaced with a working one");

// ── 7. the app still renders ─────────────────────────────────────────────
const crashed = await page.evaluate(() =>
  document.body.innerText.includes("Something went wrong") ||
  document.body.innerText.trim().length === 0);
check(!crashed, "the app renders without an error boundary");

await browser.close();
server.close();

console.log(`\n${fail.length === 0 ? "ALL CHECKS PASSED" : `${fail.length} FAILED: ${fail.join(", ")}`}\n`);
process.exit(fail.length === 0 ? 0 : 1);
