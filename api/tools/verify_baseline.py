# -*- coding: utf-8 -*-
"""Does the Alembic baseline actually reproduce the live schema?

api/tilawah.db was built by SQLModel's create_all() and then patched in place by
db/__init__.py:_add_missing_columns(). The Alembic baseline was generated from
the MODELS. Those two paths can disagree, and a baseline that quietly disagrees
with production is worse than no baseline at all - every later autogenerate
inherits the drift.

So this builds a fresh database from the baseline revision alone, reads both
schemas back out of sqlite, and diffs them column by column.

    py -3.13 tools/verify_baseline.py

Exits non-zero on any difference that is not on the known-divergence list.

KNOWN DIVERGENCE: the six columns added by _add_missing_columns() carry server
defaults in the live table (ALTER TABLE ADD COLUMN requires one for NOT NULL)
and none in the model. Recorded here rather than silently tolerated.
"""
from __future__ import annotations

import os
import subprocess
import sqlite3
import sys
import tempfile
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
LIVE_DB = API_DIR / "tilawah.db"

# column -> reason. Server-default mismatches we accept and why.
KNOWN_DEFAULT_DIVERGENCE = {
    ("user", "audio_consented"),
    ("user", "consent_seen"),
    ("attempt", "start_word"),
    ("attempt", "num_words"),
    ("attempt", "include_bismillah"),
    ("attempt", "analysable"),
}


def schema_of(db: Path) -> dict[str, dict[str, dict]]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out: dict[str, dict[str, dict]] = {}
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'")]
    for t in sorted(tables):
        cols = {}
        for cid, name, ctype, notnull, dflt, pk in con.execute(
                f"PRAGMA table_info('{t}')"):
            cols[name] = {"type": ctype.upper(), "notnull": bool(notnull),
                          "default": dflt, "pk": bool(pk)}
        idx = {}
        for r in con.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='index' "
                "AND tbl_name=? AND sql IS NOT NULL", (t,)):
            idx[r[0]] = r[1]
        fks = sorted(
            (f[2], f[3], f[4]) for f in con.execute(f"PRAGMA foreign_key_list('{t}')")
        )
        out[t] = {"columns": cols, "indexes": idx, "foreign_keys": fks}
    con.close()
    return out


def build_fresh(target: Path) -> None:
    env = dict(os.environ, TILAWAH_DATABASE_URL=f"sqlite:///{target}")
    r = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                       cwd=API_DIR, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr, sep="\n")
        raise SystemExit("alembic upgrade head failed on a fresh database")


def main() -> int:
    if not LIVE_DB.exists():
        raise SystemExit(f"no live database at {LIVE_DB}")

    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "fresh.db"
        build_fresh(fresh)
        want = schema_of(fresh)      # what the baseline produces
        have = schema_of(LIVE_DB)    # what is actually on disk

        problems: list[str] = []
        accepted: list[str] = []

        for t in sorted(set(want) | set(have)):
            if t not in have:
                problems.append(f"table {t}: in baseline, MISSING from live db")
                continue
            if t not in want:
                problems.append(f"table {t}: in live db, MISSING from baseline")
                continue

            wc, hc = want[t]["columns"], have[t]["columns"]
            for c in sorted(set(wc) | set(hc)):
                if c not in hc:
                    problems.append(f"{t}.{c}: in baseline, missing from live db")
                elif c not in wc:
                    problems.append(f"{t}.{c}: in live db, missing from baseline")
                    continue
                else:
                    for field in ("type", "notnull", "pk"):
                        if wc[c][field] != hc[c][field]:
                            problems.append(
                                f"{t}.{c}.{field}: baseline={wc[c][field]!r} "
                                f"live={hc[c][field]!r}")
                    if wc[c]["default"] != hc[c]["default"]:
                        msg = (f"{t}.{c}.default: baseline={wc[c]['default']!r} "
                               f"live={hc[c]['default']!r}")
                        (accepted if (t, c) in KNOWN_DEFAULT_DIVERGENCE
                         else problems).append(msg)

            if want[t]["foreign_keys"] != have[t]["foreign_keys"]:
                problems.append(
                    f"{t} foreign keys: baseline={want[t]['foreign_keys']} "
                    f"live={have[t]['foreign_keys']}")

            wi, hi = set(want[t]["indexes"]), set(have[t]["indexes"])
            for name in sorted(wi ^ hi):
                side = "baseline" if name in wi else "live db"
                problems.append(f"{t} index {name}: only in {side}")

        print(f"tables compared : {sorted(set(want) & set(have))}")
        print(f"live db         : {LIVE_DB}")
        if accepted:
            print(f"\nknown divergences ({len(accepted)}), accepted:")
            for a in accepted:
                print("  ~", a)
        if problems:
            print(f"\nUNEXPECTED DIFFERENCES ({len(problems)}):")
            for p in problems:
                print("  !", p)
            return 1
        print("\nOK - the baseline reproduces the live schema.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
