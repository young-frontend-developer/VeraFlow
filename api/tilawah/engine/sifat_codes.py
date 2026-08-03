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

# The ṣifāt this module routes. A disagreement in any OTHER field goes generic.
ROUTED = {"tafkheem_or_taqeeq", "hams_or_jahr", "shidda_or_rakhawa", "ghonna",
          "qalqla"}

RAA, LAM = "ر", "ل"


def code_for(field: str, letter: str, expected: str, heard: str) -> str | None:
    """The registry code for one ṣifa disagreement.

    Returns:
        a specific code   - the registry has an entry written for exactly this
        GENERIC           - a real disagreement with nothing authored about it
        None              - not an error; do not emit a card at all

    `letter` is the reference base letter, which is what makes RAA_* and
    LAM_TAFKHEEM_WRONG reachable: ر and ل have their own rulings for heaviness
    that contradict the general one, so routing on the ṣifa alone would hand a
    learner the wrong correction.
    """
    if field == "tafkheem_or_taqeeq":
        return _tafkheem(letter, expected, heard)

    if field == "hams_or_jahr":
        if expected == "hams" and heard == "jahr":
            return "HAMS_LOST"
        if expected == "jahr" and heard == "hams":
            return "JAHR_LOST"
        return GENERIC

    if field == "shidda_or_rakhawa":
        # 'between' is included on the authority of the registry entry itself,
        # whose detection_signal reads "kutilgan 'shadeed' o'rniga 'rikhw' yoki
        # 'between'". A shadeed letter that came out even partly loose is the
        # error SHIDDA_LOST is written about.
        if expected == "shadeed" and heard in ("rikhw", "between"):
            return "SHIDDA_LOST"
        # The opposite direction - a loose letter read tight - has no entry in
        # any registry generation, so it stays generic rather than borrowing
        # SHIDDA_LOST's text, which would tell the learner to do MORE of what
        # they already overdid.
        return GENERIC

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
