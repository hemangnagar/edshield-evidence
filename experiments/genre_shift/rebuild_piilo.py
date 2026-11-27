"""Rebuild the 680-essay PIILO holdout when the local validation.json is absent.

    python rebuild_piilo.py        # writes data/raw/piilo_rebuilt/validation.json

The holdout itself is not in the repo, but the committed baseline bundle
(evidence/reports/2026-10-04-6c0f163/01_piilo_holdout_model_python.bundle.json)
names every held-out essay (`piilo-<document>`) and, in its `word` view, every
whitespace token with a flag for "overlaps a gold span". The essays come from
the public PIILO corpus (CC BY 4.0) at data/raw/piilo_public/train.json; the
680 ids are selected and written in edshield's validation.json shape (tokens,
trailing_whitespace, labels; no full_text). The rebuild is accepted only if,
for every essay, the whitespace-token count and the set of gold tokens equal
what the bundle recorded for the original file.

The rebuilt file is not byte-identical to the original (sha256 bc5d0958...),
only document-, token- and gold-identical; run.py records its own sha256.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from edshield_evidence.datasets import piilo_documents

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BUNDLE_PARTS = sorted((REPO / "evidence" / "reports" / "2026-10-04-6c0f163").glob(
    "01_piilo_holdout_model_python.bundle.json.part*"))
PUBLIC = HERE / "data" / "raw" / "piilo_public" / "train.json"
OUT = HERE / "data" / "raw" / "piilo_rebuilt" / "validation.json"
TOKEN = re.compile(r"\S+")


def bundle_word_view() -> dict:
    """document id -> {word index: y_true} from the first run of the `word` view."""
    bundle = json.loads(b"".join(p.read_bytes() for p in BUNDLE_PARTS))
    out = defaultdict(dict)
    for row in bundle["views"]["word"]["runs"][0]["rows"]:
        doc, w = row["sample_id"][len("piilo-"):].split(":w")
        out[doc][int(w)] = int(row["y_true"])
    return out


def main() -> int:
    if not PUBLIC.exists():
        print(f"missing {PUBLIC}; run download.py piilo_public", file=sys.stderr)
        return 1
    want = bundle_word_view()
    records = [r for r in json.loads(PUBLIC.read_text(encoding="utf-8")) if str(r["document"]) in want]
    records.sort(key=lambda r: int(r["document"]))
    records = [{k: r[k] for k in ("document", "tokens", "trailing_whitespace", "labels")} for r in records]
    if len(records) != len(want):
        print(f"found {len(records)} of {len(want)} holdout essays in the public corpus", file=sys.stderr)
        return 1
    bad = []
    for doc in piilo_documents(records, prefix="piilo-"):
        ref = want[doc.doc_id[len("piilo-"):]]
        toks = [(m.start(), m.end()) for m in TOKEN.finditer(doc.text)]
        gold = {i for i, (a, b) in enumerate(toks) if any(s < b and a < e for s, e, _ in doc.gold_spans)}
        if len(toks) != len(ref) or gold != {i for i, y in ref.items() if y}:
            bad.append(doc.doc_id)
    if bad:
        print(f"{len(bad)} essays differ from the bundle's word view, e.g. {bad[:5]}; not written", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    n_tok = sum(len(v) for v in want.values())
    print(f"{len(records)} essays, {n_tok} tokens, {sum(sum(v.values()) for v in want.values())} gold tokens: "
          f"all match the bundle. Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
