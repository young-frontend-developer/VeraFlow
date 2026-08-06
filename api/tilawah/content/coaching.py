# -*- coding: utf-8 -*-
"""Coaching text: headline / fix / rule / drill, with templates filled in.

WHERE IT COMES FROM
-------------------
Three hand-authored registries at the repo root, merged in order:

    tajweed_error_registry_v3.json      39 entries - the makharij, madd, ghunna
                                        and ṣifāt corrections. Authored in an
                                        EARLIER SHAPE (name/short/nima_xato/
                                        qoida/nega_muhim/tuzatish/mashq), which
                                        _adapt_v3 maps onto the four fields
                                        below. No sentence is rewritten; the
                                        keys are renamed and two pairs joined.
    tajweed_registry_v4_coaching.json   rewrites the uz/ru text of EXISTING
                                        entries (structure, source_ref,
                                        detection signals and status unchanged)
    tajweed_registry_v5_gaps.json       22 NEW entries, including the generic
                                        fallbacks and the harakat category

v3 WAS NEVER LOADED. This module read v4 and v5 only, and v4 does not exist, so
39 authored entries - every specific makharij and ṣifa correction in the
project - sat on disk unreachable while the pipeline showed generic fallbacks in
their place. That is half the reason "almost everything falls through to
generic"; the other half is ALIAS below.

⚠️ v4 IS STILL NOT IN THE REPO. It is loaded if the file exists and skipped if
it does not. Because v3 now supplies the base text, its absence no longer leaves
those codes unauthored - it only means they render v3's wording rather than v4's
rewrite. See `missing_sources()`, which the API surfaces so this stays visible.

ENGINE CODES vs REGISTRY CODES
------------------------------
The two vocabularies were never the same. The engine emits MADD_SHORT; the
registry entry is MADD_TOO_SHORT. Nothing translated between them, so the lookup
missed and the learner got a fallback card. ALIAS is that translation, stated
once, in one direction, and covered by a test that fails on any engine code with
neither an entry nor an alias.

TEMPLATES
---------
Headlines are templates: {word}, {letter}, {expected}, {actual}, {n_expected},
{n_actual}, substituted from the detection result at render time.

A rendered string that still contains a brace is a BUG, not a cosmetic problem
- it means the detector did not supply a field the author relied on, and the
learner would be shown "«{word}» — «{expected}» oʻrniga...". `render()` raises
rather than letting that reach a screen. The old code did the opposite: it
caught the KeyError and returned the raw template, braces and all.

NOTHING HERE AUTHORS ANYTHING. Every sentence is copied from the registries;
this module only selects, substitutes and validates.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
V3 = _ROOT / "tajweed_error_registry_v3.json"
V4 = _ROOT / "tajweed_registry_v4_coaching.json"
V5 = _ROOT / "tajweed_registry_v5_gaps.json"
# v6 closes the four codes the engine could always emit and nobody had written
# words for - SHADDA_SHORT, SHADDA_LONG, GHUNNA_LONG, SUB_HA_HEH. Each rendered
# the unauthored stand-in: a located card with nothing to say.
V6 = _ROOT / "tajweed_registry_v6_gaps.json"

# What the REGISTRIES author. All four are still parsed, still validated, and
# still available to the review tool, which reads the registry directly.
FIELDS = ("headline", "fix", "rule", "drill")

# What a LEARNER is shown. The card answers four questions - what happened,
# where, how do I fix it, what do I practise - and `rule` and `drill` answer
# none of them.
#
# `rule` is the ruling and why it matters: 13-44 words of tajweed theory
# carrying the terms a beginner does not have (lahn jaliy, iqlab, sofiyr, mad
# muttasil). It was rendered behind a "Why" disclosure, which is exactly the
# encyclopedia this app is not.
#
# `drill` is prose describing an exercise - "say ذَ ten times in front of a
# mirror, then 'ذَلِكَ', 'الَّذِي', 'إِذَا'". That is a written homework assignment,
# not practice. It is replaced by engine/practice.py, which builds the same
# progression as something the learner can tap through and record against.
#
# Neither is deleted from the registries. They are simply not part of the card.
CARD_FIELDS = ("headline", "fix")

# Any {placeholder} left after substitution.
_BRACE = re.compile(r"\{[^}]*\}")


class UnfilledTemplate(RuntimeError):
    """A coaching string still had a placeholder after substitution."""


# ── engine code -> registry code ──────────────────────────────────────────
# The engine names an error for what the DETECTOR measured (a run came out
# short); the registry names it for what the TEACHER corrects (the madd was
# shortened). Both vocabularies are legitimate and neither is going away, so
# they are joined here rather than by renaming one side and breaking either the
# detector's tests or the authored content's identity.
#
# Only genuine synonyms belong here. If an engine code has no registry entry,
# the answer is to AUTHOR one - not to point it at the nearest-looking entry,
# which hands the learner a correction for an error they did not make.
# test_code_mapping.py fails on anything unmapped, by design.
ALIAS = {
    # duration - _duration_code() in typed_errors.py
    "MADD_SHORT":     "MADD_TOO_SHORT",
    "MADD_LONG":      "MADD_TOO_LONG",
    "GHUNNA_SHORT":   "GHUNNA_TOO_SHORT",
    # qalqalah - _missing() emits the mark, the registry names the rule
    "QALQALA_DROP":   "QALQALAH_MISSING",
    # L1 interference pairs - L1_PAIRS in typed_errors.py. Each is the same
    # confusion the makharij entry is written about, named for the language
    # prior that predicts it.
    "SUB_AYN_HAMZA":  "MAKHARIJ_AIN_TO_HAMZA",     # ع -> ء
    "SUB_HA_KHA":     "MAKHARIJ_HHA_TO_KHA",       # ح -> خ
    "SUB_SAD_SEEN":   "MAKHARIJ_SAD_TO_SEEN",      # ص -> س
    "SUB_TA_PLAIN":   "MAKHARIJ_TAA_TO_TA",        # ط -> ت
    "SUB_DAD_DAL":    "MAKHARIJ_DAD_TO_DAL",       # ض -> د
    "SUB_DHA_ZAY":    "MAKHARIJ_INTERDENTAL_TO_ZAY",   # ظ -> ز, named in-signal
    "SUB_DHAL_ZAY":   "MAKHARIJ_INTERDENTAL_TO_ZAY",   # ذ -> ز, same entry
    "SUB_QAF_KAF":    "MAKHARIJ_QAF_TO_KAF",       # ق -> ك
    "SUB_THA_SEEN":   "MAKHARIJ_THA_TO_SEEN",      # ث -> س
    "SUB_WAW_V":      "MAKHARIJ_WAW_TO_FA",        # و -> ف
}


def resolve(code: str) -> str:
    """Engine code -> the code the registry files are keyed by."""
    return ALIAS.get(code, code)


# ── v3's field names -> the four this module renders ──────────────────────
# v3 was authored before the headline/fix/rule/drill shape existed. Its uz and
# ru blocks carry the same material under different keys, so the adapter is a
# rename plus two joins - it writes nothing.
_V3_KEYS = {
    "uz": {"short": "short", "what": "nima_xato", "rule": "qoida",
           "why": "nega_muhim", "fix": "tuzatish", "drill": "mashq"},
    "ru": {"short": "short", "what": "chto_ne_tak", "rule": "pravilo",
           "why": "pochemu_vazhno", "fix": "kak_ispravit",
           "drill": "uprazhnenie"},
}


def _join(*parts: str) -> str:
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def _adapt_v3(spec: dict) -> dict:
    """One v3 entry in the four-field shape. Selection only - no text is written.

    THE CARD HAS A WORD BUDGET, so the mapping is a selection and not a
    concatenation of everything available:

        headline <- short      one sentence: what happened
        fix      <- tuzatish   ONE actionable instruction
        rule     <- qoida + nega_muhim    the ruling, then why it matters
        drill    <- mashq      the exercise

    `nima_xato` ("what went wrong") is deliberately NOT carried. It is a longer
    restatement of `short`, which already occupies the what-happened slot, and
    joining the two put two versions of the same sentence at the top of every
    card. Nothing is lost that the learner needs; the reviewer still sees the
    full entry in the review tool, which reads the registry directly.

    Only `rule` joins two fields, and it is collapsed behind a tap - the ruling
    and its reason are exactly the part worth having and not worth re-reading.
    """
    out = {k: v for k, v in spec.items() if k not in ("uz", "ru")}
    for lang, keys in _V3_KEYS.items():
        block = spec.get(lang)
        if not block:
            continue
        out[lang] = {
            "headline": block.get(keys["short"], ""),
            "fix": block.get(keys["fix"], ""),
            "rule": _join(block.get(keys["rule"], ""), block.get(keys["why"], "")),
            "drill": block.get(keys["drill"], ""),
            "name": block.get("name", ""),
        }
    return out


def _load(path: Path, *, adapt=None) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    # v5 calls the map `entries`; v3 calls it `errors`. One loader serves both,
    # and a differently-shaped v4 needs no third.
    entries = data.get("entries") or data.get("errors") or {}
    # An entry the registry itself marks NEEDS_AUTHORING is a placeholder: the
    # code exists, the words do not. MADD_ADDED_LEEN carries empty uz and ru
    # blocks, so loading it would render four empty strings - a card that looks
    # authored and says nothing, which is worse than the honest "no content"
    # path. Decision 4: the split created the code, a qori must create the
    # words. Dropping it here is what keeps render() returning None.
    entries = {code: spec for code, spec in entries.items()
               if spec.get("content_status") != "NEEDS_AUTHORING"}
    if adapt:
        return {code: adapt(spec) for code, spec in entries.items()}
    return entries


@lru_cache(maxsize=1)
def registry() -> dict:
    """code -> entry, v5 over v4 over v3.

    Later generations win on a collision: each was authored to improve on the
    one before it. v3 supplies breadth (39 specific corrections), v4 rewrites
    their wording, v5 adds the categories all of them missed.
    """
    merged = _load(V3, adapt=_adapt_v3)
    merged.update(_load(V4))
    merged.update(_load(V5))
    merged.update(_load(V6))
    return merged


def missing_sources() -> list[str]:
    """Registry files this module expects but cannot find."""
    return [p.name for p in (V3, V4, V5, V6) if not p.exists()]


def has(code: str) -> bool:
    return resolve(code) in registry()


def entry(code: str) -> dict | None:
    return registry().get(resolve(code))


# One Arabic letter either side of -> (one direction) or <-> (both). Anchored
# on the letters themselves rather than on \S+, which is what previously
# swallowed the trailing comma in "ص -> س, odatda ..." and produced a two-
# character "letter" that no lookup could ever match.
_ARABIC = r"[ء-ي]"
_PAIR = re.compile(rf"({_ARABIC})\s*(<->|->)\s*({_ARABIC})")


@lru_cache(maxsize=1)
def substitution_pairs() -> dict[tuple[str, str], str]:
    """(expected, heard) -> specific code, parsed from `detection_signal`.

    Read out of the registry rather than out of the code NAMES. A name like
    MAKHARIJ_AIN_TO_GHAYN looks parseable right up until MAKHARIJ_INTERDENTAL_
    TO_ZAY, where the source letter is a category and not a letter at all. The
    signal states the pair explicitly:

        "phoneme substitution: ع -> غ"

    so that is what is trusted.

    THREE SHAPES THE OLD PARSER MISSED, each of which silently cost every entry
    written in it:

      "ص -> س, odatda tafkheem_or_taqeeq: ..."   trailing punctuation
      "ب <-> م"                                  bidirectional, no plain ->
      "ذ -> ز yoki ظ -> ز"                       two pairs in one signal

    Between them that is most of the makharij registry - MAKHARIJ_BA_TO_MEEM,
    _JEEM_TO_YA, _LAM_TO_RAA, _NUN_TO_LAM, _SEEN_TO_SHEEN, _TA_TO_DAL,
    _ZAY_TO_SEEN and _WAW_TO_FA registered no pair at all, so every one of those
    confusions was reported as GENERIC_LETTER_SUBSTITUTED with an entry sitting
    right there. All matches in a signal are taken now, and <-> registers both
    directions.

    An entry whose signal contains no letter pair is still left out and still
    falls through to GENERIC_LETTER_SUBSTITUTED - that is the point of having a
    generic. First writer wins, so a later generation cannot quietly steal a
    pair an earlier, more specific entry already claimed.
    """
    out: dict[tuple[str, str], str] = {}
    for code, spec in registry().items():
        signal = str(spec.get("detection_signal", ""))
        if "substitution" not in signal:
            continue
        for src, arrow, dst in _PAIR.findall(signal):
            out.setdefault((src, dst), code)
            if arrow == "<->":
                out.setdefault((dst, src), code)
    return out


# Where the isolated letter recordings live. Served at /audio by the app, so a
# registry value of "audio/sad_zay.mp3" becomes the URL "/audio/sad_zay.mp3".
AUDIO_DIR = Path(__file__).parent / "audio"


def audio_url(rel: str) -> str:
    """A playable URL for a registry `audio_pair`, or "" if there is no file.

    THE EXISTENCE CHECK IS THE POINT. 13 entries name a recording; none of the
    files exist yet. Sending the path regardless would put a play button on
    every one of those cards that fails silently when tapped - a dead control,
    which is worse than no control because it teaches the learner that the app
    lies. So presence on disk, not presence in the registry, decides.

    Files land in content/audio/ and light their buttons up with no code change.
    """
    if not rel:
        return ""
    name = rel.split("/")[-1]
    # Registry values are authored, but they end up in a filesystem path and
    # then in a URL, so a stray "../" must not be able to reach outside the
    # audio directory or point the client somewhere else.
    if not name or name != Path(name).name:
        return ""
    if not (AUDIO_DIR / name).is_file():
        return ""
    return f"/audio/{name}"


def missing_audio() -> list[str]:
    """Registry entries naming a recording that is not on disk.

    Surfaced rather than logged once, for the same reason as missing_sources():
    a gap nobody can see becomes permanent.
    """
    out = []
    for code, spec in registry().items():
        rel = spec.get("audio_pair", "")
        if rel and not audio_url(rel):
            out.append(f"{code}: {rel}")
    return sorted(out)


def _fill(text: str, fields: dict, *, code: str, key: str) -> str:
    """Substitute placeholders, then refuse to return braces.

    format_map with a plain dict raises KeyError on an unknown placeholder;
    that is deliberate. The check afterwards catches the other direction - a
    field supplied as an empty string, or a stray brace in the source text -
    which format() would pass through silently.
    """
    if not text:
        return ""
    try:
        out = text.format_map(fields)
    except (KeyError, IndexError) as exc:
        raise UnfilledTemplate(
            f"{code}.{key}: no value for {exc} — the detector must supply "
            f"every placeholder the author used. Template: {text[:120]!r}"
        ) from exc
    except ValueError as exc:
        # A malformed placeholder - "{not closed", "{}" - is an authoring typo.
        # It has to surface as UnfilledTemplate like every other template
        # failure, or it escapes the pipeline's handler as a bare 500 and takes
        # the whole attempt down with it.
        raise UnfilledTemplate(
            f"{code}.{key}: malformed template ({exc}). Template: {text[:120]!r}"
        ) from exc
    leftover = _BRACE.search(out)
    if leftover:
        raise UnfilledTemplate(
            f"{code}.{key}: {leftover.group(0)!r} survived substitution. "
            f"A learner must never be shown a brace. Result: {out[:120]!r}")
    return out


def instruction(text: str) -> str:
    """The ONE actionable instruction out of an authored `fix`, by selection.

    THE AUTHORS ALREADY SEPARATED IT. Every multi-part `fix` in the registries
    is written as paragraphs split by a blank line, and the first paragraph is
    the correction while everything after it is commentary about the
    correction. 22 of the 60 entries are shaped that way, and what sits in the
    second paragraph is consistently one of three things:

        the meta-apology   "Bu xato uchun to'liq izoh hali tayyorlanmagan.
                            Ustozingiz bilan tekshiring."
        the aetiology      "Ko'pincha bu ohang uchun yuz beradi."
        the restatement    a longer version of the headline

    The first of those is the worst: GENERIC_LETTER_SUBSTITUTED and
    GENERIC_SIFAT_MISMATCH are the two codes that fire most often, and both put
    "we haven't written this yet, ask your teacher" INSIDE the slot the learner
    reads for the answer. That is a fallback message on the single most-seen
    card in the app, and taking the first paragraph is what removes it - not a
    keyword filter, which would go stale the moment someone rephrased it.

    MEASURED, NOT ASSUMED. Across all 60 entries in both languages, headline +
    first paragraph runs 45 words at worst (MAKHARIJ_AIN_TO_HAMZA) and under 35
    for 56 of them, against a 60-word card budget. Three entries carry a
    genuinely long single instruction; those are an authoring question for a
    qori, not something to truncate mechanically mid-sentence.

    Sentence-level selection was tried first and rejected. It looked tighter
    until you check it against the text: about a dozen entries open on a
    diagnosis and put the instruction second ("Maxraj bir xil — til uchi
    tishlar ildizida. Farq ovozda."), so "take sentence one" would have shown a
    description where the correction belongs, and "take sentence two" would
    have broken the other forty. The paragraph break is the split the authors
    actually made; the sentence break is one we would be inventing.

    NOTHING IS REWRITTEN HERE. This selects among sentences a qori wrote, which
    is the same thing _adapt_v3 does one layer up. Authoring stays with the
    authors.
    """
    return text.split("\n\n")[0].strip()


# ── entries whose instruction is built around ONE worked letter ───────────
# A code that names a specific confusion is entitled to talk about specific
# letters - MAKHARIJ_SAD_TO_SEEN discussing ص and س IS the error. These are the
# opposite case: one code covering a whole FAMILY of letters, with an
# instruction written around a single example.
#
#     QALQALAH_MISSING  covers ق ط ب ج د, and says
#                       "say the «د» at the end of «أَحَدْ»"
#     HAMS_LOST         covers ف ح ث ه ش خ ص س ك ت, and says
#                       "say «سَ» and «زَ» one after the other"
#
# So a learner who softened the ق in «وَٱقْتَرِب» is told to practise د. That is
# not a smaller version of the right advice, it is advice about a different
# letter, and it now sits directly above a practice ladder correctly showing ق.
#
# THE LIST IS EXPLICIT AND SHORT ON PURPOSE. The obvious general rule - "blank
# any instruction naming a letter other than the detected one" - was tried
# against all 60 entries and over-fires: MADD_WAJIB_SHORTENED names ء because
# a following hamza is the CONDITION of the ruling, not an example, and
# IQLAB_MISSING names م because م is the target sound. Both would have lost a
# correct instruction. Curating which entries have this shape is a judgement
# about authored text, so it is written down rather than inferred, and
# tools/audit_fixed_examples.py is what surfaces candidates for it.
#
# THE FIX IS AUTHORING, NOT THIS. Rewriting "«أَحَدْ» oxiridagi «د»" to work for
# five letters means rewriting the worked example, which is a qori's job -
# templating {letter} into it would produce "the ق at the end of أَحَدْ", a word
# with no ق in it. Until then, suppression is the honest option: the card keeps
# what happened, where, and what to practise, and simply says nothing about how
# rather than saying something false.
#     MAKHARIJ_INTERDENTAL_TO_ZAY   covers ذ->ز AND ظ->ز, and its HEADLINE says
#                                   "Siz «ذ» harfini «ز» kabi o'qidingiz"
#
# The third one is the worst of the three and was found by replaying a real
# 2:7 recitation: a learner who read «عَظِيمٌ» with a ز was shown a card about ذ,
# a letter that does not occur in the word. Two entries share this code by
# design - it is one confusion with two sources - but the authored text picked
# one source and named it.
LETTER_SPECIFIC_EXAMPLE = frozenset({"QALQALAH_MISSING", "HAMS_LOST",
                                     "MAKHARIJ_INTERDENTAL_TO_ZAY"})

# Where a mismatched example is FIXABLE rather than merely suppressible. A
# letter confusion always has a correct card available - the generic, whose text
# is templated on {expected} and {actual} and so names whatever letters the
# detector actually found. Falling back to it beats blanking, because the
# learner keeps a real instruction instead of losing one.
SUBSTITUTION_FALLBACK = "GENERIC_LETTER_SUBSTITUTED"

_ARABIC_RUN = re.compile(r"[ء-ي]+")


def contradicts_letter(code: str, text: str, letter: str) -> bool:
    """True when this instruction's worked example is about a different letter.

    Only consulted for the curated set above. `letter` is the letter actually
    detected; if the text names it anywhere, the example fits and is kept - so
    a genuine د qalqalah still gets its full instruction.

    KEYED ON THE RESOLVED CODE. The engine emits QALQALA_DROP and the registry
    entry is QALQALAH_MISSING; testing the raw code silently matched nothing
    and suppressed nothing, which is the failure mode this whole file exists to
    prevent - see ALIAS.
    """
    if resolve(code) not in LETTER_SPECIFIC_EXAMPLE or not text or not letter:
        return False
    named = set("".join(_ARABIC_RUN.findall(text)))
    return bool(named) and letter not in named


def render(code: str, lang: str, fields: dict) -> dict | None:
    """Coaching card for one detected error, or None if this code has none.

    `fields` is the detection result. Missing values arrive as empty strings
    rather than being absent, so a template that references a field the
    detector genuinely cannot fill fails the brace check above instead of
    raising a confusing KeyError.
    """
    spec = entry(code)
    if not spec:
        return None
    block = spec.get(lang) or spec.get("uz") or {}
    safe = {k: ("" if v is None else v) for k, v in fields.items()}

    # CARD_FIELDS, not FIELDS: `rule` and `drill` are authored but not shown.
    # `fix` is narrowed to its first paragraph - see instruction().
    #
    # Substitution runs on the SELECTED text rather than the whole field, so a
    # placeholder that only ever appeared in the discarded commentary cannot
    # fail the brace check and drop a card the learner would otherwise have got.
    out = {key: _fill(instruction(block.get(key, "")) if key == "fix"
                      else block.get(key, ""),
                      safe, code=code, key=key)
           for key in CARD_FIELDS}

    # An authored worked example about a DIFFERENT letter than the one the
    # learner got wrong. See LETTER_SPECIFIC_EXAMPLE.
    letter = str(safe.get("letter", ""))
    bad_fix = contradicts_letter(code, out["fix"], letter)
    bad_headline = contradicts_letter(code, out["headline"], letter)

    if bad_headline and resolve(code) != SUBSTITUTION_FALLBACK:
        # THE HEADLINE IS THE WHOLE CARD'S CLAIM, so a wrong letter there cannot
        # simply be blanked the way an instruction can - that would leave a card
        # with no statement of what happened. For a letter confusion there is a
        # correct card available: the generic is templated on {expected} and
        # {actual} and therefore names the letters actually detected. Swapping
        # to it keeps a full, true card instead of half of a false one.
        generic = render(SUBSTITUTION_FALLBACK, lang, fields)
        if generic and generic["headline"].strip():
            # The TEXT comes from the generic; everything else stays this
            # entry's, because the classification was never what was wrong.
            generic["severity"] = spec.get("severity", "medium")
            generic["group"] = spec.get("group", "")
            generic["label"] = ""
            generic["audio_pair"] = audio_url(spec.get("audio_pair", ""))
            generic["reviewed"] = spec.get("status", "draft") == "reviewed"
            return generic
        out["headline"] = ""

    # A mismatched instruction with a sound headline is suppressed on its own: a
    # ق qalqalah must not be answered with a drill on د, and the practice ladder
    # below it is already showing ق.
    if bad_fix:
        out["fix"] = ""

    out["severity"] = spec.get("severity", "medium")
    out["group"] = spec.get("group", "")
    # v3 entries carry a short title; v4/v5 fold it into the headline. Passed
    # through as a label so the UI has one, and empty rather than invented when
    # the entry has none.
    out["label"] = block.get("name", "")
    # The isolated letter-pair recording for this confusion, e.g.
    # "audio/sad_zay.mp3" - the sound of «ص» against «ز», which is what a
    # learner needs to hear. Sent ONLY when the file is actually on disk, so
    # the client can render the control on presence alone and never offers a
    # button that plays nothing. See audio_url().
    out["audio_pair"] = audio_url(spec.get("audio_pair", ""))
    # Every entry in both registries is status='draft' by design - the same
    # review gate applies, and nothing here has been signed off by a qori.
    out["reviewed"] = spec.get("status", "draft") == "reviewed"
    out["unauthored"] = False
    return out
