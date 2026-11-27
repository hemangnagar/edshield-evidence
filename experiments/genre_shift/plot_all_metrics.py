"""Draw every measurement in results/metrics.json on one page.

Internal working figure: shows all the groupings the scorer produced, with
95% Wilson intervals where the scorer recorded them, so nothing has to be
re-derived from the JSON by hand. Regenerate after any run:

    python experiments/genre_shift/plot_all_metrics.py

Reads  experiments/genre_shift/results/metrics.json
Writes experiments/genre_shift/results/all_metrics.png
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

HERE = Path(__file__).resolve().parent
METRICS = HERE / "results" / "metrics.json"
OUT = HERE / "results" / "all_metrics.png"

# one colour per dataset, fixed everywhere on the page
C = {
    "piilo_holdout": "#898781",  # in-domain reference, grey
    "comta": "#2a78d6",          # real students, blue
    "mathdial": "#eb6834",       # simulated students, orange
    "pooled": "#1baf7a",         # comta + mathdial, aqua
}
LABEL = {
    "piilo_holdout": "PIILO holdout\n(in-domain)",
    "comta": "CoMTA\n(real students)",
    "mathdial": "MathDial\n(simulated students)",
    "pooled": "Pooled\n(CoMTA+MathDial)",
}
INK, INK2, MUTED, HAIR = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": HAIR,
    "axes.labelcolor": INK2,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "axes.titlecolor": INK,
    "axes.titleweight": "bold",
    "axes.titlesize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "#fcfcfb",
    "axes.facecolor": "#fcfcfb",
})


def pct(x):
    return 100.0 * x


def err(rec, key="span"):
    lo, hi = rec[f"{key}_ci"]
    r = rec[f"{key}_recall"] if key != "strict" else rec["strict_span_recall"]
    # Wilson intervals from the scorer are not always centred on the point estimate
    return pct(r), [[max(0.0, pct(r - lo))], [max(0.0, pct(hi - r))]]


def grouped_bars(ax, groups, series, getter, title, ylabel="recall (%)", floor=99.5,
                 annotate=True, ylim=(0, 105)):
    """groups: list of x labels; series: list of (name, colour); getter(series_name, group)
    -> (value, yerr, n) or None."""
    n_s = len(series)
    w = 0.8 / n_s
    for i, (sname, col) in enumerate(series):
        xs, ys, es, ns = [], [], [], []
        for g_i, g in enumerate(groups):
            got = getter(sname, g)
            if got is None:
                continue
            v, e, n = got
            xs.append(g_i - 0.4 + w * (i + 0.5))
            ys.append(v)
            es.append(e)
            ns.append(n)
        if not xs:
            continue
        yerr = [[e[0][0] for e in es], [e[1][0] for e in es]] if es and es[0] is not None else None
        ax.bar(xs, ys, width=w * 0.92, color=col, label=sname, yerr=yerr,
               error_kw=dict(ecolor=INK2, elinewidth=0.8, capsize=2))
        if annotate:
            for x, y, n in zip(xs, ys, ns):
                ax.text(x, min(y, ylim[1] - 4) + 1.2, f"{y:.0f}\nn={n}", ha="center", va="bottom",
                        fontsize=5.5, color=INK2, rotation=90 if n_s >= 4 else 0)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups, fontsize=8)
    ax.set_ylim(*ylim)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left")
    if floor is not None:
        ax.axhline(floor, ls="--", lw=0.8, color=INK2)
        ax.text(len(groups) - 0.5, floor + 0.8, f"{floor}% floor", ha="right", fontsize=7, color=INK2)
    ax.grid(axis="y", color=HAIR, lw=0.6)
    ax.set_axisbelow(True)


def main():
    m = json.loads(METRICS.read_text())
    D = m["datasets"]
    P = m["pooled"]
    run = m["run"]

    fig = plt.figure(figsize=(20, 24))
    gs = GridSpec(5, 3, figure=fig, hspace=0.55, wspace=0.28,
                  left=0.045, right=0.985, top=0.95, bottom=0.03)

    fig.suptitle(
        "edshield 0.2.0 genre-shift experiment — every measurement in results/metrics.json",
        x=0.045, ha="left", fontsize=15, fontweight="bold", color=INK, y=0.985)
    fig.text(0.045, 0.967,
             f"model {run['model_id']} @ {run['model_revision'][:7]} · policy {run['policy']} · "
             f"plant seed {m['seed']} · {run['device']} ({run['versions'].get('gpu','')}) · "
             f"run {run['started']} → {run['finished']} · bars = span recall, whiskers = 95% Wilson CI",
             fontsize=9, color=INK2)

    # ---- 1. four recall definitions, per dataset, all identifiers ----
    ax = fig.add_subplot(gs[0, 0])
    sets = ["piilo_holdout", "comta", "mathdial", "pooled"]
    defs = [("span", "span"), ("strict", "strict span"), ("mention", "mention"), ("token", "token")]

    def g1(sname, g):
        key = {"span": "span", "strict span": "strict", "mention": "mention", "token": "token"}[sname]
        rec = (P if g == "pooled" else D[g])["all_identifiers"]
        v, e = err(rec, key)
        return v, e, rec["n"] if key != "token" else rec["n_tokens"]

    grouped_bars(ax, [LABEL[s] for s in sets], [(d[1], c) for d, c in zip(defs, ["#2a78d6", "#6250d6", "#1baf7a", "#eda100"])],
                 lambda s, g: g1(s, sets[[LABEL[x] for x in sets].index(g)]),
                 "1. Recall, four definitions — all planted identifiers", ylim=(60, 103))
    ax.legend(fontsize=7, frameon=False, loc="lower left", ncol=2)

    # ---- 2. recall by label, pooled + per dataset ----
    ax = fig.add_subplot(gs[0, 1])
    labels = list(P["by_label"].keys())

    def g2(sname, g):
        src = P if sname == "pooled" else D[sname]
        rec = src["by_label"].get(g)
        if rec is None:
            return None
        v, e = err(rec)
        return v, e, rec["n"]

    grouped_bars(ax, labels, [("comta", C["comta"]), ("mathdial", C["mathdial"]), ("pooled", C["pooled"])],
                 g2, "2. Recall by identifier label", ylim=(60, 103))
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.legend(fontsize=7, frameon=False, loc="lower left", ncol=3)

    # ---- 3. student names by category — all mentions vs base form ----
    ax = fig.add_subplot(gs[0, 2])
    cats = ["anglo_common", "non_anglo", "name_word_collision", "nicknames_and_variants"]
    series3 = [("comta · all mentions", C["comta"]), ("comta · base form", "#9ec5f4"),
               ("mathdial · all mentions", C["mathdial"]), ("mathdial · base form", "#f7b79a")]

    def g3(sname, g):
        ds = "comta" if sname.startswith("comta") else "mathdial"
        key = "base_form_names_by_category" if "base" in sname else "names_by_category"
        rec = D[ds][key][g]
        v, e = err(rec)
        return v, e, rec["n"]

    grouped_bars(ax, [c.replace("_", "\n") for c in cats], series3,
                 lambda s, g: g3(s, cats[[c.replace("_", "\n") for c in cats].index(g)]),
                 "3. Student-name recall by name category", ylim=(50, 103))
    ax.legend(fontsize=7, frameon=False, loc="lower left", ncol=2)

    # ---- 4. by position / nickname form / speaker / case — per dataset ----
    ax = fig.add_subplot(gs[1, :2])
    groups4 = []
    for sect, keys in [("names_by_position", ["first", "later", "nickname"]),
                       ("nicknames_by_form", ["all_caps", "initial", "truncated"]),
                       ("names_by_speaker", ["student", "tutor"]),
                       ("names_by_case", ["capitalised", "lowercase"])]:
        for k in keys:
            groups4.append((sect, k))
    gl = [f"{k}\n({sect.replace('names_by_','').replace('nicknames_by_','nick ')})" for sect, k in groups4]

    def g4(sname, g):
        sect, k = groups4[gl.index(g)]
        src = P if sname == "pooled" else D[sname]
        rec = src.get(sect, {}).get(k)
        if rec is None:
            return None
        v, e = err(rec)
        return v, e, rec["n"]

    grouped_bars(ax, gl, [("comta", C["comta"]), ("mathdial", C["mathdial"]), ("pooled", C["pooled"])],
                 g4, "4. Student-name recall by mention position, nickname form, speaker, and letter case",
                 ylim=(0, 108))
    ax.legend(fontsize=7, frameon=False, loc="lower left", ncol=3)

    # ---- 5. precision ----
    ax = fig.add_subplot(gs[1, 2])
    sets5 = ["piilo_holdout", "comta", "mathdial"]

    def g5(sname, g):
        ds = sets5[[LABEL[x] for x in sets5].index(g)]
        d = D[ds]
        if sname == "span precision":
            rec = d["precision"]
            lo, hi = rec["span_ci"]
            v = rec["span_precision"]
            return pct(v), [[max(0.0, pct(v - lo))], [max(0.0, pct(hi - v))]], rec["n_acted"]
        rec = d.get("name_precision")
        if rec is None:
            return None
        lo, hi = rec["ci"]
        v = rec["precision"]
        return pct(v), [[max(0.0, pct(v - lo))], [max(0.0, pct(hi - v))]], rec["n_acted"]

    grouped_bars(ax, [LABEL[s] for s in sets5], [("span precision", "#6250d6"), ("name precision", "#e87ba4")],
                 g5, "5. Precision (flags overlapping gold / flags)", ylabel="precision (%)", floor=None,
                 ylim=(0, 108))
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    ax.text(0.02, 0.97, "PIILO span precision is not comparable:\ncoppa policy masks DATE/AGE/LOCATION,\nwhich PIILO gold does not annotate",
            transform=ax.transAxes, fontsize=6.5, va="top", color=MUTED)

    # ---- 6. over-redaction on control, stacked by tag ----
    ax = fig.add_subplot(gs[2, 0])
    sets6 = ["piilo_holdout", "comta", "mathdial"]
    tags = ["problem_name", "persona", "curricular", "other"]
    tagc = {"problem_name": "#eb6834", "persona": "#eda100", "curricular": "#e34948", "other": "#898781"}
    bottoms = [0.0] * len(sets6)
    for t in tags:
        vals = []
        for ds in sets6:
            o = D[ds]["over_redaction"]
            vals.append(1000.0 * o["by_tag"].get(t, 0) / o["n_tokens"])
        ax.bar(range(len(sets6)), vals, bottom=bottoms, color=tagc[t], label=t, width=0.6)
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    for i, ds in enumerate(sets6):
        o = D[ds]["over_redaction"]
        ax.text(i, bottoms[i] + 0.3, f"{o['flags_per_1000_tokens']:.2f}/1k\n{o['n_flags']} flags · "
                f"{o['n_tokens']:,} tok", ha="center", va="bottom", fontsize=6.5, color=INK2)
    ax.set_xticks(range(len(sets6)))
    ax.set_xticklabels([LABEL[s] for s in sets6], fontsize=8)
    ax.set_ylabel("non-gold flags per 1,000 tokens")
    ax.set_title("6. Over-redaction on untouched control, by tag", loc="left")
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    ax.grid(axis="y", color=HAIR, lw=0.6)
    ax.set_axisbelow(True)

    # ---- 7. over-redaction by predicted label ----
    ax = fig.add_subplot(gs[2, 1])
    all_labels = sorted({k for ds in sets6 for k in D[ds]["over_redaction"]["by_label"]})
    w = 0.8 / len(sets6)
    for i, ds in enumerate(sets6):
        o = D[ds]["over_redaction"]
        vals = [1000.0 * o["by_label"].get(l, 0) / o["n_tokens"] for l in all_labels]
        ax.bar([j - 0.4 + w * (i + 0.5) for j in range(len(all_labels))], vals, width=w * 0.92,
               color=C[ds], label=ds)
    ax.set_xticks(range(len(all_labels)))
    ax.set_xticklabels(all_labels, rotation=45, ha="right", fontsize=7)
    ax.set_yscale("symlog", linthresh=0.1)
    ax.set_ylabel("flags per 1,000 tokens (symlog)")
    ax.set_title("7. Over-redaction by predicted label", loc="left")
    ax.legend(fontsize=7, frameon=False)
    ax.grid(axis="y", color=HAIR, lw=0.6)
    ax.set_axisbelow(True)

    # ---- 8. miss reasons (pooled) ----
    ax = fig.add_subplot(gs[2, 2])
    mr = P["miss_reasons"]
    ks = sorted(mr, key=mr.get, reverse=True)
    ax.barh(ks[::-1], [mr[k] for k in ks[::-1]], color="#e34948", height=0.6)
    for k in ks:
        ax.text(mr[k] + 2, k, str(mr[k]), va="center", fontsize=8, color=INK2)
    ax.set_title(f"8. Assigned reason for each missed span (pooled, n={sum(mr.values())})", loc="left")
    ax.set_xlabel("misses")
    ax.text(0.98, 0.04, f"partial residuals: {P['partial_residuals']}\n(span caught, surname survived)",
            transform=ax.transAxes, ha="right", fontsize=7, color=MUTED)
    ax.grid(axis="x", color=HAIR, lw=0.6)
    ax.set_axisbelow(True)

    # ---- 9. what was planted ----
    ax = fig.add_subplot(gs[3, 0])
    kinds = ["first", "later", "nickname", "related", "school", "username", "email", "phone"]
    w = 0.4
    for i, ds in enumerate(["comta", "mathdial"]):
        sk = D[ds]["plant"]["spans_by_kind"]
        ax.bar([j - 0.2 + w * i for j in range(len(kinds))], [sk.get(k, 0) for k in kinds], width=w * 0.92,
               color=C[ds], label=f"{ds} ({D[ds]['plant']['dialogues']} dialogues)")
    ax.set_xticks(range(len(kinds)))
    ax.set_xticklabels(kinds, fontsize=8)
    ax.set_ylabel("planted spans")
    ax.set_title("9. Planted spans by kind", loc="left")
    ax.legend(fontsize=7, frameon=False)
    ax.grid(axis="y", color=HAIR, lw=0.6)
    ax.set_axisbelow(True)

    # ---- 10. dialogues by category + register ----
    ax = fig.add_subplot(gs[3, 1])
    w = 0.4
    for i, ds in enumerate(["comta", "mathdial"]):
        dc = D[ds]["plant"]["dialogues_by_category"]
        ax.bar([j - 0.2 + w * i for j in range(len(cats))], [dc.get(k, 0) for k in cats], width=w * 0.92,
               color=C[ds], label=ds)
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels([c.replace("_", "\n") for c in cats], fontsize=8)
    ax.set_ylabel("dialogues")
    ax.set_title("10. Dialogues assigned per name category · student-turn register", loc="left")
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    reg = "\n".join(
        f"{ds}: {D[ds]['plant']['register']['n_student_turns']} student turns · "
        f"{pct(D[ds]['plant']['register']['lowercase_start']):.0f}% start lowercase · "
        f"{pct(D[ds]['plant']['register']['no_terminal_punct']):.0f}% no final punctuation"
        for ds in ["comta", "mathdial"])
    ax.text(0.98, 0.97, reg, transform=ax.transAxes, ha="right", va="top", fontsize=7, color=INK2)
    ax.grid(axis="y", color=HAIR, lw=0.6)
    ax.set_axisbelow(True)

    # ---- 11. top over-redaction terms ----
    ax = fig.add_subplot(gs[3, 2])
    ax.axis("off")
    ax.set_title("11. Most-flagged non-gold terms on control", loc="left")
    y = 0.95
    for ds in sets6:
        terms = D[ds]["over_redaction"]["top_terms"][:10]
        ax.text(0.0, y, ds, fontsize=8, fontweight="bold", color=C[ds], transform=ax.transAxes, va="top")
        ax.text(0.22, y, "  ".join(f"{t}×{n}" for t, n in terms), fontsize=7, color=INK2,
                transform=ax.transAxes, va="top", wrap=True)
        y -= 0.33

    # ---- 12. control flag examples ----
    ax = fig.add_subplot(gs[4, :2])
    ax.axis("off")
    ax.set_title("12. Control-flag examples recorded by the scorer (first eight per dataset)", loc="left")
    y = 0.95
    for ds in ["comta", "mathdial"]:
        ex = D[ds].get("control_flag_examples", [])[:8]
        ax.text(0.0, y, ds, fontsize=8, fontweight="bold", color=C[ds], transform=ax.transAxes, va="top")
        lines = []
        for e in ex:
            if isinstance(e, dict):
                lines.append(" · ".join(f"{k}={str(v)[:60]}" for k, v in e.items()))
            else:
                lines.append(str(e)[:140])
        ax.text(0.07, y, "\n".join(lines), fontsize=6.5, color=INK2, transform=ax.transAxes, va="top",
                family="DejaVu Sans Mono")
        y -= 0.5

    # ---- 13. run / timing ----
    ax = fig.add_subplot(gs[4, 2])
    ax.axis("off")
    ax.set_title("13. Sets scored and wall time", loc="left")
    rows = [(k, v["docs"], v["seconds"]) for k, v in m["sets"].items()]
    txt = "\n".join(f"{k:<24} {d:>5} docs  {s:>6.1f} s" for k, d, s in rows)
    vers = run["versions"]
    txt += "\n\n" + "\n".join(f"{k:<16} {v}" for k, v in vers.items())
    ax.text(0.0, 0.97, txt, transform=ax.transAxes, va="top", fontsize=7.5, family="DejaVu Sans Mono", color=INK2)

    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
