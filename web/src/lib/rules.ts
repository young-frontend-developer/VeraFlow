import type { RuleBadge } from "./api";

/** One rule's territory on the text, with the tone to paint it in. */
export type RuleLayer = {
  code: string;
  color: string;
  spans: [number, number][];
};

/**
 * Which rule owns a letter that two of them both govern. LOWER WINS.
 *
 * Only one pair is genuinely contested by the current detector: a shadda'd
 * nasal satisfies both the idgham and the ikhfo/ghunna preconditions, and the
 * decision is ghunna — the nasal hold is the audible, practicable quality being
 * taught at that letter, where idgham is the broader category the assimilation
 * belongs to.
 *
 * ⚠️ IT ALSO SETTLES A PAIR NOBODY RULED ON. Ghunna sorting to the top means it
 * beats EVERY other rule on a shared letter, including madd lozim — so on الٓمٓ
 * the مٓ paints green while the لٓ stays pink, even though the six-count is
 * arguably the more important thing being taught on the muqatta'at. That is a
 * consequence of the ordering, not a separate decision, and it is written down
 * here so it can be reversed by adding RULE_MADD_LOZIM above ghunna rather than
 * discovered later in a screenshot.
 *
 * Anything unlisted sorts after, in the server's own order, which is stable
 * across renders — so a letter never changes colour on a resize.
 */
const PRIORITY: Record<string, number> = {
  RULE_IKHFO_GHUNNA: 0,
  RULE_IDGHOM: 1,
};

export const rulePriority = (code: string) => PRIORITY[code] ?? 50;

/**
 * The rules to paint, in priority order (highest priority first).
 *
 * TWO FILTERS, AND BOTH ARE REFUSALS. `reviewed || showUnreviewed` is the same
 * content gate the legend uses — production shows nothing a qori has not signed
 * off. `spans.length` drops any rule the engine found but could not PLACE: the
 * idgham token-count proxy knows an assimilation happened without knowing which
 * letter did it, and a colour has to land on a specific glyph or it is a claim
 * nobody made.
 *
 * Shared by the practice screen and the reader so the same ayah cannot be
 * coloured two different ways depending on how the learner arrived at it.
 */
export function ruleLayers(
  rules: RuleBadge[] | null | undefined,
  showUnreviewed: boolean,
): RuleLayer[] {
  return (rules ?? [])
    .filter((r) => (r.reviewed || showUnreviewed) && (r.spans?.length ?? 0) > 0)
    .map((r) => ({ code: r.code, color: r.color, spans: r.spans ?? [] }))
    .sort((a, b) => rulePriority(a.code) - rulePriority(b.code));
}
