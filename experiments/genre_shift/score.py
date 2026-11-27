"""Score the stored runs: recall with Wilson intervals by dataset, name
category, mention position, speaker and label; precision on the planted set;
over-redaction on the control; PIILO in-domain reference on the same metrics.

    python score.py

Reads data/planted, data/control, results/raw/*.jsonl, results/run_meta.json.
Writes results/metrics.json, results/report.md, results/misses.csv,
results/recall_by_category.png.

Definitions
  span recall    a gold span counts as recalled when its text no longer occurs
                 as a whole word in the de-identified output (edshield-evidence's
                 residual rule, the repo's "honest number"); a surviving surname
                 after a masked first name is a partial residual, not a recall.
  token recall   a whitespace token inside a gold span counts when an acted-on
                 entity covers it.
  precision      share of acted-on entities (spans) / flagged tokens overlapping
                 a gold span, on the planted set; MathDial word-problem character
                 names are reported separately, not as misses or hits.
  over-redaction acted-on entities per 1,000 whitespace tokens on the control,
                 split into curricular terms, pre-existing simulated-student
                 persona names (MathDial), word-problem character names (MathDial)
                 and other.
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from edshield_evidence.residual import score_document

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"
RAW = RESULTS / "raw"
CATEGORIES = ("anglo_common", "non_anglo", "name_word_collision", "nicknames_and_variants")
DATASET_ORDER = ["piilo_holdout", "comta", "mathdial", "studychat", "tscc"]
NAME_KINDS = ("first", "later", "nickname")
TOKEN = re.compile(r"\S+")
WORD = re.compile(r"[A-Za-z][A-Za-z'.-]*")


class Result:
    """What edshield returned, shaped the way residual.score_document expects."""

    def __init__(self, row: dict):
        self.deidentified_text = row["output"]
        self.entities = [type("E", (), e)() for e in row["entities"]]
        self.replacements = None
        self.leaks = []


def wilson(k: int, n: int, z: float = 1.959964) -> Tuple[float, float, float]:
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def curricular_terms() -> List[str]:
    return [l.strip() for l in (HERE / "names" / "curricular_terms.txt").read_text(encoding="utf-8").splitlines() if l.strip()]


# --- per-document scoring ------------------------------------------------------

def gold_tokens(text: str, s: int, e: int) -> List[Tuple[int, int]]:
    return [(s + m.start(), s + m.end()) for m in TOKEN.finditer(text[s:e])]


def covered(ts: int, te: int, entities) -> bool:
    return any(int(x.start) < te and ts < int(x.end) for x in entities)


def context(text: str, s: int, e: int, n: int = 20) -> str:
    before = text[:s].split()[-n:]
    after = text[e:].split()[:n]
    return " ".join(before) + " [[" + text[s:e] + "]] " + " ".join(after)


def score_set(docs: List[dict], rows: Dict[str, dict]) -> List[dict]:
    """One record per gold span with everything the breakdowns need, plus one
    per acted-on entity for precision / over-redaction."""
    out = []
    for d in docs:
        row = rows.get(d["doc_id"])
        if row is None:
            continue
        res = Result(row)
        gold = [tuple(g) for g in d["gold_spans"]]
        sc = score_document(d["doc_id"], d["text"], gold, res)
        meta_spans = d.get("meta", {}).get("spans") or [{} for _ in gold]
        for ident, m in zip(sc.identifiers, meta_spans):
            toks = gold_tokens(d["text"], ident.start, ident.end)
            n_cov = sum(covered(a, b, res.entities) for a, b in toks)
            out.append({"doc_id": d["doc_id"], "dataset": d["meta"].get("dataset", "piilo_holdout"),
                        "category": d["meta"].get("category", "in_domain"), "kind": m.get("kind", "gold"),
                        "speaker": m.get("speaker", "essay"), "label": ident.label, "text": ident.text,
                        "start": ident.start, "end": ident.end, "span_hit": not ident.full_residual,
                        "partial": ident.partial, "tokens": len(toks), "tokens_hit": n_cov,
                        "mention_hit": bool(toks) and n_cov == len(toks),
                        "touched": ident.touched, "context": context(d["text"], ident.start, ident.end)})
    return out


def entity_records(docs: List[dict], rows: Dict[str, dict], terms: List[str]) -> List[dict]:
    """Every acted-on entity, tagged: gold (overlaps a gold span), curricular,
    persona, problem_name, or other."""
    term_set = {t.lower() for t in terms}
    out = []
    for d in docs:
        row = rows.get(d["doc_id"])
        if row is None:
            continue
        gold = [tuple(g) for g in d["gold_spans"]]
        meta = d.get("meta", {})
        persona = (meta.get("persona_name") or "").lower()
        problem = {p.lower() for p in (meta.get("problem_names") or [])}
        n_tokens = len(TOKEN.findall(d["text"]))
        for e in row["entities"]:
            s, t, txt = e["start"], e["end"], e["text"]
            low = txt.lower().strip(" .,!?")
            words = {w.lower().strip(".") for w in WORD.findall(txt)}
            if any(s < ge and gs < t for gs, ge, _ in gold):
                tag = "gold"
            elif low in term_set or (words & term_set) or any(low.startswith(x + "'") for x in term_set):
                tag = "curricular"
            elif persona and persona in words:
                tag = "persona"
            elif problem and (words & problem):
                tag = "problem_name"
            else:
                tag = "other"
            out.append({"doc_id": d["doc_id"], "dataset": meta.get("dataset", "piilo_holdout"), "label": e["label"],
                        "text": txt, "source": e["source"], "tag": tag, "n_tokens_doc": n_tokens,
                        "context": context(d["text"], s, t, 8)})
    return out


# --- aggregation ---------------------------------------------------------------

def agg(records: List[dict]) -> dict:
    n = len(records)
    k = sum(r["span_hit"] for r in records)
    ks = sum(r["span_hit"] and not r["partial"] for r in records)
    tk = sum(r["tokens"] for r in records)
    tkh = sum(r["tokens_hit"] for r in records)
    km = sum(r["mention_hit"] for r in records)
    p, lo, hi = wilson(k, n)
    sp, slo, shi = wilson(ks, n)
    mp, mlo, mhi = wilson(km, n)
    tp, tlo, thi = wilson(tkh, tk)
    return {"n": n, "span_recall": p, "span_ci": [lo, hi], "strict_span_recall": sp, "strict_ci": [slo, shi],
            "n_partial": k - ks, "mention_recall": mp, "mention_ci": [mlo, mhi],
            "n_tokens": tk, "token_recall": tp, "token_ci": [tlo, thi]}


def nickname_form(text: str) -> str:
    if text.endswith("."):
        return "initial"
    if len(text) > 1 and text.isupper():
        return "all_caps"
    return "truncated"


def name_precision(ents: List[dict]) -> dict:
    """Precision of the name labels alone (NAME_STUDENT, NAME_RELATED): acted
    name spans that overlap a gold span, excluding word-problem characters."""
    acted = [e for e in ents if e["label"] in ("NAME_STUDENT", "NAME_RELATED") and e["tag"] != "problem_name"]
    k = sum(e["tag"] == "gold" for e in acted)
    p, lo, hi = wilson(k, len(acted))
    return {"n_acted": len(acted), "n_gold_overlap": k, "precision": p, "ci": [lo, hi],
            "false_positive_tags": dict(Counter(e["tag"] for e in acted if e["tag"] != "gold"))}


def breakdown(records: List[dict], key) -> Dict[str, dict]:
    groups = defaultdict(list)
    for r in records:
        groups[key(r)].append(r)
    return {g: agg(v) for g, v in sorted(groups.items())}


def precision(ents: List[dict], gold_records: List[dict]) -> dict:
    acted = [e for e in ents if e["tag"] != "problem_name"]
    n = len(acted)
    k = sum(e["tag"] == "gold" for e in acted)
    p, lo, hi = wilson(k, n)
    return {"n_acted": n, "n_gold_overlap": k, "span_precision": p, "span_ci": [lo, hi],
            "false_positive_tags": dict(Counter(e["tag"] for e in acted if e["tag"] != "gold")),
            "excluded_problem_names": sum(e["tag"] == "problem_name" for e in ents)}


def over_redaction(ents: List[dict], docs: List[dict]) -> dict:
    n_tokens = sum(len(TOKEN.findall(d["text"])) for d in docs)
    tags = Counter(e["tag"] for e in ents)
    n = len(ents)
    rate = 1000 * n / n_tokens if n_tokens else float("nan")
    top = Counter(e["text"].strip().lower() for e in ents if e["tag"] in ("curricular", "other")).most_common(15)
    return {"n_docs": len(docs), "n_tokens": n_tokens, "n_flags": n, "flags_per_1000_tokens": rate,
            "by_tag": dict(tags), "share_curricular": (tags["curricular"] / n) if n else float("nan"),
            "share_curricular_ci": list(wilson(tags["curricular"], n)[1:]) if n else [float("nan")] * 2,
            "by_label": dict(Counter(e["label"] for e in ents)), "top_terms": top}


# --- miss reasons --------------------------------------------------------------

COLLISION_WORDS = None


def miss_reason(r: dict, doc_records: List[dict], collision_names: set, terms: set) -> str:
    """One word per missed span, assigned by these rules and checked by reading
    every miss (overrides in REASON_OVERRIDES where a rule is wrong for a span):
      rule_gap      a rule-only label (SCHOOL) whose rule did not fire
      elsewhere     this mention was masked, but the same string survives
                    elsewhere in the document (an unmasked other mention, or
                    a common word for collision names), so the identifier is
                    still present; the residual rule counts it as a miss
      nickname      a nickname, initial, ALL-CAPS or truncated form, or a
                    nickname-category base name (Nat, Vee, Ty)
      collision     the name is also a word or curricular term
      typo          the planted name carried a typo
      lowercase     written in lowercase and the capitalised mentions of the
                    same name in the document were caught
      non_anglo     a non-Anglo name, caught in no form
      position      a first mention missed while later mentions were caught
      other         none of the above
    """
    key = (r["doc_id"], r["start"])
    if key in REASON_OVERRIDES:
        return REASON_OVERRIDES[key]
    txt = r["text"]
    first = txt.split()[0] if txt.split() else txt
    base = first.lower().strip(".")
    same = [x for x in doc_records if x is not r and x["text"].split()[0].lower().strip(".") == base]
    is_collision = base in terms or base in {c.lower() for c in collision_names}
    if r["label"] == "SCHOOL":
        return "rule_gap"
    if r["mention_hit"]:
        return "collision" if is_collision else "elsewhere"
    if r["kind"] == "nickname":
        return "nickname"
    if is_collision:
        return "collision"
    if r.get("typo"):
        return "typo"
    if r["category"] == "nicknames_and_variants" and r["label"] in ("NAME_STUDENT", "NAME_RELATED"):
        return "nickname"
    caps_same = [x for x in same if x["text"][:1].isupper()]
    if txt[:1].islower() and (not caps_same or any(x["mention_hit"] for x in caps_same)):
        return "lowercase"
    if r["category"] == "non_anglo":
        return "non_anglo"
    if r["kind"] == "first" and any(x["mention_hit"] for x in same):
        return "position"
    return "other"


REASON_OVERRIDES: Dict[Tuple[str, int], str] = {}


# --- report ----------------------------------------------------------------------

def pct(x: float) -> str:
    return "n/a" if x != x else f"{100 * x:.1f}%"


def ci(a: dict, which: str = "span") -> str:
    lo, hi = a[f"{which}_ci" if which else "ci"]
    return f"{pct(lo)} – {pct(hi)}"


def table(rows: List[List[str]], header: List[str]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def chart(metrics: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    datasets = [d for d in DATASET_ORDER if d in metrics["datasets"]]
    cats = ["in_domain"] + list(CATEGORIES)
    labels = {"in_domain": "PIILO in-domain (all names)", "anglo_common": "anglo_common", "non_anglo": "non_anglo",
              "name_word_collision": "name_word_collision", "nicknames_and_variants": "nicknames_and_variants"}
    colors = {"in_domain": "#6b6b6b", "anglo_common": "#4c72b0", "non_anglo": "#dd8452",
              "name_word_collision": "#c44e52", "nicknames_and_variants": "#8172b3"}
    width = 0.17
    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = np.arange(len(datasets))
    for j, c in enumerate(cats):
        xs, ys, los, his = [], [], [], []
        for i, ds in enumerate(datasets):
            a = metrics["datasets"][ds]["names_by_category"].get(c)
            if not a or a["n"] == 0:
                continue
            xs.append(x[i] + (j - 2) * width)
            ys.append(100 * a["span_recall"])
            los.append(100 * (a["span_recall"] - a["span_ci"][0]))
            his.append(100 * (a["span_ci"][1] - a["span_recall"]))
        if xs:
            ax.bar(xs, ys, width, yerr=[los, his], capsize=3, label=labels[c], color=colors[c])
            aa = [metrics["datasets"][d]["names_by_category"].get(c) for d in datasets if metrics["datasets"][d]["names_by_category"].get(c)]
            for xi, yi, hi, a in zip(xs, ys, his, aa):
                ax.text(xi, yi + hi + 1.0, f"{yi:.0f}%\nn={a['n']}", ha="center", va="bottom", fontsize=7)
    ax.axhline(99.5, color="k", ls="--", lw=0.8)
    ax.text(0.5, 99.8, "99.5% floor", va="bottom", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(["PIILO holdout\n(in-domain, all names)" if d == "piilo_holdout" else d for d in datasets])
    ax.set_ylabel("span-level recall on planted student names (%)")
    ax.set_ylim(0, 118)
    ax.set_title(f"edshield 0.2.0 name recall by name category, 95% Wilson intervals (seed {metrics['seed']})")
    ax.legend(loc="upper center", fontsize=8, ncol=5, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main() -> int:
    terms = curricular_terms()
    term_set = {t.lower() for t in terms}
    collision = {l.split()[0] for l in (HERE / "names" / "name_word_collision.txt").read_text(encoding="utf-8").splitlines() if l.strip()}
    run_meta = json.loads((RESULTS / "run_meta.json").read_text(encoding="utf-8"))
    plant_log = json.loads((DATA / "plant_log.json").read_text(encoding="utf-8"))
    typo_slots = {(p["dialogue_id"], s["turn"]) for ds in plant_log["datasets"].values() for p in ds.get("plans", [])
                  for s in p["slots"] if s.get("typo")}

    metrics = {"seed": plant_log["seed"], "run": {k: v for k, v in run_meta.items() if k != "sets"},
               "sets": run_meta["sets"], "datasets": {}, "pooled": {}}
    all_gold: List[dict] = []
    misses: List[dict] = []

    # PIILO in-domain reference
    piilo_rows = {r["doc_id"]: r for r in read_jsonl(RAW / "piilo__piilo_holdout.jsonl")}
    if piilo_rows:
        from edshield_evidence.datasets import load_piilo_holdout
        ds = load_piilo_holdout()
        docs = [dict(d.to_record(), meta={"dataset": "piilo_holdout"}) for d in ds.docs]
        g = score_set(docs, piilo_rows)
        ents = entity_records(docs, piilo_rows, terms)
        names = [r for r in g if r["label"] == "NAME_STUDENT"]
        non_gold = [e for e in ents if e["tag"] != "gold"]
        metrics["datasets"]["piilo_holdout"] = {
            "role": "in-domain reference (680 held-out PIILO essays, real genre the model was trained on)",
            "n_docs": len(docs), "all_identifiers": agg(g), "student_names": agg(names),
            "names_by_category": {"in_domain": agg(names)}, "by_label": breakdown(g, lambda r: r["label"]),
            "precision": {"note": "against PIILO's seven gold labels; the coppa policy also masks DATE, AGE, LOCATION, "
                                  "which PIILO does not annotate, so span precision here is not comparable", **precision(ents, g)},
            "name_precision": name_precision(ents),
            "over_redaction": {"note": "flags not overlapping any gold span, per 1,000 tokens, on the same essays",
                               **over_redaction(non_gold, docs)},
        }

    # dialogue sets
    for name in DATASET_ORDER[1:]:
        docs = read_jsonl(DATA / "planted" / f"{name}.jsonl")
        if not docs:
            continue
        rows = {r["doc_id"]: r for r in read_jsonl(RAW / f"planted__{name}.jsonl")}
        g = score_set(docs, rows)
        turn_of = {}
        for d in docs:
            for s in d["meta"]["spans"]:
                turn_of[(d["doc_id"], s["start"])] = s["turn_idx"]
        for r in g:
            r["typo"] = (r["doc_id"], turn_of.get((r["doc_id"], r["start"]))) in typo_slots and r["kind"] in ("first", "related")
        ents = entity_records(docs, rows, terms)
        names = [r for r in g if r["kind"] in NAME_KINDS]
        ctrl_docs = read_jsonl(DATA / "control" / f"{name}.jsonl")
        ctrl_rows = {r["doc_id"]: r for r in read_jsonl(RAW / f"control__{name}.jsonl")}
        ctrl_ents = entity_records(ctrl_docs, ctrl_rows, terms)
        metrics["datasets"][name] = {
            "n_docs": len(docs), "plant": {k: v for k, v in plant_log["datasets"][name].items() if k != "plans"},
            "all_identifiers": agg(g), "student_names": agg(names),
            "related_names": agg([r for r in g if r["kind"] == "related"]),
            "names_by_category": breakdown(names, lambda r: r["category"]),
            "base_form_names_by_category": breakdown([r for r in names if r["kind"] != "nickname"], lambda r: r["category"]),
            "names_by_position": breakdown(names, lambda r: r["kind"]),
            "nicknames_by_form": breakdown([r for r in names if r["kind"] == "nickname"], lambda r: nickname_form(r["text"])),
            "names_by_speaker": breakdown(names, lambda r: r["speaker"]),
            "names_by_case": breakdown(names, lambda r: "lowercase" if r["text"][:1].islower() else "capitalised"),
            "by_label": breakdown(g, lambda r: r["label"]),
            "precision": precision(ents, g),
            "name_precision": name_precision(ents),
            "over_redaction": over_redaction(ctrl_ents, ctrl_docs),
            "control_flag_examples": [{"text": e["text"], "label": e["label"], "tag": e["tag"], "context": e["context"]}
                                      for e in ctrl_ents if e["tag"] in ("curricular", "other")][:25],
        }
        all_gold += g
        by_doc = defaultdict(list)
        for r in g:
            by_doc[r["doc_id"]].append(r)
        for r in g:
            if not r["span_hit"]:
                misses.append(dict(r, reason=miss_reason(r, by_doc[r["doc_id"]], collision, term_set)))

    pooled_names = [r for r in all_gold if r["kind"] in NAME_KINDS]
    metrics["pooled"] = {
        "datasets": [n for n in DATASET_ORDER[1:] if n in metrics["datasets"]],
        "all_identifiers": agg(all_gold), "student_names": agg(pooled_names),
        "related_names": agg([r for r in all_gold if r["kind"] == "related"]),
        "names_by_category": breakdown(pooled_names, lambda r: r["category"]),
        "base_form_names_by_category": breakdown([r for r in pooled_names if r["kind"] != "nickname"], lambda r: r["category"]),
        "names_by_position": breakdown(pooled_names, lambda r: r["kind"]),
        "nicknames_by_form": breakdown([r for r in pooled_names if r["kind"] == "nickname"], lambda r: nickname_form(r["text"])),
        "names_by_speaker": breakdown(pooled_names, lambda r: r["speaker"]),
        "names_by_case": breakdown(pooled_names, lambda r: "lowercase" if r["text"][:1].islower() else "capitalised"),
        "by_label": breakdown(all_gold, lambda r: r["label"]),
        "miss_reasons": dict(Counter(m["reason"] for m in misses)),
        "partial_residuals": sum(1 for r in all_gold if r["partial"]),
    }
    metrics["blocked"] = {k: v.get("note") for k, v in plant_log["datasets"].items() if v.get("note")}

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")

    with (RESULTS / "misses.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "dataset", "category", "kind", "speaker", "label", "gold_text", "touched_labels",
                    "this_mention_masked", "reason", "context_20_tokens"])
        for m in sorted(misses, key=lambda r: (r["dataset"], r["doc_id"], r["start"])):
            w.writerow([m["doc_id"], m["dataset"], m["category"], m["kind"], m["speaker"], m["label"], m["text"],
                        "+".join(m["touched"]), "yes" if m["mention_hit"] else "no", m["reason"], m["context"]])

    chart(metrics, RESULTS / "recall_by_category.png")
    (RESULTS / "report.md").write_text(report(metrics), encoding="utf-8")
    print(f"gold spans {len(all_gold)}, misses {len(misses)}, reasons {metrics['pooled']['miss_reasons']}")
    return 0


def report(m: dict) -> str:
    run = m["run"]
    L = [f"# Genre-shift experiment: edshield 0.2.0 on real tutoring dialogue with planted identifiers", "",
         f"Model: `{run['model_id']}` revision `{run['model_revision']}` (weights sha256 `{run['model_sha256'][:16]}…`), "
         f"rules + model, python runtime on `{run['device']}` ({run['versions'].get('gpu', '')}). "
         f"Policy `{run['policy']}` sha256 `{run['policy_sha256'][:16]}…`. edshield {run['versions']['edshield']}, "
         f"torch {run['versions']['torch']}, transformers {run['versions']['transformers']}. Plant seed {m['seed']}, decode seed {run['seed']}.",
         "", "Span recall: gold text no longer occurs whole in the output. Token recall: gold tokens covered by an acted-on entity. "
         "95% Wilson intervals. Over-redaction: acted-on entities per 1,000 whitespace tokens on the untouched control.", ""]
    if m.get("blocked"):
        L += ["Not run: " + "; ".join(f"{k} ({v})" for k, v in m["blocked"].items()), ""]

    L += ["## Recall, in-domain vs real dialogue", ""]
    rows = []
    for ds in [d for d in DATASET_ORDER if d in m["datasets"]] + ["pooled dialogue"]:
        a = m["pooled"] if ds == "pooled dialogue" else m["datasets"][ds]
        rows.append([ds, a["all_identifiers"]["n"], pct(a["all_identifiers"]["span_recall"]), ci(a["all_identifiers"]),
                     pct(a["all_identifiers"]["strict_span_recall"]), pct(a["all_identifiers"]["mention_recall"]),
                     pct(a["all_identifiers"]["token_recall"]),
                     a["student_names"]["n"], pct(a["student_names"]["span_recall"]), ci(a["student_names"]),
                     pct(a["student_names"]["mention_recall"])])
    L += [table(rows, ["set", "identifiers", "span recall", "95% CI", "strict (no surname left)", "mention recall", "token recall",
                       "student names", "span recall", "95% CI", "mention recall"]), ""]
    L += ["Span recall is the residual rule: the identifier's text no longer occurs whole anywhere in the output, so one "
          "surviving mention of a name fails every mention of it. Strict span recall also fails a full-name mention whose "
          "surname survived (`[CHILD] Green`). Mention recall is per planted span: every token of that mention was covered "
          "by an acted-on entity, whatever happened elsewhere in the document; the position and form breakdowns below use it.", ""]

    L += ["## Student-name recall by name category (span level)", "",
          "All mentions, then base-form mentions only (first and later mentions, no nickname/initial forms), "
          "since nickname forms are drawn uniformly across categories and dominate the misses.", ""]
    rows = []
    for ds in [d for d in DATASET_ORDER[1:] if d in m["datasets"]] + ["pooled dialogue"]:
        a = m["pooled"] if ds == "pooled dialogue" else m["datasets"][ds]
        for c in CATEGORIES:
            b = a["names_by_category"].get(c)
            bb = a["base_form_names_by_category"].get(c)
            if b:
                rows.append([ds, c, b["n"], pct(b["span_recall"]), ci(b), pct(b["mention_recall"]),
                             bb["n"] if bb else 0, pct(bb["span_recall"]) if bb else "n/a", ci(bb) if bb else "n/a",
                             pct(bb["mention_recall"]) if bb else "n/a"])
    L += [table(rows, ["set", "category", "n", "span recall", "95% CI", "mention recall", "base-form n", "base-form span recall", "95% CI", "base-form mention recall"]), ""]

    L += ["## Student-name recall by mention position, nickname form, speaker and case", ""]
    rows = []
    for ds in [d for d in DATASET_ORDER[1:] if d in m["datasets"]] + ["pooled dialogue"]:
        a = m["pooled"] if ds == "pooled dialogue" else m["datasets"][ds]
        for k, b in a["names_by_position"].items():
            rows.append([ds, "position: " + k, b["n"], pct(b["mention_recall"]), ci(b, "mention"), pct(b["span_recall"])])
        for k, b in a["nicknames_by_form"].items():
            rows.append([ds, "nickname form: " + k, b["n"], pct(b["mention_recall"]), ci(b, "mention"), pct(b["span_recall"])])
        for k, b in a["names_by_speaker"].items():
            rows.append([ds, "spoken in a " + k + " turn", b["n"], pct(b["mention_recall"]), ci(b, "mention"), pct(b["span_recall"])])
        for k, b in a["names_by_case"].items():
            rows.append([ds, "written " + k, b["n"], pct(b["mention_recall"]), ci(b, "mention"), pct(b["span_recall"])])
    L += [table(rows, ["set", "slice", "n", "mention recall", "95% CI", "span recall (residual rule)"]), ""]

    L += ["## By label", ""]
    rows = []
    for ds in [d for d in DATASET_ORDER if d in m["datasets"]] + ["pooled dialogue"]:
        a = m["pooled"] if ds == "pooled dialogue" else m["datasets"][ds]
        for k, b in a["by_label"].items():
            rows.append([ds, k, b["n"], pct(b["span_recall"]), ci(b)])
    L += [table(rows, ["set", "label", "n", "span recall", "95% CI"]), ""]

    L += ["## Precision on the planted set and over-redaction on the control", ""]
    rows = []
    for ds in [d for d in DATASET_ORDER if d in m["datasets"]]:
        a = m["datasets"][ds]
        p, np_, o = a["precision"], a["name_precision"], a["over_redaction"]
        rows.append([ds, p["n_acted"], pct(p["span_precision"]), np_["n_acted"], pct(np_["precision"]), ci(np_, "") .replace("% – ", "% – "),
                     o["n_tokens"], o["n_flags"], f"{o['flags_per_1000_tokens']:.2f}", pct(o["share_curricular"]),
                     ", ".join(f"{k} {v}" for k, v in sorted(o["by_tag"].items()))])
    L += [table(rows, ["set", "acted spans (planted)", "span precision, all labels", "acted name spans", "name precision", "95% CI",
                       "control tokens", "control flags", "flags / 1,000 tokens", "share on curricular terms", "control flags by tag"]), ""]
    L += ["Precision excludes flags on word-problem characters (`problem_name`); on PIILO the all-label figure is not "
          "comparable because the coppa policy also masks DATE, AGE and LOCATION, which PIILO does not annotate. "
          "`persona` = the MathDial simulated student's own name, left in the control untouched.", ""]
    for ds in [d for d in DATASET_ORDER[1:] if d in m["datasets"]]:
        o = m["datasets"][ds]["over_redaction"]
        L += [f"Most flagged non-gold strings in the {ds} control: " + ", ".join(f"`{t}` ({n})" for t, n in o["top_terms"][:12]), ""]

    L += ["## Misses", "", f"Reason distribution over all missed planted spans: {m['pooled']['miss_reasons']}. "
          f"Partial residuals (surname survived a masked first name): {m['pooled']['partial_residuals']}. See `misses.csv`.", ""]
    L += ["## Chart", "", "![recall by category](recall_by_category.png)", ""]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
