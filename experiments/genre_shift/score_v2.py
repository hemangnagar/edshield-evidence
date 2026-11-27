"""Score every detector's stored spans on one schema: name recall by dataset,
seed and stratum, precision, over-redaction, the floor-transfer test, tables
and the misses file.

    python score_v2.py

Reads data/v2/{planted/<seed>,control}/<dataset>.jsonl, results/v2/raw/<detector>/*.jsonl,
results/v2/meta/*.json. Writes results/v2/metrics.json, results/v2/tables/T*.{csv,md},
results/v2/tables/shared_misses.md, results/v2/misses.csv.

Definitions (also written into metrics.json)
  caught          a gold span is caught when predicted spans of the matching
                  class (NAME for the two name labels) cover at least 50% of its
                  characters. Coverage is the union of predicted spans, so a
                  full name tagged as given name + surname counts.
  exact           some predicted NAME span has exactly the gold boundaries
                  (predicted spans are trimmed of surrounding whitespace first).
  any_label       as `caught`, counting predicted spans of every class.
  pooled CI       95% Wilson interval over all seeds' mentions. The five seeds
                  replant the same dialogues, so mentions are not independent
                  across seeds and the pooled intervals are narrower than a
                  dialogue-level interval would be; mean and SD across seeds
                  are reported beside them.
  lower bound     exact binomial (Clopper-Pearson) one-sided 95% lower bound,
                  the bound the 3/n rule approximates at zero misses.
  precision       predicted NAME spans that overlap a gold name span / all
                  predicted NAME spans, on the planted sets; a second figure
                  leaves word-problem characters out of the denominator (v1).
  over-redaction  predicted NAME spans per 1,000 whitespace tokens on the
                  untouched control (on PIILO: NAME spans overlapping no gold
                  span), with the share on curricular terms (names/curricular_terms.txt)
                  and on word-problem characters (MathDial).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from scipy.stats import beta

import strata
from detectors import labelmap
from score import TOKEN, WORD, context, curricular_terms, read_jsonl, table, wilson

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "v2"
OUT = HERE / "results" / "v2"
RAW = OUT / "raw"
TABLES = OUT / "tables"
PRIMARY_DETECTORS = ["edshield", "presidio", "spacy_trf", "hf_pii", "gpt4o_mini"]
SECONDARY_DETECTORS = ["gpt4o_mini_propagated"]  # same GPT responses, every occurrence of a returned string
DIALOGUE = ["comta", "mathdial", "studychat", "tscc"]
PIILO = "piilo_holdout"
POOLED = "pooled_dialogue"
NAME_LABELS = ("NAME_STUDENT", "NAME_RELATED")
GOLD_CLASS = {"NAME_STUDENT": "NAME", "NAME_RELATED": "NAME", "SCHOOL": "SCHOOL", "EMAIL": "EMAIL", "PHONE_NUM": "PHONE"}
CONTEXT_TOKENS = {"comta": 6}  # CoMTA's licence forbids redistribution: keep excerpts to the planted phrase
FLOOR, CONFIDENCE = 0.995, 0.95
DEFINITIONS = __doc__.split("Definitions (also written into metrics.json)")[1].strip()


def gpt_unparseable() -> set:
    """sha256 of every document whose GPT response did not parse twice (counted as no-flag)."""
    return {p.stem for p in (HERE / "cache" / "gpt").glob("*.json")
            if json.loads(p.read_text(encoding="utf-8")).get("unparseable")}


def cp_lower(k: int, n: int, conf: float = CONFIDENCE) -> float:
    """Clopper-Pearson one-sided lower bound on a proportion."""
    if n == 0:
        return 0.0
    return 0.0 if k == 0 else float(beta.ppf(1 - conf, k, n - k + 1))


def rate(k: int, n: int) -> dict:
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "recall": None if n == 0 else p, "wilson95": None if n == 0 else [lo, hi],
            "cp_lower95": None if n == 0 else cp_lower(k, n)}


def agg(records: Iterable[dict], field: str = "hit") -> dict:
    records = list(records)
    return rate(sum(bool(r[field]) for r in records), len(records))


def by(records: List[dict], key: Callable[[dict], object], field: str = "hit") -> Dict[str, dict]:
    groups = defaultdict(list)
    for r in records:
        groups[str(key(r))].append(r)
    return {g: agg(v, field) for g, v in sorted(groups.items())}


# --- per-document scoring ------------------------------------------------------

def classed(detector: str, text: str, spans: List[dict]) -> List[Tuple[int, int, str]]:
    """Predicted spans as (start, end, class), trimmed of surrounding whitespace."""
    base = "gpt4o_mini" if detector.startswith("gpt4o_mini") else detector
    out = []
    for sp in spans:
        s, e = int(sp["start"]), int(sp["end"])
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s < e:
            out.append((s, e, labelmap.to_class(base, sp["label"], text, s, e)))
    return out


def covered(gs: int, ge: int, preds: List[Tuple[int, int, str]], cls: Optional[str]) -> float:
    """Share of [gs, ge) covered by the union of predicted spans of class `cls` (None = any)."""
    mask = bytearray(ge - gs)
    for s, e, c in preds:
        if (cls is None or c == cls) and s < ge and gs < e:
            for i in range(max(s, gs) - gs, min(e, ge) - gs):
                mask[i] = 1
    return sum(mask) / (ge - gs)


def gold_of(doc: dict, dataset: str) -> List[dict]:
    """Gold spans with their surface-form record. Planted documents carry it;
    PIILO gold names get one here (speaker `essay`, category `in_domain`)."""
    spans = doc.get("meta", {}).get("spans")
    if spans is not None:
        return spans
    out = []
    for s, e, label in doc["gold_spans"]:
        g = {"start": s, "end": e, "label": label, "kind": "gold", "text": doc["text"][s:e]}
        if label in NAME_LABELS:
            g.update(strata.surface_form(g["text"], "essay", "gold", "in_domain"))
        out.append(g)
    return out


def score_docs(detector: str, dataset: str, seed, docs: List[dict], rows: Dict[str, dict], terms: set,
               control: bool = False, no_flag: frozenset = frozenset()) -> Tuple[List[dict], List[dict], int]:
    """(gold mention records, predicted-NAME records, whitespace tokens).
    `no_flag`: sha256 of documents whose GPT response never parsed."""
    mentions, names, n_tokens = [], [], 0
    for d in docs:
        row = rows.get(d["doc_id"])
        if row is None:
            continue
        text = d["text"]
        unparsed = bool(no_flag) and hashlib.sha256(text.encode("utf-8")).hexdigest() in no_flag
        preds = classed(detector, text, row["spans"])
        gold = gold_of(d, dataset)
        n_tokens += len(TOKEN.findall(text))
        for g in gold:
            cls = GOLD_CLASS.get(g["label"])
            rec = {"detector": detector, "dataset": dataset, "seed": seed, "doc_id": d["doc_id"], **g,
                   "hit": cls is not None and covered(g["start"], g["end"], preds, cls) >= 0.5,
                   "exact": any(c == cls and s == g["start"] and e == g["end"] for s, e, c in preds),
                   "any_label": covered(g["start"], g["end"], preds, None) >= 0.5,
                   "flagged_as": "+".join(sorted({c for s, e, c in preds if s < g["end"] and g["start"] < e})),
                   "unparsed_doc": unparsed,
                   "context": context(text, g["start"], g["end"], CONTEXT_TOKENS.get(dataset, 20))}
            if g["label"] in NAME_LABELS:
                rec["stratum"] = strata.primary_stratum(g)
            mentions.append(rec)
        meta = d.get("meta", {})
        persona = (meta.get("persona_name") or "").lower() if control else ""
        problem = {p.lower() for p in (meta.get("problem_names") or [])}
        for s, e, c in preds:
            if c != "NAME":
                continue
            words = {w.lower().strip(".") for w in WORD.findall(text[s:e])}
            low = text[s:e].lower().strip(" .,!?")
            over = [g["label"] for g in gold if s < g["end"] and g["start"] < e]
            if any(l in NAME_LABELS for l in over):
                tag = "gold_name"
            elif over:
                tag = "gold_other"
            elif low in terms or (words & terms) or any(low.startswith(t + "'") for t in terms):
                tag = "curricular"
            elif persona and persona in words:
                tag = "persona"
            elif problem and (words & problem):
                tag = "problem_name"
            else:
                tag = "other"
            names.append({"doc_id": d["doc_id"], "tag": tag, "text": text[s:e]})
    return mentions, names, n_tokens


# --- aggregation ---------------------------------------------------------------

def recall_block(names: List[dict], seeds: List) -> dict:
    """Name recall: per seed, mean and SD across seeds, pooled over all seeds' mentions."""
    per_seed = {str(s): agg(r for r in names if r["seed"] == s) for s in seeds}
    vals = [v["recall"] for v in per_seed.values() if v["recall"] is not None]
    return {"per_seed": per_seed, "mean": statistics.mean(vals) if vals else None,
            "sd": statistics.stdev(vals) if len(vals) > 1 else None, "pooled": agg(names),
            "pooled_exact": agg(names, "exact"), "pooled_any_label": agg(names, "any_label")}


def breakdowns(names: List[dict]) -> dict:
    return {"by_stratum": by(names, lambda r: r["stratum"]),
            "by_category": by(names, lambda r: r["category"]),
            "by_position": by(names, lambda r: r["position"]),
            "by_n_wordpieces": by(names, lambda r: r["n_wordpieces"] if r["n_wordpieces"] < 4 else "4+"),
            "by_case": by(names, lambda r: r["case"]), "by_speaker": by(names, lambda r: r["speaker"]),
            "by_is_dict_word": by(names, lambda r: r["is_dict_word"]),
            "by_is_initial": by(names, lambda r: r["is_initial"]),
            "by_kind": by(names, lambda r: r["kind"]), "by_gold_label": by(names, lambda r: r["label"])}


def unparsed_block(det: str, mentions: List[dict], names: List[dict]) -> dict:
    """GPT only: planted documents whose response never parsed, and name recall without them."""
    if not det.startswith("gpt4o_mini"):
        return {}
    docs = {(r["seed"], r["doc_id"]) for r in mentions}
    bad = {(r["seed"], r["doc_id"]) for r in mentions if r["unparsed_doc"]}
    return {"unparsed_documents": {"docs_with_gold": len(docs), "unparsed": len(bad),
                                   "name_mentions_in_them": sum(r["unparsed_doc"] for r in names),
                                   "name_recall_excluding_them": agg(r for r in names if not r["unparsed_doc"])}}


def precision_block(preds: List[dict]) -> dict:
    tags = Counter(p["tag"] for p in preds)
    n, k = len(preds), tags["gold_name"]
    n2 = n - tags["problem_name"]
    return {"n_name_spans": n, "n_on_gold_names": k, "precision": k / n if n else None,
            "precision_excl_problem_names": k / n2 if n2 else None, "by_tag": dict(tags)}


def over_redaction_block(preds: List[dict], n_tokens: int, n_docs: int, drop: Tuple[str, ...] = ()) -> dict:
    preds = [p for p in preds if p["tag"] not in drop]
    tags = Counter(p["tag"] for p in preds)
    n = len(preds)
    share = lambda t: tags[t] / n if n else None
    return {"n_docs": n_docs, "n_tokens": n_tokens, "n_name_flags": n,
            "name_flags_per_1000_tokens": 1000 * n / n_tokens if n_tokens else None,
            "share_curricular": share("curricular"), "share_problem_names": share("problem_name"),
            "share_persona": share("persona"), "by_tag": dict(tags),
            "top_other": Counter(p["text"].strip().lower() for p in preds if p["tag"] in ("curricular", "other")).most_common(12)}


# --- floor transfer --------------------------------------------------------------

def transfer(a: List[dict], b: List[dict], fn: Callable[[dict], str]) -> dict:
    """Predict B's name recall from A's per-stratum recall and B's stratum mix,
    with the mix taken from all of B's gold mentions (oracle) and from B's
    caught mentions only. A stratum of B that A never observed has no rate: the
    point prediction renormalises over the strata A covers, the floor gives it 0."""
    ga, gb = defaultdict(list), defaultdict(list)
    for r in a:
        ga[fn(r)].append(r["hit"])
    for r in b:
        gb[fn(r)].append(r["hit"])
    r_s = {s: sum(v) / len(v) for s, v in ga.items()}
    lb_s = {s: cp_lower(sum(v), len(v)) for s, v in ga.items()}
    measured = sum(r["hit"] for r in b) / len(b)
    out = {"measured": measured, "n_b": len(b), "n_a": len(a), "n_strata_a": len(ga), "n_strata_b": len(gb)}
    for mix, weight in (("oracle", lambda v: len(v)), ("caught_only", lambda v: sum(v))):
        tot = sum(weight(v) for v in gb.values())
        if not tot:
            out[mix] = None
            continue
        w = {s: weight(v) / tot for s, v in gb.items()}
        cov = sum(x for s, x in w.items() if s in r_s)
        point = sum(x * r_s[s] for s, x in w.items() if s in r_s) / cov if cov else None
        floor = sum(x * lb_s.get(s, 0.0) for s, x in w.items())
        out[mix] = {"predicted_point": point, "predicted_floor": floor, "uncovered_weight": 1 - cov,
                    "error_pts": None if point is None else 100 * (point - measured),
                    "floor_valid": floor <= measured}
    if out["oracle"] and out["caught_only"] and out["oracle"]["predicted_point"] is not None \
            and out["caught_only"]["predicted_point"] is not None:
        out["caught_only_bias_pts"] = 100 * (out["caught_only"]["predicted_point"] - out["oracle"]["predicted_point"])
    return out


def transfer_summary(rows: List[dict], detectors: List[str]) -> dict:
    """Per strata set and mix, over the primary detectors and every ordered pair."""
    out = {}
    for name in strata.STRATA_SETS:
        sel = [r for r in rows if r["strata_set"] == name and r["detector"] in detectors]
        block = {"n_pairs_x_detectors": len(sel)}
        for mix in ("oracle", "caught_only"):
            errs = [(r[mix]["error_pts"], r) for r in sel if r[mix] and r[mix]["error_pts"] is not None]
            if not errs:
                continue
            worst = max(errs, key=lambda x: abs(x[0]))
            block[mix] = {"mean_abs_error_pts": statistics.mean(abs(e) for e, _ in errs),
                          "mean_error_pts": statistics.mean(e for e, _ in errs),
                          "max_abs_error_pts": abs(worst[0]),
                          "worst": {"detector": worst[1]["detector"], "pair": f"{worst[1]['a']}->{worst[1]['b']}",
                                    "error_pts": worst[0]},
                          "floor_valid": sum(r[mix]["floor_valid"] for r in sel if r[mix]), "n": len(errs),
                          "mean_uncovered_weight": statistics.mean(r[mix]["uncovered_weight"] for r in sel if r[mix])}
        bias = [r["caught_only_bias_pts"] for r in sel if "caught_only_bias_pts" in r]
        if bias:
            block["caught_only_bias_pts"] = {"mean": statistics.mean(bias), "max": max(bias), "min": min(bias)}
        out[name] = block
    return out


# --- output --------------------------------------------------------------------

def pct(x, d: int = 1) -> str:
    return "n/a" if x is None or x != x else f"{100 * x:.{d}f}%"


def write_table(name: str, header: List[str], rows: List[list], note: str = "") -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    with (TABLES / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    (TABLES / f"{name}.md").write_text((note + "\n\n" if note else "") + table(rows, header) + "\n", encoding="utf-8")


def main() -> int:
    terms = {t.lower() for t in curricular_terms()}
    seeds = sorted(int(p.name) for p in (DATA / "planted").iterdir() if p.is_dir())
    datasets = [d for d in DIALOGUE if (DATA / "control" / f"{d}.jsonl").exists()]
    detectors = [d for d in PRIMARY_DETECTORS + SECONDARY_DETECTORS if (RAW / d).is_dir()]
    primary = [d for d in detectors if d in PRIMARY_DETECTORS]
    planted = {(s, ds): read_jsonl(DATA / "planted" / str(s) / f"{ds}.jsonl") for s in seeds for ds in datasets}
    control = {ds: read_jsonl(DATA / "control" / f"{ds}.jsonl") for ds in datasets}
    piilo = read_jsonl(RAW / "_piilo_docs.jsonl")
    plant_log = json.loads((DATA / "plant_log.json").read_text(encoding="utf-8"))

    def rows_of(det: str, key: str) -> Dict[str, dict]:
        return {r["doc_id"]: r for r in read_jsonl(RAW / det / f"{key}.jsonl")}

    results, names_by, all_mentions = {}, {}, []
    unparseable = frozenset(gpt_unparseable())
    for det in detectors:
        results[det] = {}
        no_flag = unparseable if det.startswith("gpt4o_mini") else frozenset()
        pooled_names, pooled_preds, pooled_other = [], [], []
        for ds in datasets:
            mentions, preds = [], []
            for s in seeds:
                m, p, _ = score_docs(det, ds, s, planted[(s, ds)], rows_of(det, f"planted__{s}__{ds}"), terms, no_flag=no_flag)
                mentions += m
                preds += p
            if not mentions:
                continue
            names = [r for r in mentions if r["label"] in NAME_LABELS]
            _, cpreds, ctok = score_docs(det, ds, None, control[ds], rows_of(det, f"control__{ds}"), terms, control=True)
            results[det][ds] = {"name_recall": recall_block(names, seeds), **breakdowns(names),
                                **unparsed_block(det, mentions, names),
                                "secondary_labels": {l: {"caught": agg(v), "any_label": agg(v, "any_label")}
                                                     for l in ("SCHOOL", "EMAIL", "PHONE_NUM", "USERNAME")
                                                     for v in [[r for r in mentions if r["label"] == l]]},
                                "precision": precision_block(preds),
                                "over_redaction": over_redaction_block(cpreds, ctok, len(control[ds]))}
            names_by[(det, ds)] = names
            pooled_names += names
            pooled_preds += preds
            pooled_other += [r for r in mentions if r["label"] not in NAME_LABELS]
            all_mentions += mentions
        if pooled_names:
            results[det][POOLED] = {"datasets": [ds for ds in datasets if (det, ds) in names_by],
                                    "name_recall": recall_block(pooled_names, seeds), **breakdowns(pooled_names),
                                    **unparsed_block(det, pooled_names + pooled_other, pooled_names),
                                    "secondary_labels": {l: {"caught": agg(v), "any_label": agg(v, "any_label")}
                                                         for l in ("SCHOOL", "EMAIL", "PHONE_NUM", "USERNAME")
                                                         for v in [[r for r in pooled_other if r["label"] == l]]},
                                    "precision": precision_block(pooled_preds)}
        prow = rows_of(det, "piilo__piilo_holdout")
        if piilo and prow:
            m, p, tok = score_docs(det, PIILO, None, piilo, prow, terms, no_flag=no_flag)
            names = [r for r in m if r["label"] in NAME_LABELS]
            results[det][PIILO] = {"role": "in-domain reference: 680 held-out PIILO essays, one run",
                                   "name_recall": {"pooled": agg(names), "pooled_exact": agg(names, "exact"),
                                                   "pooled_any_label": agg(names, "any_label")},
                                   **breakdowns(names), **unparsed_block(det, m, names), "precision": precision_block(p),
                                   "over_redaction": over_redaction_block(p, tok, len(piilo), drop=("gold_name", "gold_other"))}
            names_by[(det, PIILO)] = names

    # floor transfer: every ordered pair of dialogue genres, every detector, every strata set
    genres = [ds for ds in datasets if any((d, ds) in names_by for d in detectors)]
    ft = []
    for det in detectors:
        for a in genres:
            for b in genres:
                if a != b and (det, a) in names_by and (det, b) in names_by:
                    for name, fn in strata.STRATA_SETS.items():
                        ft.append({"detector": det, "a": a, "b": b, "strata_set": name,
                                   **transfer(names_by[(det, a)], names_by[(det, b)], fn)})

    # probe cost: n per primary stratum against the n a 99.5% floor needs
    n_required = math.ceil(3 / (1 - FLOOR))
    probe = {"floor": FLOOR, "confidence": CONFIDENCE, "rule": "3/n", "n_required": n_required,
             "n_required_exact": math.ceil(math.log(1 - CONFIDENCE) / math.log(FLOOR)), "strata": []}
    for ds in genres + [POOLED]:
        for s in strata.PRIMARY_STRATA:
            row = {"dataset": ds, "stratum": s, "n_observed": 0, "detectors": {}}
            for det in detectors:
                a = results[det].get(ds, {}).get("by_stratum", {}).get(s)
                if a:
                    row["n_observed"] = a["n"]
                    row["detectors"][det] = {"misses": a["n"] - a["k"], "zero_miss": a["k"] == a["n"],
                                             "cp_lower95": a["cp_lower95"]}
            row["n_sufficient"] = row["n_observed"] >= n_required
            row["zero_miss_detectors"] = [d for d, v in row["detectors"].items() if v["zero_miss"]]
            probe["strata"].append(row)

    meta = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((OUT / "meta").glob("*.json"))}
    gpt_cache = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((HERE / "cache" / "gpt").glob("*.json"))]
    if gpt_cache:
        res = Counter()
        for c in gpt_cache:
            res.update(c["resolution"])
        meta.setdefault("gpt4o_mini", {})["cache"] = {
            "responses": len(gpt_cache), "unparseable": sum(c["unparseable"] for c in gpt_cache),
            "retried": sum(c["attempts"] > 1 for c in gpt_cache), "span_resolution": dict(res),
            "usd": round(sum(c["usd"] for c in gpt_cache), 4), "models": sorted({c["model"] for c in gpt_cache})}
    metrics = {
        "definitions": DEFINITIONS, "stratum_definition": strata.__doc__.strip(),
        "label_map": labelmap.__doc__.strip(), "seeds": seeds, "datasets": genres,
        "detectors": {"primary": primary, "secondary": [d for d in detectors if d in SECONDARY_DETECTORS]},
        "not_run": {"datasets": {k: v.get("note") for k, v in plant_log["datasets"].items() if v.get("note")},
                    "detectors": [d for d in PRIMARY_DETECTORS if d not in detectors]},
        "plant": {k: v for k, v in plant_log["datasets"].items() if not v.get("note")},
        "run": meta, "results": results,
        "floor_transfer": {"pairs": ft, "summary_primary_detectors": transfer_summary(ft, primary)},
        "probe_cost": probe,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    tables(metrics)
    misses(all_mentions, primary)
    print(f"detectors {detectors}; datasets {genres}; seeds {seeds}; mentions scored {len(all_mentions)}")
    return 0


def tables(m: dict) -> None:
    res, dets = m["results"], m["detectors"]["primary"] + m["detectors"]["secondary"]
    cols = [PIILO] + m["datasets"] + [POOLED]
    # T1 name recall, detector x dataset
    rows = []
    for d in dets:
        for ds in cols:
            a = res[d].get(ds)
            if not a:
                continue
            nr, p = a["name_recall"], a["name_recall"]["pooled"]
            rows.append([d, ds, p["n"], p["k"], pct(p["recall"]), pct(nr.get("mean")),
                         "n/a" if nr.get("sd") is None else f"{100 * nr['sd']:.2f}",
                         f"{pct(p['wilson95'][0])} – {pct(p['wilson95'][1])}", pct(nr["pooled_exact"]["recall"]),
                         pct(nr["pooled_any_label"]["recall"])])
    write_table("T1_name_recall", ["detector", "dataset", "n mentions", "caught", "recall (pooled)", "mean over seeds",
                                   "SD over seeds (pts)", "pooled 95% Wilson CI", "exact-match recall", "any-label recall"], rows,
                "Name recall by detector and dataset. PIILO is one run of the 680 held-out essays; the dialogue sets pool "
                f"{len(m['seeds'])} planting seeds. `gpt4o_mini_propagated` is secondary: the same GPT responses with every "
                "occurrence of a returned string flagged.")
    # T2 recall by primary stratum
    rows = []
    for d in dets:
        for ds in m["datasets"] + [POOLED]:
            for s in strata.PRIMARY_STRATA:
                a = res[d].get(ds, {}).get("by_stratum", {}).get(s)
                if a:
                    rows.append([d, ds, s, a["n"], a["k"], pct(a["recall"]), pct(a["cp_lower95"])])
    write_table("T2_recall_by_stratum", ["detector", "dataset", "stratum (case|speaker|dict word)", "n", "caught", "recall",
                                         "95% lower bound (Clopper-Pearson)"], rows,
                "Name recall per primary stratum, pooled over seeds. A stratum with no planted mentions has no row.")
    # T3 floor transfer, primary strata
    rows = []
    for r in m["floor_transfer"]["pairs"]:
        if r["strata_set"] != strata.PRIMARY:
            continue
        o, c = r["oracle"], r["caught_only"]
        f = lambda x, k: "n/a" if not x or x[k] is None else (f"{x[k]:+.2f}" if k == "error_pts" else pct(x[k], 2))
        rows.append([f"{r['a']} -> {r['b']}", r["detector"], pct(r["measured"], 2), f(o, "predicted_point"), f(o, "error_pts"),
                     f(o, "predicted_floor"), "n/a" if not o else ("yes" if o["floor_valid"] else "NO"),
                     f(c, "predicted_point"), f(c, "error_pts"), f(c, "predicted_floor"),
                     "n/a" if not c else ("yes" if c["floor_valid"] else "NO"),
                     "n/a" if "caught_only_bias_pts" not in r else f"{r['caught_only_bias_pts']:+.2f}",
                     pct(o["uncovered_weight"]) if o else "n/a"])
    write_table("T3_floor_transfer", ["A -> B", "detector", "measured on B", "predicted (oracle mix)", "error (pts)",
                                      "predicted floor", "floor valid", "predicted (caught-only mix)", "error (pts)",
                                      "predicted floor", "floor valid", "caught-only bias (pts)", "B weight in strata A lacks"],
                rows, "Floor transfer with the primary strata: B's name recall predicted from A's per-stratum recall and "
                      "B's stratum mix. Error = predicted - measured. Floor valid = predicted floor <= measured.")
    # T4 over-redaction
    rows = []
    for d in dets:
        for ds in [PIILO] + m["datasets"]:
            o = res[d].get(ds, {}).get("over_redaction")
            if o and o["n_tokens"]:
                rows.append([d, ds, o["n_tokens"], o["n_name_flags"], f"{o['name_flags_per_1000_tokens']:.2f}",
                             pct(o["share_curricular"]), pct(o["share_problem_names"]), pct(o["share_persona"]),
                             ", ".join(f"{k} {v}" for k, v in sorted(o["by_tag"].items()))])
    write_table("T4_over_redaction", ["detector", "dataset", "control tokens", "NAME flags", "NAME flags / 1,000 tokens",
                                      "share on curricular terms", "share on word-problem characters",
                                      "share on simulated-student persona names", "flags by tag"], rows,
                "NAME flags on the untouched control (on PIILO: NAME flags overlapping no gold span).")
    # T5 stratum ablation
    rows = []
    for name, b in m["floor_transfer"]["summary_primary_detectors"].items():
        o, c = b.get("oracle"), b.get("caught_only")
        if not o:
            continue
        rows.append([name, o["n"], f"{o['mean_abs_error_pts']:.2f}", f"{o['max_abs_error_pts']:.2f}",
                     f"{o['worst']['detector']} {o['worst']['pair']}", f"{o['floor_valid']}/{o['n']}",
                     pct(o["mean_uncovered_weight"]),
                     "n/a" if not c else f"{c['mean_abs_error_pts']:.2f}", "n/a" if not c else f"{c['floor_valid']}/{c['n']}",
                     "n/a" if "caught_only_bias_pts" not in b else f"{b['caught_only_bias_pts']['mean']:+.2f}"])
    write_table("T5_stratum_ablation", ["strata set", "pairs x detectors", "mean |error| (pts), oracle mix", "max |error| (pts)",
                                        "worst case", "floors valid", "mean B weight in strata A lacks",
                                        "mean |error| (pts), caught-only mix", "floors valid, caught-only",
                                        "mean caught-only bias (pts)"], rows,
                "Floor-transfer error by strata set, over the primary detectors and every ordered genre pair. "
                "`none` predicts B's recall with A's overall recall. `primary x is_initial` is an addition to the brief.")
    # T6 probe cost
    p = m["probe_cost"]
    rows = [[r["dataset"], r["stratum"], r["n_observed"], p["n_required"], "yes" if r["n_sufficient"] else "no",
             ", ".join(r["zero_miss_detectors"]) or "none"] for r in p["strata"] if r["n_observed"]]
    write_table("T6_probe_cost", ["dataset", "stratum", "n observed (all seeds)", "n for a 99.5% floor at 95% (3/n)",
                                  "n sufficient", "zero-miss detectors at this n"], rows,
                "Probe cost per primary stratum. Zero misses at n mentions bounds the miss rate below 3/n at 95%.")


def misses(mentions: List[dict], primary: List[str]) -> None:
    """One row per (primary detector, missed planted span), and the misses the detectors share."""
    missed_by = defaultdict(set)
    for r in mentions:
        if not r["hit"] and r["detector"] in primary:
            missed_by[(r["dataset"], r["seed"], r["doc_id"], r["start"])].add(r["detector"])
    cols = ["case", "position", "is_dict_word", "n_wordpieces", "is_initial", "stratum"]
    with (OUT / "misses.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["detector", "seed", "doc_id", "dataset", "category", "kind", "speaker", "label", "gold_text"] + cols
                   + ["flagged_as", "n_primary_detectors_missed", "context"])
        for r in sorted((r for r in mentions if not r["hit"] and r["detector"] in primary),
                        key=lambda r: (primary.index(r["detector"]), r["dataset"], r["seed"], r["doc_id"], r["start"])):
            key = (r["dataset"], r["seed"], r["doc_id"], r["start"])
            w.writerow([r["detector"], r["seed"], r["doc_id"], r["dataset"], r.get("category", ""), r["kind"],
                        r["speaker"], r["label"], r["text"]] + [r.get(c, "") for c in cols]
                       + [r["flagged_as"], len(missed_by[key]), r["context"]])
    # shared misses: name mentions at least three primary detectors missed
    first = {}
    for r in mentions:
        key = (r["dataset"], r["seed"], r["doc_id"], r["start"])
        if r["label"] in NAME_LABELS and len(missed_by.get(key, ())) >= 3:
            first.setdefault(key, r)
    by_n = Counter(len(missed_by[k]) for k in first)
    by_stratum = Counter((r["stratum"], r["is_initial"]) for r in first.values())
    L = [f"Name mentions missed by at least three of the {len(primary)} primary detectors ({', '.join(primary)}), all seeds: "
         f"{len(first)}. By number of detectors that missed: "
         + ", ".join(f"{n} detectors: {c}" for n, c in sorted(by_n.items())) + ".", "",
         table([[s, "initial" if i else "name", c] for (s, i), c in by_stratum.most_common()],
               ["stratum", "form", "shared misses"]), "",
         "First example per stratum and form (lowest seed, then document order), most detectors first:", ""]
    shown = set()
    for key, r in sorted(first.items(), key=lambda kv: (-len(missed_by[kv[0]]), kv[0][1], kv[0][0], kv[0][2], kv[0][3])):
        g = (r["stratum"], r["is_initial"])
        if g in shown:
            continue
        shown.add(g)
        L.append(f"- `{r['context']}` — {r['dataset']} {r['doc_id']}, seed {r['seed']}, {r['stratum']}"
                 f"{', initial' if r['is_initial'] else ''}, {r['category']}; missed by "
                 f"{', '.join(d for d in primary if d in missed_by[key])}.")
    (TABLES / "shared_misses.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
