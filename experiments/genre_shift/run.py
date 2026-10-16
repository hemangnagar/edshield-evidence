"""Run the pinned edshield 0.2.0 release (rules + model, python runtime) over
the planted, control and PIILO sets and store what it returned.

    python run.py --sets planted control piilo --device cuda

Output: results/raw/<set>__<dataset>.jsonl, one row per document:
    {doc_id, output, entities: [{label, text, start, end, confidence, source}], seconds}
and results/run_meta.json (versions, model revision + sha256, policy, timings).
results/raw/ is not committed: the PIILO rows hold the holdout essays.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"
POLICY = "coppa"
MODEL = "piilo_deberta_small"


def read_jsonl(path: Path) -> List[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def write_jsonl(rows: List[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def versions() -> Dict[str, str]:
    import importlib.metadata as md
    out = {"python": platform.python_version(), "platform": platform.platform()}
    for pkg in ("edshield", "edshield-evidence", "torch", "transformers", "huggingface_hub", "numpy", "matplotlib"):
        try:
            out[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            out[pkg] = "not installed"
    try:
        import torch
        out["cuda"] = torch.version.cuda or "none"
        out["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none"
    except Exception:  # noqa: BLE001
        pass
    return out


def model_revision(repo_id: str) -> str:
    from huggingface_hub import scan_cache_dir
    for repo in scan_cache_dir().repos:
        if repo.repo_id == repo_id:
            revs = sorted(repo.revisions, key=lambda r: r.last_modified)
            return revs[-1].commit_hash
    return "unknown"


def sets_to_run(names: List[str]) -> List[tuple]:
    """(set, dataset, docs) triples."""
    out = []
    for s in names:
        if s in ("planted", "control"):
            for p in sorted((DATA / s).glob("*.jsonl")):
                out.append((s, p.stem, read_jsonl(p)))
        elif s == "piilo":
            from edshield_evidence.datasets import load_piilo_holdout
            ds = load_piilo_holdout()
            out.append(("piilo", "piilo_holdout", [d.to_record() for d in ds.docs]))
            out[-1][2].append({"_sha256": ds.sha256})
        else:
            raise SystemExit(f"unknown set {s}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=["planted", "control", "piilo"])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="debug: first N docs per set")
    args = ap.parse_args(argv)

    from edshield import deid
    from edshield_evidence.runtimes import PythonRuntime
    from edshield import ner

    meta = {"policy": POLICY, "policy_sha256": deid.policy_fingerprint(POLICY), "model": MODEL,
            "model_id": ner.resolve_model_id(MODEL), "device": args.device, "seed": args.seed,
            "versions": versions(), "sets": {}, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    meta["model_revision"] = model_revision(meta["model_id"])
    triples = sets_to_run(args.sets)

    with PythonRuntime(detector="rules+model", model=MODEL, device=args.device) as rt:
        meta["model_sha256"] = rt.model_sha256
        for set_name, dataset, docs in triples:
            extra = [d for d in docs if "_sha256" in d]
            docs = [d for d in docs if "_sha256" not in d]
            if args.limit:
                docs = docs[: args.limit]
            rows, t0 = [], time.time()
            for i, d in enumerate(docs):
                t = time.time()
                r = rt.deidentify(d["text"], policy=POLICY, seed=args.seed)
                rows.append({"doc_id": d["doc_id"], "output": r.deidentified_text,
                             "entities": [{"label": e.label, "text": e.text, "start": int(e.start), "end": int(e.end),
                                           "confidence": float(e.confidence), "source": e.source} for e in r.entities],
                             "seconds": round(time.time() - t, 3)})
                if (i + 1) % 50 == 0:
                    print(f"  {set_name}/{dataset}: {i + 1}/{len(docs)} ({time.time() - t0:.0f}s)", file=sys.stderr)
            write_jsonl(rows, RESULTS / "raw" / f"{set_name}__{dataset}.jsonl")
            meta["sets"][f"{set_name}__{dataset}"] = {"docs": len(rows), "seconds": round(time.time() - t0, 1),
                                                     **({"input_sha256": extra[0]["_sha256"]} if extra else {})}
            print(f"{set_name}/{dataset}: {len(rows)} docs in {time.time() - t0:.0f}s", file=sys.stderr)
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
