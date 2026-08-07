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

THERE IS NO SINGLE LADDER. There are four, and which one a card gets is decided
by WHAT KIND OF MISTAKE IT IS. That is the whole design, and it replaced a
genuine bug: every card, of every type, opened with "the letter, bare" - and for
three of the four categories that first rung teaches nothing.

    ARTICULATION - the sound itself came out wrong
    MAKHARIJ_*, HARAKA_SUBSTITUTED, TAFKHEEM_*, QALQALAH_*,
    GENERIC_LETTER_SUBSTITUTED, GENERIC_SIFAT_MISMATCH

        1  the letter, bare                  ذ
        2  the letter under each haraka      ذَ  ذُ  ذِ
        3  the word they actually misread    ذَٰلِكَ
        4  the ayah, which is where they started

    This is the ladder the isolated-letter rung was designed for and the only
    one it belongs on. The learner's mouth is making the wrong shape, so meeting
    the sound alone - away from the timing, the vowel and the neighbours - is
    exactly the right first step.

    OMISSION - LETTER_DROPPED

        1  the word, slowly, sounding the letter that went missing
        2  the word at normal pace
        3  the ayah

    THE LETTER WAS NEVER MISPRONOUNCED. It was not said at all. A learner who
    can produce ح perfectly in isolation - and most can - learns nothing from
    being asked to produce it again; what they failed to do was REMEMBER IT
    while reading a word. So the drill has to be the word, because the word is
    where the forgetting happens.

    INSERTION - LETTER_ADDED

        1  the word, slowly, without the extra sound
        2  the word at normal pace
        3  the ayah

    The same reasoning inverted. The fix is learning NOT to insert something,
    and there is no such thing as practising the absence of a sound in
    isolation. Only the word can hold the contrast.

    DURATION - the MADD_* family

        1  the word, holding the letter for the correct count
        2  the word at normal pace
        3  the ayah

    A BARE LETTER HAS NO DURATION. Length is not a property of ا - it is a
    property of ا held inside a word, measured in harakat against what the
    ruling calls for. "Say ا on its own" asks the learner to practise the one
    dimension of the error that cannot exist outside the word. Rung 1 carries
    `hold`, the target count, so the client can drive the counter it already has
    (see web/src/components/DurationMeter.tsx) instead of printing a number the
    learner has no reference for.

NOTHING HERE IS AUTHORED, and that is the constraint the design is built
around. Decision 4 says every learner-facing sentence about tajweed comes from a
qori, so a ladder that needed a hand-picked example word per letter would need
60 entries written before it could ship, and would ship generic until then.
Every rung is DERIVED instead:

    the letter      already on the card
    the syllables   fatha/damma/kasra on a letter is Arabic orthography, not a
                    ruling
    the word        from the learner's own ayah - the one they misread, which
                    beats any example a registry could name, because it is the
                    word they are about to be tested on
    the count       the reference's own expected_count, already on the error
    the ayah        already on screen

So every ladder is complete for every code on day one, including codes nobody
has written a word of coaching for. The BRANCH is on the code, and the code is
already on the error - no new authoring, no new lookup.

⚠️ GHUNNA_* AND SHADDA_* DURATION ERRORS STILL GET THE ARTICULATION LADDER, and
by the argument above they should not: a ghunnah held too short is a duration
error, and ن alone has no duration either. They are left alone deliberately,
because the scope handed down named the madd family and only the madd family,
and quietly widening a correction is how a ladder nobody asked for ships. This
is the note that makes the gap visible rather than accidental.

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

# ── which ladder a code gets ──────────────────────────────────────────────
# Membership, not prefixes, for the two structural categories: QALQALA_DROP is
# a dropped qalqalah and would match a "dropped" prefix rule, but its fix IS an
# articulation - the bounce - so it belongs on the articulation ladder. Naming
# the two codes outright makes that impossible to get wrong by accident.
OMISSION = frozenset({"LETTER_DROPPED"})
INSERTION = frozenset({"LETTER_ADDED"})

# The madd family, by prefix, because it spans two vocabularies that both reach
# here: the engine emits MADD_SHORT / MADD_LONG, and the registry names
# MADD_TOO_SHORT, MADD_TOO_LONG, MADD_WAJIB_SHORTENED, MADD_ADDED_LEEN and
# MADD_ADDED. A membership set would have to list both and would silently miss
# whichever generation was added next.
_MADD_PREFIX = "MADD_"

# The opening rungs, one per category. `word` and `ayah` are shared by all four
# ladders and are appended after.
LETTER, SYLLABLES = "letter", "syllables"
WORD, AYAH = "word", "ayah"
# The three slow, deliberate first passes at the word. Separate focus values
# rather than one "word_slow" plus a modifier, because the client prints a
# different instruction for each and they are genuinely different acts: sound
# the letter you skipped / leave out the sound you added / hold for the count.
WORD_INCLUDE = "word_include"
WORD_OMIT = "word_omit"
WORD_HOLD = "word_hold"

WORD_FOCUSES = frozenset({WORD, WORD_INCLUDE, WORD_OMIT, WORD_HOLD})


def category(code: str) -> str:
    """Which ladder this code gets: 'omission', 'insertion', 'madd' or
    'articulation'.

    ARTICULATION IS THE DEFAULT, and deliberately so. It is the shape every card
    had before this branch existed, so a code nobody has classified keeps
    exactly the ladder it has always had rather than silently losing rungs. The
    three named categories are the ones where that default was measured wrong.
    """
    if code in OMISSION:
        return "omission"
    if code in INSERTION:
        return "insertion"
    if code.startswith(_MADD_PREFIX):
        return "madd"
    return "articulation"


def is_letter(value: str) -> bool:
    """One Arabic letter, as opposed to a haraka name, a kashida or nothing."""
    return (len(value) == 1
            and _ARABIC_LETTERS[0] <= value <= _ARABIC_LETTERS[1]
            and value != _TATWEEL)


def _rung(focus: str, items: list[str], *, recordable: bool, check: str,
          word_index: int = -1, audio: str = "", audio_source: str = "",
          hold: int = 0) -> dict:
    """One rung, with every wire key present.

    Built through one constructor so no branch can invent a rung missing a key
    the client indexes directly - the same contract cards.WIRE_KEYS enforces one
    level up.
    """
    return {"level": 0, "focus": focus, "items": items,
            "recordable": recordable, "check": check, "word_index": word_index,
            "audio": audio, "audio_source": audio_source, "hold": hold}


def _word_rung(focus: str, word: str, word_index: int, *,
               hold: int = 0) -> dict:
    """A rung whose item is the word itself.

    word_index -1 means the unit could not be placed in a word. The word can
    still be SHOWN when we have its text, but it cannot be re-recorded, because
    start_word would be a guess - and a guess here silently scores the learner
    against a different word than the one on screen.

    NO WORD-LEVEL AUDIO EXISTS on any of these. everyayah serves one file per
    whole ayah and carries no word timings, so there is nothing to clip and
    nothing honest to play. Stated here rather than left to look like an
    oversight: closing this gap is a recording or an alignment project, not a
    wiring change.
    """
    recordable = word_index >= 0
    return _rung(focus, [word], recordable=recordable,
                 check=SCORED if recordable else SELF,
                 word_index=word_index, hold=hold)


def _articulation_opening(letter: str, letter_audio: str) -> list[dict]:
    """The bare letter, then the letter under each haraka.

    THE ONLY LADDER THESE TWO RUNGS BELONG ON. See the module docstring: for an
    omission, an insertion or a duration error the physical sound was not the
    problem, and drilling it in isolation practises the one thing the learner
    already did correctly.
    """
    if not is_letter(letter):
        return []
    rungs = [_rung(LETTER, [letter], recordable=False, check=SELF,
                   audio=letter_audio,
                   audio_source="letter" if letter_audio else "")]
    if letter not in MADD_LETTERS:
        # One recording of the bare letter does not cover it under three
        # different vowels, so this rung claims no audio even when the letter
        # above it has some.
        rungs.append(_rung(SYLLABLES, [letter + h for h in HARAKAT],
                           recordable=False, check=SELF))
    return rungs


def ladder(letter: str, word: str, word_index: int, *, code: str = "",
           expected_count: int = 0, letter_audio: str = "") -> list[dict]:
    """The rungs for one merged card, narrowest first.

    `code` PICKS THE LADDER - see category() and the module docstring. It
    defaults to "" so a caller that has no code still gets a working ladder, and
    "" classifies as articulation, which is the shape every card had before the
    branch existed.

    Rungs that cannot be built are OMITTED rather than emitted empty: a card for
    a ṣifa error with no single letter starts at the word, and a learner should
    see a three-rung ladder rather than two blank rows and a real one.

    `word_index` is ayah-relative, which is what the practice-range API takes,
    so a word rung can be handed to the recorder untouched.

    `expected_count` is the harakat the reference calls for. It drives the
    counter on the madd ladder's first rung, and where it is missing that rung
    is dropped rather than shown with a made-up number - the ladder never states
    a count the reference did not supply.

    `letter_audio` is the isolated recording for this confusion, already checked
    against the filesystem by coaching.audio_url(). Empty means no file, and
    empty is the signal to render no play button - never a dead one.
    """
    kind = category(code)
    rungs: list[dict] = []

    if kind == "articulation":
        rungs += _articulation_opening(letter, letter_audio)
    elif word:
        # All three non-articulation ladders open on the word, slowly, with the
        # thing to attend to named by the focus. No opening rung at all when
        # there is no word text: the act being practised is "say this word a
        # particular way", and without the word there is nothing to say.
        if kind == "omission":
            rungs.append(_word_rung(WORD_INCLUDE, word, word_index))
        elif kind == "insertion":
            rungs.append(_word_rung(WORD_OMIT, word, word_index))
        elif kind == "madd" and expected_count > 0:
            rungs.append(_word_rung(WORD_HOLD, word, word_index,
                                    hold=expected_count))

    if word:
        rungs.append(_word_rung(WORD, word, word_index))

    # Always last, always present. The ayah is on screen already, so this rung
    # carries no text of its own - it is the way back to the test, and the point
    # of the whole ladder.
    #
    # The one rung with real audio today. The URL is the client's to build - it
    # depends on the reciter the learner picked, which the server does not hold
    # - so this names the SOURCE and lets the client resolve it. Slow playback
    # is the same file at a reduced rate, which is genuinely the recording
    # slowed down rather than a second file that does not exist.
    rungs.append(_rung(AYAH, [], recordable=True, check=SCORED,
                       audio_source="ayah"))

    # Renumbered so the client can print "1 2 3" without gaps. The `focus` is
    # what identifies a rung; `level` is only its position on the ladder, and a
    # ladder that starts at 3 reads as though two rungs failed to load.
    for i, rung in enumerate(rungs, 1):
        rung["level"] = i
    return rungs
