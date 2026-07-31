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
actually restricts, measured over all 16366 segments. Three could not be
narrowed and are marked UNIVERSAL rather than quietly left at 100%.

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

_REGISTRY_PATH = Path(__file__).resolve().parents[3] / "tajweed_error_registry_v2.json"

THROAT = set("ءهعحغخ")          # huruf al-halq - izhar halqi triggers
HARAKAT = set("َُِ")
IKHFA_NOON = "ں"
IQLAB_MEEM = "۾"
NASAL = set("نمں۾")
MADD_LETTERS = set("اوىيۥۦ")

# Substitutions are possible exactly where the source letter occurs.
SUBSTITUTION_SOURCE = {
    "MAKHARIJ_AIN_TO_HAMZA": "ع", "MAKHARIJ_AIN_TO_HHA": "ع",
    "MAKHARIJ_HAMZA_TO_AIN": "ء", "MAKHARIJ_HA_TO_HHA": "ه",
    "MAKHARIJ_KHA_TO_HHA": "خ", "MAKHARIJ_GHAYN_TO_QAF": "غ",
    "MAKHARIJ_QAF_TO_KAF": "ق", "MAKHARIJ_THA_TO_SEEN": "ث",
    "MAKHARIJ_THAL_TO_ZAY": "ذ", "MAKHARIJ_ZAA_TO_ZAY": "ظ",
    "MAKHARIJ_SAD_TO_SEEN": "ص", "MAKHARIJ_TAA_TO_TA": "ط",
    "MAKHARIJ_DAD_TO_DAL": "ض", "MAKHARIJ_DAD_TO_ZAA": "ض",
}

# Preconditions that could NOT be narrowed to anything meaningful. Kept honest
# rather than tuned to look good: they really are possible almost everywhere,
# which makes them weak coverage signals and risky detectors.
UNIVERSAL = {"JAHR_LOST", "MADD_ADDED"}

# The ahkam group's detection_signal is marked TEKSHIRILMAGAN (untested), so
# those entries are excluded from detection and from coverage entirely.
EXCLUDED_CONFIDENCE = {"low"}


@lru_cache(maxsize=1)
def registry() -> dict:
    if not _REGISTRY_PATH.exists():
        return {}
    return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))["errors"]


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


def possible_codes(phonemes: str, sifat, phonemes_spaced: str = "") -> set[str]:
    """Checks structurally possible on this reference. No recording involved."""
    groups = _sifa_groups(sifat)
    found: set[str] = set()

    # ── makharij: the source letter must occur ────────────────────────────
    for code, letter in SUBSTITUTION_SOURCE.items():
        if letter in phonemes:
            found.add(code)

    # ── tafkheem ──────────────────────────────────────────────────────────
    tafkheem = [f["tafkheem_or_taqeeq"] for _, f in groups]
    if "mofakham" in tafkheem:
        found.add("TAFKHEEM_LOST")          # restricts to 79.6% of segments
    # TAFKHEEM_ADDED narrowed: emphasis is realistically ADDED to a light letter
    # by coarticulation with an emphatic neighbour, not at random. Requiring
    # adjacency cuts this from "every segment" to something meaningful.
    for i, val in enumerate(tafkheem):
        if val != "moraqaq":
            continue
        neighbours = tafkheem[max(0, i - 1):i] + tafkheem[i + 1:i + 2]
        if "mofakham" in neighbours:
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
    if any(f["qalqla"] == "moqalqal" for _, f in groups):
        found.update({"QALQALAH_MISSING", "QALQALAH_EXCESSIVE"})
    if any(f["hams_or_jahr"] == "hams" for _, f in groups):
        found.add("HAMS_LOST")
    if any(f["hams_or_jahr"] == "jahr" for _, f in groups):
        found.add("JAHR_LOST")              # UNIVERSAL - see module docstring
    if any(f["shidda_or_rakhawa"] == "shadeed" for _, f in groups):
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

    # GHUNNA_ADDED narrowed to izhar positions, per its signal: a SAKIN noon
    # followed by a throat letter, where ghunnah must NOT be applied. Previously
    # this matched any not_maghnoon phoneme, i.e. essentially every segment.
    for i, (text, _) in enumerate(groups):
        if not text or text[-1] != "ن" or (set(text) & HARAKAT):
            continue                        # voweled noon is not sakin
        nxt = groups[i + 1][0] if i + 1 < len(groups) else ""
        if nxt and nxt[0] in THROAT:
            found.add("GHUNNA_ADDED")
            break

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

    # MADD_ADDED: lengthening can be introduced at any vowel. No structural
    # precondition exists short of "the segment contains a vowel", so it is
    # marked UNIVERSAL rather than dressed up as a restriction.
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
