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

const URL = process.env.TILAWAH_URL ?? "http://localhost:5199";
const OUT = path.resolve("./shots");
fs.mkdirSync(OUT, { recursive: true });

const problems = [];
const checks = [];
/** Where two strings first disagree, with a little context either side. */
const firstDivergence = (a, b) => {
  let i = 0;
  while (i < a.length && i < b.length && a[i] === b[i]) i++;
  return (
    `diverge at char ${i}: …${a.slice(Math.max(0, i - 40), i + 60)}` +
    `  ||  …${b.slice(Math.max(0, i - 40), i + 60)}`
  );
};

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
    tilawah_entry_done: "1",
    tilawah_auth_seen: "1",
    tilawah_consent_seen: "1",
    tilawah_consent: "1",
    tilawah_lang: "uz",
    tilawah_device_id: "screenshot-device-0001",
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
  //
  // THE OLD CHECK PASSED THROUGH TWO FAILURES. It asserted that a closed
  // subpath existed somewhere in the glyph, and both rejected versions had
  // one — a chisel nib drawn correctly, next to five other strokes that closed
  // the barrel into a solid bar and left a short crossbar reading as a pocket
  // clip. The property that actually failed was COUNT, so that is what is
  // measured now: one path, closed, and nothing else inside the icon.
  const learnPaths = await page.$eval(
    '.tab:nth-child(2) .tab__glyph svg',
    (svg) => [...svg.querySelectorAll("path")].map((p) => p.getAttribute("d")),
  );
  ok(
    "5 qalam is ONE closed outline, no interior strokes",
    learnPaths.length === 1 && /z\s*$/i.test(learnPaths[0]),
    `${learnPaths.length} path(s): ${learnPaths.join(" | ").slice(0, 70)}`,
  );
  ok(
    "5 qalam is neither of the two rejected pens",
    !learnPaths.join(" ").includes("M16.2 2.9") &&
      !learnPaths.join(" ").includes("M15.9 3.1"),
    "old paths absent",
  );
  await page.locator(".tab").nth(1).scrollIntoViewIfNeeded();
  await shot("r3-03-nav-qalam");

  // ── 3. the theme is the LEARNER's, and the device does not get a vote ──
  //
  // This block asserted the exact opposite one round ago: that the app tracked
  // `prefers-color-scheme` and had no control. Both halves are reversed here —
  // the toggle is back, and the device is set to the OPPOSITE of the choice
  // throughout, which is what would expose any surviving media-query path.
  await page.emulateMedia({ colorScheme: "light" });
  await page.waitForTimeout(300);
  const underLightDevice = await page.evaluate(() =>
    document.documentElement.getAttribute("data-theme"),
  );
  ok(
    "3 a light device does not override the stored dark choice",
    underLightDevice === "dark",
    `data-theme=${underLightDevice}`,
  );

  await page.locator(".tab", { hasText: "Profil" }).click();
  await page.waitForTimeout(900);
  const themeButtons = page
    .locator(".setting", { hasText: /Koʻrinish|Внешний/ })
    .locator("button");
  ok(
    "3 the manual theme toggle is back",
    (await themeButtons.count()) === 2,
    `${await themeButtons.count()} button(s)`,
  );
  await themeButtons.nth(1).click();
  await page.waitForTimeout(400);
  const picked = await page.evaluate(() =>
    document.documentElement.getAttribute("data-theme"),
  );
  ok("3 picking light applies it at once", picked === "light", `data-theme=${picked}`);
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1600);
  const persisted = await page.evaluate(() =>
    document.documentElement.getAttribute("data-theme"),
  );
  ok("3 the choice survives a reload", persisted === "light", `data-theme=${persisted}`);
  // Back to dark for the rest of the walk, and leave the device disagreeing.
  await page.emulateMedia({ colorScheme: "dark" });
  await page.locator(".tab", { hasText: "Profil" }).click();
  await page.waitForTimeout(900);
  await themeButtons.nth(0).click();
  await page.waitForTimeout(400);
  // ── 3. and the two sub-notes are gone from the figures on Home ────────
  await page.locator(".tab", { hasText: "Bosh sahifa" }).click();
  await page.waitForTimeout(1200);
  ok(
    "3 no streak-best / letters-read sub-notes",
    (await page.locator(".stat-tile__note").count()) === 0,
  );
  // ── 6. each mark takes its own gradient, and none share one ───────────
  //
  // A TILE AT ZERO IS DELIBERATELY COLOURLESS — see `.stat-tile--empty`, which
  // drops the mark to `--ink-3` along with the figure. This fixture's device
  // has no history, so the honest check here is on the CLASSES, which say
  // which tone each tile was assigned, plus the paint servers on whichever
  // tiles are actually lit. Asserting four distinct strokes unconditionally
  // would fail on a correct dimmed grid.
  const marks = await page.$$eval(".stat-tile", (tiles) =>
    tiles.map((tile) => {
      const m = tile.querySelector(".stat-tile__mark");
      const svg = tile.querySelector(".stat-tile__mark svg");
      return {
        tone: [...(m?.classList ?? [])].find((c) => c.startsWith("stat-tile__mark--")),
        stroke: svg ? getComputedStyle(svg).stroke : "",
        empty: tile.classList.contains("stat-tile--empty"),
      };
    }),
  );
  ok(
    "6 four stat marks, four distinct tones",
    marks.length === 4 && new Set(marks.map((m) => m.tone)).size === 4,
    marks.map((m) => m.tone?.replace("stat-tile__mark--", "")).join(" / "),
  );
  const lit = marks.filter((m) => !m.empty);
  ok(
    "6 a lit mark strokes a gradient, not a flat colour",
    lit.length === 0 || lit.every((m) => m.stroke.includes("url(")),
    lit.length === 0
      ? "all four at zero on this fixture — dimmed, which is correct"
      : lit.map((m) => m.stroke).join(" / "),
  );
  // ── 4. the pattern is drawn in ink and is actually visible ────────────
  const pattern = await page.evaluate(() => {
    const cs = getComputedStyle(document.body, "::after");
    return { opacity: Number(cs.opacity), image: cs.backgroundImage };
  });
  ok(
    "4 background pattern is ink-coloured and >= 10%",
    pattern.opacity >= 0.1 &&
      (pattern.image.includes("f4efe4") || pattern.image.includes("17211c")),
    `opacity ${pattern.opacity}`,
  );
  // ── 1. the bell is in the top bar on every screen ─────────────────────
  ok("1 bell in the top bar", (await page.locator(".app__header .bell").count()) === 1);
  await page.locator(".tab", { hasText: "Natijalar" }).click();
  await page.waitForTimeout(700);
  ok(
    "1 bell is still there on another tab",
    (await page.locator(".app__header .bell").count()) === 1,
  );

  // BACK TO THE PICKER, which is where the verse-view block below starts from.
  // The checks above walk four tabs to prove the bell and the theme travel
  // with them, and leaving the app on Home would strand the next block on a
  // screen that has no sura rows in it.
  await page.locator(".tab--center").click();
  await page.locator(".picker").waitFor({ timeout: 25000 });
  await page.waitForTimeout(500);

  // ── 7 + 8. verse view: no practise button, mic inside the ayah card ───
  //
  // THIS BLOCK USED TO ASSERT THE OPPOSITE. The mic was pinned to the
  // viewport, and these checks proved it stayed there — which is exactly what
  // made it float over the ayah card with the translation reading through it.
  // The requirement is now ordinary document layout, so the checks measure
  // that instead: the mic belongs to the card, sits under the Arabic, and
  // moves with the page when the page moves.
  await page.locator(".row--sura").first().click();
  await page.locator(".study").waitFor({ timeout: 25000 });
  await page.getByRole("tab", { name: /Oyatma-oyat/ }).click();
  await page.locator(".verse").waitFor({ timeout: 20000 });

  ok("8 no navigate-to-practice button", (await page.getByText("Bu oyatni oʻqish").count()) === 0);
  ok("8 verse view has a mic", (await page.locator(".recorder__mic").count()) === 1);
  ok("6 no reciter picker in reader", (await page.locator(".reciter__select").count()) === 0);
  await shot("r3-04-verse-recorder");

  const vw = page.viewportSize().width;

  /**
   * Everything about the recording control that could differ between the two
   * screens it appears on. Read on the reader here and on the practice screen
   * below, then compared field for field — "they look the same" is exactly the
   * claim a pair of screenshots cannot settle.
   */
  const controlProbe = () =>
    page.evaluate(() => {
      const el = document.querySelector(".recorder");
      const mic = document.querySelector(".recorder__mic");
      if (!el || !mic) return null;
      const cs = getComputedStyle(el);
      const ms = getComputedStyle(mic);
      const r = mic.getBoundingClientRect();
      return {
        wrapperBg: `${cs.backgroundImage} | ${cs.backgroundColor}`,
        wrapperBorder: cs.borderTopWidth,
        wrapperShadow: cs.boxShadow,
        wrapperMargin: `${cs.marginTop} / ${cs.marginBottom}`,
        disc: `${Math.round(r.width)}x${Math.round(r.height)}`,
        discFill: ms.backgroundImage,
        label: document.querySelector(".recorder__primary")?.textContent?.trim(),
        secondary: document.querySelector(".recorder__secondary")?.textContent ?? null,
      };
    });

  const readerControl = await controlProbe();

  // NO CONTAINER AT ALL. The old practice-screen version was a bordered navy
  // card; every one of these being empty is the property that replaced it.
  ok(
    "1 the control has no card around it",
    readerControl &&
      readerControl.wrapperBg === "none | rgba(0, 0, 0, 0)" &&
      readerControl.wrapperBorder === "0px" &&
      readerControl.wrapperShadow === "none",
    JSON.stringify(readerControl && {
      bg: readerControl.wrapperBg,
      border: readerControl.wrapperBorder,
      shadow: readerControl.wrapperShadow,
    }),
  );
  ok(
    "1 no studio / micbar node survives anywhere",
    (await page.locator(".studio, .micbar, .studio__head, .studio__stats").count()) === 0,
  );
  ok(
    "1 verse mic is in the flow, not fixed",
    (await page.locator(".recorder").evaluate((el) => getComputedStyle(el).position)) ===
      "static",
  );
  ok(
    "1 verse mic is inside the ayah card, below the Arabic",
    (await page.locator(".verse > .recorder").count()) === 1 &&
      (await page.evaluate(() => {
        const ar = document.querySelector(".verse__ar");
        return ar?.nextElementSibling?.classList.contains("recorder") ?? false;
      })),
  );

  // MOVES WITH THE PAGE. A fixed element and an in-flow one are indis-
  // tinguishable in one frame; the difference only shows across a scroll.
  const micAt = () =>
    page.evaluate(() => {
      const r = document.querySelector(".recorder__mic").getBoundingClientRect();
      return { vp: r.top, doc: r.top + window.scrollY, x: r.x, w: r.width };
    });
  const micTop = await micAt();
  await page.evaluate(() => window.scrollBy(0, 220));
  await page.waitForTimeout(350);
  const micScrolled = await micAt();
  const moved = Math.round(micTop.vp - micScrolled.vp);
  ok(
    "1 verse mic scrolls with the page",
    moved > 100 && Math.abs(micTop.doc - micScrolled.doc) < 2,
    `viewport moved ${moved}px, document offset ${Math.round(micTop.doc)}->${Math.round(micScrolled.doc)}`,
  );
  ok(
    "1 verse mic disc is centred in the column",
    Math.abs(micTop.x + micTop.w / 2 - vw / 2) < 2,
    `centre=${Math.round(micTop.x + micTop.w / 2)} vw/2=${vw / 2}`,
  );
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(250);

  // ── 2. THE PRESS IS THE START, ON THIS SCREEN ─────────────────────────
  //
  // The control has to go live before the app has fetched the practice range
  // and swapped screens. Both halves are measured: how long until it is live,
  // and whether the reader is still the screen underneath when it happens.
  await page.locator(".recorder__mic").scrollIntoViewIfNeeded();
  const pressedAt = Date.now();
  await page.locator(".recorder__mic").click();
  await page
    .locator(".mic--live")
    .waitFor({ timeout: 5000 })
    .catch(() => {});
  const liveAfter = Date.now() - pressedAt;
  const stillOnReader = (await page.locator(".verse").count()) > 0;
  ok(
    "2 the mic goes live on the press, before any navigation",
    liveAfter < 900 && stillOnReader,
    `live after ${liveAfter}ms; still on the reader: ${stillOnReader}`,
  );
  await shot("r3-05-recording-in-place");

  // ── 2. and the SAME recording continues onto the practice screen ──────
  await page.locator(".ayah-badge").waitFor({ timeout: 25000 });
  await page.waitForTimeout(1600);
  ok(
    "2 the recording survives the handoff",
    (await page.locator(".mic--live").count()) === 1,
  );
  // A clock past zero is the proof it was NOT restarted: a fresh recorder on
  // the practice screen would read 0:00 here, not the seconds since the press.
  const clock = await page.locator(".recorder__timer").innerText();
  ok(
    "2 the clock continues rather than restarting",
    /0:0[1-9]|0:[1-5]\d/.test(clock.trim()),
    `clock reads ${clock.trim()}`,
  );
  // NOTHING OVERLAPS ANY MORE, which is the whole point: the only thing that
  // can now sit on top of the content is the nav bar itself.
  ok(
    "1 nothing is fixed over the ayah but the nav",
    await page.evaluate(() =>
      [...document.querySelectorAll("body *")]
        .filter((el) => getComputedStyle(el).position === "fixed")
        .every((el) => el.closest(".tabbar") !== null || el === document.body),
    ),
    await page.evaluate(() =>
      [...document.querySelectorAll("body *")]
        .filter(
          (el) =>
            getComputedStyle(el).position === "fixed" && el.closest(".tabbar") === null,
        )
        .map((el) => el.className)
        .join(", ") || "only the tab bar",
    ),
  );
  ok("2 no duration estimate under the ayah", (await page.locator(".estimate:not(.estimate--warn)").count()) === 0);

  // ── 6 + 7. practice screen carries neither control ────────────────────
  ok("6 no reciter picker on practice", (await page.locator(".reciter__select").count()) === 0);
  ok("7 no segment picker", (await page.locator(".list--parts").count()) === 0);
  ok("7 no 'practise part' link", (await page.getByText(/qismini oʻqish|Bir qismini/i).count()) === 0);

  // ── 1. THE CONTROL DOES NOT CHANGE ACROSS THE HANDOFF ─────────────────
  //
  // Everything about the control that is state-independent — its container (or
  // absence of one), its spacing and its disc — must read the same on the
  // practice screen as it did on the reader. The label legitimately differs:
  // one says "press the button" and the other is a running clock.
  const midRecording = await controlProbe();
  const stable = ["wrapperBg", "wrapperBorder", "wrapperShadow", "wrapperMargin", "disc"];
  const drifted = stable.filter(
    (k) => JSON.stringify(readerControl?.[k]) !== JSON.stringify(midRecording?.[k]),
  );
  ok(
    "1 the control is unchanged across the handoff",
    drifted.length === 0,
    drifted.length
      ? drifted.map((k) => `${k}: ${readerControl?.[k]} vs ${midRecording?.[k]}`).join("; ")
      : `disc ${readerControl?.disc}, no container, margins ${readerControl?.wrapperMargin}`,
  );

  // ── MUSHAF AND OYATMA-OYAT LAND ON THE SAME SCREEN ────────────────────
  //
  // The defect: tapping an ayah in the mushaf went straight to the recording
  // screen, while Oyatma-oyat showed the reader's verse view — two different
  // screens for the same ayah, one of them missing the translation, the
  // reciter playback and the prominent ayah number. Mushaf now opens the verse
  // view, so both are literally the same component with the same props.
  //
  // The X releases the microphone without submitting: this machine cannot run
  // the acoustic model, and a suite that stopped the recording here would be
  // asserting the engine's absence rather than the layout.
  const verseMarkup = () =>
    page.evaluate(
      () => document.querySelector(".verse")?.outerHTML.replace(/\s+/g, " ").trim() ?? "",
    );

  await page.locator(".ayah-nav__close").click();
  await page.locator(".picker").waitFor({ timeout: 25000 });
  await page.locator(".row--sura").first().click();
  await page.locator(".study").waitFor({ timeout: 25000 });

  // From OYATMA-OYAT.
  await page.getByRole("tab", { name: /Oyatma-oyat/ }).click();
  await page.locator(".verse").waitFor({ timeout: 25000 });
  await page.waitForTimeout(900);
  const viaVerse = await verseMarkup();

  // From MUSHAF, same ayah.
  await page.getByRole("tab", { name: /Mushaf/ }).click();
  await page.locator(".mushaf__aya").first().waitFor({ timeout: 20000 });
  await page.locator(".mushaf__aya").first().click();
  await page.locator(".verse").waitFor({ timeout: 25000 });
  await page.waitForTimeout(900);
  const viaMushaf = await verseMarkup();

  ok(
    "1 the mushaf tap opens the VERSE VIEW, not a second screen",
    (await page.locator(".verse").count()) === 1 &&
      (await page.locator(".ayah-nav").count()) === 0,
  );
  ok(
    "1 mushaf and oyatma-oyat render byte-identical markup",
    viaMushaf === viaVerse && viaMushaf.length > 0,
    viaMushaf === viaVerse
      ? `${viaMushaf.length} chars, identical`
      : firstDivergence(viaMushaf, viaVerse),
  );
  ok(
    "1 and it carries the reciter playback, the translation and the badge",
    (await page.locator(".listen").count()) === 1 &&
      (await page.locator(".verse__tr").count()) === 1 &&
      (await page.locator(".verse__nav .ayah-badge").count()) === 1,
  );
  ok(
    "2 opening an ayah from the mushaf does not open the microphone",
    (await page.locator(".mic--live").count()) === 0,
  );
  await shot("r3-06-mushaf-lands-on-verse-view");

  // ── light mode, structurally identical ────────────────────────────────
  // Probed on HOME, not on the recording screen: that screen has no `.card`
  // at all (the ayah is `.ayah` and the control has no container), so sampling
  // a card there measures nothing and reports it as a missing blur.
  //
  // Set through SETTINGS, because that is the app's only theme input again —
  // the device stays dark throughout, which is what proves the choice wins.
  await page.locator(".ayah-nav__close").click().catch(() => {});
  await page.waitForTimeout(1200);
  await page.locator(".tab", { hasText: "Profil" }).click();
  await page.waitForTimeout(900);
  await themeButtons.nth(1).click();
  await page.waitForTimeout(400);
  await shot("r3-07-light");
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
