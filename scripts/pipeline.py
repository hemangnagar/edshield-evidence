"""The recurring job behind the scheduled trigger: one candidate regression and
proposal cycle, end to end, idempotent per run id.

    python scripts/pipeline.py --edshield-ref main            # full cycle on a fresh branch
    python scripts/pipeline.py --run-id 20261022 --stages diagnose,propose   # resume selected stages

Stages, in order (each one skips itself when its outputs for this run exist):
  data      raw files, sealed planted set rebuilt and checked, LLM view unsealed from git
  branch    auto/agent-diagnose-<run id> from --base (main), pushed (the sandbox clones it)
  regress   Managed Agents session: candidate at --edshield-ref, round 0 on both views + control,
            failure tables shipped back
  diagnose  Batch API: cause labels for misses not already in results/diagnosis/causes.jsonl
  propose   the bounded improve loop in the same session (task message), proposals shipped back
  verify    fresh session: driver path check + independent re-score of the kept patch set
  report    COST.md and results/RUN_<run id>.md, commit, push
Spend goes to the platform org through EDSHIELD_PLATFORM_API_KEY; this script never calls a model itself.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_api as api  # noqa: E402
import run_agent_loop as ral  # noqa: E402

ROOT = api.ROOT
STAGES = ["data", "branch", "regress", "diagnose", "propose", "verify", "report"]


def sh(cmd: List[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd), file=sys.stderr)
    return subprocess.run(cmd, cwd=ROOT, check=check, capture_output=capture, text=True)


class Pipeline:
    def __init__(self, args):
        self.args = args
        self.run_id = args.run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M")
        self.branch = args.branch or f"auto/agent-diagnose-{self.run_id}"
        self.state_dir = ROOT / "runs" / f"pipeline-{self.run_id}"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {"run_id": self.run_id, "branch": self.branch, "stages": {}}
        self.client = api.make_client()

    def save(self, stage: str, **info) -> None:
        self.state["stages"][stage] = {"done_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **info}
        self.state_path.write_text(json.dumps(self.state, indent=1), encoding="utf-8")

    def done(self, stage: str) -> bool:
        return stage in self.state["stages"] and not self.args.force

    # --- stages -------------------------------------------------------------------
    def data(self) -> None:
        sh([sys.executable, "scripts/llm_view_store.py", "unseal"])
        sh(["make", "raw"]); sh(["make", "plant-check"])
        self.save("data")

    def branch_(self) -> None:
        sh(["git", "fetch", "-q", "origin", self.args.base])
        sh(["git", "checkout", "-q", "-B", self.branch, f"origin/{self.args.base}"])
        sh(["git", "push", "-q", "-u", "origin", self.branch])
        self.save("branch", branch=self.branch)

    def _session_args(self, phase: str, extra: List[str]) -> List[str]:
        return [sys.executable, "-u", "scripts/run_agent_loop.py", "--phase", phase, "--runtime", self.args.runtime,
                "--branch", self.branch, "--budget-cents", str(self.args.budget_cents), *extra]

    def regress(self) -> None:
        msg = (ROOT / "prompts" / "agent_regress_message.md").read_text(encoding="utf-8").replace("{edshield_ref}", self.args.edshield_ref)
        setup_override = self.state_dir / "regress_message.md"
        setup_override.write_text(msg, encoding="utf-8")
        sh(self._session_args("setup", ["--setup-message", str(setup_override), "--title", f"agent-diagnose {self.run_id}: regression"]))
        sess = self._latest_session()
        if sess.get("ended") != "normal finish":
            raise SystemExit(f"regression session ended with {sess.get('ended')} ({sess.get('stop_reason')})")
        self.save("regress", session_id=sess["session_id"], run_dir=sess["run_dir"])

    def diagnose(self) -> None:
        sh([sys.executable, "scripts/build_failure_table.py", "deterministic", "llm", "--candidate", "round_0"])
        r = sh([sys.executable, "scripts/diagnose.py", "submit", "--new-only"], capture=True)
        print(r.stdout)
        if "nothing to submit" not in r.stdout:
            sh([sys.executable, "scripts/diagnose.py", "collect", "--poll", "90"])
        else:
            sh([sys.executable, "scripts/diagnose.py", "summarize"])
        self._commit("results: diagnosis for run " + self.run_id, ["results/diagnosis", "results/candidate/round_0", "runs"])
        self.save("diagnose")

    def propose(self) -> None:
        sid = self.state["stages"]["regress"]["session_id"]
        sh(self._session_args("task", ["--session", sid]))
        sess = self._latest_session()
        self._commit("proposals: run " + self.run_id, ["proposals", "results/candidate", "runs"])
        self.save("propose", session_id=sid, ended=sess.get("ended"), stop_reason=sess.get("stop_reason"))

    def verify(self) -> None:
        sh(self._session_args("verify", ["--budget-cents", "1000", "--title", f"agent-diagnose {self.run_id}: verification"]))
        self._commit("proposals: driver check for run " + self.run_id, ["proposals/DRIVER_CHECK.md", "results/candidate/driver_rescore", "runs"])
        self.save("verify")

    def report(self) -> None:
        sh([sys.executable, "scripts/cost.py", "--run", str(self.state_dir)])
        self._write_run_report()
        self._commit("report: run " + self.run_id, ["results", "runs"])
        if self.args.push:
            sh(["git", "push", "-q", "origin", self.branch])
        self.save("report")
        print(f"\nRun {self.run_id} complete on branch {self.branch}. Open a PR against main titled "
              f"\"exp: agent-diagnose run {self.run_id}\" (the scheduled session or the Actions job does this).")

    # --- helpers ---------------------------------------------------------------------
    def _latest_session(self) -> dict:
        d = sorted(p for p in (ROOT / "runs").glob("*-agent") if (p / "SESSION.json").exists())[-1]
        return json.loads((d / "SESSION.json").read_text(encoding="utf-8"))

    def _commit(self, message: str, paths: List[str]) -> None:
        sh(["git", "add", "-A", *paths], check=False)
        if sh(["git", "diff", "--cached", "--quiet"], check=False).returncode != 0:
            sh(["git", "commit", "-q", "-m", message + "\n\nAutomated by scripts/pipeline.py"])
            if self.args.push:
                sh(["git", "push", "-q", "origin", self.branch])

    def _write_run_report(self) -> None:
        def load(p):
            f = ROOT / p
            return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
        r0, kept = load("results/candidate/round_0/summary.json"), load("proposals/kept_rounds.json")
        final = load(f"results/candidate/round_{kept['final_round']}/summary.json") if kept else None
        L = [f"# Agent-diagnose run {self.run_id}", "", f"Branch `{self.branch}`; candidate edshield ref `{self.args.edshield_ref}`; "
             f"runtime {self.args.runtime}. Stages: {', '.join(self.state['stages'])}.", ""]
        if r0:
            L += ["| view | round 0 identifier recall | final kept round |", "|---|---|---|"]
            for v, h in r0["views"].items():
                f = final["views"][v]["all_identifiers"]["span_recall"] if final and v in final["views"] else None
                L.append(f"| {v} | {100 * h['all_identifiers']['span_recall']:.2f}% (n={h['all_identifiers']['n']}) | {100 * f:.2f}%" if f is not None else f"| {v} | {100 * h['all_identifiers']['span_recall']:.2f}% | n/a |")
            L += ["", f"Sanity gate: delta {r0['sanity']['deterministic_delta_pp']} pp vs the sealed baseline, within tolerance: {r0['sanity']['within_tolerance']}.", ""]
        if kept:
            L += [f"Rounds kept: {kept['kept']}; see `proposals/PROPOSAL.md` and `proposals/DRIVER_CHECK.md`. Nothing is merged; a human reviews.", ""]
        L += [f"Spend: see `{self.state_dir.relative_to(ROOT)}/COST.md`.", ""]
        (ROOT / "results" / f"RUN_{self.run_id}.md").write_text("\n".join(L), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--edshield-ref", default="main", help="git ref of hemangnagar/edshield to measure as the candidate")
    ap.add_argument("--base", default="main", help="branch the run branch forks from (and the PR targets)")
    ap.add_argument("--run-id")
    ap.add_argument("--branch")
    ap.add_argument("--stages", default=",".join(STAGES))
    ap.add_argument("--runtime", default="onnx", choices=["onnx", "python"])
    ap.add_argument("--budget-cents", type=int, default=3000)
    ap.add_argument("--force", action="store_true", help="re-run stages already recorded as done")
    ap.add_argument("--no-push", dest="push", action="store_false")
    args = ap.parse_args(argv)
    p = Pipeline(args)
    for stage in [s for s in STAGES if s in args.stages.split(",")]:
        if p.done(stage):
            print(f"[{stage}] already done for run {p.run_id}", file=sys.stderr)
            continue
        print(f"[{stage}] starting", file=sys.stderr)
        getattr(p, "branch_" if stage == "branch" else stage)()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
