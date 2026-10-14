"""results/view_comparison.md (+ one chart): deterministic vs LLM-planted view,
per dataset x name category and per label, with 95% Wilson intervals (brief §2, §6).
Reads only committed metrics files; the LLM view must have been scored first."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genre_shift_data as gs  # noqa: E402

ROOT = gs.ROOT
DET = gs.GS_RESULTS / "metrics.json"
LLM = ROOT / "results" / "llm_view" / "llm" / "metrics.json"
LOG = ROOT / "data" / "planted_llm" / "plant_llm_log.json"
OUT = ROOT / "results" / "view_comparison.md"
PNG = ROOT / "results" / "view_comparison.png"


def pct(x):
    return "n/a" if x is None or x != x else f"{100 * x:.1f}%"


def ci(a, key="span_ci"):
    lo, hi = a[key]
    return f"[{100 * lo:.1f}, {100 * hi:.1f}]"


def row(name, a, b):
    d = None if not a or not b else 100 * (b["span_recall"] - a["span_recall"])
    overlap = None
    if a and b:
        overlap = not (a["span_ci"][1] < b["span_ci"][0] or b["span_ci"][1] < a["span_ci"][0])
    return [name, a["n"] if a else 0, pct(a["span_recall"]) if a else "n/a", ci(a) if a else "", b["n"] if b else 0,
            pct(b["span_recall"]) if b else "n/a", ci(b) if b else "", f"{d:+.1f}" if d is not None else "n/a",
            "" if overlap is None else ("yes" if overlap else "**no**")]


def table(rows, header):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def main() -> int:
    if not LLM.exists():
        raise SystemExit(f"{LLM} missing: run `make score-llm-view` first")
    det, llm = json.loads(DET.read_text(encoding="utf-8")), json.loads(LLM.read_text(encoding="utf-8"))
    log = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {}
    H = ["slice", "det n", "det recall", "95% CI", "LLM n", "LLM recall", "95% CI", "Δ pp (LLM − det)", "CIs overlap"]
    L = ["# Deterministic vs LLM-planted view", "",
         f"Same dialogues, same slot decisions (which dialogue gets which identifier kinds, in which turns and forms, and the "
         f"name category) from the sealed run (seed {det['seed']}); only the wording around each identifier and the choice of "
         f"name within the category differ. The LLM view was planted by `{log.get('model', '?')}` through the Message Batches API "
         f"(prompt `prompts/plant_system.md` sha256 `{log.get('prompt_sha256', '?')[:12]}…`), validated in code, and scored by the "
         f"unchanged scorer with edshield {llm.get('run', {}).get('versions', {}).get('edshield', '0.2.0')}. Span recall is the residual rule "
         f"(the identifier no longer occurs whole in the output). Dialogues dropped after one retry: **{log.get('dropped', '?')}**"
         + (" (" + ", ".join(f"{k}: {v['dropped']}" for k, v in log.get("datasets", {}).items()) + ")" if log.get("datasets") else "") + ".",
         "", "Sources: `experiments/genre_shift/results/metrics.json` (deterministic, sealed) and `results/llm_view/llm/metrics.json`.", ""]
    L += ["## All identifiers and student names", ""]
    rows = []
    for ds in list(gs.DATASETS) + ["pooled"]:
        a = det["pooled"] if ds == "pooled" else det["datasets"].get(ds)
        b = llm["pooled"] if ds == "pooled" else llm["datasets"].get(ds)
        if not a or not b:
            continue
        rows.append(row(f"{ds}: all identifiers", a["all_identifiers"], b["all_identifiers"]))
        rows.append(row(f"{ds}: student names", a["student_names"], b["student_names"]))
    L += [table(rows, H), ""]
    L += ["## Student names by dataset × name category", ""]
    rows = []
    for ds in list(gs.DATASETS) + ["pooled"]:
        a = det["pooled"] if ds == "pooled" else det["datasets"].get(ds)
        b = llm["pooled"] if ds == "pooled" else llm["datasets"].get(ds)
        if not a or not b:
            continue
        for c in gs.CATEGORIES:
            rows.append(row(f"{ds} / {c}", a["names_by_category"].get(c), b["names_by_category"].get(c)))
    L += [table(rows, H), ""]
    L += ["## Base-form names (no nickname/initial forms) by category, pooled", ""]
    rows = [row(c, det["pooled"]["base_form_names_by_category"].get(c), llm["pooled"]["base_form_names_by_category"].get(c)) for c in gs.CATEGORIES]
    L += [table(rows, H), ""]
    L += ["## By label, pooled", ""]
    labels = sorted(set(det["pooled"]["by_label"]) | set(llm["pooled"]["by_label"]))
    L += [table([row(l, det["pooled"]["by_label"].get(l), llm["pooled"]["by_label"].get(l)) for l in labels], H), ""]
    L += ["## Nickname forms and case, pooled", ""]
    rows = [row("nickname: " + k, det["pooled"]["nicknames_by_form"].get(k), llm["pooled"]["nicknames_by_form"].get(k)) for k in ("initial", "all_caps", "truncated")]
    rows += [row("written " + k, det["pooled"]["names_by_case"].get(k), llm["pooled"]["names_by_case"].get(k)) for k in ("capitalised", "lowercase")]
    L += [table(rows, H), ""]
    L += ["## Reading it", "",
          "A slice where the two views agree within their intervals shows a detector behaviour that does not depend on the "
          "sealed run's templates; a slice where they disagree (CIs do not overlap) is one where the phrasing itself moves the "
          "number, and the deterministic figure should not be quoted alone. Miss reasons (sealed heuristic tags): deterministic "
          f"{det['pooled']['miss_reasons']}; LLM {llm['pooled']['miss_reasons']}.", "", "![view comparison](view_comparison.png)", ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    chart(det, llm)
    print(f"wrote {OUT} and {PNG}")
    return 0


def chart(det, llm):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    cats = list(gs.CATEGORIES)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, ds in zip(axes, gs.DATASETS):
        x = np.arange(len(cats))
        for j, (name, m, color) in enumerate((("deterministic", det, "#4c72b0"), ("LLM-planted", llm, "#dd8452"))):
            a = [m["datasets"][ds]["names_by_category"].get(c) for c in cats]
            ys = [100 * v["span_recall"] if v else 0 for v in a]
            lo = [100 * (v["span_recall"] - v["span_ci"][0]) if v else 0 for v in a]
            hi = [100 * (v["span_ci"][1] - v["span_recall"]) if v else 0 for v in a]
            ax.bar(x + (j - 0.5) * 0.38, ys, 0.38, yerr=[lo, hi], capsize=3, label=name, color=color)
            for xi, yi, h, v in zip(x + (j - 0.5) * 0.38, ys, hi, a):
                if v:
                    ax.text(xi, yi + h + 1, f"{yi:.0f}%\nn={v['n']}", ha="center", va="bottom", fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels(cats, rotation=15, fontsize=8)
        ax.set_title(ds)
        ax.set_ylim(0, 118)
        ax.axhline(99.5, color="k", ls="--", lw=0.8)
    axes[0].set_ylabel("student-name span recall (%)")
    axes[0].legend(loc="lower left", fontsize=8, frameon=False)
    fig.suptitle("edshield 0.2.0: student-name recall by name category, two planting views (95% Wilson)")
    fig.tight_layout()
    fig.savefig(PNG, dpi=150)


if __name__ == "__main__":
    raise SystemExit(main())
