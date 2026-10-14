"""Shared plumbing for the agent-diagnose branch: one client factory, run
directories, batch helpers and cost accounting. Every API call made from this
branch goes through here so that it is logged under runs/<timestamp>-<tag>/.

The client pins the official API base URL. This container sets
ANTHROPIC_BASE_URL to Claude Code's own proxy, and spend from this branch has
to land on the platform org that holds the credits, not on whatever that proxy
bills. Override with EDSHIELD_PLATFORM_BASE_URL only on purpose.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
OFFICIAL_BASE_URL = "https://api.anthropic.com"

# Models per the brief (§1). Batch prices are 50% of standard list price.
MODELS = {"plant": "claude-sonnet-5-5", "diagnose": "claude-opus-5-5", "agent": "claude-opus-5-5",
          "key_check": "claude-haiku-5-5"}
# USD per million tokens at standard list price: (input, output, cache write 5m, cache read)
PRICES = {
    "claude-sonnet-5-5": (2.00, 10.00, 2.50, 0.20),
    "claude-opus-5-5": (4.00, 20.00, 5.00, 0.40),
    "claude-haiku-5-5": (0.10, 0.50, 0.125, 0.01),
}
BUDGET_USD = 71.0


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def new_run_dir(tag: str) -> Path:
    d = RUNS / f"{utc_stamp()}-{tag}"
    d.mkdir(parents=True, exist_ok=False)
    return d


def latest_run_dir(tag: str) -> Optional[Path]:
    cands = sorted(p for p in RUNS.glob(f"*-{tag}") if p.is_dir())
    return cands[-1] if cands else None


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def write_jsonl(rows: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def append_jsonl(row: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# --- client ---------------------------------------------------------------------

def make_client(require_key: bool = True):
    import anthropic

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if require_key and not key:
        raise SystemExit("ANTHROPIC_API_KEY is not set; see WAITING.md (add it as an environment secret)")
    base = os.environ.get("EDSHIELD_PLATFORM_BASE_URL", OFFICIAL_BASE_URL)
    if os.environ.get("ANTHROPIC_BASE_URL") and os.environ["ANTHROPIC_BASE_URL"] != base:
        print(f"note: ignoring ANTHROPIC_BASE_URL={os.environ['ANTHROPIC_BASE_URL'][:40]}...; using {base}", file=sys.stderr)
    return anthropic.Anthropic(api_key=key or "missing", base_url=base, max_retries=4)


# --- cost -----------------------------------------------------------------------

def usage_dict(usage) -> Dict[str, int]:
    if usage is None:
        return {}
    if isinstance(usage, dict):
        d = usage
    else:
        d = usage.to_dict() if hasattr(usage, "to_dict") else dict(usage)
    out = {}
    for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
        v = d.get(k)
        if isinstance(v, (int, float)):
            out[k] = int(v)
    return out


def usage_cost_usd(model: str, usage: Dict[str, int], batch: bool) -> float:
    p_in, p_out, p_cw, p_cr = PRICES[model]
    f = 0.5 if batch else 1.0
    return f * (usage.get("input_tokens", 0) * p_in + usage.get("output_tokens", 0) * p_out
                + usage.get("cache_creation_input_tokens", 0) * p_cw
                + usage.get("cache_read_input_tokens", 0) * p_cr) / 1e6


# --- batches --------------------------------------------------------------------

def request_index_row(req: dict) -> dict:
    """Text-free record of one batch request (the full request may carry licensed dialogue text)."""
    body = json.dumps(req["params"], ensure_ascii=False, sort_keys=True)
    return {"custom_id": req["custom_id"], "model": req["params"].get("model"), "sha256": sha256_text(body),
            "chars": len(body), **{k: v for k, v in req.items() if k not in ("custom_id", "params")}}


def submit_batch(client, requests: List[dict], run_dir: Path, name: str) -> str:
    """Create a batch, log the full requests (git-ignored) and a text-free index (committed)."""
    write_jsonl(requests, run_dir / f"batch_{name}_requests.jsonl")
    write_jsonl([request_index_row(r) for r in requests], run_dir / f"batch_{name}_requests.index.jsonl")
    batch = client.messages.batches.create(
        requests=[{"custom_id": r["custom_id"], "params": r["params"]} for r in requests])
    meta = {"id": batch.id, "name": name, "created_at": str(batch.created_at), "n_requests": len(requests),
            "processing_status": batch.processing_status, "expires_at": str(batch.expires_at)}
    (run_dir / f"batch_{name}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"submitted batch {batch.id} ({len(requests)} requests) -> {run_dir}")
    return batch.id


def batch_meta(run_dir: Path, name: str) -> dict:
    return json.loads((run_dir / f"batch_{name}.json").read_text(encoding="utf-8"))


def wait_batch(client, batch_id: str, poll_seconds: int = 60, max_wait: int = 24 * 3600) -> Any:
    t0 = time.monotonic()
    while True:
        b = client.messages.batches.retrieve(batch_id)
        c = b.request_counts
        print(f"  {batch_id}: {b.processing_status} processing={c.processing} succeeded={c.succeeded} "
              f"errored={c.errored} expired={c.expired} canceled={c.canceled}", file=sys.stderr)
        if b.processing_status == "ended":
            return b
        if time.monotonic() - t0 > max_wait:
            raise SystemExit(f"batch {batch_id} did not end within {max_wait}s")
        time.sleep(poll_seconds)


def collect_batch(client, batch_id: str, run_dir: Path, name: str, model: str) -> Dict[str, dict]:
    """Stream results keyed by custom_id (never by order). Logs the full results
    (git-ignored) and a text-free index with per-request usage and cost."""
    out: Dict[str, dict] = {}
    full, index = [], []
    for res in client.messages.batches.results(batch_id):
        r = res.result
        row = {"custom_id": res.custom_id, "type": r.type}
        if r.type == "succeeded":
            msg = r.message
            text = "".join(b.text for b in msg.content if b.type == "text")
            u = usage_dict(msg.usage)
            row.update({"text": text, "stop_reason": msg.stop_reason, "usage": u, "model": msg.model,
                        "cost_usd": round(usage_cost_usd(model, u, batch=True), 6)})
        elif r.type == "errored":
            row["error"] = r.error.to_dict() if hasattr(r.error, "to_dict") else str(r.error)
        out[res.custom_id] = row
        full.append(row)
        index.append({k: v for k, v in row.items() if k != "text"} | {"text_sha256": sha256_text(row.get("text", ""))})
    write_jsonl(full, run_dir / f"batch_{name}_results.jsonl")
    write_jsonl(index, run_dir / f"batch_{name}_results.index.jsonl")
    n_ok = sum(1 for r in full if r["type"] == "succeeded")
    cost = sum(r.get("cost_usd", 0.0) for r in full)
    print(f"collected {len(full)} results ({n_ok} succeeded), batch cost ${cost:.4f}")
    return out


def dry_run(client, request: dict, run_dir: Path, name: str) -> dict:
    """One request through messages.create to catch validation errors before a batch
    (batch validation is asynchronous). Logged like a batch result."""
    msg = client.messages.create(**request["params"])
    text = "".join(b.text for b in msg.content if b.type == "text")
    u = usage_dict(msg.usage)
    model = request["params"]["model"]
    row = {"custom_id": request["custom_id"], "type": "dry_run", "text": text, "stop_reason": msg.stop_reason,
           "usage": u, "model": msg.model, "cost_usd": round(usage_cost_usd(model, u, batch=False), 6),
           "request_id": getattr(msg, "_request_id", None)}
    write_jsonl([request], run_dir / f"dryrun_{name}_request.jsonl")
    write_jsonl([row], run_dir / f"dryrun_{name}_result.jsonl")
    write_jsonl([{k: v for k, v in row.items() if k != "text"}], run_dir / f"dryrun_{name}_result.index.jsonl")
    print(f"dry run {request['custom_id']}: stop={msg.stop_reason} usage={u} cost=${row['cost_usd']:.4f}")
    return row


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str) -> Any:
    """Parse the model's JSON output; tolerates a fenced block around it."""
    s = text.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    m = _FENCE.search(s)
    if m:
        return json.loads(m.group(1))
    i, j = s.find("{"), s.rfind("}")
    if i >= 0 and j > i:
        return json.loads(s[i:j + 1])
    raise ValueError("no JSON object in output")


def cached_system(blocks: List[str]) -> List[dict]:
    """System blocks with cache_control on the last one so batch cache hits stack
    with the batch discount (prefix caching: shared text first)."""
    out = [{"type": "text", "text": t} for t in blocks]
    out[-1]["cache_control"] = {"type": "ephemeral"}
    return out
