# -*- coding: utf-8 -*-
"""Fetch the Uzbek and Russian translations once, commit the result.

    py -3.13 tools/build_translations.py

WHY AN ARTIFACT AND NOT A LIVE CALL
-----------------------------------
The verse-by-verse reader shows a translation under every ayah. Fetching that
per view would put a third-party outage between a learner and the text, add
latency to every arrow tap, and leak what they are reading. It is 1.6 MB for
the whole Quran in two languages - smaller than the segments artifact already
committed next to it.

SOURCE AND TRANSLATOR
---------------------
quran.com's API, resource ids 55 and 45:

    uz  Muhammad Sodiq Muhammad Yusuf, LATIN script (id 55)
    ru  Elmir Kuliev (id 45)

The Uzbek one is deliberately the Latin edition. alquran.cloud's `uz.sodik` is
the same translator in Cyrillic, and this app's entire interface is Latin
Uzbek - mixing the two scripts on one screen would read as broken.

⚠️ NOTHING HERE IS AUTHORED, AND NOTHING HERE IS THE QURAN. These are human
translations, reproduced verbatim apart from the two mechanical fixes below.
Decision 4 - no machine-authored content about the Quran - is why this is a
download and not a generation step. Check the licence terms for both editions
before shipping to real learners; that is a question for Rahmatulloh, not
something this script can settle.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "tilawah" / "content" / "translations.json"
API = "https://api.quran.com/api/v4/quran/translations/{id}"

EDITIONS = {
    "uz": {"id": 55, "translator": "Muhammad Sodiq Muhammad Yusuf",
           "script": "latin"},
    "ru": {"id": 45, "translator": "Elmir Kuliev", "script": "cyrillic"},
}

N_AYAT = 6236

# Footnote markers, e.g. <sup foot_note="170564">1</sup>. The footnote BODIES are
# not in this response at all, so the marker is a numeral pointing at nothing -
# it has to go rather than be left as a stray digit mid-sentence.
SUP = re.compile(r"<sup\b[^>]*>.*?</sup>", re.DOTALL)
TAG = re.compile(r"<[^>]+>")


def clean_uz(text: str) -> str:
    """Uzbek orthography, as the rest of the app writes it.

    The source uses a backtick for the turned comma and an ASCII apostrophe for
    the tutuq belgisi. Both are typewriter substitutes, and lib/i18n.ts already
    holds the app to the real characters. Verified exhaustively over all 6236
    verses before being applied blind:

        backtick    always follows o or g  (o`z, g`a)   -> ʻ  U+02BB
        apostrophe  always tutuq belgisi   (a'zo)       -> ʼ  U+02BC

    Anything else would be a different character with a different meaning, so
    this stays a substitution of two known cases rather than a tidy-up pass.
    """
    return text.replace("`", "ʻ").replace("'", "ʼ")


def strip_markup(text: str) -> str:
    return TAG.sub("", SUP.sub("", text)).strip()


def audit_uz(by_key: dict[str, str]) -> list[dict]:
    """Flag Uzbek Latin that cannot be right, WITHOUT correcting it.

    Uzbek Latin uses C only in the digraph "ch", so a bare C is a reliable
    signal of a bad Cyrillic->Latin transliteration - the source's 112:2 reads
    "Alloh — Comaddir" where the same translator's Cyrillic edition has
    "сомаддир" (Somaddir), i.e. Cyrillic С read as Latin C.

    This REPORTS and does not fix. Editing a scholar's translation of an
    attribute of Allah on the strength of a heuristic is exactly the kind of
    machine-authored content about the Quran that decision 4 forbids, and a
    one-character guess is not better for being small. The finding goes into
    the artifact's _meta so it is auditable, and into stdout so whoever runs
    the build has to see it.
    """
    findings = []
    for key, text in by_key.items():
        for word in re.findall(r"\b\w*[Cc]\w*\b", text):
            if not re.search(r"[Cc]h", word):
                findings.append({"ayah": key, "word": word,
                                 "why": "bare C: Uzbek Latin uses C only in 'ch'"})
    return findings


def fetch(edition_id: int) -> list[str]:
    url = API.format(id=edition_id)
    print(f"  GET {url}")
    # quran.com answers 403 to urllib's default User-Agent. Identify the tool
    # rather than impersonate a browser.
    req = urllib.request.Request(
        url, headers={"User-Agent": "tilawah-build-translations/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))
    return [t["text"] for t in data["translations"]]


def verse_keys() -> list[str]:
    """"sura:aya" for all 6236, in mushaf order.

    The API returns a flat ordered list with no verse key on each item, so the
    mapping is positional. Built from quran_transcript's own ayah counts rather
    than a table typed out here, and the count is asserted below - an off-by-one
    would silently shift every translation by one ayah, which is the worst
    possible failure for this file and the easiest to miss.
    """
    from quran_transcript import Aya

    keys = []
    cursor = Aya(1, 1)
    for sura in range(1, 115):
        cursor.set(sura, 1)
        for aya in range(1, cursor.get().num_ayat_in_sura + 1):
            keys.append(f"{sura}:{aya}")
    return keys


def main() -> None:
    keys = verse_keys()
    if len(keys) != N_AYAT:
        raise SystemExit(f"expected {N_AYAT} verse keys, built {len(keys)}")

    out = {"_meta": {
        "note": "Generated by tools/build_translations.py. Do not hand-edit.",
        "source": "https://api.quran.com/api/v4",
        "editions": {},
    }, "translations": {}}

    for lang, spec in EDITIONS.items():
        print(f"{lang}: {spec['translator']} ({spec['script']})")
        texts = fetch(spec["id"])
        if len(texts) != N_AYAT:
            raise SystemExit(f"{lang}: got {len(texts)} verses, want {N_AYAT}")
        clean = clean_uz if lang == "uz" else (lambda s: s)
        for key, text in zip(keys, texts):
            out["translations"].setdefault(key, {})[lang] = clean(
                strip_markup(text))
        out["_meta"]["editions"][lang] = {
            "resource_id": spec["id"],
            "translator": spec["translator"],
            "script": spec["script"],
        }

    # Spot-check a verse whose translation is unmistakable, so a silently
    # shifted mapping fails here rather than in front of a learner.
    fatiha = out["translations"]["1:1"]["uz"].lower()
    if "alloh" not in fatiha:
        raise SystemExit(f"1:1 does not look like the basmala: {fatiha[:80]!r}")

    suspect = audit_uz({k: v["uz"] for k, v in out["translations"].items()})
    out["_meta"]["uz_suspect_transliteration"] = suspect
    if suspect:
        print(f"\n⚠️  {len(suspect)} suspected transliteration error(s) in the "
              f"Uzbek source. NOT corrected here - see audit_uz().")
        for f in suspect:
            print(f"     {f['ayah']}: {f['word']!r} - {f['why']}")

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0) + "\n",
                   encoding="utf-8")
    print(f"\n{len(out['translations'])} ayat x {len(EDITIONS)} languages")
    print(f"artifact: {OUT}  ({OUT.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
