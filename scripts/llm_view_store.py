"""The LLM-planted view at rest: sealed into git, unsealed at run time.

The view carries the licensed dialogue text, so it is committed only
encrypted (AES-256-GCM, the repo's sealing primitive from
edshield_evidence.seal) with a key held outside git in EDSHIELD_LLMVIEW_KEY.
A scheduled run unseals it instead of re-planting, so every run scores the
same second view.

    python scripts/llm_view_store.py keygen            # prints a key once; store it as EDSHIELD_LLMVIEW_KEY
    python scripts/llm_view_store.py seal              # data/planted_llm/<ds>.jsonl -> <ds>.jsonl.enc (+ sha256 in the manifest)
    python scripts/llm_view_store.py unseal            # <ds>.jsonl.enc -> <ds>.jsonl, verifying the sha256
    python scripts/llm_view_store.py status
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from edshield_evidence import seal as sealmod  # noqa: E402

STORE = ROOT / "data" / "planted_llm"
MANIFEST = STORE / "sealed.json"
KEY_VAR = "EDSHIELD_LLMVIEW_KEY"
DATASETS = ("comta", "mathdial")


def key() -> bytes:
    v = os.environ.get(KEY_VAR, "")
    if not v:
        raise SystemExit(f"{KEY_VAR} is not set; see docs/AGENT-DIAGNOSE.md (scheduled runs)")
    raw = base64.urlsafe_b64decode(v + "=" * (-len(v) % 4))
    if len(raw) != 32:
        raise SystemExit(f"{KEY_VAR} must decode to 32 bytes")
    return raw


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def cmd_keygen() -> int:
    print(base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("="))
    return 0


def cmd_seal() -> int:
    k = key()
    man = {"datasets": {}, "note": "AES-256-GCM via edshield_evidence.seal; AAD = 'planted_llm/<dataset>'; key in " + KEY_VAR}
    for ds in DATASETS:
        src = STORE / f"{ds}.jsonl"
        if not src.exists():
            print(f"{ds}: no plaintext view to seal")
            continue
        data = src.read_bytes()
        (STORE / f"{ds}.jsonl.enc").write_bytes(sealmod.encrypt(data, k, f"planted_llm/{ds}".encode()))
        man["datasets"][ds] = {"sha256": sha256(data), "bytes": len(data), "docs": sum(1 for l in data.splitlines() if l.strip())}
        print(f"{ds}: sealed {len(data)} bytes, {man['datasets'][ds]['docs']} docs")
    MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8")
    return 0


def cmd_unseal(force: bool = False) -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    k = key()
    for ds, m in man["datasets"].items():
        dst = STORE / f"{ds}.jsonl"
        if dst.exists() and not force and sha256(dst.read_bytes()) == m["sha256"]:
            print(f"{ds}: plaintext already present and matches")
            continue
        data = sealmod.decrypt((STORE / f"{ds}.jsonl.enc").read_bytes(), k, f"planted_llm/{ds}".encode())
        if sha256(data) != m["sha256"]:
            raise SystemExit(f"{ds}: unsealed content does not match the manifest sha256")
        dst.write_bytes(data)
        print(f"{ds}: unsealed {m['docs']} docs")
    return 0


def cmd_status() -> int:
    if not MANIFEST.exists():
        print("no sealed view")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for ds, m in man["datasets"].items():
        have = (STORE / f"{ds}.jsonl").exists()
        print(f"{ds}: sealed sha256 {m['sha256'][:12]}… {m['docs']} docs; plaintext present: {have}")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    raise SystemExit({"keygen": cmd_keygen, "seal": cmd_seal, "status": cmd_status,
                      "unseal": lambda: cmd_unseal("--force" in sys.argv)}[mode]())
