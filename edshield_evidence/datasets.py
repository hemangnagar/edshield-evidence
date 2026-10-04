"""Dataset loaders. Every loader yields documents as (doc_id, text, gold_spans)
with gold spans as (start, end, label) in character offsets of `text`.

Three roles:
  piilo_holdout  the 680-document split edshield reports on; regression only
                 (it was used to choose the INT8 export). Local path from
                 EDSHIELD_EVIDENCE_PIILO; not in the repo and not in CI.
  k12_hard       edshield's synthetic hard set, generated once from a pinned
                 commit by scripts/gen_k12_hard.sh; regression only, dev-visible.
  sealed:<NAME>  an encrypted acceptance set (see seal.py); one decision each.

Character spans are rebuilt from BIO token labels here; nothing is imported
from edshield's evaluator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from . import SETS_DIR

Span = Tuple[int, int, str]


@dataclass
class Document:
    doc_id: str
    text: str
    gold_spans: List[Span]
    meta: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        rec = {"doc_id": self.doc_id, "text": self.text, "gold_spans": [list(s) for s in self.gold_spans]}
        if self.meta:
            rec["meta"] = self.meta
        return rec

    @classmethod
    def from_record(cls, rec: dict) -> "Document":
        spans = [(int(s), int(e), str(l)) for s, e, l in rec["gold_spans"]]
        return cls(doc_id=str(rec["doc_id"]), text=rec["text"], gold_spans=spans, meta=dict(rec.get("meta", {})))


@dataclass
class Dataset:
    name: str            # piilo_holdout | k12_hard | sealed:A1 | file:<path>
    docs: List[Document]
    path: Optional[Path]
    sha256: Optional[str]
    split: str           # "validation" for regression sets, "test" for sealed sets
    role: str            # regression | acceptance
    sealed: bool = False

    def label_counts(self) -> Counter:
        return Counter(l for d in self.docs for _, _, l in d.gold_spans)


class DatasetError(RuntimeError):
    pass


# --- BIO -> character spans --------------------------------------------------

def rebuild_spans(full_text: str, tokens: Sequence[str], labels: Sequence[str]) -> List[Span]:
    """Rebuild character spans from PIILO-style tokens and BIO labels.

    Tokens are located in `full_text` by walking a cursor, so it does not
    matter whether the separators were single spaces, newlines, or whitespace
    tokens of their own (the competition files have both). A `B-X` starts a
    span; an `I-X` extends the span of the same label that ends at the
    previous token, and otherwise starts a new span (a stray `I-` after `O`).
    """
    if len(tokens) != len(labels):
        raise DatasetError(f"{len(tokens)} tokens but {len(labels)} labels")
    spans: List[List] = []
    cursor = 0
    prev: Optional[Tuple[str, int]] = None  # (label, token index) of the previous token
    for idx, (tok, lab) in enumerate(zip(tokens, labels)):
        start = full_text.find(tok, cursor)
        if start < 0 or full_text[cursor:start].strip():
            raise DatasetError(f"token {idx} {tok!r} not found at offset {cursor}")
        end = start + len(tok)
        if lab == "O" or not lab:
            prev = None
        else:
            tag, _, label = lab.partition("-")
            continues = tag == "I" and prev is not None and prev[0] == label and prev[1] == idx - 1
            if continues:
                spans[-1][1] = end
            else:
                spans.append([start, end, label])
            prev = (label, idx)
        cursor = end
    return [(s, e, l) for s, e, l in spans]


def rebuild_text(tokens: Sequence[str], trailing_whitespace: Sequence[bool]) -> str:
    """Rebuild the document text from tokens and their trailing-whitespace flags.

    edshield's validation.json (training/prepare_piilo.py) carries no
    `full_text`; a token followed by whitespace gets one space, as in
    edshield's evaluator, so both score the same text.
    """
    if len(tokens) != len(trailing_whitespace):
        raise DatasetError(f"{len(tokens)} tokens but {len(trailing_whitespace)} trailing_whitespace flags")
    return "".join(tok + (" " if ws else "") for tok, ws in zip(tokens, trailing_whitespace))


def piilo_documents(records: Iterable[dict], prefix: str = "") -> List[Document]:
    docs = []
    for rec in records:
        text = rec.get("full_text")
        if text is None:
            text = rebuild_text(rec["tokens"], rec["trailing_whitespace"])
        spans = rebuild_spans(text, rec["tokens"], rec["labels"])
        meta = {k: rec[k] for k in ("genre", "style") if k in rec}
        docs.append(Document(doc_id=f"{prefix}{rec['document']}", text=text, gold_spans=spans, meta=meta))
    return docs


# --- Files ---------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(text: str) -> List[Document]:
    docs = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            docs.append(Document.from_record(json.loads(line)))
    return docs


def load_jsonl(path: Path) -> List[Document]:
    return read_jsonl(Path(path).read_text(encoding="utf-8"))


def write_jsonl(docs: Iterable[Document], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for d in docs:
            fh.write(json.dumps(d.to_record(), ensure_ascii=False) + "\n")


def _piilo_file(where: Path) -> Path:
    if where.is_file():
        return where
    if not where.is_dir():
        raise DatasetError(f"EDSHIELD_EVIDENCE_PIILO={where} is neither a file nor a directory")
    for name in ("validation.json", "holdout.json", "piilo_holdout.json"):
        if (where / name).exists():
            return where / name
    candidates = sorted(where.glob("*.json"))
    if len(candidates) == 1:
        return candidates[0]
    raise DatasetError(
        f"cannot pick the holdout file in {where}: expected validation.json or exactly one *.json"
    )


def load_piilo_holdout(path: Optional[str] = None) -> Dataset:
    where = path or os.environ.get("EDSHIELD_EVIDENCE_PIILO")
    if not where:
        raise DatasetError(
            "PIILO holdout is not available: set EDSHIELD_EVIDENCE_PIILO to the directory holding "
            "validation.json (the 680-document split edshield reports on)"
        )
    file = _piilo_file(Path(where))
    records = json.loads(file.read_text(encoding="utf-8"))
    if isinstance(records, dict):
        records = records.get("data") or records.get("documents") or list(records.values())
    docs = piilo_documents(records, prefix="piilo-")
    return Dataset("piilo_holdout", docs, file, sha256_file(file), split="validation", role="regression")


K12_HARD_PATH = SETS_DIR / "k12_hard_seed1.jsonl"


def load_k12_hard(path: Optional[str] = None) -> Dataset:
    file = Path(path) if path else K12_HARD_PATH
    if not file.exists():
        raise DatasetError(f"{file} is missing; run scripts/gen_k12_hard.sh to generate it from the pinned edshield commit")
    docs = load_jsonl(file)
    return Dataset("k12_hard", docs, file, sha256_file(file), split="validation", role="regression")


def load_sealed(name: str, key: Optional[bytes] = None) -> Dataset:
    from . import seal  # local import: cryptography is only needed for sealed sets

    text, manifest = seal.unseal_text(name, key=key)
    docs = read_jsonl(text)
    role = manifest.get("role", "acceptance")
    enc = SETS_DIR / f"{name}.jsonl.enc"
    return Dataset(
        f"sealed:{name}", docs, enc, manifest["sha256"],
        split="test" if role == "acceptance" else "validation", role=role, sealed=True,
    )


def load_file(path: str) -> Dataset:
    file = Path(path)
    docs = load_jsonl(file)
    return Dataset(f"file:{file.name}", docs, file, sha256_file(file), split="validation", role="regression")


def load_dataset(spec: str) -> Dataset:
    """`piilo_holdout`, `k12_hard`, `sealed:A1`, or `file:<path>` / a path to a jsonl file."""
    if spec == "piilo_holdout":
        return load_piilo_holdout()
    if spec == "k12_hard":
        return load_k12_hard()
    if spec.startswith("sealed:"):
        return load_sealed(spec.split(":", 1)[1])
    if spec.startswith("file:"):
        return load_file(spec.split(":", 1)[1])
    if spec.endswith(".jsonl") and Path(spec).exists():
        return load_file(spec)
    raise DatasetError(f"unknown dataset {spec!r}")


# --- CLI: convert a PIILO-format JSON into the repo's jsonl ----------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m edshield_evidence.datasets")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert-piilo", help="PIILO-format JSON -> (doc_id, text, gold_spans) jsonl + .sha256")
    c.add_argument("input")
    c.add_argument("--out", required=True)
    c.add_argument("--prefix", default="")
    s = sub.add_parser("stats", help="document and label counts of a dataset spec")
    s.add_argument("dataset")
    a = ap.parse_args(argv)
    if a.cmd == "convert-piilo":
        records = json.loads(Path(a.input).read_text(encoding="utf-8"))
        docs = piilo_documents(records, prefix=a.prefix)
        out = Path(a.out)
        write_jsonl(docs, out)
        digest = sha256_file(out)
        out.with_suffix(".sha256").write_text(f"{digest}  {out.name}\n", encoding="utf-8")
        counts = Counter(l for d in docs for _, _, l in d.gold_spans)
        print(f"wrote {len(docs)} documents, {sum(counts.values())} gold spans to {out} (sha256 {digest})")
        for label, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"  {label:16s} {n}")
        return 0
    ds = load_dataset(a.dataset)
    print(f"{ds.name}: {len(ds.docs)} documents, sha256 {ds.sha256}, split {ds.split}, role {ds.role}")
    for label, n in sorted(ds.label_counts().items(), key=lambda kv: -kv[1]):
        print(f"  {label:16s} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
