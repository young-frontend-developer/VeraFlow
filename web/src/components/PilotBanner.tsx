import { Lang, t } from "../lib/i18n";

/**
 * Says plainly that the tajweed corrections are not fully reviewed.
 *
 * Deliberately not dismissible: the thing it warns about is true for the whole
 * session, and a banner you can wave away is one testers stop seeing on the
 * attempt where it matters. It disappears on its own — the server derives
 * `pilot` from the content review state, so signing the corrections off in
 * rules.json removes it with no redeploy and no code change.
 */
export default function PilotBanner({ lang }: { lang: Lang }) {
  return (
    <aside className="pilot" role="note">
      <span className="pilot__mark" aria-hidden="true" />
      <div>
        <p className="pilot__title">{t(lang, "pilot_title")}</p>
        <p className="pilot__body">{t(lang, "pilot_body")}</p>
      </div>
    </aside>
  );
}
