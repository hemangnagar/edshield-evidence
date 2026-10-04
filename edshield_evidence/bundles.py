"""Bundle files on disk: reading, and splitting the ones GitHub will not take.

A step 1 bundle (PIILO holdout, four runs, a word view of 428k tokens) is
about 140 MB; GitHub refuses files over 100 MB. After the judge has read a
whole bundle, `split` stores any bundle over the limit as `<name>.partNN`
pieces and removes the whole file; `load_bundle` and `join` put them back
together. Byte concatenation, nothing else, so the sha256 of the joined file
equals the original's.

    python -m edshield_evidence.bundles split evidence/reports/<id>
    python -m edshield_evidence.bundles join  evidence/reports/<id>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import List

SPLIT_OVER = 95 * 1024 * 1024   # GitHub's limit is 100 MB
PART_SIZE = 45 * 1024 * 1024


def parts_of(path: Path) -> List[Path]:
    return sorted(path.parent.glob(path.name + ".part[0-9][0-9]"))


def read_bundle_bytes(path: Path) -> bytes:
    path = Path(path)
    if path.exists():
        return path.read_bytes()
    parts = parts_of(path)
    if not parts:
        raise FileNotFoundError(f"{path} (and no {path.name}.partNN pieces)")
    return b"".join(p.read_bytes() for p in parts)


def load_bundle(path: Path) -> dict:
    return json.loads(read_bundle_bytes(path).decode("utf-8"))


def split(path: Path, over: int = SPLIT_OVER, part_size: int = PART_SIZE) -> List[Path]:
    """Split `path` into parts when it is larger than `over`; returns the parts (empty if left whole)."""
    path = Path(path)
    if not path.exists() or path.stat().st_size <= over:
        return []
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    out = []
    for i in range(0, len(data), part_size):
        p = path.with_name(f"{path.name}.part{len(out):02d}")
        p.write_bytes(data[i:i + part_size])
        out.append(p)
    path.with_name(path.name + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    path.unlink()
    return out


def join(path: Path, remove_parts: bool = False) -> Path:
    path = Path(path)
    parts = parts_of(path)
    if path.exists() or not parts:
        return path
    data = b"".join(p.read_bytes() for p in parts)
    sha_file = path.with_name(path.name + ".sha256")
    if sha_file.exists():
        expected = sha_file.read_text(encoding="utf-8").split()[0]
        got = hashlib.sha256(data).hexdigest()
        if got != expected:
            raise ValueError(f"{path.name}: joined sha256 {got} != recorded {expected}")
    path.write_bytes(data)
    if remove_parts:
        for p in parts:
            p.unlink()
    return path


def split_directory(report_dir: Path, over: int = SPLIT_OVER) -> List[Path]:
    done = []
    for b in sorted(Path(report_dir).glob("*.bundle.json")):
        done += split(b, over)
    return done


def join_directory(report_dir: Path, remove_parts: bool = False) -> List[Path]:
    names = sorted({p.name.rsplit(".part", 1)[0] for p in Path(report_dir).glob("*.bundle.json.part[0-9][0-9]")})
    return [join(Path(report_dir) / n, remove_parts) for n in names]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m edshield_evidence.bundles", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split", help="split every bundle over the size limit in a report directory")
    s.add_argument("report_dir")
    s.add_argument("--over-mb", type=int, default=SPLIT_OVER // (1024 * 1024))
    j = sub.add_parser("join", help="rebuild whole bundles from their parts")
    j.add_argument("report_dir")
    j.add_argument("--remove-parts", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "split":
        for p in split_directory(Path(a.report_dir), a.over_mb * 1024 * 1024):
            print(f"wrote {p} ({p.stat().st_size} bytes)")
    else:
        for p in join_directory(Path(a.report_dir), a.remove_parts):
            print(f"joined {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
