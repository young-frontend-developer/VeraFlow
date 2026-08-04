# -*- coding: utf-8 -*-
"""The practice ladder: one letter, then that letter, then the real thing.

WHAT THIS REPLACES. Practice used to be two things, and neither was practice.
The registry's `drill` field is prose describing an exercise - "say ذَ ten times
in front of a mirror, then read 'ذَلِكَ', 'الَّذِي', 'إِذَا'" - which is homework
written down, not something a learner does in the app. And the only button on
the card re-recorded the whole word or the whole ayah, so a learner who dropped
one ح had to perform the entire verse again to find out whether they had fixed
it. Reciting the ayah is the TEST. It is a poor way to learn the letter you just
got wrong.

THE LADDER. Four rungs, narrow to wide, so the learner meets the sound alone
before meeting it inside anything:

    1  the letter, bare                      ذ
    2  the letter under each haraka          ذَ  ذُ  ذِ
    3  the word they actually misread        ذَٰلِكَ
    4  the ayah, which is where they started

NOTHING HERE IS AUTHORED, and that is the constraint the design is built
around. Decision 4 says every learner-facing sentence about tajweed comes from a
qori, so a ladder that needed a hand-picked example word per letter would need
60 entries written before it could ship, and would ship generic until then.
Every rung is DERIVED instead:

    rung 1  the letter is already on the card
    rung 2  fatha/damma/kasra on a letter is Arabic orthography, not a ruling
    rung 3  the word comes from the learner's own ayah - the one they misread,
            which beats any example a registry could name, because it is the
            word they are about to be tested on
    rung 4  the ayah is already on screen

So the ladder is complete for every code on day one, including codes nobody has
written a word of coaching for.

RECORDABLE IS A PROMISE, NOT A DECORATION. The engine scores audio against a
target built from a WORD RANGE of an ayah; it has no target for a bare letter,
so rungs 1-2 cannot be checked and must not offer a record button. A control
that cannot do what it says teaches the learner the app lies - the same reason
coaching.audio_url() refuses to send a path for a recording that is not on
disk. Rungs 1-2 are listen-and-say. Rungs 3-4 carry the range the recorder
needs, and are the two the recovery loop already knows how to submit.
"""

# fatha, damma, kasra. Every letter takes all three, which is what makes rung 2
# derivable rather than authored.
HARAKAT = ("َ", "ُ", "ِ")

# The madd letters. A haraka on one of these is not a syllable a learner should
# be shown practising: ا و ي carry the lengthening BECAUSE they are unvowelled,
# and "اَ" asks for a sound the letter does not make in that role. Rung 2 is
# skipped for them and the ladder goes straight from the letter to the word.
# This is orthography, not a ruling - no qori has to sign it off.
MADD_LETTERS = frozenset("اوي")  # ا و ي

# The Arabic letter block. `letter` reaches here from the phoneme layer and is
# normally one Arabic character, but the detectors do not all agree on that:
# a haraka error reports a NAME ("fatha"), and a ṣifa error can report nothing
# at all. Rungs 1-2 are built only when there is genuinely one letter to build
# them from - the same single-character test the card uses before it puts a
# value inside an Arabic-script chip.
_ARABIC_LETTERS = ("ء", "ي")  # ء .. ي


def is_letter(value: str) -> bool:
    """One Arabic letter, as opposed to a haraka name or an empty field."""
    return len(value) == 1 and _ARABIC_LETTERS[0] <= value <= _ARABIC_LETTERS[1]


def ladder(letter: str, word: str, word_index: int) -> list[dict]:
    """The rungs for one merged card, narrowest first.

    Rungs that cannot be built are OMITTED rather than emitted empty: a card for
    a ṣifa error with no single letter starts at the word, and a learner should
    see a three-rung ladder rather than two blank rows and a real one.

    `word_index` is ayah-relative, which is what the practice-range API takes,
    so rung 3 can be handed to the recorder untouched.
    """
    rungs: list[dict] = []

    if is_letter(letter):
        rungs.append({
            "level": 1, "focus": "letter", "items": [letter],
            "recordable": False, "word_index": -1,
        })
        if letter not in MADD_LETTERS:
            rungs.append({
                "level": 2, "focus": "syllables",
                "items": [letter + h for h in HARAKAT],
                "recordable": False, "word_index": -1,
            })

    # -1 means the unit could not be placed in a word. The word can still be
    # SHOWN when we have its text, but it cannot be re-recorded, because
    # start_word would be a guess - and a guess here silently scores the learner
    # against a different word than the one on screen.
    if word:
        rungs.append({
            "level": 3, "focus": "word", "items": [word],
            "recordable": word_index >= 0, "word_index": word_index,
        })

    # Always last, always present. The ayah is on screen already, so this rung
    # carries no text of its own - it is the way back to the test, and the point
    # of the whole ladder.
    rungs.append({
        "level": 4, "focus": "ayah", "items": [],
        "recordable": True, "word_index": -1,
    })

    # Renumbered so the client can print "1 2 3" without gaps. The `focus` is
    # what identifies a rung; `level` is only its position on the ladder, and a
    # ladder that starts at 3 reads as though two rungs failed to load.
    for i, rung in enumerate(rungs, 1):
        rung["level"] = i
    return rungs
