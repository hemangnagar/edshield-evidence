"""Figures F1-F4 from results/v2/metrics.json (PNG at 300 dpi and PDF).

    python plot_v2.py

F1 name recall by dataset, one bar per detector, PIILO leftmost, pooled 95% CI
F2 primary stratum x detector heatmap of name recall
F3 floor transfer: predicted vs measured recall, one point per (pair x detector)
F4 over-redaction: NAME flags per 1,000 control tokens, by what was flagged

Colours: a fixed colourblind-safe order (Okabe-Ito hues), checked for adjacent
separation under deuteranopia, protanopia and tritanopia; detectors also differ
by marker shape in F3 and are named on the axis in F2 and F4.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

import strata

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "v2"
FIG = OUT / "figures"
PIILO, POOLED = "piilo_holdout", "pooled_dialogue"
COLOR = {"edshield": "#0072B2", "presidio": "#D55E00", "spacy_trf": "#009E73", "hf_pii": "#E69F00",
         "gpt4o_mini": "#CC79A7", "gpt4o_mini_propagated": "#EBC6DA"}
MARKER = {"edshield": "o", "presidio": "s", "spacy_trf": "^", "hf_pii": "D", "gpt4o_mini": "v",
          "gpt4o_mini_propagated": "P"}
NAME = {"edshield": "edshield 0.2.0", "presidio": "Presidio", "spacy_trf": "spaCy trf", "hf_pii": "Piiranha (HF)",
        "gpt4o_mini": "gpt-4o-mini", "gpt4o_mini_propagated": "gpt-4o-mini, propagated"}
DATASET = {PIILO: "PIILO essays\n(in-domain)", "comta": "CoMTA\n(real students)", "mathdial": "MathDial\n(simulated students)",
           "studychat": "StudyChat", "tscc": "TSCC", POOLED: "Dialogue,\npooled"}
INK, MUTED, GRID = "#191919", "#666666", "#E3E3E3"
SEQ = LinearSegmentedColormap.from_list("blue", ["#EAF3FE", "#9DC8F7", "#338CED", "#0E3D7E"])

plt.rcParams.update({"font.size": 8, "axes.edgecolor": GRID, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 9, "axes.titleweight": "bold", "axes.titlelocation": "left",
                     "legend.frameon": False, "pdf.fonttype": 42, "savefig.bbox": "tight"})


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=300)
    fig.savefig(FIG / f"{name}.pdf")
    plt.close(fig)


def detectors(m: dict):
    return m["detectors"]["primary"] + m["detectors"]["secondary"]


def f1_recall(m: dict) -> None:
    dets, res = detectors(m), m["results"]
    groups = [g for g in [PIILO] + m["datasets"] + [POOLED] if any(g in res[d] for d in dets)]
    width = 0.8 / len(dets)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for j, d in enumerate(dets):
        for i, g in enumerate(groups):
            a = res[d].get(g, {}).get("name_recall", {}).get("pooled")
            if not a or not a["n"]:
                continue
            x, y = i + (j - (len(dets) - 1) / 2) * width, 100 * a["recall"]
            lo, hi = 100 * a["wilson95"][0], 100 * a["wilson95"][1]
            ax.bar(x, y, width * 0.86, color=COLOR[d], label=NAME[d] if i == 0 else None, zorder=2)
            ax.errorbar(x, y, yerr=[[y - lo], [hi - y]], color=INK, lw=0.7, capsize=1.6, capthick=0.7, zorder=3)
            ax.text(x, hi + 1.2, f"{y:.0f}", ha="center", va="bottom", fontsize=6, color=INK)
    ax.axhline(99.5, color=MUTED, lw=0.6, zorder=1)
    ax.text(len(groups) - 0.5, 100.1, "99.5% floor", ha="right", va="bottom", fontsize=6.5, color=MUTED)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([DATASET[g] for g in groups], color=INK)
    ax.set_ylim(0, 108)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Name recall (%)")
    ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=len(dets), fontsize=6.5, handlelength=1,
              columnspacing=1.0, handletextpad=0.4)
    fig.text(0.01, -0.02, f"Bars: recall over all planted name mentions ({len(m['seeds'])} planting seeds pooled; PIILO: one run). "
             "Error bars: 95% Wilson interval.", fontsize=6.5, color=MUTED)
    save(fig, "F1_recall_by_dataset")


def f2_heatmap(m: dict) -> None:
    dets, res = detectors(m), m["results"]
    rows = [s for s in strata.PRIMARY_STRATA if any(s in res[d].get(POOLED, {}).get("by_stratum", {}) for d in dets)]
    missing = [s for s in strata.PRIMARY_STRATA if s not in rows]
    grid = np.full((len(rows), len(dets)), np.nan)
    n = {}
    for j, d in enumerate(dets):
        for i, s in enumerate(rows):
            a = res[d].get(POOLED, {}).get("by_stratum", {}).get(s)
            if a:
                grid[i, j], n[s] = 100 * a["recall"], a["n"]
    fig, ax = plt.subplots(figsize=(7.2, 0.42 * len(rows) + 1.3))
    lo = min(40, np.floor(np.nanmin(grid) / 10) * 10)
    im = ax.imshow(grid, cmap=SEQ, vmin=lo, vmax=100, aspect="auto")
    for i in range(len(rows)):
        for j in range(len(dets)):
            if not np.isnan(grid[i, j]):
                dark = (grid[i, j] - lo) / (100 - lo) > 0.55
                ax.text(j, i, f"{grid[i, j]:.1f}", ha="center", va="center", fontsize=7.5,
                        color="white" if dark else INK)
    ax.set_xticks(range(len(dets)))
    ax.set_xticklabels([NAME[d].replace(", ", ",\n") for d in dets], color=INK, fontsize=7)
    ax.xaxis.tick_top()
    label = lambda s: "{}, {} turn, {}".format(*[{"upper": "Capitalised", "lower": "Lowercase", "dict": "dictionary word",
                                                   "nondict": "not a word"}.get(p, p) for p in s.split("|")])
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{label(s)}  (n = {n[s]:,})" for s in rows], color=INK, fontsize=7)
    ax.set_xticks(np.arange(-0.5, len(dets)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(rows)), minor=True)
    ax.grid(which="minor", color="white", lw=2)
    ax.tick_params(which="both", length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cb.set_label("Name recall (%)", fontsize=7)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, labelsize=6.5)
    note = "Cells: name recall (%) per primary stratum, dialogue sets and seeds pooled."
    if missing:
        note += " No planted mentions in: " + "; ".join(label(s).lower() for s in missing) + "."
    fig.text(0.01, -0.03, note, fontsize=6.5, color=MUTED, wrap=True)
    save(fig, "F2_stratum_heatmap")


def f3_transfer(m: dict) -> None:
    pairs = [r for r in m["floor_transfer"]["pairs"] if r["strata_set"] == strata.PRIMARY]
    if not pairs:
        return
    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    vals = []
    for r in pairs:
        d, y = r["detector"], 100 * r["measured"]
        for mix, filled in (("oracle", True), ("caught_only", False)):
            if not r[mix] or r[mix]["predicted_point"] is None:
                continue
            x = 100 * r[mix]["predicted_point"]
            vals += [x, y]
            ax.scatter(x, y, s=34, marker=MARKER[d], facecolor=COLOR[d] if filled else "white", edgecolor=COLOR[d],
                       linewidth=1.2, zorder=3 if filled else 4)
        if r["oracle"] and r["oracle"]["predicted_point"] is not None:
            ax.annotate(f"{r['a'][0].upper()}→{r['b'][0].upper()}", (100 * r["oracle"]["predicted_point"], y),
                        xytext=(4, -8), textcoords="offset points", fontsize=5.5, color=MUTED)
    lo, hi = np.floor(min(vals) / 5) * 5 - 2, min(100, np.ceil(max(vals) / 5) * 5 + 2)
    ax.plot([lo, hi], [lo, hi], color=MUTED, lw=0.7, zorder=1)
    ax.text(hi - 0.5, hi - 1.5, "predicted = measured", ha="right", va="top", fontsize=6.5, color=MUTED, rotation=45,
            rotation_mode="anchor")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("Predicted name recall on B from A's strata (%)")
    ax.set_ylabel("Measured name recall on B (%)")
    ax.grid(True, color=GRID, lw=0.6, zorder=0)
    ax.tick_params(length=0)
    seen = [d for d in detectors(m) if any(r["detector"] == d for r in pairs)]
    handles = [plt.Line2D([], [], marker=MARKER[d], color=COLOR[d], ls="", markersize=5, label=NAME[d]) for d in seen]
    handles += [plt.Line2D([], [], marker="o", color=MUTED, ls="", markersize=5, label="oracle mix (filled)"),
                plt.Line2D([], [], marker="o", color=MUTED, markerfacecolor="white", ls="", markersize=5,
                           label="caught-only mix (hollow)")]
    ax.legend(handles=handles, loc="upper left", fontsize=6.5, handletextpad=0.3, labelspacing=0.35)
    names = {g[0].upper(): g for g in m["datasets"]}
    fig.text(0.01, -0.03, "One point per ordered genre pair A→B and detector (" +
             ", ".join(f"{k} = {v}" for k, v in names.items()) + "). Points below the line: recall on B over-predicted.",
             fontsize=6.5, color=MUTED)
    save(fig, "F3_floor_transfer")


def f4_over_redaction(m: dict) -> None:
    dets, res = detectors(m), m["results"]
    sets = [g for g in [PIILO] + m["datasets"] if any(res[d].get(g, {}).get("over_redaction", {}).get("n_tokens") for d in dets)]
    if not sets:
        return
    tags = [("curricular", "curricular terms", "#D55E00"), ("problem_name", "word-problem characters", "#56B4E9"),
            ("persona", "simulated student's own name", "#0072B2"), ("other", "other", "#BDBDBD")]
    fig, axes = plt.subplots(1, len(sets), figsize=(7.2, 3.0), squeeze=False)
    for ax, g in zip(axes[0], sets):
        for j, d in enumerate(dets):
            o = res[d].get(g, {}).get("over_redaction")
            if not o or not o["n_tokens"]:
                continue
            bottom = 0.0
            for tag, _, c in tags:
                h = 1000 * o["by_tag"].get(tag, 0) / o["n_tokens"]
                if h:
                    ax.bar(j, h, 0.6, bottom=bottom, color=c, edgecolor="white", linewidth=1.0, zorder=2)
                bottom += h
            cur = o["share_curricular"] or 0
            ax.text(j, bottom, f"{bottom:.1f}" if bottom >= 0.95 else f"{bottom:.2f}", ha="center", va="bottom", fontsize=6.5)
            if cur:
                ax.text(j, -0.13, f"{100 * cur:.0f}% curr.", ha="center", va="top", fontsize=5.5, color=MUTED,
                        transform=ax.get_xaxis_transform())
        ax.set_title(DATASET[g].replace("\n", " "), fontsize=8)
        ax.set_xticks(range(len(dets)))
        ax.set_xticklabels([NAME[d].replace(" (HF)", "").replace(", propagated", "\nprop.").replace(" 0.2.0", "") for d in dets],
                           rotation=40, ha="right", fontsize=6.5, color=INK)
        ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        ax.margins(y=0.12)
    axes[0][0].set_ylabel("NAME flags per 1,000 tokens")
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c, label=l) for _, l, c in tags], loc="lower center",
               bbox_to_anchor=(0.5, 0.98), ncol=4, fontsize=6.5, handlelength=1, columnspacing=1.2)
    fig.text(0.01, -0.12, "Untouched control dialogues (PIILO: flags overlapping no gold span). Vertical scales differ by panel. "
             "\"% curr.\": share of a detector's flags on curricular terms, shown where it is not zero.", fontsize=6.5, color=MUTED)
    fig.tight_layout(w_pad=1.5)
    save(fig, "F4_over_redaction")


def main() -> int:
    m = json.loads((OUT / "metrics.json").read_text(encoding="utf-8"))
    f1_recall(m)
    f2_heatmap(m)
    f3_transfer(m)
    f4_over_redaction(m)
    print("figures:", ", ".join(sorted(p.name for p in FIG.glob("*.png"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
