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

# (number, standard Latin, Uzbek)
NAMES = [
    (1, "Al-Fatiha", "Fotiha"), (2, "Al-Baqara", "Baqara"),
    (3, "Ali 'Imran", "Oli Imron"), (4, "An-Nisa", "Niso"),
    (5, "Al-Ma'ida", "Moida"), (6, "Al-An'am", "An'om"),
    (7, "Al-A'raf", "A'rof"), (8, "Al-Anfal", "Anfol"),
    (9, "At-Tawba", "Tavba"), (10, "Yunus", "Yunus"),
    (11, "Hud", "Hud"), (12, "Yusuf", "Yusuf"),
    (13, "Ar-Ra'd", "Ra'd"), (14, "Ibrahim", "Ibrohim"),
    (15, "Al-Hijr", "Hijr"), (16, "An-Nahl", "Nahl"),
    (17, "Al-Isra", "Isro"), (18, "Al-Kahf", "Kahf"),
    (19, "Maryam", "Maryam"), (20, "Ta-Ha", "Toha"),
    (21, "Al-Anbiya", "Anbiyo"), (22, "Al-Hajj", "Haj"),
    (23, "Al-Mu'minun", "Mu'minun"), (24, "An-Nur", "Nur"),
    (25, "Al-Furqan", "Furqon"), (26, "Ash-Shu'ara", "Shuaro"),
    (27, "An-Naml", "Naml"), (28, "Al-Qasas", "Qasas"),
    (29, "Al-'Ankabut", "Ankabut"), (30, "Ar-Rum", "Rum"),
    (31, "Luqman", "Luqmon"), (32, "As-Sajda", "Sajda"),
    (33, "Al-Ahzab", "Ahzob"), (34, "Saba", "Saba"),
    (35, "Fatir", "Fotir"), (36, "Ya-Sin", "Yosin"),
    (37, "As-Saffat", "Soffat"), (38, "Sad", "Sod"),
    (39, "Az-Zumar", "Zumar"), (40, "Ghafir", "G'ofir"),
    (41, "Fussilat", "Fussilat"), (42, "Ash-Shura", "Shuro"),
    (43, "Az-Zukhruf", "Zuxruf"), (44, "Ad-Dukhan", "Duxon"),
    (45, "Al-Jathiya", "Josiya"), (46, "Al-Ahqaf", "Ahqof"),
    (47, "Muhammad", "Muhammad"), (48, "Al-Fath", "Fath"),
    (49, "Al-Hujurat", "Hujurot"), (50, "Qaf", "Qof"),
    (51, "Adh-Dhariyat", "Zoriyot"), (52, "At-Tur", "Tur"),
    (53, "An-Najm", "Najm"), (54, "Al-Qamar", "Qamar"),
    (55, "Ar-Rahman", "Rahmon"), (56, "Al-Waqi'a", "Voqea"),
    (57, "Al-Hadid", "Hadid"), (58, "Al-Mujadila", "Mujodala"),
    (59, "Al-Hashr", "Hashr"), (60, "Al-Mumtahina", "Mumtahana"),
    (61, "As-Saff", "Saff"), (62, "Al-Jumu'a", "Jumua"),
    (63, "Al-Munafiqun", "Munofiqun"), (64, "At-Taghabun", "Tag'obun"),
    (65, "At-Talaq", "Taloq"), (66, "At-Tahrim", "Tahrim"),
    (67, "Al-Mulk", "Mulk"), (68, "Al-Qalam", "Qalam"),
    (69, "Al-Haqqa", "Haqqa"), (70, "Al-Ma'arij", "Maorij"),
    (71, "Nuh", "Nuh"), (72, "Al-Jinn", "Jin"),
    (73, "Al-Muzzammil", "Muzzammil"), (74, "Al-Muddaththir", "Muddassir"),
    (75, "Al-Qiyama", "Qiyoma"), (76, "Al-Insan", "Inson"),
    (77, "Al-Mursalat", "Mursalot"), (78, "An-Naba", "Naba"),
    (79, "An-Nazi'at", "Noziot"), (80, "'Abasa", "Abasa"),
    (81, "At-Takwir", "Takvir"), (82, "Al-Infitar", "Infitor"),
    (83, "Al-Mutaffifin", "Mutaffifin"), (84, "Al-Inshiqaq", "Inshiqoq"),
    (85, "Al-Buruj", "Buruj"), (86, "At-Tariq", "Toriq"),
    (87, "Al-A'la", "A'lo"), (88, "Al-Ghashiya", "G'oshiya"),
    (89, "Al-Fajr", "Fajr"), (90, "Al-Balad", "Balad"),
    (91, "Ash-Shams", "Shams"), (92, "Al-Layl", "Layl"),
    (93, "Ad-Duha", "Zuho"), (94, "Ash-Sharh", "Sharh"),
    (95, "At-Tin", "Tiyn"), (96, "Al-'Alaq", "Alaq"),
    (97, "Al-Qadr", "Qadr"), (98, "Al-Bayyina", "Bayyina"),
    (99, "Az-Zalzala", "Zalzala"), (100, "Al-'Adiyat", "Odiyot"),
    (101, "Al-Qari'a", "Qoria"), (102, "At-Takathur", "Takosur"),
    (103, "Al-'Asr", "Asr"), (104, "Al-Humaza", "Humaza"),
    (105, "Al-Fil", "Fil"), (106, "Quraysh", "Quraysh"),
    (107, "Al-Ma'un", "Moun"), (108, "Al-Kawthar", "Kavsar"),
    (109, "Al-Kafirun", "Kofirun"), (110, "An-Nasr", "Nasr"),
    (111, "Al-Masad", "Masad"), (112, "Al-Ikhlas", "Ixlos"),
    (113, "Al-Falaq", "Falaq"), (114, "An-Nas", "Nos"),
]


def fold(s: str) -> str:
    """Search key: lowercase, and strip everything a learner will not type.

    Apostrophes and hyphens are exactly what people leave out - "Ali 'Imran"
    gets typed "ali imran", "Al-A'la" gets typed "ala". Folding both sides of
    the comparison is what makes the search forgiving without being fuzzy.
    """
    out = []
    for ch in s.lower():
        if ch in "'’`-–—":
            continue
        out.append(ch)
    return "".join(out).strip()


def main() -> int:
    if len(NAMES) != 114:
        print(f"transliteration table has {len(NAMES)} rows, expected 114")
        return 1

    rows = []
    for number, translit, uz in NAMES:
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

    OUT.write_text(json.dumps({"suras": rows}, ensure_ascii=False, indent=1)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT}\n{len(rows)} suras, {total} ayat")
    for r in rows[:3] + rows[-2:]:
        print(f"  {r['number']:>3} {r['name_ar']:<12} {r['translit']:<16} "
              f"{r['uz']:<12} {r['n_ayat']:>3} ayat")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
