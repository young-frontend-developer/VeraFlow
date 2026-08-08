/**
 * DARK OR LIGHT, and the two are different designs rather than one inverted.
 *
 * ── WHY NOT AN INVERSION ───────────────────────────────────────────────────
 *
 * The dark system builds depth out of LIGHT: a lit gradient ground, translucent
 * panes floating on it, brass halos, luminous Arabic. Invert those values and
 * every one of those devices turns into its own worst version — a glow becomes
 * a smear, a translucent pane over a pale ground becomes a grey rectangle, and
 * text with a bloom behind it becomes text that looks out of focus. Frosted
 * glass needs something behind it worth blurring.
 *
 * So light mode uses a different mechanism for the same job: depth comes from
 * SHADOW, panes are opaque paper, and the accent carries weight through
 * saturation instead of through emission. Same layout, same components, same
 * hierarchy — different physics.
 *
 * ── THE PALETTE IS THE PROJECT'S OWN, RECOVERED FROM ITS HISTORY ───────────
 *
 * Ivory ground and brass are taken verbatim from the pre-dark commits (6cfd7f5
 * for the ivory family, f0c39b5 for the brass), not re-picked by eye. The one
 * value with no commit behind it is the lapis primary: the historical accent
 * was forest green, and lapis was only ever a spoken direction. It is taken
 * from `--ultramarine` in the dark theme, which is already this app's blue, so
 * the two themes are lit by the same light source at different times of day.
 * See the `[data-theme="light"]` block in index.css.
 */

export type Theme = "dark" | "light";

const KEY = "veyraflow_theme";

/**
 * DARK IS THE DEFAULT, and it is not conditional on the OS setting.
 *
 * `prefers-color-scheme` is deliberately NOT consulted. The dark system is the
 * app's designed identity rather than an accommodation, so a learner whose
 * laptop is in light mode should still meet Tilawah looking like Tilawah. Light
 * mode is a choice someone makes here, and once made it is the only thing that
 * decides.
 */
export function storedTheme(): Theme {
  return localStorage.getItem(KEY) === "light" ? "light" : "dark";
}

/**
 * Paint the theme onto the document.
 *
 * Everything is driven by one attribute on <html>, which is what makes the
 * toggle instant: no reload, no re-render of anything that is not already
 * re-rendering, just a different set of custom properties resolving. The
 * attribute is set rather than a class so it can be read from CSS and from
 * the DOM inspector without ambiguity.
 *
 * `color-scheme` goes with it so the browser's own chrome — form controls,
 * scrollbars, the overscroll gutter — follows the app instead of contradicting
 * it. Without that line a light theme still gets dark scrollbars.
 */
export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);
  root.style.colorScheme = theme;
  localStorage.setItem(KEY, theme);
}
