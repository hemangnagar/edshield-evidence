"""Dataset + configuration -> model-evidence contract 2.0 bundle.

    python -m edshield_evidence.export_views \
      --dataset piilo_holdout|k12_hard|sealed:A1 \
      --policy coppa|ferpa|research \
      --detector rules|rules+model \
      --runtime python|onnx|python,onnx \
      --model piilo-deberta-v3-small-v2 \
      --seeds 0 1 2 --repeat-seed 0 \
      --out bundle.json

Views: `identifier`, `document`, `word`, and `type:<LABEL>` for every label
present in the dataset's gold. Runs: one per seed (`seed-N`), plus an exact
same-seed rerun (`seed-N-repeat`) when --repeat-seed is given, so the judge
has a comparable group for reproducibility. With two runtimes the bundle is
a parity bundle: runs `python` and `onnx` without a seed field.

A diagnostics file (<out>.diagnostics.json) carries what the judge does not
read: partial residuals, label confusion, the over-redaction sample. For a
sealed set it holds counts only, never text, unless --include-text is given.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from . import EDSHIELD_COMMIT, EXPORTER_VERSION, JUDGE_TAG, hashes
from .datasets import Dataset, load_dataset
from .residual import DocScore, score_document
from .runtimes import DEFAULT_MODEL, BaseRuntime, make_runtime

CONTRACT = "2.0"
RESIDUAL_EXAMPLES = 200

VIEW_DESCRIPTIONS = {
    "identifier": "One row per gold identifier span (cluster = document). y_true = 1; y_pred = 1 when the "
                  "normalized gold string no longer occurs as a whole word in the final de-identified text.",
    "document": "One row per document with at least one gold span. y_true = 1; y_pred = 1 when no gold span "
                "survives whole in that document's output.",
    "word": "One row per whitespace token of the original (cluster = document). y_true = 1 if the token overlaps "
            "a gold span; y_pred = 1 if the token was replaced or removed in the output. fpr is over-redaction.",
}


@dataclass
class RunSpec:
    id: str
    seed: Optional[int]
    runtime: BaseRuntime


@dataclass
class RunResult:
    spec: RunSpec
    scores: List[DocScore]
    model_sha256: str
    seconds: float


def run_one(spec: RunSpec, dataset: Dataset, policy: str, o_threshold: Optional[float] = None,
            limit: Optional[int] = None, progress=None) -> RunResult:
    docs = dataset.docs[:limit] if limit else dataset.docs
    scores: List[DocScore] = []
    t0 = time.time()
    with spec.runtime as rt:
        for k, doc in enumerate(docs):
            res = rt.deidentify(doc.text, policy=policy, seed=spec.seed, o_threshold=o_threshold)
            scores.append(score_document(doc.doc_id, doc.text, doc.gold_spans, res))
            if progress and (k + 1) % 50 == 0:
                progress(f"  {spec.id}: {k + 1}/{len(docs)} documents")
        model_sha = rt.model_sha256
    return RunResult(spec=spec, scores=scores, model_sha256=model_sha, seconds=time.time() - t0)


def rows_for(scores: Sequence[DocScore]) -> Dict[str, List[dict]]:
    views: Dict[str, List[dict]] = defaultdict(list)
    for s in scores:
        for i in s.identifiers:
            row = {"sample_id": f"{s.doc_id}:{i.index}", "cluster_id": s.doc_id, "y_true": 1, "y_pred": i.y_pred}
            views["identifier"].append(row)
            views[f"type:{i.label}"].append(dict(row))
        if s.has_gold:
            views["document"].append({"sample_id": s.doc_id, "y_true": 1, "y_pred": int(s.document_handled)})
        for w in s.words:
            views["word"].append({"sample_id": f"{s.doc_id}:w{w.index}", "cluster_id": s.doc_id,
                                  "y_true": w.y_true, "y_pred": w.y_pred})
    return dict(views)


def diagnostics_for(result: RunResult, include_text: bool) -> dict:
    by_label: Dict[str, Counter] = defaultdict(Counter)
    confusion: Dict[str, Counter] = defaultdict(Counter)
    word = Counter()
    residual_examples, partial_examples, over = [], [], []
    alignment_failures = leaks = 0
    for s in result.scores:
        alignment_failures += 0 if s.aligned else 1
        leaks += s.self_reported_leaks
        for i in s.identifiers:
            c = by_label[i.label]
            c["n"] += 1
            if i.full_residual:
                c["full_residual"] += 1
                if include_text and len(residual_examples) < RESIDUAL_EXAMPLES:
                    residual_examples.append({"doc_id": s.doc_id, "label": i.label, "text": i.text, "touched": i.touched})
            elif i.partial:
                c["partial_residual"] += 1
                if include_text and len(partial_examples) < RESIDUAL_EXAMPLES:
                    partial_examples.append({"doc_id": s.doc_id, "label": i.label, "text": i.text,
                                             "surviving_token": i.partial, "touched": i.touched})
            for t in (i.touched or ["none"]):
                confusion[i.label][t] += 1
        for w in s.words:
            word[{(1, 1): "tp", (0, 1): "fp", (1, 0): "fn", (0, 0): "tn"}[(w.y_true, w.y_pred)]] += 1
        if include_text:
            over.extend(s.over_redactions[: max(0, 50 - len(over))])
    n_gold = sum(c["n"] for c in by_label.values())
    full = sum(c["full_residual"] for c in by_label.values())
    partial = sum(c["partial_residual"] for c in by_label.values())
    out = {
        "id": result.spec.id,
        "seed": result.spec.seed,
        "runtime": result.spec.runtime.name,
        "model": result.spec.runtime.model_ref,
        "model_sha256": result.model_sha256,
        "seconds": round(result.seconds, 2),
        "n_documents": len(result.scores),
        "n_documents_with_gold": sum(1 for s in result.scores if s.has_gold),
        "n_gold": n_gold,
        "full_residuals": full,
        "partial_residuals": partial,
        "identifier_recall": (n_gold - full) / n_gold if n_gold else None,
        "by_label": {l: {"n": c["n"], "full_residual": c["full_residual"], "partial_residual": c["partial_residual"],
                         "recall": (c["n"] - c["full_residual"]) / c["n"]}
                     for l, c in sorted(by_label.items())},
        "label_confusion": {g: dict(sorted(p.items())) for g, p in sorted(confusion.items())},
        "word": {"n": sum(word.values()), **{k: word[k] for k in ("tp", "fp", "fn", "tn")},
                 "fpr": word["fp"] / (word["fp"] + word["tn"]) if (word["fp"] + word["tn"]) else None},
        "alignment_failures": alignment_failures,
        "edshield_self_reported_leaks": leaks,
        "text_included": include_text,
    }
    if include_text:
        out["residual_examples"] = residual_examples
        out["partial_examples"] = partial_examples
        out["over_redaction_sample"] = over
    return out


def build_bundle(dataset: Dataset, results: Sequence[RunResult], *, policy: str, detector: str,
                 runtime_names: Sequence[str], o_threshold: Optional[float], model_ref: str,
                 include_text: bool, limit: Optional[int] = None) -> tuple:
    runtime_label = ",".join(runtime_names)
    recipe = hashes.recipe(policy, detector, runtime_label, o_threshold)
    env = hashes.environment()
    data_sha = dataset.sha256 or hashes.sha256_json([d.to_record() for d in dataset.docs])

    views: Dict[str, dict] = {}
    for r in results:
        for name, rows in rows_for(r.scores).items():
            run = {"id": r.spec.id, "metadata": {"model_sha256": r.model_sha256}, "rows": rows}
            if r.spec.seed is not None:
                run["seed"] = r.spec.seed
            if name not in views:
                desc = VIEW_DESCRIPTIONS.get(name) or f"Identifier rows restricted to gold label {name.split(':', 1)[-1]}."
                views[name] = {"description": desc, "runs": []}
            views[name]["runs"].append(run)
    views = dict(sorted(views.items(), key=lambda kv: (kv[0].startswith("type:"), kv[0])))

    parity = len(runtime_names) > 1
    notes = (
        f"edshield {recipe['edshield_version']} (source commit {EDSHIELD_COMMIT[:7]}), policy {policy}, "
        f"detector {detector}, runtime {runtime_label}. Rows are residuals measured on the final output of "
        f"edshield.deidentify(verify=False); a surrogate equal to a gold string counts as a residual. "
        + ("Parity bundle: runs are runtimes, not seeds; stability and reproducibility are insufficient by construction, "
           "read the per-view agreement and the gates on the selected run. " if parity else "")
        + f"Exporter edshield-evidence {EXPORTER_VERSION}; judge model-evidence {JUDGE_TAG}."
    )
    bundle = {
        "contract": CONTRACT,
        "name": f"edshield {recipe['edshield_version']} · {dataset.name} · {policy} · {detector} · {runtime_label}",
        "split": dataset.split,
        "metadata": {
            "data_sha256": data_sha,
            "recipe_sha256": hashes.sha256_json(recipe),
            "environment_sha256": hashes.sha256_json(env),
            "notes": notes,
            "dataset": dataset.name,
            "dataset_file": dataset.path.name if dataset.path else None,
            "dataset_role": dataset.role,
            "dataset_sealed": dataset.sealed,
            "n_documents": len(results[0].scores) if results else 0,
            "n_documents_total": len(dataset.docs),
            "limit": limit,
            "label_counts": dict(sorted(dataset.label_counts().items())),
            "policy": policy,
            "policy_fingerprint": recipe["policy_fingerprint"],
            "detector": detector,
            "runtime": runtime_label,
            "parity": parity,
            "model": model_ref,
            "o_threshold": o_threshold,
            "edshield_version": recipe["edshield_version"],
            "edshield_commit": EDSHIELD_COMMIT,
            "exporter_version": EXPORTER_VERSION,
            "judge_tag": JUDGE_TAG,
            "recipe": recipe,
            "environment": env,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        },
        "views": views,
    }
    diagnostics = {
        "bundle": bundle["name"],
        "dataset": dataset.name,
        "data_sha256": data_sha,
        "policy": policy,
        "policy_fingerprint": recipe["policy_fingerprint"],
        "detector": detector,
        "runtime": runtime_label,
        "text_included": include_text,
        "runs": [diagnostics_for(r, include_text) for r in results],
    }
    return bundle, diagnostics


def default_diagnostics_path(out: Path) -> Path:
    """<key>.bundle.json -> <key>.diagnostics.json; otherwise <name>.diagnostics.json."""
    name = out.name
    for suffix in (".bundle.json", ".json"):
        if name.endswith(suffix):
            return out.with_name(name[: -len(suffix)] + ".diagnostics.json")
    return out.with_name(name + ".diagnostics.json")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="python -m edshield_evidence.export_views", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True, help="piilo_holdout | k12_hard | sealed:A1 | file:<path.jsonl>")
    ap.add_argument("--policy", default="coppa", help="coppa | ferpa | research (or a path to a policy YAML)")
    ap.add_argument("--detector", default="rules+model", choices=["rules", "rules+model"])
    ap.add_argument("--runtime", default="python", help="python | onnx | python,onnx (parity)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="model short name, Hub id or alias (piilo-deberta-v3-small-v2)")
    ap.add_argument("--model-dir", default=None, help="local checkpoint directory (overrides --model)")
    ap.add_argument("--model-dir-pattern", default=None,
                    help="per-seed checkpoint directory, e.g. models/ckpt-seed{seed}; overrides --model-dir")
    ap.add_argument("--onnx-dir", default=None, help="directory with onnx/model_quantized.onnx, tokenizer and config")
    ap.add_argument("--onnx-file", default=None, help="explicit .onnx file (tokenizer read from its grandparent)")
    ap.add_argument("--quant", default="int8", choices=["int8", "fp32"])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--repeat-seed", type=int, default=None,
                    help="also run this seed a second time as <seed>-repeat (reproducibility group)")
    ap.add_argument("--o-threshold", type=float, default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None, help="first N documents only (development)")
    ap.add_argument("--include-text", action="store_true", help="put residual text into the diagnostics of a sealed set")
    ap.add_argument("--out", required=True)
    ap.add_argument("--diagnostics", default=None, help="default: <out minus .json>.diagnostics.json")
    ap.add_argument("--quiet", action="store_true")
    return ap.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    a = parse_args(argv)
    say = (lambda *_: None) if a.quiet else (lambda m: print(m, file=sys.stderr, flush=True))
    runtimes = [r.strip() for r in a.runtime.split(",") if r.strip()]
    parity = len(runtimes) > 1
    if parity and a.detector != "rules+model":
        print("parity runs need --detector rules+model", file=sys.stderr)
        return 2

    dataset = load_dataset(a.dataset)
    say(f"{dataset.name}: {len(dataset.docs)} documents, sha256 {dataset.sha256}")

    def rt(name: str, seed: Optional[int]) -> BaseRuntime:
        model_dir = a.model_dir
        if a.model_dir_pattern and seed is not None:
            model_dir = a.model_dir_pattern.format(seed=seed)
        return make_runtime(name, a.detector, model=a.model, model_dir=model_dir, onnx_dir=a.onnx_dir,
                            onnx_file=a.onnx_file, quant=a.quant, threads=a.threads, device=a.device)

    specs: List[RunSpec] = []
    if parity:
        for name in runtimes:
            specs.append(RunSpec(id=name, seed=None, runtime=rt(name, None)))
    else:
        for s in a.seeds:
            specs.append(RunSpec(id=f"seed-{s}", seed=s, runtime=rt(runtimes[0], s)))
        if a.repeat_seed is not None:
            specs.append(RunSpec(id=f"seed-{a.repeat_seed}-repeat", seed=a.repeat_seed, runtime=rt(runtimes[0], a.repeat_seed)))

    results: List[RunResult] = []
    for spec in specs:
        say(f"run {spec.id}: runtime {spec.runtime.name}, model {spec.runtime.model_ref}")
        r = run_one(spec, dataset, a.policy, a.o_threshold, limit=a.limit, progress=say)
        d = diagnostics_for(r, include_text=False)
        say(f"  {spec.id}: {d['full_residuals']} of {d['n_gold']} identifiers survive whole "
            f"(recall {d['identifier_recall']:.4f}), word fpr {d['word']['fpr']:.4f}, {r.seconds:.1f}s"
            if d["n_gold"] and d["word"]["fpr"] is not None else f"  {spec.id}: done in {r.seconds:.1f}s")
        results.append(r)

    model_ref = specs[0].runtime.model_ref if specs else a.model
    include_text = a.include_text or not dataset.sealed
    bundle, diagnostics = build_bundle(
        dataset, results, policy=a.policy, detector=a.detector, runtime_names=runtimes,
        o_threshold=a.o_threshold, model_ref=model_ref, include_text=include_text, limit=a.limit,
    )
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Compact: the word view alone is ~90k rows over four runs. The judge hashes canonical JSON, not bytes.
    out.write_text(json.dumps(bundle, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    diag_path = Path(a.diagnostics) if a.diagnostics else default_diagnostics_path(out)
    diag_path.write_text(json.dumps(diagnostics, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    say(f"wrote {out} ({len(bundle['views'])} views) and {diag_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
