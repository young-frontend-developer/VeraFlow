/**
 * Does this re-read close the card?
 *
 * ── WHY THIS IS ITS OWN MODULE ─────────────────────────────────────────────
 *
 * It used to be four lines inline in Recite.tsx, and it was WRONG in a way that
 * no amount of reading it could show: the bug only appears when an ayah has
 * more than one error in it, which is exactly the case a component test never
 * covers and a live recitation always does. Pulling it out means the decision
 * can be exercised directly, over the input combinations that actually occur.
 *
 * ── THE DEADLOCK THIS FIXES ────────────────────────────────────────────────
 *
 * The old rule was:
 *
 *     cleared = judged && !stillThere && score >= need
 *
 * `score` is the accuracy of the WHOLE re-read range. The last rung of every
 * ladder is the ayah, so on the rung that actually closes a card, `score`
 * covers the entire ayah — including the errors belonging to every OTHER card.
 *
 * With one error in an ayah that is fine. With three it is a deadlock:
 *
 *   1. The learner is shown card A only (progressive reveal).
 *   2. They fix A perfectly. The re-read no longer contains A's error.
 *   3. But B and C are still in the ayah, so `score` sits below `need`.
 *   4. `cleared` is false. A does not close. B is never revealed.
 *   5. They are asked to recite the same ayah again. Forever.
 *
 * They cannot escape by trying harder, because the thing keeping the card shut
 * is a mistake the app has deliberately not told them about yet. Reveal and the
 * score gate were each reasonable and together they trapped the learner.
 *
 * THE FIX: a card is about ONE error, so it closes when THAT error is gone.
 * The score floor is kept only for the case it was written for — a re-read
 * where nothing at all was detected and the score is poor anyway, which is the
 * mumble that produces no findings rather than a clean recitation. When the
 * re-read still contains other errors, THOSE explain the score, and holding
 * this card shut on their account is blaming the learner for a card they have
 * not been shown.
 *
 * ── THE ATTEMPT CAP ────────────────────────────────────────────────────────
 *
 * Requested directly: after ATTEMPT_CAP tries at the same rung, accept the
 * result and move on regardless of score. Note what this deliberately allows —
 * a card can close with its error STILL PRESENT. That is the instruction and it
 * is the right call: a learner who has tried the same word four times is not
 * learning any more from a fifth, and the app saying "this is enough, let's
 * continue" is what a teacher would do. The error is not falsified — it is
 * still in the attempt record, and it will be found again the next time they
 * recite the ayah.
 */

import { Attempt, TajweedError } from "./api";

/** Tries at one rung before the app stops asking. Requested value: 3. */
export const ATTEMPT_CAP = 3;

export type ClearReason =
  /** The error is gone and the read was good. */
  | "clear"
  /** The error is gone; other cards' errors account for the score. */
  | "clear_others_pending"
  /** Cap reached — accepted and moving on. See the note above. */
  | "accepted"
  /** The mistake is still there. */
  | "still_wrong"
  /** Nothing to judge: rejected recording, or nothing to compare against. */
  | "unjudged"
  /** Error gone, nothing else found, but the read itself was poor. */
  | "low_score";

export type Verdict = {
  cleared: boolean;
  reason: ClearReason;
  /** True when the cap, not the recitation, is what closed this. */
  accepted: boolean;
};

export type RetryInput = {
  /** The re-read. */
  out: Attempt;
  /** The card being drilled. */
  error: TajweedError;
  /** Tries at this rung INCLUDING this one, 1-based. */
  attempt: number;
};

/** Same identity the cards use: one card per (code, letter). */
const idOf = (e: TajweedError) => `${e.code}:${e.letter}`;

export function decideRetry({ out, error, attempt }: RetryInput): Verdict {
  const judged = out.status === "ok" && out.analysable;
  if (!judged) {
    // A re-read we could not judge is NOT a fix, and it does not count toward
    // the cap either — the learner did not get a turn, the recording did.
    return { cleared: false, reason: "unjudged", accepted: false };
  }

  const id = idOf(error);
  const stillThere = out.errors.some((x) => idOf(x) === id);
  const others = out.errors.filter((x) => idOf(x) !== id).length;
  const score = out.score ?? 0;
  const need = out.pass_score ?? 0.8;
  const capped = attempt >= ATTEMPT_CAP;

  if (stillThere) {
    return capped
      ? { cleared: true, reason: "accepted", accepted: true }
      : { cleared: false, reason: "still_wrong", accepted: false };
  }

  // The error this card is about is gone. That is the finding that matters.
  if (score >= need) {
    return { cleared: true, reason: "clear", accepted: false };
  }
  if (others > 0) {
    // The score is low because of mistakes belonging to cards the learner has
    // not been shown yet. Holding this one shut for them is the deadlock.
    return { cleared: true, reason: "clear_others_pending", accepted: false };
  }
  if (capped) {
    return { cleared: true, reason: "accepted", accepted: true };
  }
  return { cleared: false, reason: "low_score", accepted: false };
}
