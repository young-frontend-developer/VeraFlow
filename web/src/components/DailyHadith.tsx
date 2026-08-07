import { useEffect, useState } from "react";
import { Hadith, hadithToday } from "../lib/api";
import { Lang, t } from "../lib/i18n";
import { StarOrnament } from "./Ornament";

/**
 * THE DAY'S HADITH.
 *
 * Replaces the daily verse card, on the same visual treatment: centred
 * ornament, small-caps label, Arabic, italic serif rendering of the meaning,
 * muted citation line. Only the source of the words changed.
 *
 * ── THE THREE RULES THIS COMPONENT ENFORCES ────────────────────────────────
 *
 * 1. IT RENDERS NOTHING IT WAS NOT GIVEN. The text, the Arabic and the citation
 *    all come from the server, out of a reviewable JSON file. There is no
 *    fallback hadith and no default string anywhere in here — a fallback is
 *    exactly where an unsourced attribution would end up, and this is the one
 *    card in the app where that would mean putting words in the Prophet's
 *    mouth ﷺ.
 *
 * 2. NULL IS A REAL ANSWER. In production only qori-reviewed entries are
 *    eligible; none are yet, so the endpoint returns null there and this draws
 *    nothing at all. Not a skeleton, not a placeholder, not "loading…"
 *    forever — the section is absent, and that is correct.
 *
 * 3. THE CITATION IS NOT OPTIONAL CHROME. Collection, reference number and
 *    grading are printed on every card, because "a hadith says" without a
 *    reference is the failure mode this whole file exists to prevent. If the
 *    server ever sends one without a collection, the card is not drawn.
 *
 * The draft chip is the same obligation as on a correction card: nothing
 * unreviewed reaches a learner looking settled.
 */

export default function DailyHadith({ lang }: { lang: Lang }) {
  const [item, setItem] = useState<Hadith | null | "loading">("loading");

  useEffect(() => {
    let alive = true;
    hadithToday(lang)
      .then((got) => alive && setItem(got))
      .catch(() => alive && setItem(null));
    return () => {
      alive = false;
    };
  }, [lang]);

  // Nothing to show and nothing to apologise for. See rule 2.
  if (item === "loading" || item === null) return null;
  // Rule 3: a citation-less entry is not rendered, whatever else it carries.
  if (!item.collection || !item.ref) return null;

  return (
    <section className="reflect card">
      <StarOrnament className="reflect__mark" size={44} />

      <p className="section-label reflect__kicker">{t(lang, "hadith_kicker")}</p>

      {item.ar && (
        <p className="reflect__ar" dir="rtl" lang="ar">
          {item.ar}
        </p>
      )}

      <p className="reflect__line">{item.text}</p>

      {/* Collection, number, grading — and the note that the line above is a
          rendering of the meaning rather than the hadith itself. */}
      <p className="reflect__cite">
        {item.collection} · {item.ref}
        {item.grading ? ` · ${item.grading}` : ""}
      </p>
      <p className="reflect__cite reflect__cite--soft">
        {t(lang, "hadith_meaning_note")}
      </p>

      {item.draft && (
        <p className="card__draft reflect__draft">
          <span className="card__draft-chip">{t(lang, "draft_chip")}</span>
          {t(lang, "hadith_draft_note")}
        </p>
      )}
    </section>
  );
}
