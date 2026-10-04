from types import SimpleNamespace

import pytest

from edshield_evidence import runtimes
from edshield_evidence.runtimes import OnnxRuntime, RuntimeUnavailable


def test_onnx_runtime_runs_inside_with_and_refuses_outside(tmp_path, monkeypatch):
    # No model here: the session load and edshield.deidentify are stubbed, the patching is real.
    rt = OnnxRuntime(onnx_dir=str(tmp_path))
    monkeypatch.setattr(rt, "_load", lambda: None)
    seen = {}

    def fake_deidentify(text, **kw):
        seen["patched"] = runtimes.ner._predict == rt._predict
        return SimpleNamespace(audit={"detector": "rules+model"})

    monkeypatch.setattr(runtimes.edshield, "deidentify", fake_deidentify)

    with pytest.raises(RuntimeUnavailable):
        rt.deidentify("x", policy="coppa")
    with rt as entered:
        assert entered.deidentify("x", policy="coppa").audit["detector"] == "rules+model"
    assert seen == {"patched": True}
    assert runtimes.ner._predict is runtimes._ORIGINAL_PREDICT
    with pytest.raises(RuntimeUnavailable):
        rt.deidentify("x", policy="coppa")
