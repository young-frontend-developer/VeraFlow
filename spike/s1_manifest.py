# -*- coding: utf-8 -*-
"""
s1_manifest.py - build the 150-clip recording plan.

10 short ayat x 15 takes = 150 clips:
   5 CORRECT takes per ayah  (50 total) -> measures FALSE POSITIVE rate
  10 single-error takes      (100 total) -> measures RECALL per error type

Every error is induced on purpose, so ground truth is known by construction.
No expert annotator is needed at this stage.

Error codes are chosen for Uzbek/Russian L1 interference - the substitutions
those speakers actually make - not a generic Tajweed checklist.

Run:  python s1_manifest.py   ->  manifest.csv
"""
import csv
import sys

from quran_transcript import Aya, MoshafAttributes, quran_phonetizer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Hafs, madd lengths at 4 counts. Must match s3/s4 exactly.
MOSHAF = MoshafAttributes(
    rewaya="hafs",
    madd_monfasel_len=4,
    madd_mottasel_len=4,
    madd_mottasel_waqf=4,
    madd_aared_len=4,
)

N_CORRECT = 5

# ---------------------------------------------------------------------------
# Error code -> (category, plain-English description of the induced mistake)
# category is what s4 groups by when reporting recall.
# ---------------------------------------------------------------------------
ERRORS = {
    "SUB_AYN_HAMZA":  ("substitution", "Read ع as a plain hamza ء (the classic Slavic/Turkic collapse)"),
    "SUB_SAD_SEEN":   ("substitution", "Read ص as plain س (Russian с) - lose the emphasis entirely"),
    "SUB_TA_PLAIN":   ("substitution", "Read ط as plain ت (Russian т)"),
    "SUB_QAF_KAF":    ("substitution", "Read ق as ك (Russian к)"),
    "SUB_DHAL_ZAY":   ("substitution", "Read ذ as ز (Russian з)"),
    "SUB_THA_SEEN":   ("substitution", "Read ث as س (Russian с)"),
    "SUB_HA_KHA":     ("substitution", "Read ح as خ / Russian х"),
    "SUB_WAW_V":      ("substitution", "Read و as English/Russian v (в) instead of w"),
    "TAFKHIM_LOSS":   ("sifa", "Keep the correct letter but read it light (muraqqaq) - no tongue raising"),
    "GHONNA_DROP":    ("sifa", "Doubled nun/mim with NO nasal hum - clip it short, no ghunnah"),
    "QALQALA_DROP":   ("sifa", "End the letter softly with no bounce - no qalqalah"),
    "MADD_SHORT":     ("duration", "Hold the madd only 2 counts instead of 4"),
    "MADD_LONG":      ("duration", "Over-stretch the madd to ~6 counts instead of 4"),
    "DEL_WORD":       ("structural", "Skip a word entirely"),
    "INS_WORD":       ("structural", "Repeat a word (stutter it twice)"),
}

# ---------------------------------------------------------------------------
# The 10 ayat. All verified to contain the targeted phenomena.
# Ordered shortest-first so recording warms up gently.
# Each entry: (sura, aya, nickname, [(error_code, target, count), ...])  sum(count) == 10
# ---------------------------------------------------------------------------
PLAN = [
    (103, 1, "al-Asr 1", [
        ("SUB_AYN_HAMZA", "ع in وَٱلْعَصْرِ", 2),
        ("SUB_SAD_SEEN",  "ص in وَٱلْعَصْرِ", 2),
        ("TAFKHIM_LOSS",  "ص in وَٱلْعَصْرِ", 2),
        ("SUB_WAW_V",     "و at the start", 2),
        ("DEL_WORD",      "drop the وَ and start at ٱلْعَصْرِ", 1),
        ("INS_WORD",      "say وَٱلْعَصْرِ ٱلْعَصْرِ", 1),
    ]),
    (112, 2, "al-Ikhlas 2", [
        ("SUB_SAD_SEEN",  "ص in ٱلصَّمَدُ", 3),
        ("TAFKHIM_LOSS",  "ص in ٱلصَّمَدُ", 3),
        ("QALQALA_DROP",  "final د of ٱلصَّمَدْ (stopping)", 3),
        ("DEL_WORD",      "drop ٱللَّهُ, say only ٱلصَّمَدُ", 1),
    ]),
    (112, 3, "al-Ikhlas 3", [
        ("QALQALA_DROP",  "the د of يَلِدْ and/or يُولَدْ", 4),
        ("MADD_SHORT",    "the وو madd in يُولَدْ", 2),
        ("MADD_LONG",     "the وو madd in يُولَدْ", 2),
        ("DEL_WORD",      "skip وَلَمْ", 1),
        ("INS_WORD",      "repeat لَمْ twice", 1),
    ]),
    (113, 1, "al-Falaq 1", [
        ("SUB_QAF_KAF",   "ق of قُلْ and/or ٱلْفَلَقِ", 3),
        ("SUB_AYN_HAMZA", "ع in أَعُوذُ", 2),
        ("SUB_DHAL_ZAY",  "ذ in أَعُوذُ", 2),
        ("QALQALA_DROP",  "final ق of ٱلْفَلَقْ (stopping)", 2),
        ("MADD_SHORT",    "the وو madd in أَعُوذُ", 1),
    ]),
    (114, 1, "an-Nas 1", [
        ("GHONNA_DROP",   "the doubled نّ in ٱلنَّاسِ", 4),
        ("MADD_SHORT",    "the ا madd in ٱلنَّاسِ (stopping)", 2),
        ("SUB_AYN_HAMZA", "ع in أَعُوذُ", 2),
        ("SUB_DHAL_ZAY",  "ذ in أَعُوذُ", 1),
        ("SUB_QAF_KAF",   "ق of قُلْ", 1),
    ]),
    (108, 3, "al-Kawthar 3", [
        ("GHONNA_DROP",   "the doubled نّ in إِنَّ", 4),
        ("QALQALA_DROP",  "the ب in ٱلْأَبْتَرُ", 3),
        ("MADD_SHORT",    "the ا madd in شَانِئَكَ", 1),
        ("DEL_WORD",      "skip هُوَ", 1),
        ("INS_WORD",      "repeat إِنَّ twice", 1),
    ]),
    (108, 1, "al-Kawthar 1", [
        ("SUB_AYN_HAMZA", "ع in أَعْطَيْنَٰكَ", 2),
        ("SUB_TA_PLAIN",  "ط in أَعْطَيْنَٰكَ", 2),
        ("GHONNA_DROP",   "the doubled نّ in إِنَّا", 2),
        ("MADD_SHORT",    "the madd bridging إِنَّآ -> أَعْطَيْنَٰكَ", 2),
        ("TAFKHIM_LOSS",  "ط in أَعْطَيْنَٰكَ (keep ط but read it light)", 1),
        ("SUB_THA_SEEN",  "ث in ٱلْكَوْثَرَ", 1),
    ]),
    (109, 1, "al-Kafirun 1", [
        ("MADD_SHORT",    "the long madd in يَٰٓأَيُّهَا - give it 2 counts", 4),
        ("MADD_LONG",     "over-stretch يَٰٓأَيُّهَا to ~6 counts", 2),
        ("MADD_SHORT",    "the final وو of ٱلْكَٰفِرُونْ (stopping)", 2),
        ("SUB_QAF_KAF",   "ق of قُلْ", 2),
    ]),
    (110, 1, "an-Nasr 1", [
        ("MADD_SHORT",    "the obligatory madd in جَآءَ - give it 2 counts", 3),
        ("SUB_SAD_SEEN",  "ص in نَصْرُ", 2),
        ("TAFKHIM_LOSS",  "ص in نَصْرُ", 2),
        ("SUB_HA_KHA",    "ح in وَٱلْفَتْحُ", 2),
        ("SUB_DHAL_ZAY",  "ذ in إِذَا", 1),
    ]),
    (1, 6, "al-Fatiha 6", [
        ("SUB_SAD_SEEN",  "ص in ٱلصِّرَٰطَ", 2),
        ("SUB_TA_PLAIN",  "ط in ٱلصِّرَٰطَ", 2),
        ("TAFKHIM_LOSS",  "ص in ٱلصِّرَٰطَ", 2),
        ("SUB_QAF_KAF",   "ق in ٱلْمُسْتَقِيمَ", 2),
        ("MADD_SHORT",    "the يي madd in ٱلْمُسْتَقِيمْ (stopping)", 2),
    ]),
]


def main():
    rows = []
    print("Building recording plan...\n")

    for sura, aya, nick, errs in PLAN:
        g = Aya(sura, aya).get()
        uth = g.uthmani
        ph = quran_phonetizer(uth, MOSHAF, remove_spaces=True).phonemes

        n_err = sum(c for _, _, c in errs)
        if n_err != 10:
            raise SystemExit(f"BUG: {nick} has {n_err} error takes, expected 10")

        print(f"  {sura}:{aya}  {nick}")
        print(f"     {uth}")
        print(f"     {ph}  ({len(ph)} phonemes)")

        take = 0
        for i in range(N_CORRECT):
            take += 1
            rows.append({
                "clip_id": f"{sura:03d}_{aya:03d}_t{take:02d}",
                "sura": sura, "aya": aya, "nickname": nick,
                "uthmani": uth, "expected_phonemes": ph,
                "error_code": "OK", "error_category": "none",
                "target": "-",
                "instruction": f"Recite CORRECTLY. Vary your volume/pace slightly from your other correct takes (take {i + 1} of {N_CORRECT}).",
                "has_error": 0,
            })

        for code, target, count in errs:
            cat, desc = ERRORS[code]
            for _ in range(count):
                take += 1
                rows.append({
                    "clip_id": f"{sura:03d}_{aya:03d}_t{take:02d}",
                    "sura": sura, "aya": aya, "nickname": nick,
                    "uthmani": uth, "expected_phonemes": ph,
                    "error_code": code, "error_category": cat,
                    "target": target,
                    "instruction": f"{desc}. TARGET: {target}. Everything else must be CORRECT.",
                    "has_error": 1,
                })

    fields = ["clip_id", "sura", "aya", "nickname", "uthmani", "expected_phonemes",
              "error_code", "error_category", "target", "instruction", "has_error"]
    with open("manifest.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    n_ok = sum(1 for r in rows if r["has_error"] == 0)
    print(f"\nWrote manifest.csv: {len(rows)} clips "
          f"({n_ok} correct / {len(rows) - n_ok} with a single induced error)")

    print("\nError takes by category:")
    cats = {}
    for r in rows:
        if r["has_error"]:
            cats[r["error_category"]] = cats.get(r["error_category"], 0) + 1
    for c, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"  {c:14s} {n:3d}")

    print("\nNext:  python s2_record.py")


if __name__ == "__main__":
    main()
