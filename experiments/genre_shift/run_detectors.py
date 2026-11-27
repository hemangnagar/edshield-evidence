"""Run the five detectors over identical files and store the spans each returned.

    python run_detectors.py                          # all five, all sets
    python run_detectors.py --detectors edshield presidio --sets planted control
    OPENAI_API_KEY=... python run_detectors.py --detectors gpt4o_mini

Sets: planted (data/v2/planted/<seed>/<dataset>.jsonl, every seed), control
(data/v2/control/<dataset>.jsonl), piilo (the 680-essay holdout, from
EDSHIELD_EVIDENCE_PIILO or data/raw/piilo_rebuilt/).

Output, one file per detector and set:
    results/v2/raw/<detector>/<set>.jsonl    {doc_id, spans: [{start, end, label}], seconds}
with labels as the detector gave them (detectors/labelmap.py maps them when
scoring), and results/v2/meta/<detector>.json (versions, model revision,
hardware, timings). results/v2/raw/ is not committed. A set whose output file
is complete is skipped, so an interrupted run resumes.

gpt4o_mini caches every validated response under cache/gpt/<sha256(text)>.json
(offsets and labels only, no text) and stops when the money spent reaches
GPT_BUDGET_USD (default 30). The model is asked for the span text as well as
its offsets, because its character offsets are almost never right; see
resolve_gpt_spans. A second file per set, gpt4o_mini_propagated, flags every
occurrence of each returned string (the model tends to list a repeated name
once); it is scored as a secondary detector from the same responses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "v2"
OUT = HERE / "results" / "v2"
CACHE = HERE / "cache" / "gpt"
PIILO_REBUILT = HERE / "data" / "raw" / "piilo_rebuilt"
DETECTORS = ("edshield", "presidio", "spacy_trf", "hf_pii", "gpt4o_mini")

EDSHIELD_MODEL = "edshield/piilo-deberta-v3-small"
EDSHIELD_REV = "5effafd0299ac576b6c5b3a91b3f26800ce89e62"
EDSHIELD_POLICY = "coppa"
HF_PII_MODEL = "iiiorg/piiranha-v1-detect-personal-information"
HF_PII_REV = "255acde67a2f34cf452eb42e365b24d2957352fc"
GPT_MODEL = "gpt-4o-mini"
GPT_USD_PER_M = {"input": 0.15, "output": 0.60}  # list price; cached-input discount ignored
# Output cap. In JSON mode the model sometimes repeats one span until it runs out of tokens
# (16k tokens, minutes per call, without a cap). 2,000 tokens hold about 90 spans; a response
# cut off at the cap does not parse and takes the brief's path: retry once, then no-flag, logged.
GPT_MAX_OUTPUT_TOKENS = 2000
Span = Dict[str, object]


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def write_jsonl(rows: List[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def versions(pkgs) -> Dict[str, str]:
    import importlib.metadata as md
    out = {"python": platform.python_version(), "platform": platform.platform(),
           "cpu": platform.processor() or platform.machine(), "cpu_count": os.cpu_count()}
    for pkg in pkgs:
        try:
            out[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            out[pkg] = "not installed"
    try:
        import torch
        out["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none"
    except ImportError:
        out["gpu"] = "none"
    return out


def piilo_docs() -> List[dict]:
    """The PIILO holdout as records, or [] with a note when it is not available."""
    where = os.environ.get("EDSHIELD_EVIDENCE_PIILO") or (str(PIILO_REBUILT) if PIILO_REBUILT.is_dir() else None)
    if not where:
        print("piilo: no holdout (set EDSHIELD_EVIDENCE_PIILO or run rebuild_piilo.py); skipped", file=sys.stderr)
        return []
    from edshield_evidence.datasets import load_piilo_holdout
    ds = load_piilo_holdout(where)
    write_jsonl([d.to_record() for d in ds.docs], OUT / "raw" / "_piilo_docs.jsonl")
    (OUT / "meta").mkdir(parents=True, exist_ok=True)
    (OUT / "meta" / "_piilo.json").write_text(json.dumps({"file": Path(where).name, "sha256": ds.sha256,
                                                          "docs": len(ds.docs)}), encoding="utf-8")
    return [d.to_record() for d in ds.docs]


def sets_to_run(names: List[str]) -> List[tuple]:
    """(set key, docs) pairs."""
    out = []
    for s in names:
        if s == "planted":
            for p in sorted((DATA / "planted").glob("*/*.jsonl")):
                out.append((f"planted__{p.parent.name}__{p.stem}", read_jsonl(p)))
        elif s == "control":
            for p in sorted((DATA / "control").glob("*.jsonl")):
                out.append((f"control__{p.stem}", read_jsonl(p)))
        elif s == "piilo":
            docs = piilo_docs()
            if docs:
                out.append(("piilo__piilo_holdout", docs))
        else:
            raise SystemExit(f"unknown set {s}")
    return out


# --- the detectors: each returns (meta, fn) with fn(texts) -> list of span lists ---

def make_edshield(device: str):
    from huggingface_hub import snapshot_download
    from edshield import deid
    from edshield_evidence.runtimes import PythonRuntime
    os.environ.setdefault("EDSHIELD_ALLOW_DOWNLOAD", "1")
    model_dir = snapshot_download(EDSHIELD_MODEL, revision=EDSHIELD_REV)
    rt = PythonRuntime(detector="rules+model", model_dir=model_dir, device=device).__enter__()

    def run(texts: List[str]) -> List[List[Span]]:
        out = []
        for t in texts:
            r = rt.deidentify(t, policy=EDSHIELD_POLICY, seed=0)
            out.append([{"start": int(e.start), "end": int(e.end), "label": e.label} for e in r.entities])
        return out

    meta = {"model_id": EDSHIELD_MODEL, "model_revision": EDSHIELD_REV, "model_sha256": rt.model_sha256,
            "detector": "rules+model", "policy": EDSHIELD_POLICY,
            "policy_sha256": deid.policy_fingerprint(EDSHIELD_POLICY), "seed": 0, "device": device,
            "versions": versions(["edshield", "edshield-evidence", "torch", "transformers"])}
    return meta, run


def make_presidio(device: str):
    import spacy
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    engine = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]}).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=engine, supported_languages=["en"])

    def run(texts: List[str]) -> List[List[Span]]:
        return [[{"start": r.start, "end": r.end, "label": r.entity_type, "score": round(float(r.score), 3)}
                 for r in analyzer.analyze(text=t, language="en")] for t in texts]

    meta = {"recognizers": sorted(r.name for r in analyzer.get_recognizers("en")),
            "spacy_model": "en_core_web_lg " + spacy.load("en_core_web_lg", disable=["ner"]).meta["version"],
            "score_threshold": "default (0)", "device": "cpu",
            "versions": versions(["presidio-analyzer", "spacy"])}
    return meta, run


def make_spacy_trf(device: str):
    import spacy
    if device == "cuda":
        spacy.require_gpu()
    nlp = spacy.load("en_core_web_trf", exclude=["tagger", "parser", "attribute_ruler", "lemmatizer"])

    def run(texts: List[str]) -> List[List[Span]]:
        return [[{"start": e.start_char, "end": e.end_char, "label": e.label_} for e in doc.ents]
                for doc in nlp.pipe(texts, batch_size=8)]

    meta = {"spacy_model": "en_core_web_trf " + nlp.meta["version"], "pipeline": nlp.pipe_names, "device": device,
            "versions": versions(["spacy", "spacy-curated-transformers", "torch"])}
    return meta, run


def make_hf_pii(device: str):
    from transformers import pipeline
    pipe = pipeline("token-classification", model=HF_PII_MODEL, revision=HF_PII_REV, aggregation_strategy="simple",
                    stride=128, device=0 if device == "cuda" else -1)

    def run(texts: List[str]) -> List[List[Span]]:
        res = pipe(texts, batch_size=1)  # on CPU, padding a batch to its longest document costs more than it saves
        return [[{"start": int(e["start"]), "end": int(e["end"]), "label": e["entity_group"],
                  "score": round(float(e["score"]), 3)} for e in doc] for doc in res]

    meta = {"model_id": HF_PII_MODEL, "model_revision": HF_PII_REV, "aggregation_strategy": "simple", "stride": 128,
            "window": "512 tokens", "device": device, "versions": versions(["transformers", "torch"])}
    return meta, run


class BudgetExceeded(RuntimeError):
    pass


def occurrences(text: str, needle: str) -> List[int]:
    """Start offsets of `needle` in `text`: whole-word occurrences when there
    are any (so "Pat" is not found inside "Patience"), otherwise all."""
    occ, i = [], text.find(needle)
    while i >= 0:
        occ.append(i)
        i = text.find(needle, i + 1)
    whole = [i for i in occ if not (text[i - 1:i].isalnum() and needle[:1].isalnum())
             and not (text[i + len(needle):i + len(needle) + 1].isalnum() and needle[-1:].isalnum())]
    return whole or occ


def resolve_gpt_spans(text: str, items) -> tuple:
    """Validate what the model returned against the document. An item is kept
    when its offsets are in range and the document reads exactly its `text`
    there (`exact`); when the text is given but the offsets are wrong, it is
    moved to the unused occurrence of the text nearest the offset it claimed
    (`relocated`); an item with in-range offsets and no text is kept as given
    (`offsets_only`). Everything else is dropped. Returns (spans, counts)."""
    spans, counts, used = [], {"exact": 0, "relocated": 0, "offsets_only": 0, "dropped": 0}, set()
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict) or not isinstance(it.get("label"), str):
            counts["dropped"] += 1
            continue
        s, e, t = it.get("start"), it.get("end"), it.get("text")
        ok = isinstance(s, int) and isinstance(e, int) and not isinstance(s, bool) and 0 <= s < e <= len(text)
        how = None
        if isinstance(t, str) and t.strip():
            if ok and text[s:e] == t and (s, e) not in used:
                how = "exact"
            else:
                claimed = s if isinstance(s, int) else 0
                occ = [i for i in occurrences(text, t) if (i, i + len(t)) not in used]
                if occ:
                    s = min(occ, key=lambda i: abs(i - claimed))
                    e, how = s + len(t), "relocated"
        elif ok:
            how = "offsets_only"
        if how is None:
            counts["dropped"] += 1
            continue
        used.add((s, e))
        counts[how] += 1
        spans.append({"start": s, "end": e, "label": it["label"].upper()})
    return sorted(spans, key=lambda x: (x["start"], x["end"])), counts


def propagate(text: str, spans: List[Span]) -> List[Span]:
    """Every occurrence of every string the model returned, under the label it
    gave: what replacing the returned strings throughout the document would
    remove. Scored as the secondary detector `gpt4o_mini_propagated`."""
    out = {}
    for sp in spans:
        needle = text[sp["start"]:sp["end"]]
        for i in occurrences(text, needle):
            out.setdefault((i, i + len(needle)), sp["label"])
    return [{"start": a, "end": b, "label": l} for (a, b), l in sorted(out.items())]


def make_gpt4o_mini(device: str):
    from openai import OpenAI
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("gpt4o_mini: OPENAI_API_KEY is not set (make v2-nogpt skips this detector)")
    client = OpenAI(max_retries=6, timeout=120)
    prompt = (HERE / "detectors" / "gpt_prompt.txt").read_text(encoding="utf-8").strip()
    prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    budget = float(os.environ.get("GPT_BUDGET_USD", "30"))
    CACHE.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    spent = {"usd": sum(json.loads(p.read_text(encoding="utf-8")).get("usd", 0.0) for p in CACHE.glob("*.json"))}
    state = {"calls": 0, "cache_hits": 0, "unparseable": 0, "models": set()}

    def one(text: str) -> List[Span]:
        path = CACHE / (hashlib.sha256(text.encode("utf-8")).hexdigest() + ".json")
        if path.exists():
            rec = json.loads(path.read_text(encoding="utf-8"))
            if rec.get("prompt_sha256") == prompt_sha and rec.get("model", "").startswith(GPT_MODEL):
                with lock:
                    state["cache_hits"] += 1
                    state["models"].add(rec["model"])
                return rec["spans"]
        usd, items, attempts, model, fingerprint, finish = 0.0, None, 0, GPT_MODEL, None, None
        for attempts in (1, 2):  # unparseable -> retry once, then no-flag
            with lock:
                if spent["usd"] >= budget:
                    raise BudgetExceeded(f"GPT_BUDGET_USD={budget} reached after ${spent['usd']:.2f}")
            r = client.chat.completions.create(
                model=GPT_MODEL, temperature=0, seed=0, response_format={"type": "json_object"},
                max_completion_tokens=GPT_MAX_OUTPUT_TOKENS,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}])
            cost = (r.usage.prompt_tokens * GPT_USD_PER_M["input"]
                    + r.usage.completion_tokens * GPT_USD_PER_M["output"]) / 1e6
            usd += cost
            model, fingerprint, finish = r.model, r.system_fingerprint, r.choices[0].finish_reason
            with lock:
                spent["usd"] += cost
                state["calls"] += 1
                state["models"].add(model)
            try:
                parsed = json.loads(r.choices[0].message.content)
                items = parsed["spans"] if isinstance(parsed, dict) else parsed
                if not isinstance(items, list):
                    raise ValueError("spans is not a list")
                break
            except (ValueError, KeyError, TypeError):
                items = None
        if items is None:
            with lock:
                state["unparseable"] += 1
            print(f"gpt4o_mini: unparseable twice (finish_reason {finish}), counted as no-flag: {path.stem[:16]}",
                  file=sys.stderr)
        spans, counts = resolve_gpt_spans(text, items or [])
        rec = {"model": model, "system_fingerprint": fingerprint, "prompt_sha256": prompt_sha, "temperature": 0,
               "seed": 0, "attempts": attempts, "finish_reason": finish, "unparseable": items is None, "resolution": counts,
               "usd": round(usd, 6), "spans": spans}
        path.write_text(json.dumps(rec), encoding="utf-8")
        return spans

    def run(texts: List[str]) -> List[List[Span]]:
        with ThreadPoolExecutor(max_workers=int(os.environ.get("GPT_WORKERS", "8"))) as ex:
            return list(ex.map(one, texts))

    meta = {"model": GPT_MODEL, "temperature": 0, "seed": 0, "response_format": "json_object",
            "max_completion_tokens": GPT_MAX_OUTPUT_TOKENS,
            "prompt_sha256": prompt_sha, "budget_usd": budget, "usd_per_million_tokens": GPT_USD_PER_M,
            "_live": (spent, state), "versions": versions(["openai"])}
    return meta, run


MAKERS: Dict[str, Callable] = {"edshield": make_edshield, "presidio": make_presidio, "spacy_trf": make_spacy_trf,
                               "hf_pii": make_hf_pii, "gpt4o_mini": make_gpt4o_mini}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--detectors", nargs="+", default=list(DETECTORS), choices=DETECTORS)
    ap.add_argument("--sets", nargs="+", default=["planted", "control", "piilo"])
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--limit", type=int, default=0, help="debug: first N docs per set (output not kept as complete)")
    ap.add_argument("--chunk", type=int, default=64, help="documents per call to a detector")
    args = ap.parse_args(argv)
    sets = sets_to_run(args.sets)
    raw = OUT / ("raw_debug" if args.limit else "raw")
    status = 0
    for name in args.detectors:
        meta_path = OUT / "meta" / f"{name}.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {"sets": {}}
        todo = []
        for key, docs in sets:
            docs = docs[: args.limit] if args.limit else docs
            done = read_jsonl(raw / name / f"{key}.jsonl")
            if name != "gpt4o_mini" and [r["doc_id"] for r in done] == [d["doc_id"] for d in docs]:
                continue  # gpt4o_mini always re-reads: its cache makes that free
            todo.append((key, docs))
        if not todo:
            print(f"{name}: all sets already done", file=sys.stderr)
            continue
        new_meta, run = MAKERS[name](args.device)
        live = new_meta.pop("_live", None)
        meta.update(new_meta, started=time.strftime("%Y-%m-%dT%H:%M:%S"))
        try:
            for key, docs in todo:
                rows, t0 = [], time.time()
                for i in range(0, len(docs), args.chunk):
                    batch = docs[i:i + args.chunk]
                    t = time.time()
                    for d, spans in zip(batch, run([d["text"] for d in batch])):
                        rows.append({"doc_id": d["doc_id"], "spans": spans})
                    print(f"  {name} {key}: {len(rows)}/{len(docs)} ({time.time() - t0:.0f}s, "
                          f"{(time.time() - t) / len(batch):.2f}s/doc)", file=sys.stderr)
                write_jsonl(rows, raw / name / f"{key}.jsonl")
                if name == "gpt4o_mini":
                    write_jsonl([{"doc_id": d["doc_id"], "spans": propagate(d["text"], r["spans"])}
                                 for d, r in zip(docs, rows)], raw / "gpt4o_mini_propagated" / f"{key}.jsonl")
                meta["sets"][key] = {"docs": len(rows), "seconds": round(time.time() - t0, 1)}
        except BudgetExceeded as exc:
            print(f"{name}: STOPPED, {exc}; sets finished so far are kept", file=sys.stderr)
            meta["stopped"] = str(exc)
            status = 2
        if live:
            spent, state = live
            meta.update(usd_spent_total=round(spent["usd"], 4), api_calls_this_run=state["calls"],
                        cache_hits_this_run=state["cache_hits"], unparseable_this_run=state["unparseable"],
                        models_served=sorted(state["models"]))
        meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        if not args.limit:
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
