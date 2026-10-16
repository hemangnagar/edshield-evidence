"""Read-only access to the sealed genre-shift run (experiments/genre_shift/).

The planted and control documents carry licensed dialogue text and are
git-ignored; `plant.py` is deterministic per dialogue id, so they are rebuilt
here from the pinned raw files when missing, and the rebuilt plant log is
checked byte-for-byte against the committed one before anything uses them.
Nothing in this module writes outside experiments/genre_shift/data/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
GS = ROOT / "experiments" / "genre_shift"
GS_DATA = GS / "data"
GS_RESULTS = GS / "results"
SEED = 20261014
DATASETS = ("comta", "mathdial")
LABELS = {"first": "NAME_STUDENT", "later": "NAME_STUDENT", "nickname": "NAME_STUDENT", "related": "NAME_RELATED",
          "school": "SCHOOL", "email": "EMAIL", "username": "USERNAME", "phone": "PHONE_NUM"}
CATEGORIES = ("anglo_common", "non_anglo", "name_word_collision", "nicknames_and_variants")

if str(GS) not in sys.path:
    sys.path.insert(0, str(GS))


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def names(category: str) -> List[str]:
    return [l.strip() for l in (GS / "names" / f"{category}.txt").read_text(encoding="utf-8").splitlines() if l.strip()]


def plant_log() -> dict:
    return json.loads((GS_DATA / "plant_log.json").read_text(encoding="utf-8"))


def ensure_raw() -> None:
    missing = [d for d in DATASETS if not (GS_DATA / "raw" / d).is_dir()]
    if missing:
        subprocess.run([sys.executable, str(GS / "download.py"), *missing], check=True, cwd=GS)


def ensure_planted() -> None:
    """Rebuild data/planted and data/control with the sealed seed if absent, and
    verify the plant log equals the committed one (determinism check)."""
    if all((GS_DATA / "planted" / f"{d}.jsonl").exists() and (GS_DATA / "control" / f"{d}.jsonl").exists() for d in DATASETS):
        return
    ensure_raw()
    committed = (GS_DATA / "plant_log.json").read_bytes()
    subprocess.run([sys.executable, str(GS / "plant.py"), "--seed", str(SEED)], check=True, cwd=GS)
    rebuilt = (GS_DATA / "plant_log.json").read_bytes()
    if json.loads(rebuilt) != json.loads(committed):
        (GS_DATA / "plant_log.json").write_bytes(committed)
        raise SystemExit("rebuilt plant_log.json differs from the committed one; the planter is not reproducing the sealed run")
    (GS_DATA / "plant_log.json").write_bytes(committed)  # keep the committed bytes exactly


def planted(dataset: str) -> List[dict]:
    ensure_planted()
    return read_jsonl(GS_DATA / "planted" / f"{dataset}.jsonl")


def control(dataset: str) -> List[dict]:
    ensure_planted()
    return read_jsonl(GS_DATA / "control" / f"{dataset}.jsonl")


def dialogues() -> Dict[str, list]:
    """Normalized dialogues (list of turns) per dataset, from the sealed loaders."""
    ensure_raw()
    import loaders  # experiments/genre_shift/loaders.py
    return {k: v for k, v in loaders.load_all().items() if v}


def baseline_metrics() -> dict:
    return json.loads((GS_RESULTS / "metrics.json").read_text(encoding="utf-8"))


SPEAKER_TAG = {"student": "Student", "tutor": "Tutor"}


def turn_ranges(doc_text: str, speakers: List[str]) -> List[tuple]:
    """(start, end) character ranges of each turn's line in a joined document.
    Turns may contain newlines, so lines are merged until the next line starts
    with the tag the dialogue's speaker sequence expects."""
    lines = doc_text.split("\n")
    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1
    ranges, k = [], 0
    cur_start = None
    for idx, ln in enumerate(lines):
        tag = SPEAKER_TAG[speakers[k]] + ": " if k < len(speakers) else None
        if tag is not None and ln.startswith(tag) and (cur_start is None or k < len(speakers)):
            if cur_start is not None:
                ranges.append((cur_start, starts[idx] - 1))
            cur_start = starts[idx]
            k += 1
    if cur_start is not None:
        ranges.append((cur_start, len(doc_text)))
    if len(ranges) != len(speakers):
        raise ValueError(f"found {len(ranges)} turns, expected {len(speakers)}")
    return ranges


def speakers_of(doc: dict, dialogue: list) -> List[str]:
    return [str(t["speaker"]) for t in dialogue]
