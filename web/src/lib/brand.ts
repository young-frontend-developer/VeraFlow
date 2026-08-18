/**
 * The product name, in ONE place.
 *
 * It has now been three different things — Tilawah, then MEKIN in a spec, then
 * VeraFlow — and each rename found the old one scattered across components,
 * the page title, the API title and a dozen strings. Every visible instance
 * reads from here, so the next change is this line and the two places that
 * cannot import TypeScript (index.html's <title> and the FastAPI app title).
 *
 * NOT for use inside translated sentences that would need regrammaring around
 * it. A brand name dropped into a template is how you get "VeraFlowga xush
 * kelibsiz" in one language and something ungrammatical in another — the i18n
 * strings carry their own copy and take the name as a {brand} placeholder only
 * where the surrounding grammar genuinely does not change.
 */
export const BRAND = "VeraFlow";

/** Fills {brand} in any translated string. */
export const withBrand = (s: string) => s.replace(/\{brand\}/g, BRAND);
