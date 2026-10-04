"""Runtimes: the python runtime calls `edshield.deidentify` directly; the onnx
runtime swaps the model call for ONNX Runtime on the INT8 export and leaves
windowing, decoding, model authority, the rules and the policy application
exactly as edshield runs them.

Both runtimes expose the same interface:

    with runtime:
        result = runtime.deidentify(text, policy="coppa", seed=0)
    runtime.model_sha256   # sha256 of the weights actually loaded

Detectors:
  rules        `model_name="rules"`; the rule layer alone.
  rules+model  the named model must load; a silent fall-back to rules is an error.

The ONNX inference (about twenty lines: tokenizer, softmax, the same window
split) reproduces what edshield's `eval/evaluate_onnx.py` does, because the
installed package has no ONNX entry point of its own and this repo must not
import from edshield's eval/. It is kept in step with edshield.ner by calling
edshield.ner's own helpers for everything except the forward pass.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import edshield
from edshield import ner

from . import hashes

_ORIGINAL_PREDICT = ner._predict

DEFAULT_MODEL = "piilo_deberta_small"  # short name in edshield's models.jsonl
MODEL_ALIASES = {
    "piilo-deberta-v3-small-v2": DEFAULT_MODEL,
    "piilo-deberta-v3-small": DEFAULT_MODEL,
    "edshield/piilo-deberta-v3-small": DEFAULT_MODEL,
}
ONNX_HF_ID = "edshield/piilo-deberta-v3-small-onnx"
ONNX_FILES = {"int8": "onnx/model_quantized.onnx", "fp32": "onnx/model.onnx"}
WEIGHT_FILES = ("model.safetensors", "pytorch_model.bin")

DETECTORS = ("rules", "rules+model")
RUNTIMES = ("python", "onnx")


class RuntimeUnavailable(RuntimeError):
    """The requested runtime or model could not be loaded or did not run."""


def downloads_allowed() -> bool:
    return os.environ.get("EDSHIELD_ALLOW_DOWNLOAD", "").strip().lower() in {"1", "true", "yes"}


class BaseRuntime:
    name = "base"

    def __init__(self, detector: str):
        if detector not in DETECTORS:
            raise ValueError(f"detector must be one of {DETECTORS}")
        self.detector = detector
        self._model_sha256: Optional[str] = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def model_ref(self) -> str:
        raise NotImplementedError

    @property
    def model_sha256(self) -> str:
        if self._model_sha256 is None:
            self._model_sha256 = self._compute_model_sha256()
        return self._model_sha256

    def _compute_model_sha256(self) -> str:
        raise NotImplementedError

    def deidentify(self, text: str, policy: str, seed: Optional[int] = None, o_threshold: Optional[float] = None):
        raise NotImplementedError

    def describe(self) -> Dict:
        return {"runtime": self.name, "detector": self.detector, "model": self.model_ref}


def _rules_sha256() -> str:
    # Rules-only runs have no weights. The "model" is the rule file, so the
    # judge's reproducibility grouping still has a 64-hex fingerprint to compare.
    return hashes.sha256_file(hashes.installed_rules_path())


class PythonRuntime(BaseRuntime):
    name = "python"

    def __init__(self, detector: str = "rules+model", model: str = DEFAULT_MODEL,
                 model_dir: Optional[str] = None, device: str = "cpu"):
        super().__init__(detector)
        self.device = device
        if detector == "rules":
            self.model_name = "rules"
        else:
            self.model_name = model_dir or MODEL_ALIASES.get(model, model)

    def __enter__(self):
        if ner._predict is not _ORIGINAL_PREDICT:
            raise RuntimeUnavailable("edshield.ner._predict is patched by another runtime; close it first")
        return self

    @property
    def model_ref(self) -> str:
        return self.model_name

    def deidentify(self, text: str, policy: str, seed: Optional[int] = None, o_threshold: Optional[float] = None):
        # verify=False: an acted-on value that survives is a residual to record, not an exception.
        r = edshield.deidentify(
            text, policy=policy, model_name=self.model_name, device=self.device,
            seed=seed, verify=False, o_threshold=o_threshold,
        )
        if self.detector == "rules+model" and r.audit.get("detector") in (None, "rules"):
            raise RuntimeUnavailable(f"model {self.model_name!r} did not run; audit says {r.audit.get('detector')!r}")
        return r

    def _compute_model_sha256(self) -> str:
        if self.detector == "rules":
            return _rules_sha256()
        return hashes.model_sha256(weight_files(self.model_name))


def weight_files(model_name: str) -> List[Path]:
    """The weight file(s) edshield loads for `model_name`: a directory's
    safetensors/bin, or the Hugging Face cache entry for the repo id."""
    model_id = ner.resolve_model_id(model_name)
    p = Path(model_id)
    if p.is_dir():
        for name in WEIGHT_FILES:
            if (p / name).exists():
                return [p / name]
        shards = sorted(p.glob("model-*.safetensors")) or sorted(p.glob("pytorch_model-*.bin"))
        if shards:
            return shards
        raise RuntimeUnavailable(f"no weights found in {p}")
    try:
        from huggingface_hub import hf_hub_download, try_to_load_from_cache
    except ImportError as exc:  # pragma: no cover
        raise RuntimeUnavailable("huggingface_hub is needed to locate the loaded weights") from exc
    for name in WEIGHT_FILES:
        cached = try_to_load_from_cache(model_id, name)
        if isinstance(cached, str):
            return [Path(cached)]
    if downloads_allowed():
        for name in WEIGHT_FILES:
            try:
                return [Path(hf_hub_download(model_id, name))]
            except Exception:  # noqa: BLE001 - try the next file name
                continue
    raise RuntimeUnavailable(f"weights for {model_id} are not in the Hugging Face cache")


class OnnxRuntime(BaseRuntime):
    """INT8 (or fp32) export under ONNX Runtime, through edshield's own windowing,
    decoding and policy application. Use as a context manager: entering patches
    `edshield.ner._predict`, leaving restores it."""

    name = "onnx"

    def __init__(self, detector: str = "rules+model", onnx_dir: Optional[str] = None,
                 onnx_file: Optional[str] = None, quant: str = "int8", threads: int = 0):
        super().__init__(detector)
        if detector != "rules+model":
            raise ValueError("the onnx runtime only makes sense with --detector rules+model")
        self.quant = quant
        self.threads = threads
        self.onnx_path, self.model_dir = self._resolve(onnx_dir, onnx_file, quant)
        self._session = None
        self._tok = None
        self._id2label: Dict[int, str] = {}

    @staticmethod
    def _resolve(onnx_dir: Optional[str], onnx_file: Optional[str], quant: str) -> Tuple[Path, Path]:
        if onnx_file:
            f = Path(onnx_file)
            return f, Path(onnx_dir) if onnx_dir else f.parent.parent
        if onnx_dir:
            d = Path(onnx_dir)
            return d / ONNX_FILES[quant], d
        try:
            from huggingface_hub import snapshot_download
        except ImportError as exc:  # pragma: no cover
            raise RuntimeUnavailable("pass --onnx-dir or install huggingface_hub") from exc
        patterns = ["*.json", "*.model", "*.txt", ONNX_FILES[quant]]
        try:
            d = Path(snapshot_download(ONNX_HF_ID, allow_patterns=patterns, local_files_only=True))
        except Exception:  # noqa: BLE001
            if not downloads_allowed():
                raise RuntimeUnavailable(
                    f"{ONNX_HF_ID} is not cached; set EDSHIELD_ALLOW_DOWNLOAD=1 or pass --onnx-dir"
                )
            d = Path(snapshot_download(ONNX_HF_ID, allow_patterns=patterns))
        return d / ONNX_FILES[quant], d

    @property
    def model_ref(self) -> str:
        return str(self.onnx_path)

    def _load(self):
        if self._session is not None:
            return
        try:
            import json

            import numpy as np  # noqa: F401
            import onnxruntime as ort
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise RuntimeUnavailable("the onnx runtime needs onnxruntime, transformers and sentencepiece") from exc
        if not self.onnx_path.exists():
            raise RuntimeUnavailable(f"{self.onnx_path} does not exist")
        self._tok = AutoTokenizer.from_pretrained(str(self.model_dir), local_files_only=True)
        config = json.loads((self.model_dir / "config.json").read_text(encoding="utf-8"))
        self._id2label = {int(i): l for i, l in config["id2label"].items()}
        opts = ort.SessionOptions()
        if self.threads:
            opts.intra_op_num_threads = self.threads
        self._session = ort.InferenceSession(str(self.onnx_path), opts, providers=["CPUExecutionProvider"])

    def _predict(self, chunk: str, model_id: str, device: str, allow_download: bool):
        import numpy as np

        enc = self._tok(chunk, return_offsets_mapping=True, return_tensors="np")
        if enc["input_ids"].shape[1] > ner.MAX_TOKENS and len(chunk) > 200:
            cut = ner._cut(chunk, len(chunk) // 4, len(chunk) // 2)
            o1, p1, _ = self._predict(chunk[:cut], model_id, device, allow_download)
            o2, p2, _ = self._predict(chunk[cut:], model_id, device, allow_download)
            return o1 + [(s + cut, e + cut) for s, e in o2], p1 + p2, self._id2label
        offsets = [tuple(o) for o in enc["offset_mapping"][0].tolist()]
        feed = {
            "input_ids": enc["input_ids"].astype(np.int64),
            "attention_mask": enc["attention_mask"].astype(np.int64),
        }
        logits = self._session.run(["logits"], feed)[0][0].astype(np.float64)
        logits -= logits.max(axis=-1, keepdims=True)
        probs = np.exp(logits)
        probs /= probs.sum(axis=-1, keepdims=True)
        return offsets, probs.tolist(), self._id2label

    def __enter__(self):
        if ner._predict is not _ORIGINAL_PREDICT:
            raise RuntimeUnavailable("edshield.ner._predict is already patched")
        self._load()
        ner._predict = self._predict
        return self

    def __exit__(self, *exc):
        ner._predict = _ORIGINAL_PREDICT
        return False

    def deidentify(self, text: str, policy: str, seed: Optional[int] = None, o_threshold: Optional[float] = None):
        if ner._predict is not self._predict:
            raise RuntimeUnavailable("use the onnx runtime inside a `with` block")
        r = edshield.deidentify(
            text, policy=policy, model_name=str(self.model_dir), seed=seed, verify=False, o_threshold=o_threshold,
        )
        if r.audit.get("detector") in (None, "rules"):
            raise RuntimeUnavailable("the onnx model did not run")
        return r

    def _compute_model_sha256(self) -> str:
        return hashes.sha256_file(self.onnx_path)


def make_runtime(name: str, detector: str, model: str = DEFAULT_MODEL, model_dir: Optional[str] = None,
                 onnx_dir: Optional[str] = None, onnx_file: Optional[str] = None, quant: str = "int8",
                 threads: int = 0, device: str = "cpu") -> BaseRuntime:
    if name == "python":
        return PythonRuntime(detector, model=model, model_dir=model_dir, device=device)
    if name == "onnx":
        return OnnxRuntime(detector, onnx_dir=onnx_dir, onnx_file=onnx_file, quant=quant, threads=threads)
    raise ValueError(f"runtime must be one of {RUNTIMES}")
