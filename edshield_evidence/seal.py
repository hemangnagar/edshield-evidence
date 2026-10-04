"""Seal and unseal acceptance sets.

    python -m edshield_evidence.seal keygen
    python -m edshield_evidence.seal seal A1 --from evidence/sets/A1.draft.jsonl --review-date 2026-10-04
    python -m edshield_evidence.seal unseal A1 --out /tmp/somewhere     # acceptance workflow only
    python -m edshield_evidence.seal mark-used A1 <report id>

Sealing writes, under evidence/sets/:
  A1.sha256          sha256 of the reviewed plaintext file
  A1.jsonl.enc       AES-256-GCM: magic, 12-byte nonce, ciphertext+tag; AAD is the set name
  A1.manifest.json   size, document count, label counts, generator version,
                     review date, role, used_for_decision (null until a verdict is opened)
and deletes the draft and its review file (both hold the set's text).

The key comes from EDSHIELD_EVIDENCE_SEAL_KEY: 64 hex characters or 44
base64 characters for 32 bytes. Unsealed data is never committed.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Optional, Tuple

from . import SETS_DIR
from .hashes import sha256_bytes

MAGIC = b"EDSEAL1\n"
NONCE_LEN = 12
KEY_ENV = "EDSHIELD_EVIDENCE_SEAL_KEY"


class SealError(RuntimeError):
    pass


def load_key(key: Optional[bytes] = None) -> bytes:
    if key is not None:
        if len(key) != 32:
            raise SealError("seal key must be 32 bytes")
        return key
    raw = os.environ.get(KEY_ENV, "").strip()
    if not raw:
        raise SealError(f"{KEY_ENV} is not set")
    try:
        if len(raw) == 64:
            k = bytes.fromhex(raw)
        else:
            k = base64.b64decode(raw, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SealError(f"{KEY_ENV} must be 64 hex or 44 base64 characters") from exc
    if len(k) != 32:
        raise SealError(f"{KEY_ENV} decodes to {len(k)} bytes, need 32")
    return k


def encrypt(data: bytes, key: bytes, aad: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(NONCE_LEN)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, data, aad)


def decrypt(blob: bytes, key: bytes, aad: bytes) -> bytes:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not blob.startswith(MAGIC) or len(blob) < len(MAGIC) + NONCE_LEN + 16:
        raise SealError("not a sealed file")
    nonce = blob[len(MAGIC):len(MAGIC) + NONCE_LEN]
    try:
        return AESGCM(key).decrypt(nonce, blob[len(MAGIC) + NONCE_LEN:], aad)
    except InvalidTag as exc:
        raise SealError("sealed file failed authentication: wrong key or tampered content") from exc


def paths(name: str, sets_dir: Path = SETS_DIR) -> dict:
    return {
        "enc": sets_dir / f"{name}.jsonl.enc",
        "sha": sets_dir / f"{name}.sha256",
        "manifest": sets_dir / f"{name}.manifest.json",
        "draft": sets_dir / f"{name}.draft.jsonl",
        "review": sets_dir / f"{name}.draft.review.md",
    }


def seal(name: str, from_path: Path, key: Optional[bytes] = None, generator_version: Optional[str] = None,
         review_date: Optional[str] = None, delete_draft: bool = True, sets_dir: Path = SETS_DIR) -> dict:
    k = load_key(key)
    p = paths(name, sets_dir)
    if p["enc"].exists():
        raise SealError(f"{p['enc']} exists; a sealed set is never re-sealed under the same name")
    data = Path(from_path).read_bytes()
    docs = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    labels = Counter(l for d in docs for _, _, l in d["gold_spans"])
    digest = sha256_bytes(data)
    sets_dir.mkdir(parents=True, exist_ok=True)
    p["enc"].write_bytes(encrypt(data, k, name.encode("utf-8")))
    p["sha"].write_text(f"{digest}  {name}.jsonl\n", encoding="utf-8")
    manifest = {
        "set": name,
        "sha256": digest,
        "size_bytes": len(data),
        "n_documents": len(docs),
        "label_counts": dict(sorted(labels.items())),
        "generator_version": generator_version,
        "review_date": review_date,
        "sealed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "cipher": "AES-256-GCM",
        "role": "acceptance",
        "used_for_decision": None,
    }
    p["manifest"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if delete_draft:
        for f in (Path(from_path), p["draft"], p["review"]):
            if f.exists():
                f.unlink()
    return manifest


def unseal_bytes(name: str, key: Optional[bytes] = None, sets_dir: Path = SETS_DIR) -> Tuple[bytes, dict]:
    k = load_key(key)
    p = paths(name, sets_dir)
    if not p["enc"].exists():
        raise SealError(f"{p['enc']} does not exist")
    data = decrypt(p["enc"].read_bytes(), k, name.encode("utf-8"))
    manifest = json.loads(p["manifest"].read_text(encoding="utf-8"))
    expected = p["sha"].read_text(encoding="utf-8").split()[0]
    digest = sha256_bytes(data)
    if digest != expected or digest != manifest["sha256"]:
        raise SealError(f"unsealed {name} has sha256 {digest}, expected {expected}")
    return data, manifest


def unseal_text(name: str, key: Optional[bytes] = None, sets_dir: Path = SETS_DIR) -> Tuple[str, dict]:
    data, manifest = unseal_bytes(name, key, sets_dir)
    return data.decode("utf-8"), manifest


def unseal_to(name: str, out_dir: Path, key: Optional[bytes] = None, sets_dir: Path = SETS_DIR) -> Path:
    data, _ = unseal_bytes(name, key, sets_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{name}.jsonl"
    target.write_bytes(data)
    return target


def mark_used(name: str, report_id: str, sets_dir: Path = SETS_DIR) -> dict:
    p = paths(name, sets_dir)
    manifest = json.loads(p["manifest"].read_text(encoding="utf-8"))
    if manifest.get("used_for_decision"):
        raise SealError(f"{name} was already used for decision {manifest['used_for_decision']}")
    manifest["used_for_decision"] = report_id
    manifest["role"] = "regression"
    manifest["decision_opened_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    p["manifest"].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m edshield_evidence.seal", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("keygen", help="print a fresh 32-byte key as hex")
    s = sub.add_parser("seal")
    s.add_argument("name")
    s.add_argument("--from", dest="from_path", required=True)
    s.add_argument("--generator-version", default=None)
    s.add_argument("--review-date", default=None, help="YYYY-MM-DD of the human review")
    s.add_argument("--keep-draft", action="store_true")
    s.add_argument("--sets-dir", default=str(SETS_DIR))
    u = sub.add_parser("unseal")
    u.add_argument("name")
    u.add_argument("--out", required=True, help="temp directory; never inside the repo")
    u.add_argument("--sets-dir", default=str(SETS_DIR))
    m = sub.add_parser("mark-used")
    m.add_argument("name")
    m.add_argument("report_id")
    m.add_argument("--sets-dir", default=str(SETS_DIR))
    a = ap.parse_args(argv)
    try:
        if a.cmd == "keygen":
            print(os.urandom(32).hex())
        elif a.cmd == "seal":
            man = seal(a.name, Path(a.from_path), generator_version=a.generator_version, review_date=a.review_date,
                       delete_draft=not a.keep_draft, sets_dir=Path(a.sets_dir))
            print(json.dumps(man, indent=2))
        elif a.cmd == "unseal":
            print(unseal_to(a.name, Path(a.out), sets_dir=Path(a.sets_dir)))
        elif a.cmd == "mark-used":
            print(json.dumps(mark_used(a.name, a.report_id, sets_dir=Path(a.sets_dir)), indent=2))
    except SealError as exc:
        print(f"seal: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
