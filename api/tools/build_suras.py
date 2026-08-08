# -*- coding: utf-8 -*-
"""Generate content/suras.json - the catalogue the sura picker is built on.

quran_transcript supplies the Arabic name and the ayah count, and is the source
of truth for both. It does NOT supply transliterations, so those live in the
table below.

Two transliterations per sura, on purpose. `translit` is the standard Latin form
most people have seen in print; `uz` is the Uzbek spelling, which differs enough
that searching "Fotiha" or "Ixlos" would otherwise find nothing. Both feed the
search index, so either spelling works and so does the bare number.

Run:  py -3.13 tools/build_suras.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from quran_transcript import Aya  # noqa: E402

OUT = ROOT / "tilawah" / "content" / "suras.json"

# THE TABLE. (number, standard Latin, Uzbek, revelation place)
#
# quran_transcript supplies the Arabic name and the ayah count and is the
# source of truth for both. It supplies NEITHER a transliteration NOR a
# revelation place, so those live here and are the two columns that can be
# wrong without anything crashing. Both were audited Aug 2026 - see below.
#
# -- THE TWO TRANSLITERATIONS --------------------------------------------
#
# `translit` is the standard Latin form most people have seen in print; `uz`
# is the Uzbek spelling, which differs enough that searching "Fotiha" or
# "Ixlos" would otherwise find nothing. Both feed the search index, so either
# spelling works and so does the bare number.
#
# UZBEK USES ITS OWN LETTERS, NOT APOSTROPHES. o<U+02BB> and g<U+02BB> take the modifier
# letter turned comma (U+02BB); the glottal stop in a<U+02BC>lo and Mu<U+02BC>minun takes the
# modifier letter apostrophe (U+02BC). This column used ASCII ' for all four,
# which is a misspelling in the app's primary language. Fixing it means both
# fold() here and foldQuery() in the client must strip the new characters, or
# every corrected name silently drops out of search - they do.
#
# -- REVELATION PLACE, AND ITS PROVENANCE --------------------------------
#
# makki | madani, following the designation printed in the standard Cairo
# (1924) mushaf, which is the one the Uzbek printings follow. It yields 86
# makki and 28 madani, which is the figure normally cited and is asserted below
# so a future edit cannot quietly drift off it.
#
# THIS IS NAVIGATION METADATA, NOT A RULING. Roughly ten suras are classified
# differently by different scholars - 13, 55, 76, 83, 97, 99 and 107 are the
# usual ones - and this file follows the mushaf's designation in every case
# rather than adjudicating. It is COMPILED AND UNREVIEWED, like every other
# content table in this project, and wants a qori pass before launch; the
# provenance travels into suras.json's _meta so the claim is visible from the
# data rather than only from this comment.
NAMES = [    (1, "Al-Fatiha", "Fotiha", "makki"),
    (2, "Al-Baqara", "Baqara", "madani"),
    (3, "Ali 'Imran", "Oli Imron", "madani"),
    (4, "An-Nisa", "Niso", "madani"),
    (5, "Al-Ma'ida", "Moida", "madani"),
    (6, "Al-An'am", "Anʼom", "makki"),
    (7, "Al-A'raf", "Aʼrof", "makki"),
    (8, "Al-Anfal", "Anfol", "madani"),
    (9, "At-Tawba", "Tavba", "madani"),
    (10, "Yunus", "Yunus", "makki"),
    (11, "Hud", "Hud", "makki"),
    (12, "Yusuf", "Yusuf", "makki"),
    (13, "Ar-Ra'd", "Raʼd", "madani"),
    (14, "Ibrahim", "Ibrohim", "makki"),
    (15, "Al-Hijr", "Hijr", "makki"),
    (16, "An-Nahl", "Nahl", "makki"),
    (17, "Al-Isra", "Isro", "makki"),
    (18, "Al-Kahf", "Kahf", "makki"),
    (19, "Maryam", "Maryam", "makki"),
    (20, "Ta-Ha", "Toha", "makki"),
    (21, "Al-Anbiya", "Anbiyo", "makki"),
    (22, "Al-Hajj", "Haj", "madani"),
    (23, "Al-Mu'minun", "Muʼminun", "makki"),
    (24, "An-Nur", "Nur", "madani"),
    (25, "Al-Furqan", "Furqon", "makki"),
    (26, "Ash-Shu'ara", "Shuaro", "makki"),
    (27, "An-Naml", "Naml", "makki"),
    (28, "Al-Qasas", "Qasas", "makki"),
    (29, "Al-'Ankabut", "Ankabut", "makki"),
    (30, "Ar-Rum", "Rum", "makki"),
    (31, "Luqman", "Luqmon", "makki"),
    (32, "As-Sajda", "Sajda", "makki"),
    (33, "Al-Ahzab", "Ahzob", "madani"),
    (34, "Saba", "Saba", "makki"),
    (35, "Fatir", "Fotir", "makki"),
    (36, "Ya-Sin", "Yosin", "makki"),
    (37, "As-Saffat", "Soffat", "makki"),
    (38, "Sad", "Sod", "makki"),
    (39, "Az-Zumar", "Zumar", "makki"),
    (40, "Ghafir", "Gʻofir", "makki"),
    (41, "Fussilat", "Fussilat", "makki"),
    (42, "Ash-Shura", "Shuro", "makki"),
    (43, "Az-Zukhruf", "Zuxruf", "makki"),
    (44, "Ad-Dukhan", "Duxon", "makki"),
    (45, "Al-Jathiya", "Josiya", "makki"),
    (46, "Al-Ahqaf", "Ahqof", "makki"),
    (47, "Muhammad", "Muhammad", "madani"),
    (48, "Al-Fath", "Fath", "madani"),
    (49, "Al-Hujurat", "Hujurot", "madani"),
    (50, "Qaf", "Qof", "makki"),
    (51, "Adh-Dhariyat", "Zoriyot", "makki"),
    (52, "At-Tur", "Tur", "makki"),
    (53, "An-Najm", "Najm", "makki"),
    (54, "Al-Qamar", "Qamar", "makki"),
    (55, "Ar-Rahman", "Rahmon", "madani"),
    (56, "Al-Waqi'a", "Voqea", "makki"),
    (57, "Al-Hadid", "Hadid", "madani"),
    (58, "Al-Mujadila", "Mujodala", "madani"),
    (59, "Al-Hashr", "Hashr", "madani"),
    (60, "Al-Mumtahana", "Mumtahana", "madani"),
    (61, "As-Saff", "Saff", "madani"),
    (62, "Al-Jumu'a", "Jumua", "madani"),
    (63, "Al-Munafiqun", "Munofiqun", "madani"),
    (64, "At-Taghabun", "Tagʻobun", "madani"),
    (65, "At-Talaq", "Taloq", "madani"),
    (66, "At-Tahrim", "Tahrim", "madani"),
    (67, "Al-Mulk", "Mulk", "makki"),
    (68, "Al-Qalam", "Qalam", "makki"),
    (69, "Al-Haqqa", "Haqqa", "makki"),
    (70, "Al-Ma'arij", "Maorij", "makki"),
    (71, "Nuh", "Nuh", "makki"),
    (72, "Al-Jinn", "Jin", "makki"),
    (73, "Al-Muzzammil", "Muzzammil", "makki"),
    (74, "Al-Muddaththir", "Muddassir", "makki"),
    (75, "Al-Qiyama", "Qiyoma", "makki"),
    (76, "Al-Insan", "Inson", "madani"),
    (77, "Al-Mursalat", "Mursalot", "makki"),
    (78, "An-Naba", "Naba", "makki"),
    (79, "An-Nazi'at", "Noziot", "makki"),
    (80, "'Abasa", "Abasa", "makki"),
    (81, "At-Takwir", "Takvir", "makki"),
    (82, "Al-Infitar", "Infitor", "makki"),
    (83, "Al-Mutaffifin", "Mutaffifin", "makki"),
    (84, "Al-Inshiqaq", "Inshiqoq", "makki"),
    (85, "Al-Buruj", "Buruj", "makki"),
    (86, "At-Tariq", "Toriq", "makki"),
    (87, "Al-A'la", "Aʼlo", "makki"),
    (88, "Al-Ghashiya", "Gʻoshiya", "makki"),
    (89, "Al-Fajr", "Fajr", "makki"),
    (90, "Al-Balad", "Balad", "makki"),
    (91, "Ash-Shams", "Shams", "makki"),
    (92, "Al-Layl", "Layl", "makki"),
    (93, "Ad-Duha", "Zuho", "makki"),
    (94, "Ash-Sharh", "Sharh", "makki"),
    (95, "At-Tin", "Tiyn", "makki"),
    (96, "Al-'Alaq", "Alaq", "makki"),
    (97, "Al-Qadr", "Qadr", "makki"),
    (98, "Al-Bayyina", "Bayyina", "madani"),
    (99, "Az-Zalzala", "Zalzala", "madani"),
    (100, "Al-'Adiyat", "Odiyot", "makki"),
    (101, "Al-Qari'a", "Qoria", "makki"),
    (102, "At-Takathur", "Takosur", "makki"),
    (103, "Al-'Asr", "Asr", "makki"),
    (104, "Al-Humaza", "Humaza", "makki"),
    (105, "Al-Fil", "Fil", "makki"),
    (106, "Quraysh", "Quraysh", "makki"),
    (107, "Al-Ma'un", "Moun", "makki"),
    (108, "Al-Kawthar", "Kavsar", "makki"),
    (109, "Al-Kafirun", "Kofirun", "makki"),
    (110, "An-Nasr", "Nasr", "madani"),
    (111, "Al-Masad", "Masad", "makki"),
    (112, "Al-Ikhlas", "Ixlos", "makki"),
    (113, "Al-Falaq", "Falaq", "makki"),
    (114, "An-Nas", "Nos", "makki"),
]


# Everything a learner leaves out when typing a sura name.
#
# THE LAST FOUR ARE NEW AND THE UZBEK COLUMN DEPENDS ON THEM. U+02BB (oʻ, gʻ)
# and U+02BC (aʼlo) are the correct Uzbek letters and they are not on anyone's
# keyboard, so "Gʻofir" gets typed "gofir" and "Aʼrof" gets typed "arof". They
# have to fold away exactly like the ASCII apostrophe they replaced, and the
# CLIENT'S foldQuery() strips the same set - if the two lists ever disagree,
# the query is folded one way and the haystack the other and nine suras become
# unsearchable with no error anywhere.
STRIP = "'’`ʻʼ’-–—"


def fold(s: str) -> str:
    """Search key: lowercase, and strip everything a learner will not type.

    Apostrophes and hyphens are exactly what people leave out - "Ali 'Imran"
    gets typed "ali imran", "Al-A'la" gets typed "ala". Folding both sides of
    the comparison is what makes the search forgiving without being fuzzy.
    """
    return "".join(ch for ch in s.lower() if ch not in STRIP).strip()


PLACES = ("makki", "madani")


def main() -> int:
    if len(NAMES) != 114:
        print(f"transliteration table has {len(NAMES)} rows, expected 114")
        return 1

    bad = [n for n, _, _, p in NAMES if p not in PLACES]
    if bad:
        print(f"rows with an unknown revelation place: {bad}")
        return 1

    # The count the mushaf's own designation yields. Asserted rather than
    # trusted: this column is hand-maintained and a single flipped row is
    # invisible by inspection but moves this number.
    madani = sum(1 for _, _, _, p in NAMES if p == "madani")
    if madani != 28:
        print(f"madani count is {madani}, expected 28 - refusing to write")
        return 1

    rows = []
    for number, translit, uz, place in NAMES:
        meta = Aya(number, 1).get()
        # Both name and count come from the library, never from the table -
        # a typo in a hand-maintained ayah count would silently truncate a
        # sura's picker and be very hard to notice.
        rows.append({
            "number": number,
            "name_ar": meta.sura_name,
            "translit": translit,
            "uz": uz,
            "n_ayat": meta.num_ayat_in_sura,
            "place": place,
            # Precomputed so the client filters on a plain substring test and
            # every spelling lands on the same row.
            "search": " ".join(dict.fromkeys(
                [str(number), fold(translit), fold(uz),
                 fold(translit.split("-", 1)[-1]), meta.sura_name])),
        })

    total = sum(r["n_ayat"] for r in rows)
    if total != 6236:
        print(f"ayah total is {total}, expected 6236 - refusing to write")
        return 1

    # The provenance travels WITH the data, not only in this file's comments.
    # Anyone reading suras.json can see that the revelation places are
    # compiled and unreviewed without having to find the generator.
    meta_block = {
        "generated_by": "tools/build_suras.py",
        "names_source": "quran_transcript (Arabic name, ayah count)",
        "translit_source": "hand-maintained table in the generator; audited "
                           "Aug 2026, UNREVIEWED by a qori",
        "place_source": "designation printed in the standard Cairo (1924) "
                        "mushaf; 86 makki / 28 madani",
        "place_caveat": "Navigation metadata, not a ruling. Around ten suras "
                        "(13, 55, 76, 83, 97, 99, 107 among them) are "
                        "classified differently by different scholars; this "
                        "follows the mushaf in every case rather than "
                        "adjudicating.",
        "review_required": True,
    }

    OUT.write_text(
        json.dumps({"_meta": meta_block, "suras": rows},
                   ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    # Windows consoles default to cp1252, which cannot encode Arabic or the
    # Uzbek turned comma - and the summary printed AFTER the file was written,
    # so the tool exited non-zero having actually succeeded. Reconfigure the
    # stream rather than dropping the characters: a build tool whose output you
    # cannot read is only marginally better than one that crashes.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(f"wrote {OUT}\n{len(rows)} suras, {total} ayat, "
          f"{madani} madani / {114 - madani} makki")
    for r in rows[:3] + rows[-2:]:
        print(f"  {r['number']:>3} {r['name_ar']:<12} {r['translit']:<16} "
              f"{r['uz']:<12} {r['n_ayat']:>3} ayat  {r['place']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
