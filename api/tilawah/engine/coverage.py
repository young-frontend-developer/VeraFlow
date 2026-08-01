# -*- coding: utf-8 -*-
"""Which checks are even POSSIBLE in a segment, and how many of them are backed
by reviewed content.

The problem this solves: with 6236 ayat and only a handful of reviewed error
entries, almost every attempt fell into "couldn't fully assess", which reads as
broken software rather than as honest uncertainty. But "we checked nothing" and
"we checked twelve things and they were all fine" are completely different
results, and the app was reporting them identically.

So each segment gets a set of RELEVANT checks, derived from the reference
phonetic script alone - never from a recording. QALQALAH_MISSING cannot fire
where no qalqalah letter carries sukun; MAKHARIJ_SAD_TO_SEEN cannot fire where
there is no ص. Coverage is then the fraction of those relevant checks that a
qori has actually signed off.

PRECONDITION QUALITY
--------------------
A precondition that is true everywhere carries no information: it makes coverage
look high without telling the learner anything, and it makes the detector fire
in contexts nobody validated. Each precondition below is annotated with what it
actually restricts, measured over all 16366 segments. One could not be narrowed
and is marked UNIVERSAL rather than quietly left at 100%.

The narrowing rule, applied uniformly rather than per-code so the result is not
just whichever definition scored lowest. A check may fire only where the error is

  (a) PRODUCIBLE   - the articulation can physically go wrong there. Most ṣifa
                     errors need a SAKIN consonant: with a following vowel the
                     release carries the ṣifa and the error has nowhere to live.
  (b) AUDIBLE      - the difference is hearable, therefore correctable. A
                     pedagogical judgement, and the part most in need of a qori.
  (c) UNCLAIMED    - no other registry code already owns that context. A sakin
                     ق that loses its stop is QALQALAH_MISSING; reporting
                     SHIDDA_LOST on the same letter is double jeopardy.

Measured over all 16366 segments (loose -> narrowed):

    TAFKHEEM_ADDED  100.0% -> 28.0%   light letter beside a MUTBAQ neighbour
    HAMS_LOST        95.6% -> 41.4%   sakin hams letter only
    SHIDDA_LOST      97.3% -> 17.7%   sakin shadeed, minus the qalqalah letters
    JAHR_LOST       100.0% ->  8.8%   sakin jahr obstruent, minus the qalqalah
                                      letters -> ذ ز ض ظ غ
    MADD_ADDED      100.0% -> 100.0%  NOT NARROWED - see UNIVERSAL below, and
                                      MADD_ADDED_LEEN (26.9%) split out of it
    GHUNNA_ADDED    100.0% -> deleted The narrowing worked (14.7%) but the
                                      ENTRY was unsalvageable - no ṣifa flip
                                      exists to detect. See izhar_positions().

⚠️ These narrowings are modelling claims about WHERE learners err, and they are
not measured against real learner errors - only counted against the reference
text. Narrowing too far buys precision with false negatives. That is the right
direction under decision 5, but every rule above is a hypothesis awaiting a
qori's sign-off, not a finding. tools/audit_preconditions.py prints the loose
and narrow numbers side by side so the claim stays checkable.

QPS specifics this relies on:
  * ن  is an izhar noon - pronounced clearly
  * ں  is an ikhfa noon - hidden, the ghunnah ruling applies
  * ۾  is an iqlab meem
  * length is encoded by REPEATING a character, so a madd is a run >= 2
  * every noon and meem carries ghonna=maghnoon inherently, which is a property
    of the letter and NOT the tajweed ruling - so ghunnah rulings must be found
    positionally, not from the sifa flag
"""
import json
import re
from functools import lru_cache
from pathlib import Path

_REGISTRY_PATH = Path(__file__).resolve().parents[3] / "tajweed_error_registry_v3.json"
# v2 stays in the repo as the auditable "before". Regenerate v3 with
# api/tools/apply_v3_patch.py - never hand-edit it.
_REGISTRY_FALLBACK = Path(__file__).resolve().parents[3] / "tajweed_error_registry_v2.json"

THROAT = set("ءهعحغخ")          # huruf al-halq - izhar halqi triggers
HARAKAT = set("َُِ")
IKHFA_NOON = "ں"
# ۾ is the HIDDEN meem, and it covers two different rulings, not one:
#   iqlab           sukunli nuvn + بo   (2:10  مِ۾۾۾بَقلِهَا)
#   ikhfa shafawiya sukunli miym + بo   (105:4 تَرمِيهِ۾۾۾بِحِجَارَة)
# Verified from the phonetizer. The old name IQLAB_MEEM named only the first and
# is kept as an alias so nothing outside breaks.
HIDDEN_MEEM = "۾"
IQLAB_MEEM = HIDDEN_MEEM
IKHFA_MEEM = HIDDEN_MEEM
NASAL = set("نمں۾")
MADD_LETTERS = set("اوىيۥۦ")
MARKS = HARAKAT | {"ڇ"}         # ڇ marks qalqalah, it is not a letter

# huruf al-itbaq - the emphatics whose emphasis actually spreads to a neighbour.
# ق غ خ are musta'liya but not mutbaq and colour far less, so including them was
# what kept TAFKHEEM_ADDED at 79.5% instead of 28%.
MUTBAQ = set("صضطظ")
# Owned by QALQALAH_MISSING / QALQALAH_EXCESSIVE. A sakin qalqalah letter that
# loses its stop or its voicing is a qalqalah finding, not a shidda or jahr one.
QALQALA_LETTERS = set("قطبجد")
# Voiced obstruents - the only jahr letters that devoice. Sonorants (ل م ن ر و ي)
# and madd letters do not, and neither does ع in practice.
JAHR_OBSTRUENTS = set("بجدذزضظغق")

# Substitutions are possible exactly where a source letter occurs. The value is
# the set of letters that can trigger the code - most are one letter, but a
# confusion PAIR can be provoked from either side.
SUBSTITUTION_SOURCE = {
    "MAKHARIJ_AIN_TO_HAMZA": "ع", "MAKHARIJ_AIN_TO_HHA": "ع",
    "MAKHARIJ_HAMZA_TO_AIN": "ء", "MAKHARIJ_HA_TO_HHA": "ه",
    "MAKHARIJ_KHA_TO_HHA": "خ", "MAKHARIJ_GHAYN_TO_QAF": "غ",
    "MAKHARIJ_QAF_TO_KAF": "ق", "MAKHARIJ_THA_TO_SEEN": "ث",
    # ذ->ز and ظ->ز were separate entries; they are one failure with one drill
    # (the tongue tip never comes out between the teeth) so they are now one
    # code. Heaviness is NOT part of it - that is THAL_TO_ZAA_CONFUSION.
    "MAKHARIJ_INTERDENTAL_TO_ZAY": "ذظ",
    "MAKHARIJ_SAD_TO_SEEN": "ص", "MAKHARIJ_TAA_TO_TA": "ط",
    "MAKHARIJ_DAD_TO_DAL": "ض", "MAKHARIJ_DAD_TO_ZAA": "ض",
    # v3, from 3-dars. ش/ج share a makhraj (mid-tongue) and differ only by
    # hams/jahr; و/ف differ only by lip-vs-lip-and-teeth; ذ/ظ by tongue
    # position plus iste'lo. All three are provokable from either letter.
    "MAKHARIJ_SHEEN_TO_JEEM": "ش",
    "MAKHARIJ_WAW_TO_FA": "وف",
    "MAKHARIJ_THAL_TO_ZAA_CONFUSION": "ذظ",
}

# 6-dars. Sukunli miym has exactly three rulings, and QPS distinguishes all
# three by character, so they are structurally derivable:
#   idgham mislayn   miym + miym -> a run of م      (مممم)
#   ikhfa shafawiya  miym + بo   -> the hidden meem (۾۾۾)
#   izhar shafawiya  miym + any other of the 26     (plain م, then a consonant)
# The book singles out ف and و: their makhraj sits so close to miym that an
# unintended ixfo slips in. Those positions are counted separately.
MIM_IZHAR_HIGH_RISK_NEXT = set("فو")

# Preconditions that could NOT be narrowed to anything meaningful. Kept honest
# rather than tuned to look good: they really are possible almost everywhere,
# which makes them weak coverage signals and risky detectors.
#
# MADD_ADDED is the whole list. Its signal is "the reference has no lengthening
# here but the recitation does", and a learner can hold ANY vowel too long, so
# the only true precondition is "the segment contains a vowel" - 100.0%. Two
# narrowings were measured and both rejected:
#
#   unlengthened madd letter present   73.0%  - not a restriction worth the name
#   contains a leen letter (خَوْف)       26.9%  - a DIFFERENT error. Claiming madd
#                                               is only ever added on a leen
#                                               letter would be false, and the
#                                               check would go quiet exactly
#                                               where beginners over-lengthen a
#                                               plain fatha.
#
# The honest fix is not a precondition but a split in the registry: a narrow
# MADD_ADDED_LEEN that can be detected, leaving MADD_ADDED as an unscored
# catch-all. That is a registry change and it needs Rahmatulloh, so it is
# recorded here rather than done quietly.
UNIVERSAL = {"MADD_ADDED"}

# The ahkam group's detection_signal is marked TEKSHIRILMAGAN (untested), so
# those entries are excluded from detection and from coverage entirely.
EXCLUDED_CONFIDENCE = {"low"}


@lru_cache(maxsize=1)
def registry() -> dict:
    """The generated catalogue with qori review decisions merged over it.

    The overlay lives in tajweed_registry_review.json rather than in v3 itself,
    because v3 is regenerated from its inputs and would otherwise lose every
    approval. See engine/review.py. Cleared by review.record() on every write.
    """
    from .review import apply_overlay

    path = _REGISTRY_PATH if _REGISTRY_PATH.exists() else _REGISTRY_FALLBACK
    if not path.exists():
        return {}
    errors = json.loads(path.read_text(encoding="utf-8"))["errors"]
    return apply_overlay(errors)


@lru_cache(maxsize=1)
def in_scope() -> dict:
    """Entries we attempt to detect at all: high and medium confidence only."""
    return {k: v for k, v in registry().items()
            if v.get("detection_confidence") not in EXCLUDED_CONFIDENCE}


def is_reviewed(code: str) -> bool:
    """The safety gate. Nothing unreviewed is ever shown to a learner."""
    return registry().get(code, {}).get("status") == "reviewed"


def _sifa_groups(sifat) -> list[tuple[str, dict]]:
    out = []
    for s in sifat:
        g = getattr(s, "phonemes", None) or getattr(s, "phonemes_group", None)
        text = g if isinstance(g, str) else getattr(g, "text", "")
        fields = {}
        for f in ("hams_or_jahr", "shidda_or_rakhawa", "tafkheem_or_taqeeq",
                  "itbaq", "qalqla", "ghonna", "istitala"):
            v = getattr(s, f, None)
            fields[f] = getattr(v, "text", v)
        out.append((text or "", fields))
    return out


def _has_run(text: str, chars: set[str]) -> bool:
    """A repeated character = length in QPS."""
    return any(text[i] == text[i + 1] and text[i] in chars
               for i in range(len(text) - 1))


def _base(text: str) -> str:
    """The consonant a ṣifa group is about, ignoring harakat and the qalqalah mark."""
    for ch in text or "":
        if ch not in MARKS:
            return ch
    return ""


def _is_sakin(text: str) -> bool:
    """No haraka in the group = the letter carries sukun.

    This is the workhorse of the ṣifa narrowings. A voweled consonant releases
    into its vowel and takes its ṣifa with it; a sakin one has to hold the ṣifa
    on its own, which is where hams, shidda and jahr are actually lost.
    """
    return not (set(text or "") & HARAKAT)


def izhar_positions(groups: list[tuple[str, dict]]) -> list[int]:
    """Izhar halqi: a SAKIN noon directly followed by a throat letter.

    Retained after GHUNNA_ADDED was deleted, because the replacement for that
    entry is a run-length check at exactly these positions - an izhar noon is
    one count, so an added ghunnah surfaces as a run.

    Verified against the phonetizer rather than reasoned about, because QPS
    distinguishes the noon rulings by CHARACTER, not by position:
      izhar  1:7   أَنْعَمْتَ      -> ...نعَ...   plain ن + throat  -> hit
      tanwin 112:4 كُفُوًا أَحَدٌ  -> ...وَنءَ... plain ن + hamza   -> hit
      ikhfa  114:4 مِن شَرِّ       -> مِںںں       ikhfa ں           -> no
      idgham 2:5   هُدًى مِّن      -> دَممممِ     assimilated       -> no
      ghunna 110:2 ٱلنَّاسَ        -> ننننَ       run, then haraka  -> no
    """
    out = []
    for i, (text, _f) in enumerate(groups):
        if not text or text[-1] != "ن" or not _is_sakin(text):
            continue                        # voweled noon is not sakin
        nxt = groups[i + 1][0] if i + 1 < len(groups) else ""
        if nxt and nxt[0] in THROAT:
            out.append(i)
    return out


def leen_positions(phonemes: str) -> list[int]:
    """Leen letters: a sakin و or ي preceded by fatha (خَوْف, عَلَيْهِمْ).

    The precondition for MADD_ADDED_LEEN, split out of MADD_ADDED because it is
    the one over-lengthening case with a real structural restriction - 26.9% of
    segments against MADD_ADDED's irreducible 100.0%.
    """
    out = []
    for k in range(1, len(phonemes)):
        if phonemes[k] not in "وي" or phonemes[k - 1] != "َ":
            continue
        nxt = phonemes[k + 1] if k + 1 < len(phonemes) else ""
        if nxt != phonemes[k] and nxt not in HARAKAT:
            out.append(k)                   # already long, or voweled = not leen
    return out


def mim_izhar_positions(phonemes: str) -> list[tuple[int, str]]:
    """Izhar shafawiya positions: [(index, following letter)].

    A sukunli miym is a plain م that is not followed by a haraka and is not part
    of a run. م + م is idgham mislayn and م + بo is written ۾, so anything left
    that is followed by a consonant is izhar - the miym must be sounded clearly.
    """
    out: list[tuple[int, str]] = []
    for i, ch in enumerate(phonemes):
        if ch != "م":
            continue
        if i and phonemes[i - 1] == "م":
            continue                            # second half of a run
        nxt = phonemes[i + 1] if i + 1 < len(phonemes) else ""
        if not nxt or nxt in HARAKAT or nxt == "م":
            continue                            # voweled, final, or a run
        out.append((i, nxt))
    return out


def detection_weight(code: str, phonemes: str) -> float:
    """Confidence multiplier for one code on one reference. 1.0 = no change.

    6-dars singles out ف and و after a sukunli miym: their makhraj sits close
    enough to miym that an unintended ixfo slips in, so a ghunna detected there
    is likelier to be a real error than a model artefact.

    ⚠️ NOTHING CONSUMES THIS YET, deliberately. MIM_IZHAR_SHAFAWIYA_WRONG is
    detection_confidence='low' and its whole `ahkam` group is excluded from
    in_scope(), so the code cannot fire at all today. Weighting a detector that
    does not run would be theatre. This computes the number, and a test pins it,
    so promoting the entry is a one-line change rather than a re-derivation.
    """
    if code != "MIM_IZHAR_SHAFAWIYA_WRONG":
        return 1.0
    risky = sum(1 for _i, nxt in mim_izhar_positions(phonemes)
                if nxt in MIM_IZHAR_HIGH_RISK_NEXT)
    return 1.5 if risky else 1.0


def possible_codes(phonemes: str, sifat, phonemes_spaced: str = "") -> set[str]:
    """Checks structurally possible on this reference. No recording involved."""
    groups = _sifa_groups(sifat)
    found: set[str] = set()

    # ── makharij: one of the source letters must occur ────────────────────
    for code, letters in SUBSTITUTION_SOURCE.items():
        if any(ch in phonemes for ch in letters):
            found.add(code)

    # ── sukunli miym (6-dars) ─────────────────────────────────────────────
    if _has_run(phonemes, {"م"}):
        found.add("MIM_IDGHAM_MISLAYN_MISSING")
    if IKHFA_MEEM in phonemes:
        found.add("MIM_IKHFA_SHAFAWIYA_MISSING")
    if mim_izhar_positions(phonemes):
        found.add("MIM_IZHAR_SHAFAWIYA_WRONG")

    # ── tafkheem ──────────────────────────────────────────────────────────
    tafkheem = [f["tafkheem_or_taqeeq"] for _, f in groups]
    if "mofakham" in tafkheem:
        found.add("TAFKHEEM_LOST")          # restricts to 79.6% of segments

    # TAFKHEEM_ADDED: emphasis is added to a light letter by coarticulation with
    # an emphatic neighbour, not at random. "Any mofakham neighbour" was tried
    # first and left it at 79.5% - because mofakham includes ق, غ, خ and every
    # mofakham ر, which is most of the Quran. Requiring a MUTBAQ neighbour, the
    # emphatics whose iṭbāq genuinely colours what is next to it, gives 28.0%.
    # ر is excluded on the light side: RAA_TARQIQ_MISSING owns that letter.
    for i, (text, f) in enumerate(groups):
        if f["tafkheem_or_taqeeq"] != "moraqaq" or "ر" in text:
            continue
        if any(0 <= j < len(groups) and groups[j][1]["itbaq"] == "motbaq"
               for j in (i - 1, i + 1)):
            found.add("TAFKHEEM_ADDED")
            break

    # raa carries its own entries, and needs the letter AND the expected sifa
    for text, f in groups:
        if "ر" not in text:
            continue
        if f["tafkheem_or_taqeeq"] == "mofakham":
            found.add("RAA_TAFKHEEM_MISSING")
        elif f["tafkheem_or_taqeeq"] == "moraqaq":
            found.add("RAA_TARQIQ_MISSING")

    # ── qalqalah / hams / jahr / shidda ───────────────────────────────────
    # These three ṣifāt are only losable on a SAKIN consonant - see the narrowing
    # rule (a) in the module docstring - and never on a letter whose failure
    # another code already reports.
    if any(f["qalqla"] == "moqalqal" for _, f in groups):
        found.update({"QALQALAH_MISSING", "QALQALAH_EXCESSIVE"})

    for text, f in groups:
        base = _base(text)
        if not base or not _is_sakin(text) or base in MADD_LETTERS:
            continue
        # 95.6% -> 41.4%. The weakest of the four narrowings: breathiness is
        # hardest to localise, and "sakin" is the only restriction defensible
        # without asserting a mechanism. Narrowing further to "before a jahr
        # letter" reaches 22.1% but silences hams lost at waqf, which is a real
        # and common learner failure.
        if f["hams_or_jahr"] == "hams":
            found.add("HAMS_LOST")
        # 100% -> 8.8%. Devoicing needs a voiced obstruent; sonorants and madd
        # letters do not devoice. Positions that actually carry qalqalah are
        # removed because a devoiced sakin ق or ب is heard, and reported, as a
        # qalqalah problem - leaving ذ ز ض ظ غ, exactly the Uzbek/Russian
        # final-devoicing set from risk 4 of the architecture doc.
        #
        # The exclusion tests the ṣifa, not the letter. Equivalent here - every
        # sakin qalqalah letter is moqalqal - but it is the correct test rather
        # than a coincidentally correct one, and it inherits the shadda
        # exception (2-dars) instead of restating it. See test_preconditions.
        if (f["hams_or_jahr"] == "jahr" and base in JAHR_OBSTRUENTS
                and f["qalqla"] != "moqalqal"):
            found.add("JAHR_LOST")
        # 97.3% -> 17.7%. A shadeed letter's stop is only assessable when sakin,
        # and for the qalqalah letters the incomplete stop IS the qalqalah check.
        # What is left is sakin ء ك ت.
        if f["shidda_or_rakhawa"] == "shadeed" and f["qalqla"] != "moqalqal":
            found.add("SHIDDA_LOST")

    # ── ghunnah ───────────────────────────────────────────────────────────
    # Ruling positions only. Every noon/meem is inherently maghnoon, so the sifa
    # flag alone would match nearly every segment and mean nothing.
    #   prolonged ghunnah = ikhfa noon, iqlab meem, or a shadda'd nasal (a run)
    has_ruling_ghunnah = (
        IKHFA_NOON in phonemes or IQLAB_MEEM in phonemes
        or _has_run(phonemes, {"ن", "م"})
    )
    if has_ruling_ghunnah:
        found.update({"GHUNNA_MISSING", "GHUNNA_TOO_SHORT"})

    # GHUNNA_ADDED WAS HERE AND IS GONE. It asked for expected 'not_maghnoon'
    # surfacing as 'maghnoon' at izhar positions, but the reference marks even an
    # izhar noon 'maghnoon' - ghunnah is a property of the LETTER, not of the
    # ruling - so there was no ṣifa flip to detect anywhere in the Quran and no
    # precondition could have fixed that. Deleted from the registry 2026-08-01.
    #
    # The izhar POSITION logic it needed survives as izhar_positions() below,
    # because an added ghunnah is really a duration error (an izhar noon is one
    # count, so holding it shows up as a run) and whatever replaces this entry
    # will need exactly those positions.

    # ── madd ──────────────────────────────────────────────────────────────
    if _has_run(phonemes, MADD_LETTERS | HARAKAT):
        found.update({"MADD_TOO_SHORT", "MADD_TOO_LONG"})
    # madd muttasil: madd letter followed by hamza WITHIN one word, which needs
    # the spaced phonemes - remove_spaces=True destroys exactly this boundary.
    src = phonemes_spaced or phonemes
    for word in src.split():
        for i in range(len(word) - 2):
            if word[i] == word[i + 1] and word[i] in MADD_LETTERS \
                    and word[i + 2] == "ء":
                found.add("MADD_WAJIB_SHORTENED")
                break

    # MADD_ADDED_LEEN: the one over-lengthening case with a real restriction.
    # Split out of MADD_ADDED 2026-08-01 - 26.9% of segments.
    if leen_positions(phonemes):
        found.add("MADD_ADDED_LEEN")

    # MADD_ADDED: everything else. Lengthening can be introduced at any vowel,
    # so this stays at 100.0% and stays in UNIVERSAL - excluded from the coverage
    # score and sorted last in the review ranking. Kept rather than deleted so
    # the case is still nameable when a learner lengthens an arbitrary haraka.
    found.add("MADD_ADDED")

    return found & set(in_scope())


def coverage(phonemes: str, sifat, phonemes_spaced: str = "") -> dict:
    """Relevant checks, how many are reviewed, and the resulting score."""
    relevant = possible_codes(phonemes, sifat, phonemes_spaced)
    reviewed = {c for c in relevant if is_reviewed(c)}
    informative = relevant - UNIVERSAL
    return {
        "relevant": sorted(relevant),
        "reviewed": sorted(reviewed),
        "unreviewed": sorted(relevant - reviewed),
        "n_relevant": len(relevant),
        "n_reviewed": len(reviewed),
        # Universal checks are excluded from the score: counting a check that is
        # possible everywhere would inflate every segment identically and tell
        # the learner nothing about THIS passage.
        "score": (len(reviewed & informative) / len(informative)
                  if informative else 0.0),
    }
