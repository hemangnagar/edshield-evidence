"""No output file under evidence/ and no summary.md anywhere may contain a forbidden word."""

from pathlib import Path

from edshield_evidence import FORBIDDEN_REPORT_WORDS

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".md", ".json", ".jsonl", ".txt", ".csv", ".yaml", ".yml", ".html"}


def _files():
    for p in (ROOT / "evidence").rglob("*"):
        if p.is_file() and p.suffix in TEXT_SUFFIXES:
            yield p
    for p in ROOT.rglob("summary.md"):
        if "judge" not in p.parts and ".git" not in p.parts:
            yield p
    for p in (ROOT / "policies").glob("*.json"):
        yield p
    for p in (ROOT / "docs").glob("*.md"):
        yield p


def test_no_forbidden_words_in_outputs():
    offenders = []
    for p in _files():
        low = p.read_text(encoding="utf-8", errors="replace").lower()
        for w in FORBIDDEN_REPORT_WORDS:
            if w in low:
                offenders.append(f"{p.relative_to(ROOT)}: {w}")
    assert not offenders, offenders
