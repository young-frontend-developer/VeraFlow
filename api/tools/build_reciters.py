# -*- coding: utf-8 -*-
"""Verify a shortlist of everyayah reciters and commit the ones that work.

    py -3.13 tools/build_reciters.py

everyayah.com/data/ exposes 72 audio folders, and they are not equivalent:
some are partial, some are duplicates of each other under different spellings,
and the folder name is a filesystem path, not something to show a learner
("Abu_Bakr_Ash-Shaatree_128kbps"). So this does three things the raw listing
cannot:

  1. CURATES. A learner choosing a reciter wants a short list of names they
     recognise, not every mirror on the host. The shortlist below is murattal
     -weighted because this is a practice app - a mujawwad recitation is
     beautiful and a poor model for a beginner copying phrasing.
  2. VERIFIES. Every candidate is probed at four corners of the mushaf,
     including 2:282 (the longest ayah) and 114:6 (the very last). A folder
     that 404s on any of them is dropped, with the reason printed - that is
     precisely the "playback dies on long suras" failure, and it must be found
     here rather than by a learner.
  3. NAMES. Each entry carries a display name and the bitrate, so the UI can
     show "Mishary Alafasy · 128 kbps" instead of a directory.

Re-run it when adding a reciter; it is a few hundred HEAD requests.
"""
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "tilawah" / "content" / "reciters.json"
BASE = "https://everyayah.com/data"

# (folder, display name, style). Style is shown to the learner: murattal is the
# measured recitation you learn from, mujawwad the ornamented one.
# `muallim` folders repeat each phrase for the listener - the best thing on the
# host for a beginner, and worth surfacing first.
CANDIDATES = [
    ("Husary_Muallim_128kbps",         "Mahmud Xusariy (muallim)",   "muallim"),
    ("Minshawy_Teacher_128kbps",       "Muhammad Minshawiy (muallim)", "muallim"),
    ("Alafasy_128kbps",                "Mishari Alafasi",            "murattal"),
    ("Husary_128kbps",                 "Mahmud Xusariy",             "murattal"),
    ("Abdul_Basit_Murattal_64kbps",    "Abdulbosit Abdussamad",      "murattal"),
    ("Minshawy_Murattal_128kbps",      "Muhammad Minshawiy",         "murattal"),
    ("Abdurrahmaan_As-Sudais_192kbps", "Abdurrahmon Sudays",         "murattal"),
    ("Saood_ash-Shuraym_128kbps",      "Saud Shuraym",               "murattal"),
    ("Muhammad_Ayyoub_128kbps",        "Muhammad Ayyub",             "murattal"),
    ("MaherAlMuaiqly128kbps",          "Mohir al-Muayqiliy",         "murattal"),
    ("Abu_Bakr_Ash-Shaatree_128kbps",  "Abu Bakr ash-Shotiriy",      "murattal"),
    ("Nasser_Alqatami_128kbps",        "Nosir al-Qatomiy",           "murattal"),
    ("Yasser_Ad-Dussary_128kbps",      "Yosir ad-Dusariy",           "murattal"),
    ("Hudhaify_128kbps",               "Ali al-Huzayfiy",            "murattal"),
    ("Abdul_Basit_Mujawwad_128kbps",   "Abdulbosit (mujavvad)",      "mujawwad"),
    ("Husary_128kbps_Mujawwad",        "Mahmud Xusariy (mujavvad)",  "mujawwad"),
]

# Four corners plus the pathological one. 2:282 is the longest ayah in the
# Quran and the file most likely to be missing from a partial mirror.
PROBES = [(1, 1), (2, 282), (36, 1), (114, 6)]


def url_for(folder: str, sura: int, aya: int) -> str:
    return f"{BASE}/{folder}/{sura:03d}{aya:03d}.mp3"


def probe(folder: str) -> tuple[str, list[str]]:
    """Returns (folder, [failures]). Empty list means every probe passed."""
    bad = []
    for sura, aya in PROBES:
        url = url_for(folder, sura, aya)
        req = urllib.request.Request(
            url, method="HEAD",
            headers={"User-Agent": "tilawah-build-reciters/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status != 200:
                    bad.append(f"{sura}:{aya} HTTP {r.status}")
                elif int(r.headers.get("Content-Length") or 0) < 1000:
                    # A 200 with a near-empty body is a placeholder, not audio.
                    bad.append(f"{sura}:{aya} empty body")
        except urllib.error.HTTPError as exc:
            bad.append(f"{sura}:{aya} HTTP {exc.code}")
        except Exception as exc:                      # noqa: BLE001
            bad.append(f"{sura}:{aya} {type(exc).__name__}")
    return folder, bad


def main() -> None:
    print(f"probing {len(CANDIDATES)} reciters x {len(PROBES)} ayat\n")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(pool.map(probe, [c[0] for c in CANDIDATES]))

    kept, dropped = [], []
    for folder, name, style in CANDIDATES:
        bad = results[folder]
        if bad:
            dropped.append((folder, bad))
            print(f"  DROP {name:32} {folder}\n         {'; '.join(bad)}")
            continue
        bitrate = next((int(p.replace("kbps", ""))
                        for p in folder.replace("128kbps", "_128kbps").split("_")
                        if p.endswith("kbps") and p[:-4].isdigit()), 0)
        kept.append({"id": folder, "name": name, "style": style,
                     "bitrate_kbps": bitrate})
        print(f"  ok   {name:32} {folder}")

    if not kept:
        raise SystemExit("every candidate failed - is everyayah reachable?")

    # The default must be one that passed, or the app ships pointing at nothing.
    default = "Husary_Muallim_128kbps"
    if default not in {r["id"] for r in kept}:
        default = kept[0]["id"]

    OUT.write_text(json.dumps({
        "_meta": {
            "note": "Generated by tools/build_reciters.py. Do not hand-edit.",
            "base_url": BASE,
            "url_format": "{base_url}/{id}/{sura:03d}{aya:03d}.mp3",
            "probed_ayat": [f"{s}:{a}" for s, a in PROBES],
            "dropped": {f: b for f, b in dropped},
        },
        "default": default,
        "reciters": kept,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"\n{len(kept)} kept, {len(dropped)} dropped -> {OUT}")
    print(f"default: {default}")


if __name__ == "__main__":
    main()
