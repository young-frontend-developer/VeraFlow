# -*- coding: utf-8 -*-
"""audio bytes -> learner-facing feedback. The whole engine in one function.

Order matters:
  1. decode
  2. QUALITY GATE - reject before inference, never after (see audio.py)
  3. computed target (decision 1)
  4. transcribe
  5. typed errors (decision 2)
  6. TOLERANCE GATE - drop deviations too small to be real (config/tolerances.json)
  7. content gate - production only, see present()

Everything the learner sees comes from content/rules.json. This module decides
WHICH errors to mention and in what order; it never writes a sentence.
"""
import logging
from dataclasses import dataclass, field

from .. import content
from ..config import settings
from ..content import coaching, sifat
from .audio import DecodeInfo, check_quality, decode
from . import cards
from .collapse import looks_collapsed
from .debug_capture import capture
from . import headlines
from .model import transcribe
from . import practice
from .ranges import Range, is_legal_range, n_words, reference
from .runlength import MARKS, MARK_SOUND
from .segments import (segments_for_range, unit_char_spans, unit_letters,
                       unit_spans_for_range, unit_word_indices, unit_words)
from .target import Target
from . import teaching
from .tolerances import apply as apply_tolerances
from .typed_errors import TypedError, typed_diff

log = logging.getLogger(__name__)

# THE DISPLAY CAP IS GONE. It was MAX_SHOWN = 2, on the theory that two
# actionable errors beat ten true ones. In practice it meant a learner who made
# five mistakes was told about two of them and never learned the rest existed,
# and combined with the content gate below it was usually a cap on nothing -
# the gate had already emptied the list. If the engine found five, show five.
#
# WHAT REPLACED IT IS NOT A CAP. Every card is still sent, ordered by POSITION
# IN THE RECITATION (see _rank), and each carries `reveal_order`. The CLIENT
# opens one at a time and unlocks the next when the current one is fixed - so
# the learner meets one correction at a time while the engine still reports
# everything it found, and "hali N ta bor" can be honest about the rest because
# the rest is actually there.

# Retained but NO LONGER CONSULTED BY THE SORT. `severity` used to break ties
# inside a teaching tier; ordering is now purely positional and two errors
# cannot share a unit index, so there are no ties left to break. It stays
# because the registry still carries the field and the review tool still reads
# it - deleting it here would not remove it from the content.
SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Feedback:
    status: str                      # ok | retry_recording | error
    sura: int = 0
    aya: int = 0
    reason: str = ""                 # why status != ok
    expected_phonemes: str = ""
    heard_phonemes: str = ""
    clean: bool = False              # nothing detected at all - safe to praise
    suppressed: bool = False         # detected something, showed nothing
    # False when the model returned nothing to compare against, so no judgement
    # of any kind was formed. Distinct from `suppressed`, which means a
    # judgement WAS formed and then withheld. The UI must not print the same
    # sentence for both - see Feedback.tsx.
    analysable: bool = True
    errors: list[dict] = field(default_factory=list)      # shown to the learner
    silent_errors: list[dict] = field(default_factory=list)  # logged only
    # Deviations measured but judged too small to be real - see the tolerance
    # gate below. Logged, never shown, and the input to threshold calibration.
    within_tolerance: list[dict] = field(default_factory=list)
    snr_db: float = 0.0
    duration_s: float = 0.0
    mean_prob: float = 0.0
    # Fraction of the recited range's sounds with no error against them, and
    # the mark a practice rung has to clear to unlock the next one. Both travel
    # so the client never has to hard-code the threshold it is comparing to -
    # see config.practice_pass and RULE 9.
    score: float = 0.0
    pass_score: float = 0.0


def _is_allocation_failure(exc: BaseException) -> bool:
    """Torch raises a bare RuntimeError for an allocator failure, so the message
    is the only thing distinguishing it from a genuine bug. Matched narrowly on
    purpose - swallowing every RuntimeError here would hide real breakage as
    "your ayah was too long"."""
    if isinstance(exc, MemoryError):
        return True
    text = str(exc).lower()
    return ("not enough memory" in text
            or "defaultcpuallocator" in text
            or "out of memory" in text
            or "cannot allocate" in text)


def _sifat_errors(phonetized, pred) -> list[TypedError]:
    """Ṣifa disagreements, routed to the entry written about each one.

    The model reports WHICH ṣifa disagreed and in which direction. This used to
    discard both and stamp everything GENERIC_SIFAT_MISMATCH, so a learner whose
    ط came out thin was shown "the ṣifa did not come out right" while
    TAFKHEEM_LOST - with the ruling, the correction and the drill - sat unread
    in the registry. sifat_codes.code_for is that routing, and the generic now
    fires only for ṣifāt nobody has authored an entry for.

    ⚠️ THE FALSE-POSITIVE FLOOR FOR THIS IS UNMEASURED. sifa_compare.py was
    written to quantify it - how often the predicted ṣifa disagrees with the
    reference on recitation a qori certifies as CORRECT - and that calibration
    has not been run. Every entry is status='draft' and carries the draft
    marker, and production withholds them, so the exposure is bounded; but this
    is the one detector here resting on an unknown rather than on a measurement.
    Run tools/calibrate.py before this goes anywhere near a real learner.

    `at` is remapped from ṣifa-group index to run-length unit index. The two
    are equal for most ayat and NOT for all - 112:1 has 11 units to 10 groups -
    so using the group index directly would put the highlight, and the word in
    the headline, on the wrong letter exactly where the text is unusual.
    """
    from .sifa_compare import compare, reference_groups
    from .sifat_codes import OUT_OF_SCOPE, code_for

    ref = reference_groups(phonetized.sifat)
    got = pred.sifat or []
    if not ref or not got:
        return []
    to_unit = _group_to_unit(phonetized.phonemes, ref)
    keys = [_group_letter(g) for g in ref]
    out = []
    for d in compare(ref, got):
        # THE SCOPE GATE, and it is here rather than only inside code_for so the
        # pipeline says out loud which comparisons it declines to act on.
        # compare() still measures hams/jahr and shidda/rakhawa - that is the
        # calibration surface, and sifa_compare is observation-only by design -
        # but nothing downstream of this line ever sees one. See
        # sifat_codes.OUT_OF_SCOPE for why the two ṣifāt are excluded.
        if d.field in OUT_OF_SCOPE:
            continue
        at, letter = _reanchor_tafkheem(d.field, d.at, d.letter, keys)
        code = code_for(d.field, letter, d.expected, d.heard)
        if code is None:
            # Not an error. Either a difference in degree between two values
            # that are both correct enough that no entry exists to correct it,
            # or - see sifat_codes.applies - a ṣifa this letter does not have,
            # which cannot be a mistake at all. Dropped here rather than shown
            # as a generic.
            continue
        out.append(TypedError(code=code, at=to_unit.get(at, at),
                              letter=letter, expected=d.expected,
                              heard=d.heard, sifa=d.field))
    return out


def _group_letter(group: dict) -> str:
    from .sifa_compare import _base
    return _base(group.get("phonemes") or "")


def _reanchor_tafkheem(field: str, at: int, letter: str,
                       keys: list[str]) -> tuple[int, str]:
    """Move a heaviness error off a madd letter and onto the consonant it
    lengthens. Returns the (position, letter) the card should be about.

    RULE 5. ا has no tafkheem or tarqiq ruling of its own - it is a lengthening,
    and it comes out heavy or light entirely because the consonant in front of
    it did. «طَا» is heavy because of the ط. So a card saying "the alif came out
    light" names a letter with no such property, and the learner has nothing to
    change about the alif that would fix it.

    RE-ANCHORED RATHER THAN DROPPED, because the observation is real: something
    did come out light, and it was the consonant. Walking back to it turns an
    unactionable card into the correct one. If there is no consonant to walk
    back to - a madd letter opening the range - the position is returned
    unchanged and sifat_codes.applies() then refuses it, because at that point
    there is genuinely nothing to say.
    """
    from .sifat_codes import BORROWS_TAFKHEEM

    if field != "tafkheem_or_taqeeq" or letter not in BORROWS_TAFKHEEM:
        return at, letter
    for back in range(at - 1, -1, -1):
        if keys[back] and keys[back] not in BORROWS_TAFKHEEM:
            return back, keys[back]
    return at, letter


def _group_to_unit(phonemes: str, ref_groups: list[dict]) -> dict[int, int]:
    """ṣifa-group index -> run-length unit index, via character offsets.

    The groups tile the phoneme string in order, so walking their lengths gives
    each group's span, and unit_char_spans gives the units'. Anything that does
    not line up is dropped rather than guessed.
    """
    from .segments import unit_char_spans

    spans = unit_char_spans(phonemes)
    char_to_unit = {}
    for unit, (a, b) in enumerate(spans):
        for c in range(a, b):
            char_to_unit[c] = unit

    out, pos = {}, 0
    for i, g in enumerate(ref_groups):
        text = g.get("phonemes") or ""
        if pos in char_to_unit:
            out[i] = char_to_unit[pos]
        pos += len(text)
    return out


def _resolve_marks(e: TypedError, letters: dict[int, str]) -> None:
    """Replace every QPS notation symbol on one error with a real letter.

    THE ONE PLACE THIS CAN HAPPEN. typed_diff sees phoneme strings and has no
    mushaf to consult; the client must not be trusted to translate symbols it
    should never receive. The pipeline is the only layer holding both the unit
    index and the Uthmani text, which is why it already fills in `word` here.

    THE TWO SIDES ARE RESOLVED DIFFERENTLY, because they mean different things.

    `letter` and `expected` describe the REFERENCE - what the text says - so
    they resolve against the mushaf and get the real letter, whatever it is.

    `heard` describes the PREDICTION. There is no reference character to look
    up: the learner said something that is not in the text. So it falls back to
    what the symbol notates as a sound (MARK_SOUND), which is a transcription
    fact rather than a ruling. ڇ has no such answer and blanks instead - a
    qalqalah is an echo on a letter, not a letter - and the insertion case that
    used to produce it is now filed as QALQALA_EXCESSIVE; see _added().

    ORDER MATTERS. _duration_code() classifies MADD vs GHUNNA vs SHADDA by
    testing the QPS letter against MADD_LETTERS and GHUNNA_LETTERS, and it has
    already run by the time this is called. Resolving earlier would send every
    ۥ-madd and ں-ghunna down the SHADDA fallback and out as a code with no
    content - silently, and only for the errors this function exists to fix.
    """
    real = letters.get(e.at, "")
    if e.letter in MARKS:
        e.letter = real
    if e.expected in MARKS:
        e.expected = real
    if e.heard in MARKS:
        e.heard = MARK_SOUND.get(e.heard, "")


def locate(detected: list[TypedError], uthmani: str, sura: int, aya: int,
           start_word: int, num_words: int) -> list[TypedError]:
    """Attach word, word index and real letter to every detected error.

    Split out of analyze() so it can be exercised WITHOUT the 2.42 GB model.
    That is not a convenience: the merge depends on `letter`, `letter` depends
    on this function, and the bug it fixes - every qalqalah error in an ayah
    collapsing into one card - is invisible unless a test can drive real ayah
    text through the real resolution. A test that reimplemented this loop would
    have gone on passing while the pipeline broke.

    Mutates in place and returns the same list, because the caller wants both.
    """
    segs = segments_for_range(sura, aya, start_word, num_words)
    words = unit_words(uthmani, segs)
    # Ayah-relative, so "re-record just this word" can be handed straight to the
    # practice range API. unit_word_indices counts within the text it is given,
    # which here is the SELECTED RANGE - so the range's own offset has to be
    # added back or every re-record inside a partial selection would target the
    # wrong word.
    windex = unit_word_indices(uthmani, segs)
    # unit -> the real Arabic letter, read out of the mushaf. See
    # segments.unit_letters(): five QPS notation symbols were reaching cards as
    # though they were letters, which broke the card AND the merge, since cards
    # group on (code, letter) and every qalqalah error carried the same ڇ.
    letters = unit_letters(uthmani, segs)
    for e in detected:
        e.word = words.get(e.at, "")
        w = windex.get(e.at)
        e.word_index = -1 if w is None else w + start_word
        _resolve_marks(e, letters)
    return detected


def _kind_of(e: TypedError) -> str:
    """One error's card kind, without rendering the card.

    Ranking has to know the kind BEFORE the body is rendered, because the kind
    is what the tier is keyed on. The registry group is read directly rather
    than taken from a rendered body, which is the same lookup cards.kind_of()
    would get one step later.
    """
    entry = coaching.entry(e.code) or {}
    return cards.kind_of(e.code, entry.get("group", ""), e.sifa)


def _rank(e: TypedError) -> tuple:
    """RECITATION ORDER. Where the mistake happened, and nothing else.

    ── THIS IS A DELIBERATE OVERRIDE, NOT A MERGE ─────────────────────────
    It reverses the teaching-tier ordering documented in engine/teaching.py,
    under which cards were sorted by what the mistake DID - wrong letter, then
    articulation, then ruling, then timing - with severity breaking ties inside
    a tier and position breaking ties inside that.

    The two systems are NOT combined. Tier is no longer consulted here at all,
    because a hybrid would be the worst of both: cards would look
    position-ordered until two mistakes of different tiers sat close together,
    and then jump, which is harder to follow than either rule applied
    consistently. If the tier ordering is ever wanted back it should replace
    this outright rather than be folded into it.

    THE ARGUMENT FOR POSITION. A learner works through the cards with the ayah
    in front of them, and reading is left to right through the recitation. Cards
    in recitation order let them walk the verse once, fixing each spot as they
    reach it. Tier order made them jump around the ayah - fix a letter at the
    end, then an articulation at the start, then a ruling in the middle - which
    is three passes over the text to do one pass of work.

    WHAT IS LOST, STATED PLAINLY. The dependency argument in teaching.py is
    real and this does not refute it: correcting the length of a sound whose
    letter is wrong still teaches holding a wrong sound for the right count.
    That case now depends on the two mistakes being close together in the ayah,
    which they usually are - they are typically the same word - but not always.

    teaching.tier() IS STILL USED, and still by this module: it sets `tier` on
    each card for the client's reveal chain. Only the SORT stopped reading it.
    """
    return (e.at,)


def _unauthored_body(code: str) -> dict:
    """Stand-in for a code nobody has written content for.

    It deliberately does NOT invent a rule, a correction or a reason - decision
    4 forbids exactly that, and showing drafts by default is not an exemption.
    Empty strings everywhere a sentence about tajweed would otherwise go.

    IT NO LONGER CARRIES THE CODE AS A LABEL. `label` is printed as the card's
    kicker, so putting GHUNNA_LONG there showed a learner an internal
    identifier - the thing Part B forbids outright. The card is not left
    anonymous: `kind` still gives it a real title, and `word`/`letter` still
    locate it. The code travels on the record for logging and for the draft
    marker's audit trail, where no learner reads it.

    Reaching this is now rare and getting rarer: GENERIC_LETTER_SUBSTITUTED
    catches every unlisted letter confusion and GENERIC_SIFAT_MISMATCH every
    unlisted sifa one, so what is left is the handful of duration codes with no
    entry in either registry. The learner still sees the word and the letter -
    those travel on the error itself, not in this body - which is the whole
    requirement: located, always, even when we have nothing to say about it.
    """
    return {"headline": "", "fix": "", "label": "",
            "audio_pair": "", "group": "",
            "severity": content.rules().get(code, {}).get("severity", "medium"),
            "reviewed": False, "unauthored": True}


# Codes whose authored text describes the ERROR CLASS rather than the error:
# "the letter's ṣifa did not come out right", which is true of every ṣifa fault
# ever detected and useful for none of them.
_GENERIC_SIFAT = "GENERIC_SIFAT_MISMATCH"


def _name_the_sifat(e: TypedError, body: dict | None,
                    guide: dict | None) -> dict | None:
    """Replace generic ṣifa language with the named property, where we have it.

    RULES 3 AND 4. "Harfning sifati to'g'ri chiqmadi" is banned outright, and it
    was the most-shown sentence in the app: every ṣifa disagreement with no
    specific entry rendered it, over a detector that had already said which of
    hams, shidda, tafkheem, itbaq, qalqala or ghunna was the one that flipped.

    ONLY THE GENERIC IS OVERWRITTEN. A specific entry - TAFKHEEM_LOST,
    RAA_TAFKHEEM_MISSING, GHUNNA_MISSING - is authored about exactly this fault
    in exactly this direction, and is better than anything keyed on the ṣifa
    alone could be. Those keep their own headline and instruction and merely
    gain the articulation note beside it.

    With no guidance authored for the ṣifa, the card is left as it was rather
    than blanked: a vague sentence about a located letter still beats an empty
    slot, and sifat.missing_guidance() is what makes that gap countable.
    """
    if body is None or guide is None:
        return body
    if coaching.resolve(e.code) != _GENERIC_SIFAT:
        return body
    out = dict(body)
    out["headline"] = guide["wrong"]
    out["fix"] = guide["how"]
    return out


def _distinct(text: str, already_shown: str) -> str:
    """`text`, unless the card is already saying exactly that."""
    return "" if text.strip() == already_shown.strip() else text


def accuracy(n_units: int, errors: list[TypedError]) -> float:
    """Fraction of this range's sounds that came out with no error against them.

    THE SCORE RULE 9 GATES ON. Deliberately the simplest thing that is actually
    measured rather than a weighted composite: how many of the units the learner
    was asked to produce came back clean. One error on a five-unit word is 0.8;
    the same error inside a forty-unit ayah is 0.975, which is the right
    behaviour - it is a smaller share of a longer read.

    Distinct occurrences are counted, not cards, so a letter missed four times
    costs four units rather than one. Clamped at zero because a range can pick
    up more errors than it has units when insertions pile up.
    """
    if n_units <= 0:
        return 0.0
    return max(0.0, 1.0 - len({e.at for e in errors}) / n_units)


# ── which placed rule a given error is ABOUT ──────────────────────────────
# A unit can carry more than one ruling at once - the ا in ضضَااااااللِۦۦۦۦن is a
# madd lozim sitting inside a word that also contains an istila letter - so
# "the rule at this position" is a set, and the card needs one member of it.
#
# The ERROR CODE picks. A shortened madd is about the madd ruling and not about
# the tafkheem that happens to share the sound, and the registry group already
# says which family the code belongs to. Preference is ordered within a family
# because the madd subtypes are mutually exclusive at a position but the set is
# not ordered: lozim before muttasil before munfasil before tabiiy, longest
# first, so a six-count is never reported as the two-count it also technically
# matches.
_RULE_PREFERENCE = {
    "madd": ("RULE_MADD_LOZIM", "RULE_MADD_MUTTASIL", "RULE_MADD_MUNFASIL",
             "RULE_MADD_TABIIY"),
    "ghunna": ("RULE_IKHFO_GHUNNA",),
    "ahkam": ("RULE_IKHFO_GHUNNA", "RULE_IDGHOM"),
    "sifat": ("RULE_QALQALA", "RULE_TAFXIM"),
    "shadda": ("RULE_IKHFO_GHUNNA",),
}


def _rules_at(uthmani: str, phonemes: str) -> dict[int, list[str]]:
    """Unit index -> the rules governing it, for the range being analysed.

    A SECOND PHONETIZER RUN, and it is not avoidable. `target.phonemes` is the
    flat string, and remove_spaces=True destroys the one thing that separates
    madd muttasil from madd munfasil. The spaced run is thrown away immediately
    after the map is built.

    FAILING HERE COSTS RULE NAMES, NOT THE ATTEMPT. Same trade as the badge
    strip in routes._rule_badges: a learner who has just recorded an ayah must
    get their corrections back even if the rule layer cannot be computed, and a
    card with no rule name is exactly the degraded-but-honest state the whole
    §12 fallback path is built for.
    """
    try:
        from quran_transcript import quran_phonetizer

        from .moshaf import MOSHAF
        from .rule_presence import rules_by_unit

        spaced = quran_phonetizer(uthmani, MOSHAF, remove_spaces=False)
        return rules_by_unit(spaced.phonemes, unit_char_spans(phonemes))
    except Exception:
        log.warning("rule placement unavailable; cards will name no rules")
        return {}


def _placed_rule(group: str, placed: list[str]) -> str:
    """The one rule code this card may name, or "" if none of them fit.

    "" when the error's family has no preference listed, when nothing was
    placed at the position, or when what was placed belongs to a different
    family. All three are the same answer - we cannot say which ruling this is -
    and all three must produce a headline that names no rule.
    """
    for code in _RULE_PREFERENCE.get(group, ()):
        if code in placed:
            return code
    return ""


def _headline(body: dict, e: TypedError, lang: str,
              placed: list[str]) -> tuple[str, str]:
    """(headline, rule name) for a restructured card. ("", "") for the rest.

    THE ONLY PLACE A RULE NAME IS ALLOWED TO REACH A LEARNER-FACING SENTENCE.
    Everything upstream deals in rule CODES; everything downstream renders a
    string. If the name is empty here, no pattern that needs one can build, and
    the entry's own `headline_no_rule` is used instead.
    """
    pattern = body.get("headline_pattern", "")
    if not pattern or not body.get("card_kind"):
        return "", ""

    rule_code = _placed_rule(body.get("group", ""), placed)
    # An entry may name a MORE PRECISE title than the placed badge carries -
    # see v7's _override_note on «Ixfo va g'unna». The override never creates a
    # placement, it only renames one that already happened, so a card with no
    # placed rule stays nameless no matter what it asks for.
    if rule_code:
        rule_code = body.get("rule_name_override") or rule_code
    rule_name = coaching.rule_title(rule_code, lang) if rule_code else ""
    gender = coaching.rule_gender(rule_code) if rule_code else ""

    letter = e.expected or e.letter
    return headlines.build(pattern, lang, rule_name=rule_name, letter=letter,
                           gender=gender,
                           fallback=body.get("headline_no_rule", "")), rule_name


def present(raw: list[TypedError], lang: str, *, uthmani: str = "",
            spans: dict[int, tuple[int, int]] | None = None,
            rules_at: dict[int, list[str]] | None = None
            ) -> tuple[list[dict], list[dict]]:
    """Detected errors -> (shown to the learner, logged only).

    Split out of analyze() so the gate is testable without the 2.42 GB model.

    EVERYTHING DETECTED IS SHOWN, in severity order, uncapped - unless this is
    production, where an unreviewed correction is withheld instead. `draft` is
    the contract with the client: any record carrying it must be rendered with
    a visible marker and never as settled guidance.

    The two halves are asymmetric on purpose. Hiding a real error from the
    person building the app buys nothing and costs the whole feedback loop;
    hiding one from a learner, on the strength of words no qori has read, is
    the trust failure this project is arranged to avoid.
    """
    shown, silent = [], []

    # ── contradictions are withheld before anything else ──────────────────
    # Two high-confidence detectors saying incompatible things about one unit
    # is a detection bug, not a correction. Neither card is shown and the pair
    # is logged for review - see engine/teaching.py for why guessing between
    # them is worse than showing nothing. This runs BEFORE ranking so a
    # conflicting error cannot take the first slot and stall the whole reveal
    # chain behind a card the learner cannot act on.
    conflicted, conflict_log = teaching.conflicts(raw, _kind_of)
    if conflicted:
        for e in raw:
            if e.at in conflicted:
                silent.append({**e.dict(), "status": "conflict",
                               "content": None, "draft": True})
        raw = [e for e in raw if e.at not in conflicted]

    # Rank FIRST, then merge. Merging preserves the order buckets first appear
    # in, so ranking here puts the most serious card first and the merge keeps
    # it there; merging first would rank buckets by whichever member happened
    # to land in front.
    for group in cards.merge(sorted(raw, key=_rank)):
        e = group[0]
        status = content.status_of(e.code)
        try:
            body = content.render(e.code, lang, e.dict())
        except coaching.UnfilledTemplate as exc:
            # LOUD, but not fatal to the whole attempt. A template the detector
            # cannot fill is a bug in one entry; raising here would throw away
            # every other correction in the same recitation and hand the
            # learner a 500 after minutes of waiting. So: shout in the log,
            # drop this one card, keep the rest. What must never happen -
            # showing a brace to a learner - still cannot.
            log.error("UNFILLED TEMPLATE %s: %s", e.code, exc)
            silent.append({**e.dict(), "status": "template_error",
                           "content": None, "draft": True})
            continue
        # A coaching entry is authored content in its own right. rules.json
        # knows nothing about the v4/v5 codes, so status_of() returns
        # "collect" for them - treating that as "not shippable" would silence
        # every new entry including the generics, which is exactly the failure
        # they exist to fix. They are still status='draft' and so still
        # unreviewed; production withholds them like anything else.
        if coaching.has(e.code):
            status = "draft"
        reviewed = status != "collect" and bool(body) and body.get("reviewed", False)

        # RULES 3 AND 4. The detector said WHICH ṣifa flipped and the card never
        # asked. `guide` carries that property's name and the physical
        # instruction for producing it - where the tongue, throat or lips go -
        # and where it exists it REPLACES the generic sentence rather than
        # sitting under it. See _name_the_sifat().
        guide = sifat.guidance(e.sifa, e.letter, lang)
        body = _name_the_sifat(e, body, guide)

        # THE RESTRUCTURED HEADLINE. Built from the entry's pattern and the
        # rule actually PLACED at this unit - never from the ayah-wide badge
        # set, which would let a madd lozim three words away name a card about
        # a different sound entirely. An unconverted entry (card_kind 0) gets
        # ("", "") back and keeps the headline its own generation authored.
        placed = (rules_at or {}).get(e.at, [])
        built, rule_named = _headline(body or {}, e, lang, placed)
        if built:
            body = {**(body or {}), "headline": built}

        record = {
            **e.dict(), "status": status, "content": body,
            "draft": False, "needs_teacher": status == "teacher",
            # The learner-facing category. The client renders THIS, never
            # `code` - see cards.py. `group` comes from the registry entry so a
            # code filed under makharij reads as "wrong letter" without the
            # engine needing a row for every entry.
            "kind": cards.kind_of(e.code, (body or {}).get("group", ""),
                                  e.sifa),
            # Every occurrence of this (code, letter), so the ayah can mark all
            # of them red while the learner reads a single card.
            "occurrences": cards.occurrences(group, spans, uthmani),
            "count": len(group),
            "words": cards.distinct_words(group),
            # The practice ladder. DERIVED, not authored, so it is present on
            # every card including the ones with no coaching text at all: a
            # learner whose error we cannot explain can still be shown what to
            # drill.
            #
            # `code` and `expected_count` are what pick the ladder SHAPE - an
            # omission, an insertion and a duration error each need a different
            # first rung, and the bare-letter opening belongs only to
            # articulation errors. See practice.category(). The ENGINE code is
            # passed, not the resolved registry one, because LETTER_DROPPED and
            # LETTER_ADDED exist only in the engine vocabulary; practice.py
            # classifies both vocabularies.
            "practice": practice.ladder(
                e.letter, e.word, e.word_index, code=e.code,
                expected_count=e.expected_count,
                letter_audio=(body or {}).get("audio_pair", "")),
            # RULE 12 gives the card a "rule name" slot. Taken from what is
            # already authored - the registry entry's own short title, or the
            # ṣifa's name - and left EMPTY rather than invented when neither
            # exists. The client falls back to the `kind` title, which is a real
            # name too; what it must never fall back to is the code.
            # A PLACED rule name outranks the entry's own label. The label is a
            # property of the entry ("Cho'zish (mad) qisqa qilingan" - true of
            # every shortened madd anywhere); the placed name is a property of
            # THIS position ("Mad lozim"), which is the thing the learner can
            # look up and the thing the ayah's colour coding will agree with.
            "rule_name": rule_named or (body or {}).get("label", "") or (
                guide or {}).get("name", ""),
            # The rule CODE, so the client can tint the card to match the same
            # rule's colour in the ayah above it. Empty whenever no rule was
            # placed - there is no "probably this one" here.
            "rule_code": _placed_rule((body or {}).get("group", ""), placed),
            "sifa_name": (guide or {}).get("name", ""),
            # The physical instruction. Separate from `fix` because they answer
            # different questions: `fix` is what to do about THIS mistake,
            # articulation is how the sound is made at all.
            #
            # OMITTED WHEN IT IS ALREADY THE FIX. On a generic ṣifa card the two
            # are the same sentence by construction - _name_the_sifat puts the
            # articulation INTO the fix slot, because there was nothing better
            # to put there - and rendering both printed it twice under its own
            # heading.
            "articulation": _distinct(
                (guide or {}).get("how", ""), (body or {}).get("fix", "")),
            # WHERE THE CORRECT LETTER COMES FROM, above the fix instruction.
            # A card could previously say "you read ص as س" and how to correct
            # it without ever saying what ص is - and the two GENERIC entries,
            # which catch every unlisted confusion and are therefore the
            # most-shown cards in the app, described no letter at all. Keyed by
            # letter in content/makharij.json, so every card gets one without
            # anybody authoring it per error pair. Draft like all content.
            "makhraj": cards.makhraj_line(e.code, e.expected, e.letter, lang),
        }

        if reviewed:
            shown.append(record)
        elif settings.show_unreviewed:
            record["draft"] = True
            if body is None:
                record["content"] = _unauthored_body(e.code)
            shown.append(record)
        else:
            # Production only. Flip `reviewed` in rules.json once a qualified
            # qori has signed the string off.
            silent.append(record)

    # ── the reveal chain ──────────────────────────────────────────────────
    # Stamped AFTER the content gate, not before, so the numbering counts cards
    # the learner will actually meet. Numbering before the gate would promise
    # "hali 4 ta bor" and then reveal two, which is a worse lie than saying
    # nothing - the count exists precisely so the learner can trust that the
    # rest is really there.
    for i, record in enumerate(shown):
        record["reveal_order"] = i
        record["tier"] = teaching.tier(record["kind"])
    return shown, silent


def analyze(audio: bytes, sura: int, aya: int, lang: str = "uz", *,
            start_word: int = 0, num_words: int = 0,
            include_bismillah: bool = False,
            device_id: str = "", audio_consented: bool = False) -> Feedback:
    """`num_words=0` means the whole ayah. Indices are relative to the ayah."""
    try:
        total_words = n_words(sura, aya)
    except Exception:
        return Feedback(status="error", sura=sura, aya=aya,
                        reason="ayah_not_in_catalogue")

    if num_words <= 0:
        start_word, num_words = 0, total_words
    if not is_legal_range(sura, aya, start_word, num_words):
        # The UI is expected to offer only legal cuts, so reaching here means a
        # hand-built request or a stale client - name it rather than let
        # PartOfUthmaniWord surface as a 500.
        return Feedback(status="error", sura=sura, aya=aya,
                        reason="illegal_word_range")
    rng = Range(sura, aya, start_word, num_words, include_bismillah)

    info = DecodeInfo()
    try:
        wave = decode(audio, info)
    except Exception as exc:
        # Log the bytes even when decoding fails - that is precisely the case
        # you cannot diagnose without them.
        capture(audio, None, sura, aya, info.as_dict(), {},
                {"outcome": "decode_failed", "error": str(exc)},
                device_id=device_id, audio_consented=audio_consented)
        log.error("[%03d:%03d] decode failed (%s): %s",
                  sura, aya, info.sniff, exc)
        return Feedback(status="error", sura=sura, aya=aya,
                        reason=f"decode_failed: {exc}")

    q = check_quality(wave)
    meas = {"duration_s": q.duration_s, "peak": q.peak, "rms": q.rms,
            "clipped_pct": q.clipped_pct, "speech_db": q.speech_db,
            "noise_db": q.noise_db, "snr_db": q.snr_db,
            "snr_measurable": q.snr_measurable}

    if not q.ok:
        capture(audio, wave, sura, aya, info.as_dict(), meas,
                {"outcome": "retry_recording", "reason": q.reason},
                device_id=device_id, audio_consented=audio_consented)
        return Feedback(status="retry_recording", sura=sura, aya=aya,
                        reason=q.reason, snr_db=q.snr_db, duration_s=q.duration_s)

    # The target covers the SELECTED RANGE only, not the whole ayah - otherwise
    # every segment would read as a huge deletion error.
    uthmani, phonetized = reference(rng)
    target = Target(sura=sura, aya=aya, uthmani=uthmani,
                    phonemes=phonetized.phonemes, n_sifat=len(phonetized.sifat))

    try:
        pred = transcribe(wave, phonetized)
    except (RuntimeError, MemoryError) as exc:
        # Running out of memory mid-forward is a 500 if left alone, and the
        # learner has already waited minutes for it. The cause is quadratic:
        # wav2vec2-BERT's relative-position attention allocates
        # (47*seconds)^2 * 256 bytes, so a long ayah asks for gigabytes.
        # settings.max_audio_seconds is meant to catch this before inference;
        # this is the net for when it is set too high for the box.
        if not _is_allocation_failure(exc):
            raise
        capture(audio, wave, sura, aya, info.as_dict(), meas,
                {"outcome": "out_of_memory", "error": str(exc)[:400],
                 "duration_s": q.duration_s},
                device_id=device_id, audio_consented=audio_consented)
        log.error("[%03d:%03d] OOM on %.0fs of audio: %s",
                  sura, aya, q.duration_s, exc)
        return Feedback(status="retry_recording", sura=sura, aya=aya,
                        reason="too_long_for_engine", snr_db=q.snr_db,
                        duration_s=q.duration_s)

    # The model answers confidently even when the audio was unusable, returning
    # huruf muqatta'at rather than low probabilities. Catch that from the output
    # itself - it is the failure the audio gate was aiming at and never hit.
    collapsed, detail = looks_collapsed(pred.phonemes, sura, aya, target.phonemes)
    if collapsed:
        capture(audio, wave, sura, aya, info.as_dict(), meas,
                {"outcome": "collapsed", "detail": detail,
                 "expected": target.phonemes, "heard": pred.phonemes,
                 "mean_prob": pred.mean_prob},
                device_id=device_id, audio_consented=audio_consented)
        log.warning("[%03d:%03d] muqatta'at collapse: %s | heard=%s expected=%s",
                    sura, aya, detail, pred.phonemes, target.phonemes)
        return Feedback(status="retry_recording", sura=sura, aya=aya,
                        reason="unclear_recitation", snr_db=q.snr_db,
                        duration_s=q.duration_s, mean_prob=pred.mean_prob,
                        expected_phonemes=target.phonemes,
                        heard_phonemes=pred.phonemes)

    # Nothing came back to diff against. Not a collapse (that is caught above,
    # and returns huruf muqatta'at rather than silence) and not a clean read
    # either - the engine simply has no opinion to offer. It gets its own flag
    # so the UI can say precisely that, instead of borrowing the sentence meant
    # for a suppressed correction.
    if not pred.phonemes.strip():
        capture(audio, wave, sura, aya, info.as_dict(), meas,
                {"outcome": "not_analysable", "expected": target.phonemes,
                 "heard": pred.phonemes, "mean_prob": pred.mean_prob},
                device_id=device_id, audio_consented=audio_consented)
        log.warning("[%03d:%03d] model returned no phonemes", sura, aya)
        return Feedback(status="ok", sura=sura, aya=aya, analysable=False,
                        expected_phonemes=target.phonemes, heard_phonemes="",
                        snr_db=q.snr_db, duration_s=q.duration_s,
                        mean_prob=pred.mean_prob)

    detected = typed_diff(target.phonemes, pred.phonemes)
    detected += _sifat_errors(phonetized, pred)

    locate(detected, uthmani, sura, aya, rng.start_word, rng.num_words)

    # Two correct takes of the same ayah by the same reciter do not produce the
    # same phoneme string - a madd held 4 counts in one reads as 5 in the other -
    # so an untoleranced duration check reports an error on correct recitation.
    # Thresholds come from config/tolerances.json and are calibrated by
    # tools/calibrate.py against recordings certified correct. The shipped
    # defaults are deliberately inert (min_delta = 1, i.e. no change in
    # behaviour) until that calibration has actually been run.
    raw, within_tolerance = apply_tolerances(detected, pred.mean_prob)

    spans = unit_spans_for_range(sura, aya, rng.start_word, rng.num_words)
    shown, silent = present(raw, lang, uthmani=uthmani, spans=spans,
                            rules_at=_rules_at(uthmani, target.phonemes))
    # RULE 9's gate. Measured over the RANGE that was actually recited, so a
    # word-rung re-read is scored against that word and not against the ayah it
    # came from.
    score = accuracy(len(unit_char_spans(target.phonemes)), raw)

    # Within-tolerance deviations are logged in full, never just counted. They
    # are the raw material tools/calibrate.py turns into thresholds, and once a
    # threshold is raised this list is where you find out what it started hiding.
    tolerated = [{**e.dict(), "margin": v.margin, "threshold": v.threshold,
                  "reason": v.reason} for e, v in within_tolerance]

    capture(audio, wave, sura, aya, info.as_dict(), meas,
            {"outcome": "ok", "expected": target.phonemes,
             "heard": pred.phonemes, "mean_prob": pred.mean_prob,
             "errors_detected": [e.code for e in raw],
             "errors_shown": [e["code"] for e in shown],
             "errors_suppressed": [e["code"] for e in silent],
             "within_tolerance": tolerated},
            device_id=device_id, audio_consented=audio_consented)

    # `clean` must mean "nothing was detected", not "nothing was displayed".
    # Praising a recitation the engine flagged - but suppressed for lack of
    # reviewed content - is a false reassurance, and decision 5 cuts both ways:
    # do not claim an error you are unsure of, and do not claim perfection you
    # are equally unsure of. The UI shows a neutral "not fully assessed" instead.
    #
    # A within-tolerance deviation does NOT block `clean`, and that is the one
    # deliberate difference. Suppressing for lack of reviewed content means "we
    # found something and cannot talk about it"; falling under a tolerance means
    # "we measured it and it is not an error". Only the first is uncertainty.
    # That distinction is only as good as the thresholds, which is why the
    # shipped ones are inert until calibrate.py has been run against real
    # certified-correct takes.
    return Feedback(
        status="ok", sura=sura, aya=aya, analysable=True,
        expected_phonemes=target.phonemes, heard_phonemes=pred.phonemes,
        clean=not raw, suppressed=bool(raw) and not shown,
        errors=shown, silent_errors=silent, within_tolerance=tolerated,
        snr_db=q.snr_db, duration_s=q.duration_s, mean_prob=pred.mean_prob,
        score=round(score, 3), pass_score=settings.practice_pass,
    )
