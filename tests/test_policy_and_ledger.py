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
