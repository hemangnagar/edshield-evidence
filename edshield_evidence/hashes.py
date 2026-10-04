"""Fingerprints recorded in every bundle so the judge can group runs.

data_sha256         the dataset file.
recipe_sha256       sha256 over {edshield version, policy fingerprint,
                    sha256 of the installed edshield/rules.py, detector,
                    runtime, o_threshold, exporter version}.
environment_sha256  python version, platform, pinned package versions.
model_sha256        sha256 of the model weights file(s) actually loaded.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional, Union

from . import EDSHIELD_VERSION, EXPORTER_VERSION

PINNED_PACKAGES = (
    "edshield", "pyyaml", "faker", "cryptography", "numpy", "torch", "transformers",
    "tokenizers", "sentencepiece", "onnxruntime", "onnx", "huggingface-hub", "safetensors",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def sha256_file(path: Union[str, Path]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _js_numbers(obj):
    """JSON.stringify writes 1.0 as 1; match it so Python-side digests equal the judge's."""
    if isinstance(obj, float) and obj.is_integer():
        return int(obj)
    if isinstance(obj, dict):
        return {k: _js_numbers(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_js_numbers(v) for v in obj]
    return obj


def canonical_json(obj) -> str:
    """Sorted keys at every depth, no whitespace, JavaScript number formatting:
    the judge's `canonical()`, so `sha256_json(bundle)` equals the verdict's
    `input_sha256` and `sha256_json(policy)` its `policy_sha256`."""
    return json.dumps(_js_numbers(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(obj) -> str:
    return sha256_text(canonical_json(obj))


def installed_rules_path() -> Path:
    import edshield.rules  # the installed package, not a checkout

    return Path(edshield.rules.__file__)


def installed_edshield_version() -> str:
    import edshield

    return edshield.__version__


def policy_fingerprint(policy: str) -> str:
    from edshield.deid import policy_fingerprint as fp  # public helper of the runtime, not of eval/

    return fp(policy)


def recipe(policy: str, detector: str, runtime: str, o_threshold: Optional[float] = None,
           rules_path: Optional[Union[str, Path]] = None, policy_fp: Optional[str] = None) -> Dict:
    return {
        "edshield_version": installed_edshield_version(),
        "edshield_pin": EDSHIELD_VERSION,
        "policy": policy if "/" not in str(policy) else Path(policy).stem,
        "policy_fingerprint": policy_fp or policy_fingerprint(policy),
        "rules_sha256": sha256_file(rules_path or installed_rules_path()),
        "detector": detector,
        "runtime": runtime,
        "o_threshold": o_threshold,
        "exporter_version": EXPORTER_VERSION,
    }


def recipe_sha256(policy: str, detector: str, runtime: str, o_threshold: Optional[float] = None,
                  rules_path: Optional[Union[str, Path]] = None) -> str:
    return sha256_json(recipe(policy, detector, runtime, o_threshold, rules_path))


def package_versions(names: Iterable[str] = PINNED_PACKAGES) -> Dict[str, Optional[str]]:
    from importlib.metadata import PackageNotFoundError, version

    out: Dict[str, Optional[str]] = {}
    for n in names:
        try:
            out[n] = version(n)
        except PackageNotFoundError:
            out[n] = None
    return out


def environment() -> Dict:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": package_versions(),
    }


def environment_sha256() -> str:
    return sha256_json(environment())


def model_sha256(paths: Iterable[Union[str, Path]]) -> str:
    """One digest over several weight files: the sorted (name, sha256) pairs."""
    paths = sorted(Path(p) for p in paths)
    if len(paths) == 1:
        return sha256_file(paths[0])
    return sha256_json([[p.name, sha256_file(p)] for p in paths])
