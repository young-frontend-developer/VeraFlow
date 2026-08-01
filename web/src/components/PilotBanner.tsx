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
export default function PilotBanner({
  lang,
  showUnreviewed = false,
}: {
  lang: Lang;
  showUnreviewed?: boolean;
}) {
  // The review gate being off is a stronger statement than "pilot", and it
  // replaces rather than stacks with it — two warnings compete and neither
  // gets read. The server already forces pilot=true whenever this is on.
  const draft = showUnreviewed;
  return (
    <aside className={draft ? "pilot pilot--draft" : "pilot"} role="note">
      <span className="pilot__mark" aria-hidden="true" />
      <div>
        <p className="pilot__title">
          {t(lang, draft ? "draft_banner_title" : "pilot_title")}
        </p>
        <p className="pilot__body">
          {t(lang, draft ? "draft_banner_body" : "pilot_body")}
        </p>
      </div>
    </aside>
  );
}
