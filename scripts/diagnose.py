"""Component B: a cause label for every miss, from the Batch API (brief §3).

    python scripts/diagnose.py build                       # requests only
    python scripts/diagnose.py dry-run [--n 1]
    python scripts/diagnose.py submit [--views deterministic llm]   # main batch + the 50-row agreement batch
    python scripts/diagnose.py collect [--run DIR]         # -> results/diagnosis/causes.jsonl + summary.md
    python scripts/diagnose.py status [--run DIR]

One request per row of results/<view>/failure_table.jsonl. The rubric is
prompts/diagnose_system.md and is not edited after the first submission
(its sha256 is recorded in the run directory and in causes.jsonl).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_api as api  # noqa: E402

ROOT = api.ROOT
RUBRIC_PATH = ROOT / "prompts" / "diagnose_system.md"
RUBRIC = RUBRIC_PATH.read_text(encoding="utf-8")
OUT = ROOT / "results" / "diagnosis"
MODEL = api.MODELS["diagnose"]
MAX_TOKENS = 4000
CAUSES = ["REGISTER", "NAME_WORD_COLLISION", "NON_ANGLO_NAME", "SCHEMA_GAP", "TOKENIZATION", "CONTEXT_CUE_MISSING",
          "AMBIGUOUS", "OTHER"]
FIX_CLASSES = ["RULE", "GAZETTEER", "MODEL", "LABEL_SCHEMA", "NONE"]
AGREEMENT_N = 50

SCHEMA = {
    "type": "object",
    "properties": {
        "primary": {"type": "string", "enum": CAUSES},
        "secondary": {"type": ["string", "null"], "enum": CAUSES + [None]},
        "confidence": {"type": "number"},
        "fix_class": {"type": "string", "enum": FIX_CLASSES},
        "evidence": {"type": "string"},
        "note": {"type": ["string", "null"]},
    },
    "required": ["primary", "secondary", "confidence", "fix_class", "evidence", "note"],
    "additionalProperties": False,
}


def failure_rows(view: str) -> List[dict]:
    p = ROOT / "results" / ("deterministic" if view == "deterministic" else "llm_view") / "failure_table.jsonl"
    rows = api.read_jsonl(p)
    if not rows:
        print(f"note: no failure table for view {view} ({p})", file=sys.stderr)
    return rows


def reordered_rubric() -> str:
    """The same rubric with the taxonomy bullets in reverse order (agreement check)."""
    lines = RUBRIC.split("\n")
    idx = [i for i, l in enumerate(lines) if any(l.startswith(f"- {c}:") for c in CAUSES)]
    block = [lines[i] for i in idx]
    for i, l in zip(idx, reversed(block)):
        lines[i] = l
    return "\n".join(lines)


def make_request(row: dict, alt: bool = False) -> dict:
    system = api.cached_system([reordered_rubric() if alt else RUBRIC])
    user = {
        "dataset": row["dataset"], "name_category": row["category"], "label": row["label"],
        "planted_form": row["form"], "speaker_of_turn": row["speaker"], "gold_span": row["gold_text"],
        "detector_output": {"labels_touching_span": row["touched_labels"], "this_mention_masked": row["this_mention_masked"],
                            "same_string_masked_elsewhere_in_document": row["same_string_masked_elsewhere"],
                            "other_mentions_of_this_name_in_document": row["n_other_mentions_of_name"]},
        "window": row["window"],
    }
    cid = f"diag-{row['view'][:3]}-{row['dataset']}-{row['doc_id']}-{row['span_idx']}" + ("-alt" if alt else "")
    return {"custom_id": cid, "view": row["view"], "dataset": row["dataset"], "doc_id": row["doc_id"],
            "span_idx": row["span_idx"], "alt": alt,
            "params": {"model": MODEL, "max_tokens": MAX_TOKENS, "system": system,
                       "output_config": {"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
                       "messages": [{"role": "user", "content": json.dumps(user, ensure_ascii=False)}]}}


def build_requests(views: List[str]) -> Tuple[List[dict], List[dict]]:
    main, rows_all = [], []
    for v in views:
        rows = failure_rows(v)
        rows_all += rows
        main += [make_request(r) for r in rows]
    rng = random.Random(20261014)
    sample = rng.sample(rows_all, min(AGREEMENT_N, len(rows_all)))
    agree = [make_request(r, alt=True) for r in sample]
    return main, agree


def validate(resp: dict) -> List[str]:
    errs = []
    if resp.get("primary") not in CAUSES:
        errs.append("bad primary")
    if resp.get("secondary") not in CAUSES + [None]:
        errs.append("bad secondary")
    if resp.get("fix_class") not in FIX_CLASSES:
        errs.append("bad fix_class")
    c = resp.get("confidence")
    if not isinstance(c, (int, float)) or not 0 <= c <= 1:
        errs.append("bad confidence")
    if not isinstance(resp.get("evidence"), str) or len(resp["evidence"].split()) > 30:
        errs.append("evidence missing or over 25 words")
    if resp.get("primary") == "OTHER" and not resp.get("note"):
        errs.append("OTHER without note")
    return errs


def save_built(main, agree, run_dir: Path) -> None:
    api.write_jsonl(main, run_dir / "diag_requests_built.jsonl")
    api.write_jsonl(agree, run_dir / "diag_agreement_requests_built.jsonl")
    (run_dir / "rubric.sha256").write_text(api.sha256_text(RUBRIC) + "\n", encoding="utf-8")
    print(f"built {len(main)} diagnosis requests + {len(agree)} agreement requests; rubric sha256 {api.sha256_text(RUBRIC)[:12]}")


def cmd_build(args) -> int:
    run_dir = Path(args.run) if args.run else api.new_run_dir("diagnose")
    main, agree = build_requests(args.views)
    save_built(main, agree, run_dir)
    return 0


def cmd_dry_run(args) -> int:
    run_dir = Path(args.run) if args.run else api.new_run_dir("diagnose-dryrun")
    main, agree = build_requests(args.views)
    save_built(main, agree, run_dir)
    client = api.make_client()
    for req in random.Random(0).sample(main, args.n):
        row = api.dry_run(client, req, run_dir, req["custom_id"])
        resp = api.extract_json(row["text"])
        print(json.dumps(resp, ensure_ascii=False), "validation:", validate(resp) or "OK")
    return 0


def cmd_submit(args) -> int:
    run_dir = Path(args.run) if args.run else api.new_run_dir("diagnose")
    main, agree = build_requests(args.views)
    if not main:
        raise SystemExit("nothing to submit")
    save_built(main, agree, run_dir)
    client = api.make_client()
    api.submit_batch(client, main, run_dir, "diag")
    api.submit_batch(client, agree, run_dir, "diag-agreement")
    return 0


def cmd_collect(args) -> int:
    run_dir = Path(args.run) if args.run else api.latest_run_dir("diagnose")
    client = api.make_client()
    main = {r["custom_id"]: r for r in api.read_jsonl(run_dir / "diag_requests_built.jsonl")}
    agree = {r["custom_id"]: r for r in api.read_jsonl(run_dir / "diag_agreement_requests_built.jsonl")}
    rubric_sha = (run_dir / "rubric.sha256").read_text().strip()
    if rubric_sha != api.sha256_text(RUBRIC):
        raise SystemExit("prompts/diagnose_system.md changed since submission; the rubric is frozen after the first submit")
    causes: List[dict] = []
    bad: List[dict] = []
    for name, reqs in (("diag", main), ("diag-agreement", agree)):
        if not (run_dir / f"batch_{name}.json").exists():
            continue
        bid = api.batch_meta(run_dir, name)["id"]
        api.wait_batch(client, bid, poll_seconds=args.poll)
        results = api.collect_batch(client, bid, run_dir, name, MODEL)
        for cid, row in results.items():
            req = reqs[cid]
            rec = {"custom_id": cid, "view": req["view"], "dataset": req["dataset"], "doc_id": req["doc_id"],
                   "span_idx": req["span_idx"], "alt_order": req["alt"], "rubric_sha256": rubric_sha, "model": MODEL}
            if row["type"] != "succeeded":
                bad.append({**rec, "error": row.get("error") or row["type"]})
                continue
            try:
                resp = api.extract_json(row["text"])
                errs = validate(resp)
            except Exception as exc:  # noqa: BLE001
                resp, errs = {}, [f"unparseable: {exc}"]
            if errs:
                bad.append({**rec, "error": errs, "raw": row["text"][:500]})
                continue
            causes.append({**rec, **resp, "usage": row["usage"], "cost_usd": row["cost_usd"]})
    OUT.mkdir(parents=True, exist_ok=True)
    api.write_jsonl(causes, OUT / "causes.jsonl")
    api.write_jsonl(bad, run_dir / "diag_rejects.jsonl")
    print(f"{len(causes)} cause rows, {len(bad)} rejected -> {OUT / 'causes.jsonl'}")
    write_summary(causes, bad)
    return 0


def write_summary(causes: List[dict], bad: List[dict]) -> None:
    main = [c for c in causes if not c["alt_order"]]
    alt = {(c["view"], c["doc_id"], c["span_idx"]): c for c in causes if c["alt_order"]}
    rows_by_view: Dict[str, List[dict]] = defaultdict(list)
    for c in main:
        rows_by_view[c["view"]].append(c)
    ft: Dict[Tuple[str, str, int], dict] = {}
    for v in ("deterministic", "llm"):
        for r in failure_rows(v):
            ft[(v, r["doc_id"], r["span_idx"])] = r
    L = ["# Miss diagnosis (Batch API, %s)" % MODEL, "",
         f"Rubric `prompts/diagnose_system.md` sha256 `{api.sha256_text(RUBRIC)[:16]}…`; {len(main)} rows diagnosed, "
         f"{len(bad)} rejected (see the run directory). Every number below is read from `results/diagnosis/causes.jsonl`.", ""]
    for v, rows in rows_by_view.items():
        n = len(rows)
        L += [f"## View: {v} ({n} misses)", "", "| primary cause | n | share | mean confidence |", "|---|---|---|---|"]
        for cause, k in Counter(r["primary"] for r in rows).most_common():
            conf = sum(r["confidence"] for r in rows if r["primary"] == cause) / k
            L.append(f"| {cause} | {k} | {100 * k / n:.1f}% | {conf:.2f} |")
        L += ["", "| fix class | n | share |", "|---|---|---|"]
        for fc, k in Counter(r["fix_class"] for r in rows).most_common():
            L.append(f"| {fc} | {k} | {100 * k / n:.1f}% |")
        L += ["", "Primary cause by name category:", "", "| category | " + " | ".join(CAUSES) + " |", "|---|" + "---|" * len(CAUSES)]
        by_cat: Dict[str, Counter] = defaultdict(Counter)
        for r in rows:
            by_cat[ft.get((v, r["doc_id"], r["span_idx"]), {}).get("category", "?")][r["primary"]] += 1
        for cat, cnt in sorted(by_cat.items()):
            L.append(f"| {cat} | " + " | ".join(str(cnt.get(c, 0)) for c in CAUSES) + " |")
        L.append("")
    if alt:
        pairs = [(c, alt[(c["view"], c["doc_id"], c["span_idx"])]) for c in main if (c["view"], c["doc_id"], c["span_idx"]) in alt]
        agree_p = sum(a["primary"] == b["primary"] for a, b in pairs)
        agree_f = sum(a["fix_class"] == b["fix_class"] for a, b in pairs)
        L += ["## Consistency check", "",
              f"{len(pairs)} rows were submitted twice, the second time with the taxonomy listed in reverse order. "
              f"Primary-cause agreement: **{agree_p}/{len(pairs)} = {100 * agree_p / max(1, len(pairs)):.0f}%**; "
              f"fix-class agreement: {agree_f}/{len(pairs)} = {100 * agree_f / max(1, len(pairs)):.0f}%.", ""]
    top = sorted([r for r in main if r["fix_class"] in ("RULE", "GAZETTEER")], key=lambda r: -r["confidence"])[:10]
    L += ["## Ten highest-confidence RULE / GAZETTEER misses", "", "| view | dataset | doc | span | cause | fix | conf | evidence |", "|---|---|---|---|---|---|---|---|"]
    for r in top:
        f = ft.get((r["view"], r["doc_id"], r["span_idx"]), {})
        L.append(f"| {r['view']} | {r['dataset']} | {r['doc_id']} | `{f.get('gold_text', '?')}` ({f.get('form', '?')}) | {r['primary']} | {r['fix_class']} | {r['confidence']:.2f} | {r['evidence'].replace('|', '/')} |")
    cost = sum(c["cost_usd"] for c in causes)
    L += ["", f"Batch spend for this component: ${cost:.2f} (from the per-request `usage` fields, batch price).", ""]
    (OUT / "summary.md").write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT / 'summary.md'}")


def cmd_status(args) -> int:
    run_dir = Path(args.run) if args.run else api.latest_run_dir("diagnose")
    client = api.make_client()
    for name in ("diag", "diag-agreement"):
        if (run_dir / f"batch_{name}.json").exists():
            b = client.messages.batches.retrieve(api.batch_meta(run_dir, name)["id"])
            print(name, b.id, b.processing_status, b.request_counts)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["build", "dry-run", "submit", "collect", "status", "summarize"])
    ap.add_argument("--run")
    ap.add_argument("--views", nargs="+", default=["deterministic", "llm"])
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--poll", type=int, default=60)
    args = ap.parse_args(argv)
    if args.mode == "summarize":
        causes = api.read_jsonl(OUT / "causes.jsonl")
        write_summary(causes, [])
        return 0
    return {"build": cmd_build, "dry-run": cmd_dry_run, "submit": cmd_submit, "collect": cmd_collect, "status": cmd_status}[args.mode](args)


if __name__ == "__main__":
    raise SystemExit(main())
