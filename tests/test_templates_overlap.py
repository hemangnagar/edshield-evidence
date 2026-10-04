"""The acceptance-draft generator must not reuse edshield's k12_bench templates.

String literals of scripts/gen_acceptance_draft.py, shingled into word
5-grams, must have Jaccard overlap < 0.05 with the string literals of
edshield's eval/k12_bench.py at the pinned commit, fetched read-only at test
time and never written to disk.
"""

import ast
import os
import re
import ssl
import urllib.request
from pathlib import Path

import pytest

from edshield_evidence import EDSHIELD_COMMIT

ROOT = Path(__file__).resolve().parent.parent
GENERATOR = ROOT / "scripts" / "gen_acceptance_draft.py"
PINNED_URL = f"https://raw.githubusercontent.com/hemangnagar/edshield/{EDSHIELD_COMMIT}/eval/k12_bench.py"
MAX_JACCARD = 0.05
N = 5


def string_literals(source: str):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
    return out


def shingles(literals, n=N):
    s = set()
    for lit in literals:
        words = re.findall(r"\w+", lit.lower())
        for i in range(len(words) - n + 1):
            s.add(tuple(words[i:i + n]))
    return s


def _fetch(url: str) -> str:
    ctx = ssl.create_default_context()
    bundle = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if bundle and Path(bundle).exists():
        ctx.load_verify_locations(bundle)
    with urllib.request.urlopen(url, timeout=30, context=ctx) as resp:  # noqa: S310 - pinned https URL
        return resp.read().decode("utf-8")


def test_generator_templates_do_not_overlap_k12_bench():
    ours = shingles(string_literals(GENERATOR.read_text(encoding="utf-8")))
    assert len(ours) > 150, "the generator should carry a real template set"
    try:
        theirs_src = _fetch(PINNED_URL)
    except Exception as exc:  # noqa: BLE001
        if os.environ.get("CI") or os.environ.get("EDSHIELD_EVIDENCE_REQUIRE_NETWORK"):
            raise
        pytest.skip(f"cannot fetch the pinned k12_bench.py ({exc}); set EDSHIELD_EVIDENCE_REQUIRE_NETWORK=1 to make this fail")
    theirs = shingles(string_literals(theirs_src))
    assert len(theirs) > 50, "fetched file does not look like the generator"
    inter = ours & theirs
    jaccard = len(inter) / len(ours | theirs)
    assert jaccard < MAX_JACCARD, f"Jaccard {jaccard:.3f}; shared shingles: {sorted(inter)[:10]}"
    # and no sentence template of ours appears verbatim in theirs
    for lit in string_literals(GENERATOR.read_text(encoding="utf-8")):
        if len(lit.split()) >= 4 and "{" in lit:
            assert lit not in theirs_src, lit
