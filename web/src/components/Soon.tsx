import { Lang, t } from "../lib/i18n";
import { BookOrnament, KnotOrnament } from "./Ornament";

/**
 * LEARN and MEMORIZE — tabs that exist, with nothing behind them yet.
 *
 * THE POINT OF THIS SCREEN IS WHAT IT DOES NOT CONTAIN. No sample courses, no
 * instructor names, no locked lessons with padlocks, no "0 of 12 complete", no
 * fake progress ring at zero. Every one of those is a lie that costs nothing to
 * draw and everything to be caught at, and in an app about the Quran a
 * fabricated curriculum is worse than an empty tab.
 *
 * What it does contain is an ornament, a sentence saying plainly that the work
 * has not been done, and one line about what it will be when it is. That is
 * enough to feel intentional. A screen can be empty and still be finished.
 *
 * There is deliberately NO "notify me" control either — there is no mailing
 * list, and a button that quietly does nothing is the same failure in a
 * smaller size.
 */

export function Learn({ lang }: { lang: Lang }) {
  return (
    <section className="soon">
      <BookOrnament className="soon__ornament" size={54} />
      <h2 className="soon__title">{t(lang, "learn_title")}</h2>
      <p className="soon__body">{t(lang, "learn_body")}</p>
      <p className="soon__note">{t(lang, "learn_note")}</p>
    </section>
  );
}

export function Memorize({ lang }: { lang: Lang }) {
  return (
    <section className="soon">
      <KnotOrnament className="soon__ornament" size={54} />
      <h2 className="soon__title">{t(lang, "memorize_title")}</h2>
      <p className="soon__body">{t(lang, "memorize_body")}</p>
      <p className="soon__note">{t(lang, "memorize_note")}</p>
    </section>
  );
}
