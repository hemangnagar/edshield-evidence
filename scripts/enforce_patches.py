"""Post-session enforcement (brief §4.6): apply each proposals/round_N.patch to a
clean edshield checkout at the pinned commit, fail loudly if a patch touches a
path outside the allowed rules/gazetteer files, then re-run the candidate
evaluation once for the final kept patch set and compare with the agent's
reported numbers.

    python scripts/enforce_patches.py                 # check + rescore
    python scripts/enforce_patches.py --check-only
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_api as api  # noqa: E402
from edshield_evidence import EDSHIELD_COMMIT, EDSHIELD_REPO  # noqa: E402

ROOT = api.ROOT
PROPOSALS = ROOT / "proposals"
ALLOWED = re.compile(r"^(edshield/rules\.py|edshield/gazetteer/[^/]+)$")
TOLERANCE_PP = 0.5
SCRATCH = ROOT / "runs" / "edshield-checkout"


def sh(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


def checkout() -> Path:
    if not (SCRATCH / ".git").exists():
        sh(["git", "clone", "--quiet", EDSHIELD_REPO, str(SCRATCH)])
    sh(["git", "checkout", "--quiet", "--force", EDSHIELD_COMMIT], cwd=SCRATCH)
    sh(["git", "clean", "-fdq"], cwd=SCRATCH)
    return SCRATCH


def patch_files(repo: Path, patch: Path):
    out = sh(["git", "apply", "--numstat", str(patch)], cwd=repo).stdout
    return [line.split("\t")[2] for line in out.strip().splitlines() if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--runtime", default="python")
    args = ap.parse_args(argv)
    patches = sorted(PROPOSALS.glob("round_*.patch"), key=lambda p: int(re.search(r"(\d+)", p.name).group(1)))
    if not patches:
        raise SystemExit("no proposals/round_*.patch files")
    kept = json.loads((PROPOSALS / "kept_rounds.json").read_text(encoding="utf-8")) if (PROPOSALS / "kept_rounds.json").exists() else {}
    final_round = kept.get("final_round", int(re.search(r"(\d+)", patches[-1].name).group(1)))
    repo = checkout()
    report = ["# Driver check of the agent's patches", "", f"edshield checkout `{EDSHIELD_COMMIT[:7]}`; allowed paths: `edshield/rules.py`, `edshield/gazetteer/*`.", ""]
    ok = True
    for p in patches:
        sh(["git", "checkout", "--quiet", "--force", EDSHIELD_COMMIT], cwd=repo)
        sh(["git", "clean", "-fdq"], cwd=repo)
        chk = sh(["git", "apply", "--check", str(p)], cwd=repo, check=False)
        if chk.returncode != 0:
            report.append(f"- `{p.name}`: **does not apply** to {EDSHIELD_COMMIT[:7]}: {chk.stderr.strip()[:300]}")
            ok = False
            continue
        files = patch_files(repo, p)
        bad = [f for f in files if not ALLOWED.match(f)]
        if bad:
            report.append(f"- `{p.name}`: **REJECTED**, touches {bad}")
            ok = False
        else:
            report.append(f"- `{p.name}`: applies cleanly; touches {files}")
    final_patch = PROPOSALS / f"round_{final_round}.patch"
    report.append("")
    if not ok:
        report.append("**At least one patch failed the path check. Nothing was re-scored for it.**")
    if args.check_only or not ok or not final_patch.exists():
        (PROPOSALS / "DRIVER_CHECK.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        print("\n".join(report))
        return 0 if ok else 1
    # independent re-score of the final kept patch set
    sh(["git", "checkout", "--quiet", "--force", EDSHIELD_COMMIT], cwd=repo)
    sh(["git", "clean", "-fdq"], cwd=repo)
    sh(["git", "apply", str(final_patch)], cwd=repo)
    sh([sys.executable, "-m", "pip", "install", "-q", "-e", str(repo)])
    try:
        out = ROOT / "results" / "candidate" / "driver_rescore"
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_views.py"), "--out", str(out), "--runtime", args.runtime], cwd=ROOT)
        if r.returncode != 0:
            raise SystemExit("re-score failed")
        mine = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        theirs_p = ROOT / "results" / "candidate" / f"round_{final_round}" / "summary.json"
        report += [f"## Independent re-score of `{final_patch.name}` vs the agent's `round_{final_round}/summary.json`", "",
                   "| number | agent | driver | diff |", "|---|---|---|---|"]
        if theirs_p.exists():
            theirs = json.loads(theirs_p.read_text(encoding="utf-8"))
            a_sha = (theirs.get("edshield") or {}).get("rules_sha256", "")
            b_sha = (mine.get("edshield") or {}).get("rules_sha256", "")
            report.append(f"| rules.py sha256 | {a_sha[:12] or 'n/a'} | {b_sha[:12] or 'n/a'} | "
                          + ("same" if a_sha and a_sha == b_sha else "**DIFFERENT: not the same patch**") + " |")
            worst = 0.0
            for v in ("deterministic", "llm"):
                for key in ("all_identifiers", "student_names"):
                    a = theirs["views"].get(v, {}).get(key, {}).get("span_recall")
                    b = mine["views"].get(v, {}).get(key, {}).get("span_recall")
                    if a is not None and b is not None:
                        d = 100 * (b - a)
                        worst = max(worst, abs(d))
                        report.append(f"| {v} {key} recall | {100 * a:.2f}% | {100 * b:.2f}% | {d:+.2f} pp |")
            for ds in mine["control"]:
                a = theirs["control"].get(ds, {}).get("flags_per_1000_tokens")
                b = mine["control"][ds]["flags_per_1000_tokens"]
                if a is not None:
                    d = b - a
                    worst = max(worst, abs(d))
                    report.append(f"| control {ds} flags/1k | {a:.3f} | {b:.3f} | {d:+.3f} |")
            report += ["", f"Largest discrepancy: {worst:.2f} (tolerance {TOLERANCE_PP}). "
                       + ("**Matches within rounding.**" if worst <= TOLERANCE_PP else "**DISCREPANCY beyond rounding; reported, not overwritten.**")
                       + ("" if a_sha and a_sha == b_sha else " **The agent summary and the driver measured different rules.py files; the comparison is void.**")]
        else:
            report.append(f"| (agent summary {theirs_p} missing) | | | |")
    finally:
        sh([sys.executable, "-m", "pip", "install", "-q", "edshield==0.2.0"])  # restore the pin
    (PROPOSALS / "DRIVER_CHECK.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
