/**
 * The sign-in screen, in a real browser, in both of its configurations.
 *
 * WHAT THIS CAN AND CANNOT PROVE. Without a registered Google client id and a
 * real Google account, no browser test can complete an actual sign-in - the
 * credential comes from Google's own iframe. So this proves the two things
 * that ARE ours:
 *
 *   unconfigured  the server answers 503, and the screen falls back to the
 *                 disabled button with its honest line, rather than showing a
 *                 control that cannot work or leaving an empty gap.
 *   configured    the client asks for a nonce before offering sign-in, and
 *                 mounts Google's button. The nonce is the login-CSRF defence;
 *                 a button rendered without one would be the bug.
 *
 * Point it at a THROWAWAY api. It creates sessions.
 *
 *   API=http://127.0.0.1:8041 node e2e-google.mjs
 */
import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join } from "node:path";

const API = process.env.API ?? "http://127.0.0.1:8000";
const PORT = Number(process.env.PORT ?? 5198);
const EXPECT = process.env.EXPECT ?? "configured"; // configured | unconfigured
const DIST = new URL("./dist/", import.meta.url).pathname.slice(1);
const MIME = {
  ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
  ".woff": "font/woff", ".woff2": "font/woff2", ".svg": "image/svg+xml",
};

const server = createServer(async (req, res) => {
  const p = req.url.split("?")[0];
  const file = p === "/" ? "index.html" : p.slice(1);
  try {
    const body = await readFile(join(DIST, file));
    res.writeHead(200, { "Content-Type": MIME[extname(file)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(await readFile(join(DIST, "index.html")));
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

const calls = [];
page.on("request", (r) => {
  const u = new URL(r.url());
  if (u.pathname.startsWith("/api/")) calls.push(u.pathname);
  if (u.hostname === "accounts.google.com") calls.push("GIS:" + u.pathname);
});
const responses = new Map();
page.on("response", (r) => {
  const u = new URL(r.url());
  if (u.pathname.startsWith("/api/")) responses.set(u.pathname, r.status());
});

// Land on the STANDALONE sign-in screen. App.tsx gates it as:
//     if (!entryDone)  -> the onboarding journey (which has its own account step)
//     if (!authSeen)   -> this screen
// so the entry flow must be marked done and the auth screen must not be.
//
// The key really is `veyraflow_entry_done`, from before the rename; the others
// are `tilawah_*`. Guessing it cost a run of five false failures.
await page.addInitScript(() => {
  localStorage.setItem("tilawah_device_id", "e2e-google-device");
  localStorage.setItem("veyraflow_entry_done", "1");
  localStorage.setItem("tilawah_consent_seen", "1");
  localStorage.setItem("tilawah_consent", "1");
  localStorage.removeItem("tilawah_auth_seen");
});

console.log(`\napi=${API}  expecting Google to be ${EXPECT}\n`);
await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: "networkidle" });
await page.waitForTimeout(2500);

const body = await page.evaluate(() => document.body.innerText);
const onAuthScreen = body.includes("Google") || body.includes("Hisobsiz") ||
  body.includes("аккаунт");
check(onAuthScreen, "the sign-in screen is showing");

// The nonce request is the security-relevant one and must happen either way.
check(calls.includes("/api/auth/google/start"),
      "the client asks the server for a nonce before offering Google");
const startStatus = responses.get("/api/auth/google/start");

if (EXPECT === "unconfigured") {
  check(startStatus === 503, "server reports Google unavailable", `HTTP ${startStatus}`);
  const disabled = await page.evaluate(() => {
    const b = [...document.querySelectorAll("button.btn-provider")]
      .find((x) => x.textContent.includes("Google"));
    return b ? b.disabled : null;
  });
  check(disabled === true, "the Google button falls back to disabled");
  check(!calls.some((c) => c.startsWith("GIS:")),
        "Google's script is NOT loaded when there is nothing to sign into");
} else {
  check(startStatus === 200, "server issued a nonce", `HTTP ${startStatus}`);
  check(calls.some((c) => c.startsWith("GIS:")),
        "Google's script is fetched so its button can mount");
  const mounted = await page.evaluate(() =>
    Boolean(document.querySelector(".auth__google")));
  check(mounted, "the Google button container is mounted");
}

// The anonymous path must survive whatever Google does.
const anonWorks = await page.evaluate(() => {
  const b = [...document.querySelectorAll("button")]
    .find((x) => /Hisobsiz|без аккаунта/.test(x.textContent));
  return Boolean(b && !b.disabled);
});
check(anonWorks, "'continue without an account' is still offered and enabled");

const crashed = await page.evaluate(() =>
  document.body.innerText.includes("Something went wrong") ||
  document.body.innerText.trim().length === 0);
check(!crashed, "the screen renders without an error boundary");

await browser.close();
server.close();
console.log(`\n${fail.length === 0 ? "ALL CHECKS PASSED" : `${fail.length} FAILED: ${fail.join(", ")}`}\n`);
process.exit(fail.length === 0 ? 0 : 1);
