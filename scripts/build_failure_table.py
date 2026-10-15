"""Failure tables with dialogue windows, one row per missed gold span, for both
views (brief §3 input).

    python scripts/build_failure_table.py deterministic   # from the sealed misses.csv + rebuilt planted docs
    python scripts/build_failure_table.py llm             # from results/llm_view/misses.csv + data/planted_llm

Writes results/<view>/failure_table.jsonl: view, dataset, doc_id, span_idx,
start, end, label, kind, category, speaker, gold_text, form, touched_labels,
this_mention_masked, same_string_masked_elsewhere, sealed_reason (the sealed
run's heuristic tag; recorded, never shown to the diagnoser), turn_idx and a
±3-turn window with the span marked [[...]]. Rows of misses.csv are matched
to gold spans by doc id, gold text and the 20-token context the scorer wrote,
so the match is exact or the script fails.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genre_shift_data as gs  # noqa: E402

ROOT = gs.ROOT
import score  # noqa: E402  (experiments/genre_shift/score.py, read-only: context() and nickname_form())

VIEWS = {
    "deterministic": {"misses": gs.GS_RESULTS / "misses.csv", "docs": lambda ds: gs.planted(ds),
                      "out": ROOT / "results" / "deterministic"},
    "llm": {"misses": ROOT / "results" / "llm_view" / "llm" / "misses.csv",
            "docs": lambda ds: gs.read_jsonl(ROOT / "data" / "planted_llm" / f"{ds}.jsonl"),
            "out": ROOT / "results" / "llm_view"},
}
WINDOW = 3


def form_of(kind: str, text: str) -> str:
    if kind == "nickname":
        return "nickname:" + score.nickname_form(text)
    if kind in ("first", "later", "related"):
        return ("lowercase_" if text[:1].islower() else "capitalised_") + ("full_name" if " " in text else "first_name")
    return kind


def window(doc_text: str, start: int, end: int, turn_idx: int, speakers: List[str]) -> str:
    ranges = gs.turn_ranges(doc_text, speakers)
    ts, te = ranges[turn_idx]
    if not (ts <= start < end <= te):
        raise ValueError("span does not lie in its turn")
    lo, hi = max(0, turn_idx - WINDOW), min(len(ranges), turn_idx + WINDOW + 1)
    out = []
    for i in range(lo, hi):
        a, b = ranges[i]
        seg = doc_text[a:b]
        if i == turn_idx:
            seg = seg[:start - a] + "[[" + seg[start - a:end - a] + "]]" + seg[end - a:]
        out.append(seg)
    return "\n".join(out)


def build(view: str) -> List[dict]:
    cfg = VIEWS[view]
    if not cfg["misses"].exists():
        raise SystemExit(f"{cfg['misses']} is missing (score the {view} view first)")
    with cfg["misses"].open(encoding="utf-8", newline="") as f:
        misses = list(csv.DictReader(f))
    rows: List[dict] = []
    docs: Dict[str, dict] = {}
    for ds in gs.DATASETS:
        for d in cfg["docs"](ds):
            docs[d["doc_id"]] = d
    speakers = {str(d[0]["dialogue_id"]): [str(t["speaker"]) for t in d] for ds in gs.dialogues().values() for d in ds}
    for m in misses:
        d = docs.get(m["doc_id"])
        if d is None:
            raise SystemExit(f"{view}: document {m['doc_id']} not available")
        spans = d["meta"]["spans"]
        cands = [(i, s) for i, s in enumerate(spans)
                 if s["text"] == m["gold_text"] and score.context(d["text"], s["start"], s["end"]) == m["context_20_tokens"]]
        if len(cands) != 1:
            raise SystemExit(f"{view}: {len(cands)} spans match {m['doc_id']} {m['gold_text']!r}; cannot build an exact table")
        i, s = cands[0]
        same = [x for x in spans if x["text"].split()[0].lower().strip(".") == s["text"].split()[0].lower().strip(".") and x is not s]
        rows.append({
            "view": view, "dataset": m["dataset"], "doc_id": m["doc_id"], "span_idx": i, "start": s["start"], "end": s["end"],
            "label": s["label"], "kind": s["kind"], "category": m["category"], "speaker": s["speaker"],
            "gold_text": s["text"], "form": form_of(s["kind"], s["text"]),
            "touched_labels": [x for x in m["touched_labels"].split("+") if x],
            "this_mention_masked": m["this_mention_masked"] == "yes",
            "same_string_masked_elsewhere": m["reason"] == "elsewhere",
            "n_other_mentions_of_name": len(same),
            "sealed_reason": m["reason"], "turn_idx": s["turn_idx"],
            "window": window(d["text"], s["start"], s["end"], s["turn_idx"], speakers[m["doc_id"]]),
        })
    rows.sort(key=lambda r: (r["dataset"], r["doc_id"], r["start"]))
    cfg["out"].mkdir(parents=True, exist_ok=True)
    with (cfg["out"] / "failure_table.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{view}: {len(rows)} rows -> {cfg['out'] / 'failure_table.jsonl'}")
    return rows


if __name__ == "__main__":
    for v in sys.argv[1:] or ["deterministic"]:
        build(v)
