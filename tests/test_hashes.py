import shutil

from edshield_evidence import hashes


def _policy_copy(tmp_path, name="coppa"):
    import edshield.deid

    src = edshield.deid.POLICY_DIR / f"{name}.yaml"
    dst = tmp_path / f"{name}.yaml"
    shutil.copy(src, dst)
    return dst


def test_recipe_hash_is_stable_and_tracks_policy_and_rules(tmp_path):
    pol = _policy_copy(tmp_path)
    rules = tmp_path / "rules.py"
    shutil.copy(hashes.installed_rules_path(), rules)
    base = hashes.recipe_sha256(str(pol), "rules", "python", None, rules_path=rules)
    assert base == hashes.recipe_sha256(str(pol), "rules", "python", None, rules_path=rules)
    assert len(base) == 64

    pol.write_text(pol.read_text() + "\n# changed\n")
    changed_policy = hashes.recipe_sha256(str(pol), "rules", "python", None, rules_path=rules)
    assert changed_policy != base

    rules.write_text(rules.read_text() + "\n# changed\n")
    changed_rules = hashes.recipe_sha256(str(pol), "rules", "python", None, rules_path=rules)
    assert changed_rules not in (base, changed_policy)

    assert hashes.recipe_sha256(str(pol), "rules+model", "python", None, rules_path=rules) != changed_rules
    assert hashes.recipe_sha256(str(pol), "rules", "onnx", None, rules_path=rules) != changed_rules
    assert hashes.recipe_sha256(str(pol), "rules", "python", 0.3, rules_path=rules) != changed_rules


def test_policy_fingerprint_matches_edshield():
    from edshield.deid import policy_fingerprint

    assert hashes.policy_fingerprint("coppa") == policy_fingerprint("coppa")


def test_environment_and_model_hashes(tmp_path):
    assert len(hashes.environment_sha256()) == 64
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"1")
    b.write_bytes(b"2")
    assert hashes.model_sha256([a]) == hashes.sha256_file(a)
    assert hashes.model_sha256([a, b]) == hashes.model_sha256([b, a])
    assert hashes.canonical_json({"b": 1, "a": [1, {"z": 0, "y": None}]}) == '{"a":[1,{"y":null,"z":0}],"b":1}'
