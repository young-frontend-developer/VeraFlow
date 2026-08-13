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
    """The ONE thing this card asks the learner to record: the affected word.

    ── WHAT THIS REPLACED, AND WHY THE LADDER HAD TO GO ────────────────────

    There used to be four rungs - letter, letter+harakat, word, ayah - and the
    last of them was the defect. `AYAH` was appended to EVERY card, so a
    recitation with ten corrections asked for the whole ayah ten times, once
    per card, and asked for it again after mistake ten even though mistakes one
    through nine had each already ended in a full re-read. A learner who fixed
    card 2 last still had to perform the entire verse for it, having already
    performed the entire verse for card 8.

    Reciting the ayah is the TEST. Running the test after every single
    correction is not practice, it is nine redundant examinations, and it is
    the reason the loop felt endless rather than finishable.

    So the ayah is no longer a rung at all. It is requested ONCE, by the
    results screen, after every card has been addressed - see
    web/src/components/Feedback.tsx, which gates it on there being no open
    cards left. That gate is order-independent by construction: it is derived
    from the set of resolved cards, not from a counter, so a learner who fixes
    card 2 after card 8 still gets exactly one final recitation, at the end.

    The two NARROW rungs are gone for a different reason, given in full in the
    module docstring above: a bare letter and a letter under three harakat are
    not the mistake for three of the four categories, and even for articulation
    they could not be scored - `check: "self"` meant the learner graded
    themselves on the first thing they touched. One recordable, scorable act
    beats three, two of which the engine could not judge.

    `letter_audio` IS STILL ACCEPTED AND NO LONGER USED. The isolated-letter
    recordings stay on disk and stay in the registry: they are the right raw
    material for an alphabet reference, which is a feature someone may build.
    They are simply not wired into this flow any more. The parameter is kept so
    that every existing caller - including cards.ensure_shape() replaying rows
    written years ago - keeps working untouched.

    ── WHAT SURVIVES ───────────────────────────────────────────────────────

    The FOCUS still branches on the code, because the instruction differs and
    the difference is real: sound the letter you skipped / leave out the sound
    you added / hold for the count / say it as written. That is one action
    described four ways, not four actions.

    Returns [] when there is no word to record - a ṣifa error the engine could
    not place in one. An empty ladder renders no recorder, which is correct:
    there is nothing honest to record against.
    """
    kind = category(code)

    if not word:
        return []

    if kind == "omission":
        rung = _word_rung(WORD_INCLUDE, word, word_index)
    elif kind == "insertion":
        rung = _word_rung(WORD_OMIT, word, word_index)
    elif kind == "madd" and expected_count > 0:
        rung = _word_rung(WORD_HOLD, word, word_index, hold=expected_count)
    else:
        rung = _word_rung(WORD, word, word_index)

    rung["level"] = 1
    return [rung]
