# -*- coding: utf-8 -*-
"""Headline patterns: a small closed set, one per KIND of mistake.

WHAT THIS REPLACES. Every Kind 1 card was going to read "[Rule] qilinmadi",
and for ten of the twenty-four Kind 1 entries that is simply false. A madd held
too LONG was not "not done"; a qalqalah on a letter that carries none was not
"not done" either - it was done, in the wrong place. Forcing one grammatical
frame onto sixty-one different mistakes produces a card that is confidently
wrong about what the learner did, which is worse than a vague one.

Section 5 of the restructure spec names four patterns; a fifth was added for
rule SUBSTITUTION - the learner applied a real ruling, just not the one this
position calls for - which none of the four could say.

THE PATTERN IS AUTHORED, THE RULE NAME IS DETECTED. A pattern is a sentence
frame with one slot in it, and the slot is filled from rule_presence's PLACED
rule. Where nothing is placed, the entry's `headline_no_rule` is used instead
and no rule is named at all. That is the §3/§12 requirement made structural: it
is not possible to render a rule name this module was not handed one for.

RUSSIAN IS NOT A TRANSLATION OF THE UZBEK FRAME. Uzbek builds "«X» qilinmadi"
by suffixing; Russian needs agreement with the rule name's gender, and the rule
names themselves are Uzbek-only in rule_badges.json. So the ru frames are
written separately and the ru rule NAMES come from the v7 `rule_names_ru`
table, which is sourced from authored Russian rather than transliterated. A
rule with no authored Russian name falls back to headline_no_rule, which is why
that field is required on every Kind 1 entry in both languages.
"""

# ── the closed set ────────────────────────────────────────────────────────
MISSING_RULE = "missing_rule"          # the ruling was not applied
TOO_WEAK = "too_weak"                  # applied, but not enough
TOO_STRONG = "too_strong"              # applied, but held too long
EXCESSIVE = "excessive"                # applied, but overdone
WRONG_LOCATION = "wrong_location"      # applied where it does not belong
RULE_SUBSTITUTED = "rule_substituted"  # a different ruling applied instead
MISPRONOUNCED = "mispronounced"        # Kind 2: the sound came out wrong
LETTER_OMITTED = "letter_omitted"      # Kind 2: the sound was not made
LETTER_ADDED = "letter_added"          # Kind 2: a sound was added

#: Patterns whose frame has a {rule} slot. These are the ones that cannot be
#: rendered without a placed rule, and that fall back to `headline_no_rule`.
NEEDS_RULE = frozenset({MISSING_RULE, TOO_WEAK, TOO_STRONG, EXCESSIVE,
                        WRONG_LOCATION, RULE_SUBSTITUTED})

PATTERNS = frozenset({MISSING_RULE, TOO_WEAK, TOO_STRONG, EXCESSIVE,
                      WRONG_LOCATION, RULE_SUBSTITUTED, MISPRONOUNCED,
                      LETTER_OMITTED, LETTER_ADDED})

# ── the frames ────────────────────────────────────────────────────────────
# UI copy, not tajweed: these state what the detector measured, so they live in
# the engine rather than behind the content gate. The RULE NAME they wrap is
# authored content and does come from the registry.
_FRAMES = {
    "uz": {
        MISSING_RULE:     "{rule} qilinmadi",
        TOO_WEAK:         "{rule} yetarli bajarilmadi",
        TOO_STRONG:       "{rule} ortiqcha cho'zildi",
        EXCESSIVE:        "{rule} ortiqcha qo'llandi",
        WRONG_LOCATION:   "{rule} kerak bo'lmagan joyda qilindi",
        RULE_SUBSTITUTED: "{rule} o'rnida boshqa qoida qo'llandi",
        MISPRONOUNCED:    "«{letter}» tovushi noto'g'ri talaffuz qilindi",
        LETTER_OMITTED:   "«{letter}» harfi tushirib qoldirildi",
        LETTER_ADDED:     "«{letter}» tovushi ortiqcha qo'shildi",
    },
    # RUSSIAN AGREES WITH THE RULE NAME'S GENDER, so five of these are three
    # sentences each rather than one. Uzbek suffixes and does not care; Russian
    # does, and "Гунна не выполнено" is the kind of mistake that makes a
    # careful learner stop trusting the rest of the card.
    #
    # THE GENDER IS SOURCED, NOT GUESSED. Every rule in v7's `rule_names`
    # carries one, read off the authored Russian entry it was taken from:
    # «Гунна не выполнена» is feminine, «Идгам не выполнен» masculine, «Ихфа не
    # выполнено» neuter. A qori wrote those agreements; this table only reuses
    # them across the other four patterns.
    "ru": {
        MISSING_RULE: {"m": "{rule} не выполнен",
                       "f": "{rule} не выполнена",
                       "n": "{rule} не выполнено"},
        TOO_WEAK: {"m": "{rule} выполнен недостаточно",
                   "f": "{rule} выполнена недостаточно",
                   "n": "{rule} выполнено недостаточно"},
        TOO_STRONG: {"m": "{rule} растянут сверх меры",
                     "f": "{rule} растянута сверх меры",
                     "n": "{rule} растянуто сверх меры"},
        EXCESSIVE: {"m": "{rule} применён сверх меры",
                    "f": "{rule} применена сверх меры",
                    "n": "{rule} применено сверх меры"},
        WRONG_LOCATION: {"m": "{rule} применён там, где не требуется",
                         "f": "{rule} применена там, где не требуется",
                         "n": "{rule} применено там, где не требуется"},
        # No agreement: the rule sits in a prepositional slot and «правило»
        # governs the participle, so one form serves all three genders.
        RULE_SUBSTITUTED: "Вместо «{rule}» применено другое правило",
        MISPRONOUNCED:    "Звук «{letter}» произнесён неверно",
        LETTER_OMITTED:   "Буква «{letter}» пропущена",
        LETTER_ADDED:     "Добавлен лишний звук «{letter}»",
    },
}

#: Used when a rule name carries no gender. Neuter is the least wrong default
#: in Russian for an indeclinable borrowing, but it IS a default, so
#: coaching.rule_gender() returning "" is worth noticing rather than papering
#: over - a name with no authored gender is a name nobody checked.
_DEFAULT_GENDER = "n"


def frame(pattern: str, lang: str, gender: str = "") -> str:
    """The sentence frame for one pattern, or "" if there is none."""
    got = _FRAMES.get(lang, _FRAMES["uz"]).get(pattern, "")
    if isinstance(got, dict):
        return got.get(gender or _DEFAULT_GENDER, got[_DEFAULT_GENDER])
    return got


def build(pattern: str, lang: str, *, rule_name: str = "", letter: str = "",
          gender: str = "", fallback: str = "") -> str:
    """One headline, or "" when it cannot be built honestly.

    THE FALLBACK IS NOT A DEFAULT, it is the §12 refusal. A rule-shaped pattern
    with no placed rule does not degrade into naming a plausible one; it uses
    the entry's own `headline_no_rule`, which states the mistake WITHOUT
    claiming a ruling ("Cho'zish qisqa qilindi" rather than "Mad lozim
    qilinmadi"). Where even that is missing the card headline is empty and the
    client falls back to the kind title, which is a real name and never a code.
    """
    if pattern not in PATTERNS:
        return fallback
    if pattern in NEEDS_RULE:
        if not rule_name:
            return fallback
        return frame(pattern, lang, gender).format(rule=rule_name)
    if not letter:
        return fallback
    return frame(pattern, lang).format(letter=letter)
