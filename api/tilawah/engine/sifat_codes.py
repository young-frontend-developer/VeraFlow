# -*- coding: utf-8 -*-
"""Ṣifa disagreement -> the specific error code that describes it.

WHY THIS EXISTS
---------------
The model does not just say "this letter is wrong". It says WHICH ṣifa
disagreed and in which direction: tafkheem_or_taqeeq went mofakham -> moraqaq,
qalqla went moqalqal -> not_moqalqal. That is exactly the distinction the
registry entries are written against - TAFKHEEM_LOST and TAFKHEEM_ADDED are two
different corrections with two different drills - and the pipeline was throwing
it away, stamping every ṣifa disagreement GENERIC_SIFAT_MISMATCH and showing the
learner "the ṣifa did not come out right" over entries that say precisely what
went wrong and how to fix it.

WHAT FALLS THROUGH ON PURPOSE
-----------------------------
The generic is not deleted, it is narrowed. It now fires only for ṣifāt nobody
has authored an entry for - itbaq, safeer, tikraar, tafashie, istitala - which
is what a fallback is for. If a ṣifa in ROUTED gains a specific entry later, it
moves out of the generic by adding a row here, not by touching the pipeline.

WHAT IS OUT OF SCOPE, WHICH IS A DIFFERENT THING
------------------------------------------------
OUT_OF_SCOPE is not the fallback and not a gap. It is a list of ṣifāt this app
has decided not to correct at all, and a disagreement in one of them produces no
error - not a generic, not a suppressed card, nothing. See the set below.

The value vocabulary is quran_transcript's, not ours - see
quran_transcript/phonetics/sifa.py, SifaOutput:

    hams_or_jahr        hams | jahr
    shidda_or_rakhawa   shadeed | between | rikhw
    tafkheem_or_taqeeq  mofakham | moraqaq | low_mofakham
    itbaq               monfateh | motbaq
    qalqla              moqalqal | not_moqalqal
    ghonna              maghnoon | not_maghnoon
"""

# mofakham and low_mofakham are both HEAVY. The registry knows two directions -
# heaviness lost and heaviness added - and has no entry for "heavy, but a
# different degree of heavy", because that is not an error a teacher corrects.
HEAVY = {"mofakham", "low_mofakham"}

GENERIC = "GENERIC_SIFAT_MISMATCH"

# ── ṢIFĀT THIS APP DOES NOT CORRECT ───────────────────────────────────────
# SCOPE DECISION 2026-08-07, requested by Rahmatulloh. Not a bug, not a
# measurement problem, and not a gap waiting to be filled.
#
# hams/jahr and shidda/rakhawa are lahn khafiy khafiy - the faintest class of
# error. A shadeed letter read slightly loose, or a mahmus letter with a trace
# of voice, is inaudible to most reciters, changes no meaning, and breaks no
# required rule. The app's current purpose is the errors that DO one of those
# two things, so these are removed rather than shown, ranked or counted.
#
# WHAT THIS IS NOT. It is not a claim the detectors failed. Both had sound,
# measured preconditions (HAMS_LOST 95.6% -> 41.4%; JAHR_LOST 100% -> 8.8%;
# SHIDDA_LOST 97.3% -> 17.7%) and their registry entries were sourced and
# usable. They are switched off because of what they are about, so the restore
# for an advanced-user mode is mechanical - see tajweed_registry_v3_amendments
# .json -> delete -> HAMS_LOST for the exact steps.
#
# CHECKED BEFORE THE GENERIC, deliberately. Removing these from ROUTED alone
# would drop them into the fallback, and the learner would get "the ṣifa did not
# come out right" for exactly the errors we just decided not to report - the
# worst of both.
OUT_OF_SCOPE = {"hams_or_jahr", "shidda_or_rakhawa"}

# The ṣifāt this module routes. A disagreement in any OTHER field goes generic,
# unless it is OUT_OF_SCOPE, in which case there is no error at all.
ROUTED = {"tafkheem_or_taqeeq", "ghonna", "qalqla"}

RAA, LAM = "ر", "ل"

# ── which letters each ṣifa can be an error ABOUT ─────────────────────────
# RULE 5: NEVER INVENT IMPOSSIBLE TAJWEED. Three of these ṣifāt are properties
# only certain letters have, and a disagreement reported on any other letter is
# a measurement artifact - the model guessing a value for a field that does not
# apply. Emitting a card for one produces a correction for a ruling that does
# not exist, which a learner cannot act on and a teacher would have to unteach.
#
#   qalqla    only the five qalqalah letters, «قطب جد». A qalqalah on ه is not
#             a mistake in degree, it is a category error.
#   ghonna    only ن and م and the notation marks standing for them. Nothing
#             else in the alphabet has a nasal to hold.
#   tafkheem  NOT a letter list - see below. Heaviness ADDED is a real error on
#             any light letter (a ت read heavy is a common and correctable
#             mistake), so restricting the ṣifa to the isti'la letters would
#             delete the useful direction. The single impossible case is the
#             MADD LETTER, which has no heaviness of its own at all.
#
# hams_or_jahr and shidda_or_rakhawa are absent from this section because they
# are absent from the whole module now - see OUT_OF_SCOPE. They never had a
# letter guard when they were routed, and correctly so: every Arabic letter has
# a value for both, so there was no letter on which a disagreement was
# impossible. Noted here so a restore does not go looking for a guard that was
# never needed and invent one.
QALQALA_LETTERS = frozenset("قطبجد")
GHUNNA_LETTERS = frozenset("نمںۦ۾")
ISTILA_LETTERS = frozenset("خصضطظغق")
# Heaviness IS a real question for these two beyond isti'la - ر by its vowel,
# ل in the name of Allah - which is why they route to their own codes below.
TAFKHEEM_LETTERS = ISTILA_LETTERS | {RAA, LAM}

# THE ALIF CASE, which is what RULE 5 was written about. ا has no independent
# tafkheem or tarqiq ruling: it is a lengthening, and it comes out heavy or
# light entirely because the consonant in front of it did. "The alif became
# heavy" names a property the letter does not have, and there is nothing the
# learner can change about the alif to fix it.
#
# So a heaviness error on one of these is RE-ANCHORED to the consonant it
# lengthens - see pipeline._reanchor_tafkheem - and only refused here if that
# walk found no consonant to move it to.
BORROWS_TAFKHEEM = frozenset("اىوي")

# THE GUARD IS ON WHAT THE REFERENCE CLAIMS, NOT ON THE LETTER ALONE, and
# getting that wrong deletes real detections. Read as: "the reference says this
# letter HAS the property" is only believable for these letters.
#
#     expected moqalqal on ه          impossible - refuse
#     expected not_moqalqal, heard moqalqal on س
#                                     a learner bouncing a letter that does not
#                                     bounce. Real, common, and exactly what
#                                     QALQALAH_ON_WRONG_LETTER is written for.
#
# A letter-only guard refuses both, and the second is a correction worth giving.
CLAIMS_PROPERTY = {
    "qalqla": ("moqalqal", QALQALA_LETTERS),
    "ghonna": ("maghnoon", GHUNNA_LETTERS),
}


def applies(field: str, letter: str, expected: str) -> bool:
    """Whether the reference's claim about this letter is one it can make.

    False means the reference says a letter has a property it cannot have, so
    the disagreement is a measurement artifact and there is no error to report.
    Unknown ṣifāt and unknown letters answer True: this refuses named
    impossibilities, it does not require a letter to be on a list before it may
    be corrected.
    """
    rule = CLAIMS_PROPERTY.get(field)
    if rule is None:
        return True
    value, letters = rule
    return expected != value or letter in letters


def code_for(field: str, letter: str, expected: str, heard: str) -> str | None:
    """The registry code for one ṣifa disagreement.

    Returns:
        a specific code   - the registry has an entry written for exactly this
        GENERIC           - a real disagreement with nothing authored about it
        None              - not an error; do not emit a card at all. Covers three
                            cases: a ṣifa this app does not correct
                            (OUT_OF_SCOPE), a ṣifa this letter cannot have
                            (applies), and a difference of degree between two
                            values that are both acceptable.

    `letter` is the reference base letter, which is what makes RAA_* and
    LAM_TAFKHEEM_WRONG reachable: ر and ل have their own rulings for heaviness
    that contradict the general one, so routing on the ṣifa alone would hand a
    learner the wrong correction.
    """
    # Before everything, including the letter guard: an out-of-scope ṣifa is not
    # a weak error or an unauthored one, it is not an error this app reports.
    if field in OUT_OF_SCOPE:
        return None

    if not applies(field, letter, expected):
        return None

    if field == "tafkheem_or_taqeeq":
        return _tafkheem(letter, expected, heard)

    if field == "ghonna":
        if expected == "maghnoon" and heard == "not_maghnoon":
            return "GHUNNA_MISSING"
        return GENERIC

    if field == "qalqla":
        if expected == "moqalqal" and heard == "not_moqalqal":
            return "QALQALAH_MISSING"
        if expected == "not_moqalqal" and heard == "moqalqal":
            # v5 wrote this for exactly this signal: "qalqla: 'moqalqal'
            # produced on a letter outside ق ط ب ج د".
            return "QALQALAH_ON_WRONG_LETTER"
        return GENERIC

    return GENERIC


def _tafkheem(letter: str, expected: str, heard: str) -> str | None:
    # RULE 5. A madd letter has no heaviness of its own. Reaching here still
    # carrying one means the re-anchor walk found no consonant in front of it -
    # the range opens on the madd - so there is genuinely nothing to correct
    # and no card is emitted. Never "the alif came out heavy".
    if letter in BORROWS_TAFKHEEM:
        return None

    if expected in HEAVY and heard == "moraqaq":
        if letter == RAA:
            return "RAA_TAFKHEEM_MISSING"
        return "TAFKHEEM_LOST"

    if expected == "moraqaq" and heard in HEAVY:
        if letter == RAA:
            return "RAA_TARQIQ_MISSING"
        if letter == LAM:
            # The anticipatory error v5 documents: ل pulled heavy because the
            # mouth is already preparing for the ض in «وَلَا الضَّالِّينَ».
            return "LAM_TAFKHEEM_WRONG"
        return "TAFKHEEM_ADDED"

    # Both sides heavy, differing only in degree. Dropped rather than sent to
    # the generic: there is no correction to give, and a card that says "the
    # ṣifa did not come out right" about a letter the learner read heavily
    # enough is a false positive with a confusing explanation attached.
    return None
