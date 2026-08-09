import { Lang, t } from "../lib/i18n";

/**
 * WHICH AYAH YOU ARE ON.
 *
 * One component, used by the reader's verse view and by the recording screen,
 * in the same slot on both: the centre of the row of navigation arrows at the
 * top of the ayah. It was previously two things — a prominent plate on the
 * recording screen and a 12px tracked-out "112:1" in the reader, which is the
 * treatment this app gives a timestamp — and the pair of them was half of why
 * the two screens did not look like the same screen.
 *
 * THE NUMERAL IS THE AYAH ALONE, not "112:1". A colon pair is a citation
 * format: it is what you write when you are pointing someone else at a verse.
 * Here the sura is already named directly above, and repeating its number
 * inside the badge would make the badge's largest character the one piece of
 * information the learner already has.
 */
export default function AyahBadge({ lang, aya }: { lang: Lang; aya: number }) {
  return (
    <span className="ayah-badge" aria-label={`${t(lang, "ayah")} ${aya}`}>
      <span className="ayah-badge__label" aria-hidden="true">
        {t(lang, "ayah")}
      </span>
      <span className="ayah-badge__num" aria-hidden="true">
        {aya}
      </span>
    </span>
  );
}
