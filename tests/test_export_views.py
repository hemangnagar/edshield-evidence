"""Five-document synthetic fixture with known gold -> expected rows per view;
the bundle must be accepted by the judge CLI (exit 0/1/2, never 3)."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from edshield_evidence import JUDGE_CLI, export_views, report
from edshield_evidence.datasets import Dataset, Document

ROOT = Path(__file__).resolve().parent.parent

FIXTURE = [
    # doc_id, text, gold spans, replacements the stub applies (original -> rendered)
    ("f1", "hi im maya chen call 415-555-0199", [(6, 15, "NAME_STUDENT"), (21, 33, "PHONE_NUM")],
     {"maya chen": "[CHILD]", "415-555-0199": "[PHONE_NUM]"}),                       # both handled
    ("f2", "maya chen goes to lincoln middle school", [(0, 9, "NAME_STUDENT"), (18, 39, "SCHOOL")],
     {"maya": "[CHILD]"}),                                                           # surname survives: partial
    ("f3", "email ann at gmail dot com please", [(6, 26, "EMAIL")], {}),              # untouched: full residual
    ("f4", "nothing personal here at all", [], {"personal": "[X]"}),                  # over-redaction, no gold
    ("f5", "see Ann at the annual fair", [(4, 7, "NAME_RELATED")], {"Ann": "[PERSON]"}),  # Ann vs annual
]


class Ent:
    def __init__(self, label, text, start, end):
        self.label, self.text, self.start, self.end = label, text, start, end


class Res:
    def __init__(self, out, ents, rep):
        self.deidentified_text, self.entities, self.replacements, self.leaks, self.audit = out, ents, rep, [], {"detector": "stub"}


class StubRuntime:
    """Replaces fixed strings; the label of a replacement is the gold label it overlaps, else X."""
    name = "stub"
    detector = "rules"
    model_ref = "stub"
    model_sha256 = "ab" * 32

    def __init__(self, dataset):
        self.by_doc = {d.doc_id: d for d in dataset.docs}
        self.rep = {doc_id: rep for doc_id, _, _, rep in FIXTURE}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def deidentify(self, text, policy, seed=None, o_threshold=None):
        doc = next(d for d in self.by_doc.values() if d.text == text)
        ents, out, replacements = [], text, {}
        for original, rendered in self.rep[doc.doc_id].items():
            s = text.index(original)
            label = next((l for gs, ge, l in doc.gold_spans if gs < s + len(original) and s < ge), "X")
            ents.append(Ent(label, original, s, s + len(original)))
            replacements[original] = rendered
        for e in sorted(ents, key=lambda e: -e.start):
            out = out[: e.start] + replacements[e.text] + out[e.end:]
        return Res(out, sorted(ents, key=lambda e: e.start), replacements)


@pytest.fixture
def dataset(tmp_path):
    docs = [Document(doc_id, text, spans) for doc_id, text, spans, _ in FIXTURE]
    return Dataset("file:fixture", docs, None, "11" * 32, split="validation", role="regression")


def _results(dataset, seeds=(0, 1, 2), repeat=0):
    specs = [export_views.RunSpec(f"seed-{s}", s, StubRuntime(dataset)) for s in seeds]
    if repeat is not None:
        specs.append(export_views.RunSpec(f"seed-{repeat}-repeat", repeat, StubRuntime(dataset)))
    return [export_views.run_one(spec, dataset, "coppa") for spec in specs]


def test_rows_per_view(dataset):
    results = _results(dataset)
    bundle, diag = export_views.build_bundle(dataset, results, policy="coppa", detector="rules", runtime_names=["python"],
                                             o_threshold=None, model_ref="stub", include_text=True)
    views = bundle["views"]
    assert set(views) == {"identifier", "document", "word", "type:NAME_STUDENT", "type:PHONE_NUM", "type:SCHOOL",
                          "type:EMAIL", "type:NAME_RELATED"}
    ident = {r["sample_id"]: r["y_pred"] for r in views["identifier"]["runs"][0]["rows"]}
    assert ident == {"f1:0": 1, "f1:1": 1, "f2:0": 1, "f2:1": 0, "f3:0": 0, "f5:0": 1}
    assert all(r["y_true"] == 1 and r["cluster_id"] == r["sample_id"].split(":")[0] for r in views["identifier"]["runs"][0]["rows"])
    docv = {r["sample_id"]: r["y_pred"] for r in views["document"]["runs"][0]["rows"]}
    assert docv == {"f1": 1, "f2": 0, "f3": 0, "f5": 1}  # f4 has no gold span, so no row
    assert {r["sample_id"] for r in views["type:SCHOOL"]["runs"][0]["rows"]} == {"f2:1"}
    words = {r["sample_id"]: (r["y_true"], r["y_pred"]) for r in views["word"]["runs"][0]["rows"]}
    assert words["f4:w1"] == (0, 1)      # "personal" removed without gold: over-redaction
    assert words["f1:w2"] == (1, 1)      # "maya" replaced
    assert words["f2:w1"] == (1, 0)      # "chen" survives
    assert words["f5:w4"] == (0, 0)      # "annual" untouched
    assert len(views["word"]["runs"][0]["rows"]) == sum(len(t.split()) for _, t, _, _ in FIXTURE)
    # four runs, identical ids/y_true across runs, seed on each, repeat shares seed 0
    assert [r["id"] for r in views["identifier"]["runs"]] == ["seed-0", "seed-1", "seed-2", "seed-0-repeat"]
    assert views["identifier"]["runs"][3]["seed"] == 0
    assert all(r["metadata"]["model_sha256"] == "ab" * 32 for r in views["identifier"]["runs"])
    md = bundle["metadata"]
    assert md["data_sha256"] == "11" * 32 and len(md["recipe_sha256"]) == 64 and len(md["environment_sha256"]) == 64
    assert bundle["contract"] == "2.0" and bundle["split"] == "validation"
    run = diag["runs"][0]
    assert run["full_residuals"] == 2 and run["partial_residuals"] == 1 and run["n_gold"] == 6
    assert run["by_label"]["NAME_STUDENT"] == {"n": 2, "full_residual": 0, "partial_residual": 1, "recall": 1.0}
    assert run["label_confusion"]["EMAIL"] == {"none": 1}
    assert run["over_redaction_sample"][0]["token"] == "personal"
    assert run["partial_examples"][0]["surviving_token"] == "chen"


def test_sealed_diagnostics_hold_no_text(dataset):
    dataset.sealed = True
    results = _results(dataset, seeds=(0,), repeat=None)
    _, diag = export_views.build_bundle(dataset, results, policy="coppa", detector="rules", runtime_names=["python"],
                                        o_threshold=None, model_ref="stub", include_text=False)
    run = diag["runs"][0]
    assert "over_redaction_sample" not in run and "partial_examples" not in run and "residual_examples" not in run
    assert run["full_residuals"] == 2
    assert "maya" not in json.dumps(diag)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is needed for the judge CLI")
def test_bundle_is_accepted_by_judge_and_summarized(dataset, tmp_path):
    assert JUDGE_CLI.exists(), "judge submodule missing: git submodule update --init"
    results = _results(dataset)
    bundle, diag = export_views.build_bundle(dataset, results, policy="coppa", detector="rules", runtime_names=["python"],
                                             o_threshold=None, model_ref="stub", include_text=True)
    key = "00_fixture_rules_python"
    (tmp_path / f"{key}.bundle.json").write_text(json.dumps(bundle))
    (tmp_path / f"{key}.diagnostics.json").write_text(json.dumps(diag))
    policy = {"contract": "2.0", "confidence": False, "minRuns": 3, "_ratified": False, "views": {
        "identifier": {"recall": 0.5, "stabilityMetric": "recall", "maxSpread": 0.01, "selectedRun": "seed-0"},
        "document": {"recall": 0.5, "stabilityMetric": "recall", "maxSpread": 0.01, "selectedRun": "seed-0"},
        "word": {"fpr": 0.1, "stabilityMetric": "fpr", "maxSpread": 0.01, "selectedRun": "seed-0"},
        "type:EMAIL": {"recall": 0.9, "stabilityMetric": "recall", "maxSpread": 0.01, "selectedRun": "seed-0", "required": False},
    }}
    for name in bundle["views"]:  # a view without a policy entry is insufficient evidence, so cover them all
        policy["views"].setdefault(name, {"recall": 0.0, "stabilityMetric": "recall", "maxSpread": 0.01, "selectedRun": "seed-0"})
    (tmp_path / f"{key}.policy.json").write_text(json.dumps(policy))
    proc = subprocess.run(["node", str(JUDGE_CLI), str(tmp_path / f"{key}.bundle.json"), str(tmp_path / f"{key}.policy.json"),
                           "--out", str(tmp_path / f"{key}.verdict.json"), "--quiet"], capture_output=True, text=True)
    assert proc.returncode in (0, 1, 2), proc.stderr
    verdict = json.loads((tmp_path / f"{key}.verdict.json").read_text())
    assert verdict["contract"] == "2.0" and set(verdict["views"]) == set(bundle["views"])
    ident = verdict["views"]["identifier"]
    assert ident["confusion"]["recall"]["value"] == pytest.approx(4 / 6)
    assert ident["confusion"]["recall"]["interval_method"] == "cluster_bootstrap"
    assert ident["reproducibility"] == "pass"       # seed-0 and seed-0-repeat share every hash
    assert ident["stability"] == "pass"             # three distinct seeds, zero spread
    assert verdict["views"]["type:EMAIL"]["overall"] == "fail"  # 0 of 1, not required
    assert verdict["overall"] == "pass"
    # summary.md: PROVISIONAL first line, wording rule, no forbidden words
    out = report.summarize(tmp_path)
    text = out.read_text()
    assert text.splitlines()[0] == report.PROVISIONAL_LINE
    assert "meets** defined redaction criteria on evidence set file:fixture (sha256 " + "11" * 32 in text
    assert "compliant" not in text.lower()


def test_cli_runs_rules_only_on_a_jsonl_file(tmp_path):
    """Real edshield, rules only, on five tiny documents: the exporter CLI end to end."""
    import warnings

    f = tmp_path / "tiny.jsonl"
    docs = [Document(d, t, s) for d, t, s, _ in FIXTURE]
    from edshield_evidence.datasets import write_jsonl

    write_jsonl(docs, f)
    out = tmp_path / "tiny.bundle.json"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rc = export_views.main(["--dataset", f"file:{f}", "--policy", "coppa", "--detector", "rules", "--runtime", "python",
                                "--seeds", "0", "--out", str(out), "--quiet"])
    assert rc == 0
    bundle = json.loads(out.read_text())
    assert (tmp_path / "tiny.diagnostics.json").exists()
    assert bundle["metadata"]["detector"] == "rules" and bundle["metadata"]["policy_fingerprint"]
    rows = {r["sample_id"]: r["y_pred"] for r in bundle["views"]["identifier"]["runs"][0]["rows"]}
    assert rows["f1:1"] == 1  # the phone number is a rule hit under coppa
