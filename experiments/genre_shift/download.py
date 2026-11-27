"""Fetch the raw dialogue sets into data/raw/<name>/, each pinned to a commit
or revision. Raw data is never committed (see .gitignore); data/SOURCES.md
records provenance and licenses, and the sha256 of every file fetched is
written to data/raw/<name>/SHA256SUMS.

    python download.py            # all sets; a blocked set is reported, not fatal
    python download.py comta      # one set
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent / "data" / "raw"

COMTA_COMMIT = "fbbeff86b5c1a689161b8f6092a6be7d0532a6dd"
MATHDIAL_COMMIT = "b06c020a0a1f57a87577fec33e657b63e7eb476e"
STUDYCHAT_REV = "24d7987d9fbb30d9da12acc53455a10f1cdd2d7f"

GITHUB = {
    "comta": [
        ("CoMTA_dataset.json",
         f"https://raw.githubusercontent.com/Khan/tutoring-accuracy-dataset/{COMTA_COMMIT}/CoMTA_dataset.json"),
        ("LICENSE",
         f"https://raw.githubusercontent.com/Khan/tutoring-accuracy-dataset/{COMTA_COMMIT}/LICENSE"),
    ],
    "mathdial": [
        ("test.jsonl",
         f"https://raw.githubusercontent.com/eth-nlped/mathdial/{MATHDIAL_COMMIT}/data/test.jsonl"),
    ],
}
STUDYCHAT = ("wmcnicho/StudyChat", STUDYCHAT_REV, ["data.jsonl", "LICENSE"])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _record(d: Path, fname: str) -> None:
    digest = sha256(d / fname)
    sums = d / "SHA256SUMS"
    lines = [l for l in sums.read_text().splitlines() if not l.endswith("  " + fname)] if sums.exists() else []
    lines.append(f"{digest}  {fname}")
    sums.write_text("\n".join(lines) + "\n")
    print(f"[{d.name}] {fname} sha256 {digest}")


def fetch_github(name: str) -> None:
    d = RAW / name
    d.mkdir(parents=True, exist_ok=True)
    for fname, url in GITHUB[name]:
        dest = d / fname
        if not dest.exists():
            print(f"[{name}] downloading {url}")
            with urllib.request.urlopen(url, timeout=120) as r, dest.open("wb") as f:
                f.write(r.read())
        _record(d, fname)


def fetch_studychat() -> bool:
    d = RAW / "studychat"
    d.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.errors import GatedRepoError
    except ImportError:
        print("[studychat] huggingface_hub not installed; skipped")
        return False
    repo, rev, files = STUDYCHAT
    try:
        for f in files:
            hf_hub_download(repo, f, repo_type="dataset", revision=rev, local_dir=str(d))
            _record(d, f)
        return True
    except GatedRepoError:
        print(f"[studychat] BLOCKED: gated dataset and this Hugging Face account is not on its access list. "
              f"Request access at https://huggingface.co/datasets/{repo}, then rerun.")
        return False


def main(argv):
    want = argv or ["comta", "mathdial", "studychat", "tscc"]
    for name in want:
        if name in GITHUB:
            fetch_github(name)
        elif name == "studychat":
            fetch_studychat()
        elif name == "tscc":
            if not (RAW / "tscc").is_dir():
                print("[tscc] arrives by request form; drop the files into data/raw/tscc/ (see loaders.load_tscc)")
        else:
            raise SystemExit(f"unknown dataset {name}")


if __name__ == "__main__":
    main(sys.argv[1:])
