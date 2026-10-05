import json
import os

import pytest

from edshield_evidence import seal

KEY = bytes(range(32))


def _draft(tmp_path, name="T1"):
    sets = tmp_path / "sets"
    sets.mkdir()
    draft = sets / f"{name}.draft.jsonl"
    draft.write_text(json.dumps({"doc_id": "a", "text": "hi Bo", "gold_spans": [[3, 5, "NAME_STUDENT"]]}) + "\n")
    (sets / f"{name}.draft.review.md").write_text("review\n")
    return sets, draft


def test_seal_unseal_round_trip_and_manifest(tmp_path):
    sets, draft = _draft(tmp_path)
    plaintext = draft.read_bytes()
    man = seal.seal("T1", draft, key=KEY, generator_version="g1", review_date="2026-10-04", sets_dir=sets)
    assert not draft.exists() and not (sets / "T1.draft.review.md").exists()
    assert man["n_documents"] == 1 and man["label_counts"] == {"NAME_STUDENT": 1} and man["used_for_decision"] is None
    assert (sets / "T1.sha256").read_text().split()[0] == man["sha256"]
    assert (sets / "T1.jsonl.enc").read_bytes() != plaintext
    text, man2 = seal.unseal_text("T1", key=KEY, sets_dir=sets)
    assert text.encode() == plaintext and man2 == json.loads((sets / "T1.manifest.json").read_text())
    out = seal.unseal_to("T1", tmp_path / "tmpdir", key=KEY, sets_dir=sets)
    assert out.read_bytes() == plaintext
    with pytest.raises(seal.SealError):
        seal.seal("T1", out, key=KEY, sets_dir=sets)  # never re-sealed under the same name


def test_tampered_enc_fails(tmp_path):
    sets, draft = _draft(tmp_path)
    seal.seal("T1", draft, key=KEY, sets_dir=sets)
    enc = sets / "T1.jsonl.enc"
    blob = bytearray(enc.read_bytes())
    blob[-1] ^= 0x01
    enc.write_bytes(bytes(blob))
    with pytest.raises(seal.SealError):
        seal.unseal_text("T1", key=KEY, sets_dir=sets)


def test_wrong_key_and_sha_mismatch_fail(tmp_path):
    sets, draft = _draft(tmp_path)
    seal.seal("T1", draft, key=KEY, sets_dir=sets)
    with pytest.raises(seal.SealError):
        seal.unseal_text("T1", key=bytes(32), sets_dir=sets)
    (sets / "T1.sha256").write_text("0" * 64 + "  T1.jsonl\n")
    with pytest.raises(seal.SealError):
        seal.unseal_text("T1", key=KEY, sets_dir=sets)


def test_key_from_environment_and_mark_used(tmp_path, monkeypatch):
    sets, draft = _draft(tmp_path)
    monkeypatch.setenv(seal.KEY_ENV, KEY.hex())
    assert seal.load_key() == KEY
    seal.seal("T1", draft, sets_dir=sets)
    man = seal.mark_used("T1", "2026-10-04-abc1234", sets_dir=sets)
    assert man["used_for_decision"] == "2026-10-04-abc1234" and man["role"] == "regression"
    with pytest.raises(seal.SealError):
        seal.mark_used("T1", "again", sets_dir=sets)
    monkeypatch.setenv(seal.KEY_ENV, "nothex")
    with pytest.raises(seal.SealError):
        seal.load_key()


def test_load_sealed_uses_positional_ids(tmp_path):
    from edshield_evidence.datasets import load_sealed

    sets = tmp_path / "sets"
    sets.mkdir()
    draft = sets / "S1.draft.jsonl"
    draft.write_text(json.dumps({"doc_id": "a-123456789-0", "text": "hi Bo", "gold_spans": [[3, 5, "NAME_STUDENT"]]}) + "\n"
                     + json.dumps({"doc_id": "a-123456789-1", "text": "bye", "gold_spans": []}) + "\n")
    seal.seal("S1", draft, key=KEY, sets_dir=sets)
    ds = load_sealed("S1", key=KEY, sets_dir=sets)
    assert [d.doc_id for d in ds.docs] == ["S1-0000", "S1-0001"]
    assert ds.sealed and ds.split == "test" and ds.docs[0].gold_spans == [(3, 5, "NAME_STUDENT")]
    assert "123456789" not in json.dumps([d.to_record() for d in ds.docs])
