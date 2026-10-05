import json

from edshield_evidence import ledger, policy
from edshield_evidence.policy import ACCEPTANCE, REGRESSION

REQUIRED_VIEWS = {"identifier", "document", "word"}


def test_policy_files_are_well_formed():
    for path in (REGRESSION, ACCEPTANCE):
        keyed = policy.load_keyed(path)
        assert keyed["policies"], path
        for key, pol in keyed["policies"].items():
            assert pol["contract"] == "2.0" and 2 <= pol["minRuns"] <= 50, key
            assert REQUIRED_VIEWS <= set(pol["views"]) or key.endswith("parity"), key
            for name, v in pol["views"].items():
                assert "stabilityMetric" in v and "maxSpread" in v, (key, name)
                assert any(v.get(g) is not None for g in ("accuracy", "precision", "recall", "fpr")), (key, name)
                if v["stabilityMetric"] in v:
                    assert v[v["stabilityMetric"]] is not None, (key, name)


def test_select_drops_only_absent_type_views(tmp_path):
    bundle = {"views": {"identifier": {}, "document": {}, "word": {}, "type:EMAIL": {}}}
    bp = tmp_path / "b.json"
    bp.write_text(json.dumps(bundle))
    pol, dropped = policy.select(REGRESSION, "k12_hard/rules", bp)
    assert set(pol["views"]) == {"identifier", "document", "word", "type:EMAIL"}
    assert "type:NAME_STUDENT" in dropped and "identifier" not in dropped
    assert pol["_ratified"] is False
    assert pol["views"]["type:EMAIL"] == policy.load_keyed(REGRESSION)["policies"]["k12_hard/rules"]["views"]["type:EMAIL"]


def test_ledger_append_and_parse(tmp_path):
    path = tmp_path / "ledger.md"
    entry = {c: f"v{i}" for i, c in enumerate(ledger.COLUMNS)}
    ledger.append(entry, path)
    ledger.append(dict(entry, note="second | with pipe".replace("|", "/")), path)
    rows = ledger.parse(path)
    assert len(rows) == 2 and rows[0]["dataset"] == "v2" and rows[1]["note"] == "second / with pipe"
    assert path.read_text().startswith("# Experiment ledger")


def test_pin_respects_fixed_policies_and_drops_placeholders(tmp_path):
    import json
    from pathlib import Path

    from edshield_evidence import REPORTS_DIR

    rows = ledger.parse()
    report_dirs = {r["report id"] for r in rows}
    assert report_dirs, "the committed ledger should have rows"
    policy = tmp_path / "regression.json"
    keyed = {"policies": {
        "k12_hard/rules": {"contract": "2.0", "confidence": False, "minRuns": 3, "_placeholder": "x",
                           "views": {"identifier": {"recall": 0.0, "stabilityMetric": "recall", "maxSpread": 0.01, "_placeholder": "y"}}},
        "piilo_holdout/parity": {"contract": "2.0", "confidence": False, "minRuns": 2, "_pin": False,
                                 "views": {"identifier": {"recall": 0.99, "stabilityMetric": "recall", "maxSpread": 0.01}}},
    }}
    policy.write_text(json.dumps(keyed))
    changes = ledger.pin(policy, ledger.LEDGER, REPORTS_DIR)
    out = json.loads(policy.read_text())
    assert out["policies"]["k12_hard/rules"]["views"]["identifier"]["recall"] == 0.221
    assert "_placeholder" not in out["policies"]["k12_hard/rules"]
    assert "_placeholder" not in out["policies"]["k12_hard/rules"]["views"]["identifier"]
    assert out["policies"]["piilo_holdout/parity"]["views"]["identifier"]["recall"] == 0.99
    assert any("skipped" in c and "parity" in c for c in changes)
