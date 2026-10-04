"""Judge policy bundles.

policies/regression.json and policies/acceptance.json each hold several judge
policy bundles keyed by `<dataset>/<detector>` (regression) or `<detector>`
(acceptance), because the judge rejects a policy that names a view the
bundle does not have, and PIILO, k12_hard and a sealed set carry different
label sets and different targets.

`select` copies one sub-bundle to a file for the judge CLI. With --bundle it
also drops `type:*` entries for labels the bundle has no view for, printing
each one; it never adds, relaxes or computes a target.

A policy file is ratified when a commit whose message starts with `ratify:`
touched it. Until then every summary says "criteria PROVISIONAL, not ratified".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from . import POLICIES_DIR, REPO_ROOT

REGRESSION = POLICIES_DIR / "regression.json"
ACCEPTANCE = POLICIES_DIR / "acceptance.json"


def load_keyed(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def select(path: Path, key: str, bundle_path: Optional[Path] = None) -> Tuple[dict, List[str]]:
    keyed = load_keyed(path)
    try:
        pol = json.loads(json.dumps(keyed["policies"][key]))
    except KeyError:
        raise SystemExit(f"{path} has no policy {key!r}; available: {sorted(keyed.get('policies', {}))}")
    dropped: List[str] = []
    if bundle_path is not None:
        views = set(json.loads(Path(bundle_path).read_text(encoding="utf-8")).get("views", {}))
        for name in list(pol["views"]):
            if name.startswith("type:") and name not in views:
                dropped.append(name)
                del pol["views"][name]
    pol["_source"] = f"{Path(path).relative_to(REPO_ROOT) if Path(path).is_absolute() and REPO_ROOT in Path(path).parents else path}#{key}"
    pol["_ratified"] = is_ratified(path)
    pol["_dropped_views"] = dropped
    return pol, dropped


def is_ratified(path: Path) -> bool:
    try:
        out = subprocess.run(
            ["git", "log", "--format=%s", "--", str(path)], cwd=str(REPO_ROOT),
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return any(line.startswith("ratify:") for line in out.splitlines())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m edshield_evidence.policy")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select", help="write one keyed sub-policy to a file for the judge")
    s.add_argument("file")
    s.add_argument("key")
    s.add_argument("--out", required=True)
    s.add_argument("--bundle", default=None, help="drop type:* entries the bundle has no view for")
    l = sub.add_parser("list")
    l.add_argument("file")
    st = sub.add_parser("status", help="ratification status of the policy files")
    a = ap.parse_args(argv)
    if a.cmd == "select":
        pol, dropped = select(Path(a.file), a.key, Path(a.bundle) if a.bundle else None)
        Path(a.out).write_text(json.dumps(pol, indent=2) + "\n", encoding="utf-8")
        for d in dropped:
            print(f"policy: dropped {d} (no such view in the bundle)", file=sys.stderr)
        print(f"wrote {a.out} from {a.file}#{a.key} (ratified: {pol['_ratified']})", file=sys.stderr)
    elif a.cmd == "list":
        for k, v in load_keyed(Path(a.file))["policies"].items():
            print(f"{k}: views {', '.join(v['views'])}; minRuns {v['minRuns']}; confidence {v.get('confidence', False)}")
    else:
        for p in (REGRESSION, ACCEPTANCE):
            print(f"{p.relative_to(REPO_ROOT)}: {'ratified' if is_ratified(p) else 'PROVISIONAL, not ratified'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
