"""The product is called VeraFlow, and it stays called VeraFlow.

The old spelling has come back twice — a rename lands, a branch that predates
it gets merged, and the old name reappears in the API title and in user-facing
copy. Nobody catches it in review because it reads as ordinary product text.

`web/lint-brand.mjs` guards the same thing from the npm side and covers both
trees. This test exists so the guard also runs for anyone who touches the API
without ever running a frontend build, which is most backend work.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tilawah.api.main import app

BANNED = re.compile(r"veyraflow", re.IGNORECASE)
MARKER = "veraflow-lint-ignore"

ROOT = Path(__file__).resolve().parents[2]
# Both trees, plus the root README — the first thing anyone reads, and the file
# that carried the old name longest.
TREES = (ROOT / "web", ROOT / "api")
LOOSE_FILES = (ROOT / "README.md",)

SKIP_DIRS = {
    "node_modules", "dist", "build", ".git", ".venv", "__pycache__",
    ".gradle", ".idea", "e2e-shots", "screens", "shots", "debug_audio",
}
# Generated, not written: `npx cap sync` rebuilds these from capacitor.config.ts
# and web/dist, both of which are scanned. The two guards name what they forbid.
SKIP_RELATIVE = {
    "web/android/app/src/main/assets",
    "web/lint-brand.mjs",
    "web/src/lib/storage-migrations.ts",
    "api/tests/test_brand_name.py",
}
TEXT_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".json", ".html", ".css",
    ".md", ".xml", ".gradle", ".java", ".kt", ".yml", ".yaml", ".txt",
    ".properties", ".env", ".example",
}


def _sources() -> list[Path]:
    out: list[Path] = []
    for tree in TREES:
        for path in tree.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            rel = path.relative_to(ROOT).as_posix()
            if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
                continue
            if any(rel == s or rel.startswith(s + "/") for s in SKIP_RELATIVE):
                continue
            out.append(path)
    out.extend(p for p in LOOSE_FILES if p.is_file())
    return out


def test_api_title_is_veraflow() -> None:
    assert app.title == "VeraFlow API"


def test_old_product_name_appears_nowhere() -> None:
    """Any case variant, anywhere under web/ or api/, fails the build."""
    hits: list[str] = []
    for path in _sources():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not BANNED.search(text):
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            if MARKER in line:
                continue
            if BANNED.search(line):
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{n}: {line.strip()}")

    if hits:
        pytest.fail(
            "The product is called VeraFlow. Found the old name in:\n  "
            + "\n  ".join(hits)
        )
