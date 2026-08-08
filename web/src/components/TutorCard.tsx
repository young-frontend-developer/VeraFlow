import { Lang, t } from "../lib/i18n";
import { Mic, TutorMark } from "./Ornament";

/**
 * THE AI TUTOR CARD.
 *
 * ── NO FACE. NOT ONE, NOT EVER, NOT ILLUSTRATED ────────────────────────────
 *
 * The reference designs for this category all put a person here: a photographed
 * teacher, an illustrated one, a friendly 3D character with a name. This app
 * does not, and the reason is not squeamishness about generated imagery.
 *
 * A face beside a correction is a claim. It says a person listened to your
 * recitation and formed a view of it, and that a person stands behind the
 * ruling on your ص. No person did. The engine is a phoneme model and a table of
 * rules written by people who have never heard you. Putting a face on that is
 * the single most misleading thing this product could do, and it would be
 * misleading in a domain where being misled has consequences the learner takes
 * seriously.
 *
 * So the tutor is a LIGHT: the app's own khatam with a qalam stroke turning
 * through it, glowing. See TutorMark in Ornament.tsx.
 *
 * ── NO PERSONAS, EITHER, AND THAT IS A SCOPE DECISION ──────────────────────
 *
 * Named tutor "modes" differing by tone were considered and are not built,
 * because they are not built — there is one feedback voice, out of
 * content/rules.json, and offering a choice of three would be three buttons
 * that do the same thing. The card describes WHAT THE TUTOR DOES instead, and
 * every clause of that description is a thing the engine actually does:
 * it hears the recitation, locates the letter and the word, and says how to fix
 * it. When tone modes exist they belong here; until then this card is the
 * feature, not an advertisement for one.
 */
export default function TutorCard({
  lang,
  onStart,
}: {
  lang: Lang;
  onStart: () => void;
}) {
  return (
    <section className="today__block">
      <article className="card card--tutor">
        <span className="tutor__mark" aria-hidden="true">
          <TutorMark size={64} />
        </span>

        <p className="section-label">{t(lang, "tutor_kicker")}</p>
        <h3 className="tutor__title">{t(lang, "tutor_title")}</h3>
        <p className="tutor__body">{t(lang, "tutor_body")}</p>

        <button className="btn-primary tutor__cta" onClick={onStart}>
          <Mic size={18} />
          {t(lang, "tutor_cta")}
        </button>

        {/* Stated on the card, not buried in a settings page. The absence of a
            face is a deliberate feature of this product and saying so is
            cheaper than letting someone wonder why the teacher has no
            picture. */}
        <p className="tutor__disclosure">{t(lang, "tutor_no_face")}</p>
      </article>
    </section>
  );
}
