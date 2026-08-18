/**
 * ONE-TIME localStorage KEY MIGRATION.
 *
 * Four keys — the entry-experience flag, the theme, the journey and the
 * reflection count — were named after the product. The product has now been
 * renamed three times before settling on VeraFlow, and each rename left them
 * stranded on the previous name. Renaming them again in place would
 * have silently reset every existing install: onboarding replays, the theme
 * snaps back to dark, and the journey and reflection count — the only data here
 * that a learner actually built up — are gone.
 *
 * So the keys are now on the `tilawah_` prefix that the other seven keys in
 * App.tsx already use. That prefix is the package name, not the product name;
 * it does not move when marketing does, which is the whole point. This module
 * carries the old values across once so the rename costs nobody their data.
 *
 * SAFE TO DELETE once no meaningful number of installs predate the rename —
 * it is a no-op on any device that never held the old keys. Delete the lint
 * marker below with it.
 */

/**
 * old -> new. The legacy names carry the pre-rename product name, which is the
 * one thing `npm run lint:brand` exists to forbid; the marker below is the
 * single, deliberate exemption. Do not add to it — new code has no business
 * naming the old brand.
 */
/* veraflow-lint-ignore: legacy-storage-key */
const RENAMED: ReadonlyArray<readonly [string, string]> = [
  ["veyraflow_entry_done", "tilawah_entry_done"],
  ["veyraflow_theme", "tilawah_theme"],
  ["veyraflow_journey", "tilawah_journey"],
  ["veyraflow_reflections", "tilawah_reflections"],
];

/**
 * Move any pre-rename values onto their new keys, then drop the old ones.
 *
 * Must run BEFORE anything reads storage — see main.tsx. An existing value on
 * the new key always wins: if both are present the new one is the live value
 * and the old one is a leftover, never the other way round.
 *
 * Wrapped because storage throws rather than returning null in a handful of
 * real situations (Safari private mode, a disabled-cookies profile). A failed
 * migration must degrade to "this looks like a fresh install", never to a
 * blank screen at startup.
 */
export function migrateStorageKeys(): void {
  try {
    for (const [from, to] of RENAMED) {
      const old = localStorage.getItem(from);
      if (old === null) continue;
      if (localStorage.getItem(to) === null) localStorage.setItem(to, old);
      localStorage.removeItem(from);
    }
  } catch {
    /* storage unavailable — nothing to migrate, and nothing to report. */
  }
}
