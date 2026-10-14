"""Run the installed edshield (pinned release or a candidate checkout) over the
planted views and the control, then score with the sealed experiment's own
scoring functions (experiments/genre_shift/score.py, imported read-only).

    python scripts/run_views.py --out results/llm_view --views llm            # score the LLM-planted view with 0.2.0 (brief §2)
    python scripts/run_views.py --out results/candidate/round_1 --views deterministic llm   # make eval-candidate

Per view it writes <out>/<view>/metrics.json and <out>/<view>/misses.csv (the
same columns as the sealed run, so build_failure_table.py works on either),
<out>/control/metrics.json, <out>/run_meta.json, and <out>/summary.json with
the headline numbers next to the baselines and their deltas. Raw model
outputs go to <out>/raw/ (git-ignored: they carry the licensed dialogue text).
"""
from __future__ import annotations

import argparse
import csv
import importlib.metadata as md
import json
import os
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genre_shift_data as gs  # noqa: E402

ROOT = gs.ROOT
import score  # noqa: E402  (experiments/genre_shift/score.py)

POLICY = "coppa"
TOLERANCE_PP = 0.5
VIEW_DOCS = {"deterministic": lambda ds: gs.planted(ds),
             "llm": lambda ds: gs.read_jsonl(ROOT / "data" / "planted_llm" / f"{ds}.jsonl")}
BASELINE = {"deterministic": gs.GS_RESULTS / "metrics.json", "llm": ROOT / "results" / "llm_view" / "llm" / "metrics.json"}


def write_jsonl(rows: List[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def edshield_identity() -> dict:
    import edshield
    from edshield_evidence import hashes
    src = Path(edshield.__file__).resolve().parent.parent
    commit = os.environ.get("EDSHIELD_EVIDENCE_SUT_COMMIT")
    if not commit and (src / ".git").exists():
        try:
            commit = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
            dirty = subprocess.run(["git", "-C", str(src), "status", "--porcelain", "--", "edshield"], capture_output=True, text=True).stdout.strip()
            if dirty:
                commit += "+dirty"
        except Exception:  # noqa: BLE001
            commit = None
    return {"version": edshield.__version__, "installed_from": str(src), "commit": commit or "pypi 0.2.0 (a568e73)",
            "rules_sha256": hashes.sha256_file(hashes.installed_rules_path())}


def versions() -> Dict[str, str]:
    out = {"python": platform.python_version(), "platform": platform.platform()}
    for pkg in ("edshield", "edshield-evidence", "torch", "transformers", "onnxruntime", "huggingface_hub", "numpy"):
        try:
            out[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            out[pkg] = "not installed"
    return out


def infer(sets, args, out: Path) -> dict:
    from edshield import deid
    from edshield_evidence.runtimes import make_runtime
    meta = {"policy": POLICY, "policy_sha256": deid.policy_fingerprint(POLICY), "runtime": args.runtime,
            "detector": args.detector, "device": args.device, "seed": args.seed, "versions": versions(),
            "edshield": edshield_identity(), "sets": {}, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    rt = make_runtime(args.runtime, args.detector, threads=args.threads, device=args.device,
                      onnx_dir=args.onnx_dir or None, model_dir=args.model_dir or None)
    with rt:
        meta["model_sha256"] = rt.model_sha256
        meta["model_ref"] = rt.model_ref
        for set_name, dataset, docs in sets:
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
                if (i + 1) % 100 == 0:
                    print(f"  {set_name}/{dataset}: {i + 1}/{len(docs)} ({time.time() - t0:.0f}s)", file=sys.stderr)
            write_jsonl(rows, out / "raw" / f"{set_name}__{dataset}.jsonl")
            meta["sets"][f"{set_name}__{dataset}"] = {"docs": len(rows), "seconds": round(time.time() - t0, 1)}
            print(f"{set_name}/{dataset}: {len(rows)} docs in {time.time() - t0:.0f}s", file=sys.stderr)
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def score_view(view: str, out: Path, typo_slots: set, terms: List[str], collision: set) -> dict:
    """metrics.json + misses.csv for one view, with score.py's functions and definitions."""
    term_set = {t.lower() for t in terms}
    metrics: dict = {"view": view, "datasets": {}, "pooled": {}}
    all_gold, misses = [], []
    for ds in gs.DATASETS:
        docs = VIEW_DOCS[view](ds)
        if not docs:
            continue
        rows = {r["doc_id"]: r for r in gs.read_jsonl(out / "raw" / f"{view}__{ds}.jsonl")}
        g = score.score_set(docs, rows)
        turn_of, typo_of = {}, {}
        for d in docs:
            for s in d["meta"]["spans"]:
                turn_of[(d["doc_id"], s["start"])] = s["turn_idx"]
                if "typo" in s:
                    typo_of[(d["doc_id"], s["start"])] = bool(s["typo"])
        for r in g:
            key = (r["doc_id"], r["start"])
            if key in typo_of:
                r["typo"] = typo_of[key] and r["kind"] in ("first", "related")
            else:
                r["typo"] = (r["doc_id"], turn_of.get(key)) in typo_slots and r["kind"] in ("first", "related")
        ents = score.entity_records(docs, rows, terms)
        names = [r for r in g if r["kind"] in score.NAME_KINDS]
        metrics["datasets"][ds] = {
            "n_docs": len(docs), "all_identifiers": score.agg(g), "student_names": score.agg(names),
            "related_names": score.agg([r for r in g if r["kind"] == "related"]),
            "names_by_category": score.breakdown(names, lambda r: r["category"]),
            "base_form_names_by_category": score.breakdown([r for r in names if r["kind"] != "nickname"], lambda r: r["category"]),
            "names_by_position": score.breakdown(names, lambda r: r["kind"]),
            "nicknames_by_form": score.breakdown([r for r in names if r["kind"] == "nickname"], lambda r: score.nickname_form(r["text"])),
            "names_by_speaker": score.breakdown(names, lambda r: r["speaker"]),
            "names_by_case": score.breakdown(names, lambda r: "lowercase" if r["text"][:1].islower() else "capitalised"),
            "by_label": score.breakdown(g, lambda r: r["label"]),
            "precision": score.precision(ents, g), "name_precision": score.name_precision(ents),
        }
        all_gold += g
        by_doc = defaultdict(list)
        for r in g:
            by_doc[r["doc_id"]].append(r)
        for r in g:
            if not r["span_hit"]:
                misses.append(dict(r, reason=score.miss_reason(r, by_doc[r["doc_id"]], collision, term_set)))
    pooled_names = [r for r in all_gold if r["kind"] in score.NAME_KINDS]
    metrics["pooled"] = {
        "datasets": [d for d in gs.DATASETS if d in metrics["datasets"]],
        "all_identifiers": score.agg(all_gold), "student_names": score.agg(pooled_names),
        "related_names": score.agg([r for r in all_gold if r["kind"] == "related"]),
        "names_by_category": score.breakdown(pooled_names, lambda r: r["category"]),
        "base_form_names_by_category": score.breakdown([r for r in pooled_names if r["kind"] != "nickname"], lambda r: r["category"]),
        "names_by_position": score.breakdown(pooled_names, lambda r: r["kind"]),
        "nicknames_by_form": score.breakdown([r for r in pooled_names if r["kind"] == "nickname"], lambda r: score.nickname_form(r["text"])),
        "names_by_speaker": score.breakdown(pooled_names, lambda r: r["speaker"]),
        "names_by_case": score.breakdown(pooled_names, lambda r: "lowercase" if r["text"][:1].islower() else "capitalised"),
        "by_label": score.breakdown(all_gold, lambda r: r["label"]),
        "miss_reasons": dict(Counter(m["reason"] for m in misses)),
        "partial_residuals": sum(1 for r in all_gold if r["partial"]),
    }
    vdir = out / view
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    with (vdir / "misses.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "dataset", "category", "kind", "speaker", "label", "gold_text", "touched_labels",
                    "this_mention_masked", "reason", "context_20_tokens"])
        for m in sorted(misses, key=lambda r: (r["dataset"], r["doc_id"], r["start"])):
            w.writerow([m["doc_id"], m["dataset"], m["category"], m["kind"], m["speaker"], m["label"], m["text"],
                        "+".join(m["touched"]), "yes" if m["mention_hit"] else "no", m["reason"], m["context"]])
    print(f"{view}: gold spans {len(all_gold)}, misses {len(misses)}, reasons {metrics['pooled']['miss_reasons']}")
    return metrics


def score_control(out: Path, terms: List[str]) -> dict:
    res = {}
    for ds in gs.DATASETS:
        docs = gs.control(ds)
        rows = {r["doc_id"]: r for r in gs.read_jsonl(out / "raw" / f"control__{ds}.jsonl")}
        if not rows:
            continue
        ents = score.entity_records(docs, rows, terms)
        res[ds] = score.over_redaction(ents, docs)
    (out / "control").mkdir(parents=True, exist_ok=True)
    (out / "control" / "metrics.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def headline(m: dict) -> dict:
    """The numbers the agent and the comparison read, from a metrics.json."""
    p = m["pooled"]
    return {"all_identifiers": {"n": p["all_identifiers"]["n"], "span_recall": p["all_identifiers"]["span_recall"],
                                "ci": p["all_identifiers"]["span_ci"]},
            "student_names": {"n": p["student_names"]["n"], "span_recall": p["student_names"]["span_recall"],
                              "ci": p["student_names"]["span_ci"]},
            "names_by_category": {c: {"n": v["n"], "span_recall": v["span_recall"], "ci": v["span_ci"]}
                                  for c, v in p["names_by_category"].items()},
            "by_label": {c: {"n": v["n"], "span_recall": v["span_recall"]} for c, v in p["by_label"].items()},
            "per_dataset": {ds: {"all_identifiers": d["all_identifiers"]["span_recall"],
                                 "student_names": d["student_names"]["span_recall"]} for ds, d in m["datasets"].items()}}


def pp(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return None if a is None or b is None else round(100 * (a - b), 2)


def summarize(out: Path, views: List[str], meta: dict, view_metrics: Dict[str, dict], control: dict) -> dict:
    summary = {"out": str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out), "edshield": meta["edshield"],
               "runtime": meta["runtime"], "detector": meta["detector"], "model_sha256": meta.get("model_sha256"),
               "views": {}, "control": {}, "baseline": {"views": {}, "control": {}}, "delta_pp": {"views": {}, "control": {}},
               "definitions": {"span_recall": "gold text no longer occurs whole in the output (residual rule), pooled over comta + mathdial",
                               "control": "acted-on entities per 1,000 whitespace tokens on the untouched dialogues",
                               "delta_pp": "candidate minus baseline, percentage points (recall) or flags per 1,000 tokens (control)"}}
    for v in views:
        summary["views"][v] = headline(view_metrics[v])
        bpath = BASELINE[v]
        if bpath.exists():
            b = json.loads(bpath.read_text(encoding="utf-8"))
            summary["baseline"]["views"][v] = {"source": str(bpath.relative_to(ROOT)), **headline(b)}
            hb, hv = summary["baseline"]["views"][v], summary["views"][v]
            summary["delta_pp"]["views"][v] = {
                "all_identifiers": pp(hv["all_identifiers"]["span_recall"], hb["all_identifiers"]["span_recall"]),
                "student_names": pp(hv["student_names"]["span_recall"], hb["student_names"]["span_recall"]),
                "names_by_category": {c: pp(hv["names_by_category"].get(c, {}).get("span_recall"), hb["names_by_category"].get(c, {}).get("span_recall"))
                                      for c in hb["names_by_category"]},
                "by_label": {c: pp(hv["by_label"].get(c, {}).get("span_recall"), hb["by_label"].get(c, {}).get("span_recall"))
                             for c in hb["by_label"]}}
    for ds, o in control.items():
        summary["control"][ds] = {"flags_per_1000_tokens": o["flags_per_1000_tokens"], "n_flags": o["n_flags"],
                                  "n_tokens": o["n_tokens"], "by_tag": o["by_tag"], "top_terms": o["top_terms"][:10]}
    det_base = BASELINE["deterministic"]
    if det_base.exists() and control:
        b = json.loads(det_base.read_text(encoding="utf-8"))
        for ds in control:
            bo = b["datasets"].get(ds, {}).get("over_redaction")
            if bo:
                summary["baseline"]["control"][ds] = {"source": str(det_base.relative_to(ROOT)), "flags_per_1000_tokens": bo["flags_per_1000_tokens"],
                                                      "by_tag": bo["by_tag"]}
                summary["delta_pp"]["control"][ds] = round(control[ds]["flags_per_1000_tokens"] - bo["flags_per_1000_tokens"], 3)
    d = summary["delta_pp"]["views"].get("deterministic", {}).get("all_identifiers")
    summary["sanity"] = {"tolerance_pp": TOLERANCE_PP, "deterministic_delta_pp": d,
                         "within_tolerance": (abs(d) <= TOLERANCE_PP) if d is not None else None,
                         "note": "round 0 on the unmodified checkout must be within tolerance of the sealed baseline, which was run on a GPU with the python runtime"}
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--views", nargs="+", default=["deterministic", "llm"], choices=["deterministic", "llm"])
    ap.add_argument("--no-control", action="store_true")
    ap.add_argument("--runtime", default="python", choices=["python", "onnx"])
    ap.add_argument("--detector", default="rules+model", choices=["rules+model", "rules"], help="rules: smoke test without a model")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--onnx-dir", default="")
    ap.add_argument("--model-dir", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="debug: first N docs per set")
    ap.add_argument("--score-only", action="store_true", help="reuse <out>/raw")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    views = [v for v in args.views if any(VIEW_DOCS[v](ds) for ds in gs.DATASETS)]
    missing = set(args.views) - set(views)
    if missing:
        print(f"note: no documents for views {sorted(missing)}; skipped", file=sys.stderr)
    if not args.score_only:
        sets = [(v, ds, VIEW_DOCS[v](ds)) for v in views for ds in gs.DATASETS if VIEW_DOCS[v](ds)]
        if not args.no_control:
            sets += [("control", ds, gs.control(ds)) for ds in gs.DATASETS]
        meta = infer(sets, args, out)
    else:
        meta = json.loads((out / "run_meta.json").read_text(encoding="utf-8"))
    terms = score.curricular_terms()
    collision = {l.split()[0] for l in gs.names("name_word_collision")}
    log = gs.plant_log()
    typo_slots = {(p["dialogue_id"], s["turn"]) for d in log["datasets"].values() for p in d.get("plans", []) for s in p["slots"] if s.get("typo")}
    view_metrics = {v: score_view(v, out, typo_slots, terms, collision) for v in views}
    control = {} if args.no_control else score_control(out, terms)
    s = summarize(out, views, meta, view_metrics, control)
    for v in views:
        h = s["views"][v]
        d = s["delta_pp"]["views"].get(v, {})
        print(f"{v}: identifier recall {100 * h['all_identifiers']['span_recall']:.1f}% (n={h['all_identifiers']['n']}), "
              f"delta vs baseline {d.get('all_identifiers')} pp")
    for ds, c in s["control"].items():
        print(f"control/{ds}: {c['flags_per_1000_tokens']:.2f} flags per 1,000 tokens, delta {s['delta_pp']['control'].get(ds)}")
    print(f"summary: {out / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
