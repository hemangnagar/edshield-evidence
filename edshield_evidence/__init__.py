"""edshield-evidence: the protected bench for edshield.

Runs the full `edshield.deidentify()` pipeline under a named policy and
runtime, measures what identifying text survives in the final output, reduces
the result to binary row views, and hands those to the model-evidence judge
(git submodule at `judge/`, tag v2.0.0) for a verdict.

Nothing in this package modifies edshield, and nothing here imports from
edshield's own evaluator (`eval/` in the edshield repository).
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"

# Pins. The system under test is the PyPI release; the commit is the source it
# was built from and the commit the k12_hard generator is run from.
EDSHIELD_VERSION = "0.2.0"
EDSHIELD_COMMIT = "a568e73a6c34d40335802235db81950e84004ab1"
EDSHIELD_REPO = "https://github.com/hemangnagar/edshield"
JUDGE_TAG = "v2.0.0"

EXPORTER_VERSION = __version__

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = REPO_ROOT / "evidence"
SETS_DIR = EVIDENCE_DIR / "sets"
REPORTS_DIR = EVIDENCE_DIR / "reports"
POLICIES_DIR = REPO_ROOT / "policies"
JUDGE_DIR = REPO_ROOT / "judge"
JUDGE_CLI = JUDGE_DIR / "dist" / "run-evidence.mjs"

# Words that must not appear in any report. The bench states that a system
# "meets defined redaction criteria on evidence set X under policy Y"; it does
# not certify anything.
FORBIDDEN_REPORT_WORDS = ("compliant",)
