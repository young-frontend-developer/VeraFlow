/**
 * THE PRODUCT IS CALLED VeraFlow. FAIL THE BUILD IF THE OLD NAME COMES BACK.
 *
 * It has come back twice. A rename commit lands, a branch that predates it gets
 * merged, and the old spelling reappears in a page title, an app label or a
 * string nobody re-reads — visible to every user, invisible in a diff review
 * because it looks like ordinary product copy. This check makes the third time
 * impossible: any case variant of the old name anywhere under web/ or api/ is
 * an error, not a review comment.
 *
 *   node web/lint-brand.mjs        # from the repo root or from web/
 *
 * Exit 0 clean, 1 with a file:line list of every hit.
 *
 * ── THE ONE EXEMPTION ──────────────────────────────────────────────────────
 *
 * A line carrying the marker `veraflow-lint-ignore` is skipped, along with the
 * lines that follow it up to the next blank line. That exists for exactly one
 * caller — web/src/lib/storage-migrations.ts, which must name the old
 * localStorage keys in order to migrate people off them — and it is deliberately
 * noisy to type. If you are reaching for it for anything else, the answer is
 * that you should be writing "VeraFlow".
 */
import fs from "node:fs";
import path from "node:path";

const BANNED = /veyraflow/i;
const MARKER = "veraflow-lint-ignore";

/**
 * Where the product name can appear. Both trees are scanned in full, plus the
 * root README — it is the first thing anyone reads and it carried the old name
 * for longer than anything else did.
 */
const ROOTS = ["web", "api", "README.md"];

/** Build output, dependencies and binaries: not sources, and huge. */
const SKIP_DIRS = new Set([
  "node_modules", "dist", "build", ".git", ".venv", "__pycache__",
  ".gradle", ".idea", "e2e-shots", "screens", "shots", "debug_audio",
]);

/**
 * Repo-relative paths that are generated rather than written, so a hit in them
 * means a stale artifact and not a source defect. `npx cap sync` rebuilds the
 * Android assets from capacitor.config.ts and web/dist, both of which ARE
 * checked. This file is skipped for the obvious reason: it has to name the
 * string it forbids.
 */
const SKIP_PATHS = new Set([
  "web/android/app/src/main/assets",
  "web/lint-brand.mjs",
  "api/tests/test_brand_name.py", // the same check, from the pytest side
]);

const rel = (p) => path.relative(ROOT, p).replace(/\\/g, "/");
const SKIP_EXT = new Set([
  ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".docx",
  ".woff", ".woff2", ".ttf", ".otf", ".mp3", ".wav", ".webm", ".db",
  ".jar", ".keystore", ".jks", ".tsbuildinfo",
]);

/** Repo root, whether this was run from there or from web/. */
const here = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
const ROOT = path.resolve(here, "..");

const hits = [];

const walk = (dir) => {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return; // unreadable or vanished mid-walk — not this check's problem
  }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (SKIP_PATHS.has(rel(full))) continue;
    if (e.isDirectory()) {
      if (!SKIP_DIRS.has(e.name)) walk(full);
    } else if (e.isFile() && !SKIP_EXT.has(path.extname(e.name).toLowerCase())) {
      scan(full);
    }
  }
};

const scan = (file) => {
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch {
    return;
  }
  if (!BANNED.test(text)) return; // fast path: almost every file

  const lines = text.split(/\r?\n/);
  let exempt = false;
  lines.forEach((line, i) => {
    if (line.includes(MARKER)) {
      exempt = true;
      return;
    }
    // The exemption covers the marked block and ends at the blank line after it.
    if (exempt && line.trim() === "") exempt = false;
    if (exempt) return;
    if (BANNED.test(line)) {
      hits.push(`${rel(file)}:${i + 1}: ${line.trim()}`);
    }
  });
};

for (const r of ROOTS) {
  const target = path.join(ROOT, r);
  if (fs.existsSync(target) && fs.statSync(target).isDirectory()) walk(target);
  else scan(target);
}

if (hits.length) {
  console.error(
    `\nThe product is called VeraFlow. Found ${hits.length} instance(s) of the old name:\n`,
  );
  for (const h of hits) console.error(`  ${h}`);
  console.error(
    "\nRename them to VeraFlow. Visible copy should read the name from " +
      "web/src/lib/brand.ts rather than spelling it out.\n",
  );
  process.exit(1);
}

console.log("brand check: no occurrences of the old product name in web/, api/ or README.md");
