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

── HOW A RUNG IS CHECKED, AND WHY TWO OF THEM CANNOT BE SCORED ─────────────

RULES 7 and 9 ask for record-and-score on every rung, gated so that the next one
unlocks only after an acceptable score. Two of the four can honour that and two
cannot, and the difference is not a matter of effort:

    word, ayah      `check: "score"`
                    The engine builds a target from a WORD RANGE of an ayah,
                    transcribes the recording and diffs. That machinery already
                    exists and already runs - it is the same path the first
                    attempt took.

    letter, syllab  `check: "self"`
                    There is no target. A bare letter is not a word range, the
                    phonetizer works on Quranic text rather than on arbitrary
                    characters, and the model is trained on connected recitation
                    - a 300 ms isolated consonant lands in exactly the huruf
                    muqatta'at collapse that collapse.py exists to catch. A
                    score there would be a number with nothing behind it, handed
                    to a beginner on the first rung they touch, and a wrong
                    "correct!" is worse than no verdict at all.

So the chain is complete but not uniformly automatic: the narrow rungs are
listen, say, and confirm you said it; the wide rungs are recorded and scored. A
`self` rung still gates the next one, so the ladder is climbed in order either
way - what changes is who does the judging, and the client must say which.

RECORDABLE IS A PROMISE, NOT A DECORATION. A control that cannot do what it says
teaches the learner the app lies - the same reason coaching.audio_url() refuses
to send a path for a recording that is not on disk. `recordable` is the server
saying which rungs it can judge; `audio` is the server saying which rungs it can
play. Both are empty rather than optimistic.
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
# U+0640 sits inside that range and is not a letter - see segments._SKIP, where
# it reached a ladder and produced a syllable rung offering «ـَ ـُ ـِ».
_TATWEEL = "ـ"

# How a rung is judged. See the module docstring: this is a wire contract, and
# the client renders a different control for each.
SCORED = "score"
SELF = "self"


def is_letter(value: str) -> bool:
    """One Arabic letter, as opposed to a haraka name, a kashida or nothing."""
    return (len(value) == 1
            and _ARABIC_LETTERS[0] <= value <= _ARABIC_LETTERS[1]
            and value != _TATWEEL)


def ladder(letter: str, word: str, word_index: int, *,
           letter_audio: str = "") -> list[dict]:
    """The rungs for one merged card, narrowest first.

    Rungs that cannot be built are OMITTED rather than emitted empty: a card for
    a ṣifa error with no single letter starts at the word, and a learner should
    see a three-rung ladder rather than two blank rows and a real one.

    `word_index` is ayah-relative, which is what the practice-range API takes,
    so rung 3 can be handed to the recorder untouched.

    `letter_audio` is the isolated recording for this confusion, already checked
    against the filesystem by coaching.audio_url(). Empty means no file, and
    empty is the signal to render no play button - never a dead one.
    """
    rungs: list[dict] = []

    if is_letter(letter):
        rungs.append({
            "level": 1, "focus": "letter", "items": [letter],
            "recordable": False, "check": SELF, "word_index": -1,
            "audio": letter_audio, "audio_source": "letter" if letter_audio
            else "",
        })
        if letter not in MADD_LETTERS:
            rungs.append({
                "level": 2, "focus": "syllables",
                "items": [letter + h for h in HARAKAT],
                "recordable": False, "check": SELF, "word_index": -1,
                # One recording of the bare letter does not cover it under three
                # different vowels, so this rung claims no audio even when the
                # letter above it has some.
                "audio": "", "audio_source": "",
            })

    # -1 means the unit could not be placed in a word. The word can still be
    # SHOWN when we have its text, but it cannot be re-recorded, because
    # start_word would be a guess - and a guess here silently scores the learner
    # against a different word than the one on screen.
    if word:
        recordable = word_index >= 0
        rungs.append({
            "level": 3, "focus": "word", "items": [word],
            "recordable": recordable,
            "check": SCORED if recordable else SELF,
            "word_index": word_index,
            # NO WORD-LEVEL AUDIO EXISTS. everyayah serves one file per whole
            # ayah and carries no word timings, so there is nothing to clip and
            # nothing honest to play. Stated here rather than left to look like
            # an oversight: closing this gap is a recording or an alignment
            # project, not a wiring change.
            "audio": "", "audio_source": "",
        })

    # Always last, always present. The ayah is on screen already, so this rung
    # carries no text of its own - it is the way back to the test, and the point
    # of the whole ladder.
    rungs.append({
        "level": 4, "focus": "ayah", "items": [],
        "recordable": True, "check": SCORED, "word_index": -1,
        # The one rung with real audio today. The URL is the client's to build -
        # it depends on the reciter the learner picked, which the server does
        # not hold - so this names the SOURCE and lets the client resolve it.
        # Slow playback is the same file at a reduced rate, which is genuinely
        # the recording slowed down rather than a second file that does not
        # exist.
        "audio": "", "audio_source": "ayah",
    })

    # Renumbered so the client can print "1 2 3" without gaps. The `focus` is
    # what identifies a rung; `level` is only its position on the ladder, and a
    # ladder that starts at 3 reads as though two rungs failed to load.
    for i, rung in enumerate(rungs, 1):
        rung["level"] = i
    return rungs
