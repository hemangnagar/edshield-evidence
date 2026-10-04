"""Append-only experiment ledger (evidence/ledger.md) and the regression
target pin.

    python -m edshield_evidence.ledger append --report evidence/reports/<id> --key <step key> [--note ...]
    python -m edshield_evidence.ledger show
    python -m edshield_evidence.ledger pin        # a human runs this; agents do not

One row per report step:
date | report id | dataset | policy | detector | runtime | edshield commit | recipe sha |
identifier recall [interval] | document recall | word fpr | verdict | note

`pin` re-pins the regression targets in policies/regression.json from the
latest ledger entry of each dataset/detector: recall targets become the
measured value rounded down to three decimals, the word fpr target becomes
the measured value + 0.005 rounded up. It changes nothing else.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import EDSHIELD_COMMIT, EVIDENCE_DIR, REPO_ROOT
from .policy import REGRESSION

LEDGER = EVIDENCE_DIR / "ledger.md"
COLUMNS = ["date", "report id", "dataset", "policy", "detector", "runtime", "edshield commit", "recipe sha",
           "identifier recall [interval]", "document recall", "word fpr", "verdict", "note"]
HEADER = "| " + " | ".join(COLUMNS) + " |\n|" + "|".join("---" for _ in COLUMNS) + "|\n"
PREAMBLE = (
    "# Experiment ledger\n\n"
    "Append-only. One row per report step. Regression targets are re-pinned from the latest row of each "
    "dataset/detector by `python -m edshield_evidence.ledger pin` (a human runs this). "
    "Identifier recall is 1 - full residuals / gold spans on the final output; edshield's own figures "
    "count a span as handled when any flag touches it, so the two are not comparable one to one.\n\n"
)

# edshield's own reported "got through" counts (any flag touching the span counts as handled), for the note.
EDSHIELD_REPORTED = {
    ("k12_hard", "rules+model"): "edshield reports 319 of 1,433 got through",
    ("k12_hard", "rules"): "edshield reports 1,100 of 1,433 got through",
    ("piilo_holdout", "rules+model"): "edshield reports 0 of 165 got through",
}


def _fmt(v: Optional[float]) -> str:
    return "n/a" if v is None else f"{v:.4f}"


def _interval(m: dict) -> str:
    iv = m.get("interval")
    return f"[{iv[0]:.4f}, {iv[1]:.4f}]" if iv else "[n/a]"


def entry_from_report(report_dir: Path, key: str, note: str = "") -> Dict[str, str]:
    bundle = json.loads((report_dir / f"{key}.bundle.json").read_text(encoding="utf-8"))
    verdict = json.loads((report_dir / f"{key}.verdict.json").read_text(encoding="utf-8"))
    diag_path = report_dir / f"{key}.diagnostics.json"
    diag = json.loads(diag_path.read_text(encoding="utf-8")) if diag_path.exists() else {}
    md = bundle["metadata"]
    views = verdict["views"]

    def metric(view: str, name: str) -> dict:
        v = views.get(view)
        return v["confusion"][name] if v else {}

    ident, doc, word = metric("identifier", "recall"), metric("document", "recall"), metric("word", "fpr")
    auto_note = []
    if diag.get("runs"):
        r0 = diag["runs"][0]
        auto_note.append(f"{r0['full_residuals']} of {r0['n_gold']} identifiers survive whole, "
                         f"{r0['partial_residuals']} partially")
        ref = EDSHIELD_REPORTED.get((md["dataset"], md["detector"]))
        if ref:
            auto_note.append(ref)
    if not bundle["metadata"].get("parity") and (verdict["views"].get("identifier") or {}).get("agreement") is not None:
        pass
    if md.get("parity") and views.get("identifier"):
        auto_note.append(f"identifier agreement python/onnx {views['identifier']['agreement']:.4f}")
    if note:
        auto_note.append(note)
    return {
        "date": md.get("generated_at", "")[:10],
        "report id": report_dir.name,
        "dataset": md["dataset"],
        "policy": f"{md['policy']} ({md['policy_fingerprint'][:8]})",
        "detector": md["detector"],
        "runtime": md["runtime"],
        "edshield commit": f"{md['edshield_version']} ({md['edshield_commit'][:7]})",
        "recipe sha": md["recipe_sha256"][:12],
        "identifier recall [interval]": f"{_fmt(ident.get('value'))} {_interval(ident)}" if ident else "n/a",
        "document recall": _fmt(doc.get("value")) if doc else "n/a",
        "word fpr": _fmt(word.get("value")) if word else "n/a",
        "verdict": verdict["overall"],
        "note": "; ".join(auto_note).replace("|", "/"),
    }


def append(entry: Dict[str, str], ledger: Path = LEDGER) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    if not ledger.exists() or HEADER.strip() not in ledger.read_text(encoding="utf-8"):
        ledger.write_text(PREAMBLE + HEADER, encoding="utf-8")
    row = "| " + " | ".join(entry.get(c, "") for c in COLUMNS) + " |\n"
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write(row)


def parse(ledger: Path = LEDGER) -> List[Dict[str, str]]:
    if not ledger.exists():
        return []
    rows = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("| date") or re.fullmatch(r"\|(?:---\|)+", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == len(COLUMNS):
            rows.append(dict(zip(COLUMNS, cells)))
    return rows


def _floor3(x: float) -> float:
    return math.floor(x * 1000) / 1000


def _ceil3(x: float) -> float:
    return min(1.0, math.ceil(x * 1000) / 1000)


def pin(policy_path: Path = REGRESSION, ledger: Path = LEDGER, reports_dir: Path = EVIDENCE_DIR / "reports") -> List[str]:
    keyed = json.loads(policy_path.read_text(encoding="utf-8"))
    changes: List[str] = []
    latest: Dict[str, Dict[str, str]] = {}
    for row in parse(ledger):
        key = f"{row['dataset']}/{'parity' if ',' in row['runtime'] else row['detector']}"
        latest[key] = row  # later rows win
    for key, row in latest.items():
        if key not in keyed["policies"]:
            continue
        report_dir = reports_dir / row["report id"]
        verdicts = list(report_dir.glob("*.verdict.json"))
        verdict = None
        for vp in verdicts:
            b = json.loads(vp.with_name(vp.name.replace(".verdict.json", ".bundle.json")).read_text(encoding="utf-8"))
            md = b["metadata"]
            if md["dataset"] == row["dataset"] and md["runtime"] == row["runtime"] and md["detector"] == row["detector"]:
                verdict = json.loads(vp.read_text(encoding="utf-8"))
                break
        if verdict is None:
            changes.append(f"{key}: no verdict found under {report_dir}; skipped")
            continue
        pol = keyed["policies"][key]
        for vname, vp in pol["views"].items():
            res = verdict["views"].get(vname)
            if not res:
                continue
            for metric in ("recall", "precision", "accuracy"):
                if vp.get(metric) is not None and res["confusion"][metric]["value"] is not None:
                    new = _floor3(res["confusion"][metric]["value"])
                    if new != vp[metric]:
                        changes.append(f"{key} {vname}.{metric}: {vp[metric]} -> {new}")
                        vp[metric] = new
            if vp.get("fpr") is not None and res["confusion"]["fpr"]["value"] is not None:
                new = _ceil3(res["confusion"]["fpr"]["value"] + 0.005)
                if new != vp["fpr"]:
                    changes.append(f"{key} {vname}.fpr: {vp['fpr']} -> {new}")
                    vp["fpr"] = new
        pol["_pinned_from"] = row["report id"]
    policy_path.write_text(json.dumps(keyed, indent=2) + "\n", encoding="utf-8")
    return changes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m edshield_evidence.ledger", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a_ = sub.add_parser("append")
    a_.add_argument("--report", required=True, help="report directory")
    a_.add_argument("--key", required=True, help="step key: <key>.bundle.json / <key>.verdict.json")
    a_.add_argument("--note", default="")
    a_.add_argument("--ledger", default=str(LEDGER))
    sub.add_parser("show")
    p = sub.add_parser("pin")
    p.add_argument("--policy", default=str(REGRESSION))
    p.add_argument("--ledger", default=str(LEDGER))
    a = ap.parse_args(argv)
    if a.cmd == "append":
        entry = entry_from_report(Path(a.report), a.key, a.note)
        append(entry, Path(a.ledger))
        print(" | ".join(entry[c] for c in COLUMNS))
    elif a.cmd == "show":
        for row in parse():
            print(" | ".join(row[c] for c in COLUMNS))
    else:
        for c in pin(Path(a.policy), Path(a.ledger)):
            print(c)
        print(f"re-pinned {a.policy}; review the diff and commit it (a `ratify:` commit if these are the ratified criteria)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
