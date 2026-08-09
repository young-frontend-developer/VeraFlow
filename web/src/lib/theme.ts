/**
 * DARK OR LIGHT, CHOSEN BY THE LEARNER — and the two are different designs
 * rather than one inverted.
 *
 * ── THE DEVICE DOES NOT GET A VOTE ─────────────────────────────────────────
 *
 * `prefers-color-scheme` is deliberately NOT consulted. A previous version
 * followed it and removed the control entirely; this reverses that. What the
 * learner picks here holds regardless of what their phone is set to, and it
 * holds across launches.
 *
 * The reasoning against following the system is the same one that makes dark
 * the default: the dark system is this app's designed identity rather than an
 * accommodation. Someone whose phone is in light mode for their mail should
 * still meet Tilawah looking like Tilawah, and someone who then decides they
 * want the ivory can say so once and have it stay said. A theme that changes
 * underneath you at sunset because the OS decided so is a change nobody asked
 * this app to make.
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
 * hierarchy, same background pattern — different physics. See the
 * `[data-theme="light"]` block in index.css.
 */

export type Theme = "dark" | "light";

const KEY = "veyraflow_theme";

/**
 * What was chosen last, or dark.
 *
 * DARK IS THE DEFAULT AND IT IS NOT CONDITIONAL. Only an explicit "light" in
 * storage produces light; everything else — never chosen, corrupt value,
 * storage unavailable — is the app's own identity.
 */
export function storedTheme(): Theme {
  try {
    return localStorage.getItem(KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

/**
 * Paint the theme onto the document, and remember it.
 *
 * Everything is driven by one attribute on <html>, which is what makes the
 * toggle instant: no reload, no re-render of anything that is not already
 * re-rendering, just a different set of custom properties resolving. The
 * attribute is set rather than a class so it can be read from CSS and from the
 * DOM inspector without ambiguity.
 *
 * `color-scheme` goes with it so the browser's own chrome — form controls,
 * scrollbars, the overscroll gutter — follows the app instead of contradicting
 * it. Without that line a light theme still gets dark scrollbars.
 */
export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);
  root.style.colorScheme = theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    // Private mode, or storage disabled. The theme still applies for this
    // session; it simply will not be remembered, which is not worth a dialog.
  }
}
