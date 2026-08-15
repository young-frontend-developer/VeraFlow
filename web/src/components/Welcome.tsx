import { useState } from "react";
import { withBrand } from "../lib/brand";
import { Lang, t } from "../lib/i18n";
import { ArchOrnament, KnotOrnament, StarOrnament } from "./Ornament";

/**
 * WELCOME — what this app is, in three screens and about forty words.
 *
 * The learner arrived because someone told them to. They know the name and
 * nothing else. Three screens is the whole budget, and each carries ONE idea:
 *
 *   1  the promise      your Quran journey, guided
 *   2  what it does     you recite, it listens, it tells you precisely what to
 *                       fix — which is the one thing this product actually has
 *                       that a book does not
 *   3  the relief       you do not have to work out what to do next
 *
 * ── NO FEATURE LIST, AND NOT FOR STYLE REASONS ─────────────────────────────
 *
 * A bulleted list of six capabilities is a promise of six things, and this app
 * currently does two of them well: it listens to recitation and it explains
 * Tajweed mistakes. Memorization and lessons are named in the brief and do not
 * exist. Putting them on a welcome screen would be selling them, and the first
 * thing the learner would do is go looking. So the screens describe the thing
 * that is real, in the register of a promise rather than a spec sheet.
 *
 * Each screen is an ornament, a line, and a sentence. Skippable throughout —
 * an introduction nobody can leave is an advertisement.
 *
 * ── IT IS A CARD, THE SAME CARD AS THE ACCOUNT SCREEN ──────────────────────
 *
 * The three screens sit in a centred 420px column with the content in a
 * `.card`, because that is what the rest of the app does and this is the first
 * screen a learner ever sees — the one that sets the expectation everything
 * after it has to meet. Full-bleed it looked like a landing page at any width
 * above a phone. See the onboarding block in index.css.
 */

const SCREENS = [
  { mark: StarOrnament, title: "welcome_1_title", body: "welcome_1_body" },
  { mark: ArchOrnament, title: "welcome_2_title", body: "welcome_2_body" },
  { mark: KnotOrnament, title: "welcome_3_title", body: "welcome_3_body" },
] as const;

export default function Welcome({
  lang,
  onDone,
}: {
  lang: Lang;
  onDone: () => void;
}) {
  const [i, setI] = useState(0);
  const screen = SCREENS[i];
  const Mark = screen.mark;
  const last = i === SCREENS.length - 1;

  return (
    <div className="onboard welcome">
      <div className="onboard__inner">
        <div className="card onboard__card">
          <div className="onboard__step" key={i}>
            <Mark className="onboard__ornament" size={44} />
            <h2 className="onboard__display">
              {withBrand(t(lang, screen.title))}
            </h2>
            <p className="onboard__lede">
              {withBrand(t(lang, screen.body))}
            </p>

            <div className="onboard__foot">
              <button
                className="btn-primary"
                onClick={() => (last ? onDone() : setI(i + 1))}
              >
                {t(lang, last ? "welcome_start" : "onboard_next")}
              </button>
              {!last && (
                <button className="onboard__skip" onClick={onDone}>
                  {t(lang, "onboard_skip")}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Under the card, not adrift below it. */}
        <div className="onboard__dots" aria-hidden="true">
          {SCREENS.map((s, n) => (
            <span
              key={s.title}
              className={n === i ? "onboard__dot onboard__dot--on" : "onboard__dot"}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
