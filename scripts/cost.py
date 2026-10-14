"""COST.md: per-component spend from the logged batch usage fields and the agent
session's usage event, against the $71 budget (brief §6).

    python scripts/cost.py [--run DIR]      # default: a new runs/<ts>-cost/COST.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_api as api  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    args = ap.parse_args(argv)
    comp: Dict[str, dict] = {}

    def add(component: str, kind: str, usd: float, n: int, usage: Dict[str, int]):
        c = comp.setdefault(component, {"usd": 0.0, "requests": 0, "usage": {}, "kinds": set()})
        c["usd"] += usd
        c["requests"] += n
        c["kinds"].add(kind)
        for k, v in usage.items():
            c["usage"][k] = c["usage"].get(k, 0) + v

    for run in sorted(api.RUNS.glob("*-*")):
        if not run.is_dir():
            continue
        tag = run.name.split("-", 1)[1]
        for idx in sorted(run.glob("batch_*_results.index.jsonl")):
            rows = api.read_jsonl(idx)
            usage = {}
            for r in rows:
                for k, v in (r.get("usage") or {}).items():
                    usage[k] = usage.get(k, 0) + v
            add(tag, "batch", sum(r.get("cost_usd", 0) for r in rows), len(rows), usage)
        for idx in sorted(run.glob("dryrun_*_result.index.jsonl")):
            rows = api.read_jsonl(idx)
            add(tag, "dry-run", sum(r.get("cost_usd", 0) for r in rows), len(rows), rows[0].get("usage", {}) if rows else {})
        sess = run / "SESSION.json"
        if sess.exists():
            s = json.loads(sess.read_text(encoding="utf-8"))
            lc = (s.get("usage") or {}).get("list_cost") or {}
            usd = int(lc.get("amount", 0)) / 100 if lc else 0.0
            u = {k: v for k, v in (s.get("usage") or {}).items() if isinstance(v, int)}
            add("agent", "session", usd, 1, u)
            comp["agent"]["active_seconds"] = (s.get("usage") or {}).get("active_seconds")
            comp["agent"]["stop_reason"] = s.get("stop_reason")
    kc = api.RUNS / "KEY_CHECK.md"
    if kc.exists():
        for line in kc.read_text(encoding="utf-8").splitlines():
            if line.startswith("- cost of this check: $"):
                add("key-check", "messages", float(line.split("$")[1]), 1, {})
    total = sum(c["usd"] for c in comp.values())
    L = ["# Spend", "", "Per component, from the per-request `usage` fields of every logged batch/dry-run result "
         "(batch requests at 50% of list price) and the agent session's `session.usage` event (list price, as the platform bills "
         f"and caps it). Budget: ${api.BUDGET_USD:.0f}.", "",
         "| component | kind | requests | input tok | output tok | cache write | cache read | USD |", "|---|---|---|---|---|---|---|---|"]
    for name, c in sorted(comp.items()):
        u = c["usage"]
        L.append(f"| {name} | {', '.join(sorted(c['kinds']))} | {c['requests']} | {u.get('input_tokens', 0):,} | {u.get('output_tokens', 0):,} | "
                 f"{u.get('cache_creation_input_tokens', 0):,} | {u.get('cache_read_input_tokens', 0):,} | {c['usd']:.2f} |")
    L += [f"| **total** | | | | | | | **{total:.2f}** |", "", f"Remaining of the ${api.BUDGET_USD:.0f} budget: ${api.BUDGET_USD - total:.2f}."]
    if "agent" in comp:
        L.append(f"Agent session: stop reason `{comp['agent'].get('stop_reason')}`, active {comp['agent'].get('active_seconds')} s "
                 "(runtime is billed per active hour on top of tokens; the list_cost above includes it).")
    L.append("")
    L.append("The platform Console is the authority for what was actually charged; these are list-price reconstructions from the logs.")
    run_dir = Path(args.run) if args.run else api.new_run_dir("cost")
    (run_dir / "COST.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"-> {run_dir / 'COST.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
