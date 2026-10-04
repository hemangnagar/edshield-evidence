"""summary.md for a report directory.

    python -m edshield_evidence.report evidence/reports/<id>

Reads every <key>.verdict.json with its bundle, policy and diagnostics and
writes one table per step: view, n, gate, point, interval, verdict; then the
partial-residual counts by label, the label-confusion table and the
over-redaction sample. The first line states PROVISIONAL until the policy
file used has a `ratify:` commit.

Wording rule: a system "meets defined redaction criteria on evidence set X
(sha256 …) under policy Y (fingerprint …)". Nothing here certifies anything,
and the summary is refused if a forbidden word slipped in.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import EDSHIELD_COMMIT, FORBIDDEN_REPORT_WORDS, JUDGE_TAG

PROVISIONAL_LINE = "criteria PROVISIONAL, not ratified"


def pct(v: Optional[float]) -> str:
    return "n/a" if v is None else f"{v * 100:.2f}%"


def interval(g: dict) -> str:
    iv = g.get("interval")
    return f"{pct(iv[0])} – {pct(iv[1])}" if iv else "no denominator"


def wording(md: dict, overall: str) -> str:
    phrase = {"pass": "meets", "fail": "does not meet", "insufficient": "has insufficient evidence for"}[overall]
    return (f"edshield {md['edshield_version']} ({md['detector']}, {md['runtime']}) **{phrase}** defined redaction "
            f"criteria on evidence set {md['dataset']} (sha256 {md['data_sha256']}) under policy {md['policy']} "
            f"(fingerprint {md['policy_fingerprint']}). Judge verdict: **{overall.upper()}**.")


def step_section(key: str, bundle: dict, verdict: dict, policy: dict, diag: dict) -> List[str]:
    md = bundle["metadata"]
    out = [f"## {key}", "", wording(md, verdict["overall"]), ""]
    if md.get("parity"):
        out += ["Parity bundle: the two runs are the python and onnx runtimes on the same documents. The judge's "
                "stability and reproducibility axes need seeds and are insufficient by construction; read the gates "
                "on the selected run and the agreement figure.", ""]
    if policy.get("_dropped_views"):
        out += [f"Policy entries dropped because the bundle has no such view: {', '.join(policy['_dropped_views'])}.", ""]
    out += ["| view | n | gate | point | 95% interval | target | result | view verdict |", "|---|---|---|---|---|---|---|---|"]
    for name, v in verdict["views"].items():
        active = [g for g in v["gates"] if g["status"] != "skipped"]
        req = "" if (v.get("policy") or {}).get("required", True) else " (not required)"
        if not active:
            out.append(f"| {name} | {v['confusion']['n']} | (no policy) | | | | | {v['overall']}{req} |")
        for i, g in enumerate(active):
            tgt = f"{'≥' if g['direction'] == 'min' else '≤'} {pct(g['target'])}"
            out.append(f"| {name if i == 0 else ''} | {v['confusion']['n'] if i == 0 else ''} | {g['key']} | {pct(g['value'])} | "
                       f"{interval(g)} | {tgt} | {g['status']} | {v['overall'] + req if i == 0 else ''} |")
    out.append("")
    axes_parts = []
    for n, v in verdict["views"].items():
        if n.startswith("type:"):
            continue
        spread = "" if v.get("spread") is None else f", spread {v['spread'] * 100:.2f} pp"
        agree = ""
        if v.get("agreement") is not None and len(v["runs"]) > 1:
            agree = f", agreement {v['agreement']:.4f}"
        axes_parts.append(f"{n}: performance {v['performance']}, stability {v['stability']} "
                          f"({v['stabilityMetric']}{spread}), reproducibility {v['reproducibility']}{agree}")
    first_view = next(iter(verdict["views"].values()))
    run_names = []
    for r in first_view["runs"]:
        seed = "" if r.get("seed") is None else f" (seed {r['seed']})"
        run_names.append(f"{r['id']}{seed}")
    out += [f"Axes — {'; '.join(axes_parts)}.", "",
            f"Runs: {', '.join(run_names)}. Required views: {', '.join(verdict['requiredViews'])}. "
            f"Policy sha256 {verdict.get('policy_sha256')}; input sha256 {verdict.get('input_sha256')}.", ""]
    runs = diag.get("runs", [])
    if len(runs) > 1:
        out += ["| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |",
                "|---|---|---|---|---|---|---|---|"]
        for run in runs:
            out.append(f"| {run['id']} | {'' if run.get('seed') is None else run['seed']} | {run['full_residuals']} of {run['n_gold']} | "
                       f"{run['partial_residuals']} | {pct(run['identifier_recall'])} | {pct(run['word']['fpr'])} | "
                       f"{run['model_sha256'][:12]} | {run['seconds']} |")
        out += ["", "Residual detail below is for the first run; the others differ only where the table says so.", ""]
    for run in runs[:1]:
        out += [f"### Residuals, run {run['id']}", "",
                f"{run['full_residuals']} of {run['n_gold']} gold identifiers survive whole in the output "
                f"(identifier recall {pct(run['identifier_recall'])}); {run['partial_residuals']} more survive partially "
                f"(a token of ≥ 3 characters). Word view: {run['word']['fp']} of {run['word']['fp'] + run['word']['tn']} "
                f"non-identifier tokens were removed (fpr {pct(run['word']['fpr'])}). "
                f"edshield's own leak check reported {run['edshield_self_reported_leaks']} leaks; alignment failures {run['alignment_failures']}.", "",
                "| label | n | full residual | partial residual | recall |", "|---|---|---|---|---|"]
        for label, c in run["by_label"].items():
            out.append(f"| {label} | {c['n']} | {c['full_residual']} | {c['partial_residual']} | {pct(c['recall'])} |")
        out += ["", "Label confusion (gold label → labels of acted-on entities touching it; `none` = untouched):", "",
                "| gold \\ acted | " + " | ".join(sorted({p for row in run['label_confusion'].values() for p in row})) + " |"]
        preds = sorted({p for row in run["label_confusion"].values() for p in row})
        out.append("|---|" + "---|" * len(preds))
        for g, row in run["label_confusion"].items():
            out.append(f"| {g} | " + " | ".join(str(row.get(p, "")) for p in preds) + " |")
        out.append("")
        if run.get("over_redaction_sample"):
            out += ["Over-redaction sample (removed tokens outside any gold span, for human review):", ""]
            for o in run["over_redaction_sample"]:
                ctx = o["context"].replace("\n", " ").replace("|", "/")
                out.append(f"- `{o['doc_id']}` `{o['token']}` as {', '.join(o['labels']) or '?'}: …{ctx}…")
            out.append("")
        elif not run.get("text_included", True):
            out += ["Over-redaction sample and residual text withheld: sealed set.", ""]
        if run.get("partial_examples"):
            out += ["Partial residuals (first 25):", ""]
            for p in run["partial_examples"][:25]:
                out.append(f"- `{p['doc_id']}` {p['label']} `{p['text']}` → `{p['surviving_token']}` survives (touched: {', '.join(p['touched']) or 'none'})")
            out.append("")
    return out


def summarize(report_dir: Path, out_name: str = "summary.md") -> Path:
    report_dir = Path(report_dir)
    keys = sorted(p.name[: -len(".verdict.json")] for p in report_dir.glob("*.verdict.json"))
    skipped = sorted(report_dir.glob("*.skipped.txt"))
    lines: List[str] = []
    policies, bundles = [], []
    sections: List[str] = []
    for key in keys:
        bundle = json.loads((report_dir / f"{key}.bundle.json").read_text(encoding="utf-8"))
        verdict = json.loads((report_dir / f"{key}.verdict.json").read_text(encoding="utf-8"))
        pol_path = report_dir / f"{key}.policy.json"
        policy = json.loads(pol_path.read_text(encoding="utf-8")) if pol_path.exists() else {}
        diag_path = report_dir / f"{key}.diagnostics.json"
        diag = json.loads(diag_path.read_text(encoding="utf-8")) if diag_path.exists() else {}
        policies.append(policy)
        bundles.append(bundle)
        sections += step_section(key, bundle, verdict, policy, diag)
    ratified = bool(policies) and all(p.get("_ratified") for p in policies)
    lines.append(("criteria ratified" if ratified else PROVISIONAL_LINE))
    lines += ["", f"# Report {report_dir.name}", "",
              f"System under test: edshield {bundles[0]['metadata']['edshield_version'] if bundles else '?'} "
              f"(source commit {EDSHIELD_COMMIT[:7]}). Judge: model-evidence {JUDGE_TAG}. "
              f"Steps: {len(keys)} run, {len(skipped)} skipped.", ""]
    for s in skipped:
        lines.append(f"- skipped `{s.name[:-len('.skipped.txt')]}`: {s.read_text(encoding='utf-8').strip()}")
    if skipped:
        lines.append("")
    lines += ["Residuals are measured on the final output of `edshield.deidentify(verify=False)`: an identifier counts as "
              "handled only when its normalized text no longer occurs whole. A surrogate that equals a gold string counts "
              "as a residual (known conservative bias). The verdicts come from the judge CLI; nothing here computes pass/fail.", ""]
    lines += sections
    text = "\n".join(lines).rstrip() + "\n"
    low = text.lower()
    for w in FORBIDDEN_REPORT_WORDS:
        if w in low:
            raise SystemExit(f"summary contains the forbidden word {w!r}; refusing to write it")
    out = report_dir / out_name
    out.write_text(text, encoding="utf-8")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m edshield_evidence.report")
    ap.add_argument("report_dir")
    ap.add_argument("--out", default="summary.md")
    a = ap.parse_args(argv)
    print(summarize(Path(a.report_dir), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
