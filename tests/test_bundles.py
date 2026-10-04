import hashlib
import json

from edshield_evidence import bundles


def test_split_and_join_round_trip(tmp_path):
    b = tmp_path / "x.bundle.json"
    payload = json.dumps({"views": {"identifier": {"runs": [{"id": "seed-0", "rows": [{"sample_id": str(i), "y_true": 1, "y_pred": 1} for i in range(5000)]}]}}})
    b.write_text(payload, encoding="utf-8")
    original_sha = hashlib.sha256(b.read_bytes()).hexdigest()
    assert bundles.split(b, over=10 ** 9) == []           # under the limit: left whole
    parts = bundles.split(b, over=1000, part_size=40000)
    assert len(parts) >= 2 and not b.exists()
    assert (tmp_path / "x.bundle.json.sha256").read_text().split()[0] == original_sha
    assert bundles.load_bundle(b)["views"]["identifier"]["runs"][0]["id"] == "seed-0"   # reads the parts
    joined = bundles.join(b)
    assert hashlib.sha256(joined.read_bytes()).hexdigest() == original_sha
    assert bundles.split_directory(tmp_path, over=10 ** 9) == []


def test_join_refuses_tampered_parts(tmp_path):
    import pytest

    b = tmp_path / "y.bundle.json"
    b.write_bytes(b"0" * 5000)
    bundles.split(b, over=10, part_size=2000)
    p = sorted(tmp_path.glob("y.bundle.json.part*"))[1]
    p.write_bytes(b"1" + p.read_bytes()[1:])
    with pytest.raises(ValueError):
        bundles.join(b)
