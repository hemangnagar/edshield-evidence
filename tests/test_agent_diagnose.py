"""Offline checks of the agent-diagnose pipeline pieces that need no API key."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import genre_shift_data as gs  # noqa: E402
import platform_api as api  # noqa: E402

RAW_PRESENT = all((gs.GS_DATA / "raw" / d).is_dir() for d in gs.DATASETS)
needs_raw = pytest.mark.skipif(not RAW_PRESENT, reason="raw dialogue files not downloaded (make raw)")


@needs_raw
def test_failure_table_matches_every_sealed_miss(tmp_path):
    import build_failure_table as bft
    rows = bft.build("deterministic")
    import csv
    with (gs.GS_RESULTS / "misses.csv").open(encoding="utf-8", newline="") as f:
        misses = list(csv.DictReader(f))
    assert len(rows) == len(misses)
    for r in rows:
        assert "[[" + r["gold_text"] + "]]" in r["window"]
        assert r["label"] in gs.LABELS.values()
    assert {r["sealed_reason"] for r in rows} == {m["reason"] for m in misses}


@needs_raw
def test_diagnosis_requests_are_well_formed():
    import diagnose
    main, agree = diagnose.build_requests(["deterministic"])
    assert len(main) == 275 and len(agree) == 50
    ids = [r["custom_id"] for r in main]
    assert len(set(ids)) == len(ids)
    r = main[0]["params"]
    assert r["model"] == api.MODELS["diagnose"]
    assert r["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert r["output_config"]["format"]["type"] == "json_schema"
    user = json.loads(r["messages"][0]["content"])
    assert "sealed_reason" not in user and "reason" not in user, "the sealed heuristic tag must not bias the diagnoser"
    assert diagnose.reordered_rubric() != diagnose.RUBRIC
    assert diagnose.validate({"primary": "REGISTER", "secondary": None, "confidence": 0.8, "fix_class": "RULE",
                              "evidence": "hi im summer", "note": None}) == []
    assert diagnose.validate({"primary": "OTHER", "secondary": None, "confidence": 0.8, "fix_class": "RULE",
                              "evidence": "x", "note": None})


def test_cost_accounting_uses_batch_discount():
    u = {"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 2_000_000}
    std = api.usage_cost_usd("claude-sonnet-5-5", u, batch=False)
    bat = api.usage_cost_usd("claude-sonnet-5-5", u, batch=True)
    assert abs(std - (2.0 + 1.0 + 0.4)) < 1e-9 and abs(bat - std / 2) < 1e-9


def test_extract_json_tolerates_fences():
    assert api.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert api.extract_json('text {"a": [1,2]} more') == {"a": [1, 2]}


def test_agent_definition_mirrors_prompt():
    import run_agent_loop as ral
    spec = ral.agent_spec()
    assert spec["model"] == api.MODELS["agent"]
    assert spec["tools"][0]["type"] == "agent_toolset_20260401"
    assert all(c["enabled"] is False for c in spec["tools"][0]["configs"] if c["name"] in ("web_fetch", "web_search"))
    env = ral.env_spec()
    assert env["config"]["networking"]["type"] == "limited" and "huggingface.co" in env["config"]["networking"]["allowed_hosts"]


def test_no_forbidden_words_in_new_prompts_and_docs():
    from edshield_evidence import FORBIDDEN_REPORT_WORDS
    for p in list((ROOT / "prompts").glob("*.md")) + list((ROOT / "agents").glob("*.md")):
        low = p.read_text(encoding="utf-8").lower()
        for w in FORBIDDEN_REPORT_WORDS:
            # the agent prompt names the word only to forbid it
            assert low.count(w) <= (1 if p.name in ("agent_system.md", "rule_proposer.md") else 0), (p, w)


def test_llm_view_store_round_trip(tmp_path, monkeypatch):
    import base64, os
    import llm_view_store as st
    monkeypatch.setattr(st, "STORE", tmp_path)
    monkeypatch.setattr(st, "MANIFEST", tmp_path / "sealed.json")
    monkeypatch.setenv(st.KEY_VAR, base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("="))
    (tmp_path / "comta.jsonl").write_text('{"doc_id": "x", "text": "licensed text"}\n', encoding="utf-8")
    assert st.cmd_seal() == 0
    (tmp_path / "comta.jsonl").unlink()
    assert st.cmd_unseal() == 0
    assert (tmp_path / "comta.jsonl").read_text(encoding="utf-8").startswith('{"doc_id": "x"')
    monkeypatch.setenv(st.KEY_VAR, base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("="))
    (tmp_path / "comta.jsonl").unlink()
    with pytest.raises(Exception):
        st.cmd_unseal()


def test_sealed_llm_view_is_committed_and_plaintext_is_not():
    import subprocess
    tracked = subprocess.run(["git", "ls-files", "data/planted_llm"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    assert "data/planted_llm/comta.jsonl.enc" in tracked and "data/planted_llm/sealed.json" in tracked
    assert "data/planted_llm/comta.jsonl" not in tracked


def test_pipeline_stage_order_and_workflow_reference():
    import pipeline
    assert pipeline.STAGES == ["data", "branch", "regress", "diagnose", "propose", "verify", "report"]
    wf = (ROOT / ".github" / "workflows" / "agent-diagnose.yml").read_text(encoding="utf-8")
    assert "scripts/pipeline.py" in wf and "EDSHIELD_PLATFORM_API_KEY" in wf and "EDSHIELD_LLMVIEW_KEY" in wf
