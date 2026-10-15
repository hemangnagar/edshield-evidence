"""Offline checks of the LLM-planting validator (no API).

Round trip: when the "model" answers with exactly the sealed run's phrasing,
validate() must rebuild the sealed document byte for byte, gold spans
included. Then a few deliberate corruptions must be rejected."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import genre_shift_data as gs  # noqa: E402
import plant_llm  # noqa: E402

RAW_PRESENT = all((gs.GS_DATA / "raw" / d).is_dir() for d in gs.DATASETS)
pytestmark = pytest.mark.skipif(not RAW_PRESENT, reason="raw dialogue files not downloaded (make raw)")


def sealed_answer(doc, manifest, dialogue):
    """The sealed doc, expressed as the response schema (persona names restored in the turn text)."""
    ranges = gs.turn_ranges(doc["text"], [str(t["speaker"]) for t in dialogue])
    lines = [doc["text"][a:b] for a, b in ranges]
    turns = {}
    by_turn = {}
    for s in doc["meta"]["spans"]:
        by_turn.setdefault(s["turn_idx"], []).append(s)
    slot_by_turn = {}
    for sl in manifest["slots"]:
        slot_by_turn.setdefault(sl["turn_idx"], []).append(sl)
    line_starts = [a for a, b in ranges]
    persona = (manifest.get("persona") or {}).get("name")
    for i, sls in slot_by_turn.items():
        line = lines[i]
        tag, body = line.split(": ", 1)
        head = line_starts[i] + len(tag) + 2
        spans = sorted(by_turn[i], key=lambda s: s["start"])
        name_spans = [s for s in spans if s["kind"] in plant_llm.NAME_KINDS]
        n_inserted = sum(1 for sl in sls if sl["kind"] == "name")
        persona_spans = name_spans[n_inserted:]
        # restore the persona name so the original turn text is a verbatim substring again
        body2, shift = body, 0
        edits = []
        for s in sorted(persona_spans, key=lambda s: s["start"]):
            ls, le = s["start"] - head, s["end"] - head
            edits.append((ls, le))
        for ls, le in reversed(edits):
            body2 = body2[:ls] + persona + body2[le:]
        inserted = [s for s in spans if id(s) not in {id(x) for x in persona_spans}]
        out_spans = []
        for sl, s in zip(sls, inserted):
            ls, le = s["start"] - head, s["end"] - head
            delta = sum(len(persona) - (b - a) for a, b in edits if a < ls)
            out_spans.append({"slot_id": sl["slot_id"], "text": s["text"], "start": ls + delta, "end": le + delta})
        turns[i] = {"turn_idx": i, "text": body2, "spans": out_spans}
    school = next((s["text"] for s in doc["meta"]["spans"] if s["kind"] == "school"), None)
    return {"student_name": doc["meta"]["name"], "related_name": doc["meta"]["related"], "school": school,
            "turns": [turns[i] for i in sorted(turns)]}


@pytest.mark.parametrize("dataset", list(gs.DATASETS))
def test_round_trip_reproduces_sealed_docs(dataset):
    log = gs.plant_log()
    plans = {p["dialogue_id"]: p for p in log["datasets"][dataset]["plans"]}
    dialogues = {str(d[0]["dialogue_id"]): d for d in gs.dialogues()[dataset]}
    n = 0
    for doc in gs.planted(dataset):
        m = plant_llm.manifest_for(doc, plans[doc["doc_id"]], dialogues[doc["doc_id"]])
        if not m["slots"] and not m["persona"]:
            continue
        resp = sealed_answer(doc, m, dialogues[doc["doc_id"]])
        rebuilt, errs = plant_llm.validate(resp, m, dialogues[doc["doc_id"]])
        assert not errs, (doc["doc_id"], errs)
        assert rebuilt["text"] == doc["text"], doc["doc_id"]
        assert rebuilt["gold_spans"] == doc["gold_spans"], doc["doc_id"]
        assert [s["kind"] for s in rebuilt["meta"]["spans"]] == [s["kind"] for s in doc["meta"]["spans"]], doc["doc_id"]
        n += 1
    assert n > 100


def test_corruptions_are_rejected():
    dataset = "comta"
    log = gs.plant_log()
    plans = {p["dialogue_id"]: p for p in log["datasets"][dataset]["plans"]}
    dialogues = {str(d[0]["dialogue_id"]): d for d in gs.dialogues()[dataset]}
    doc = next(d for d in gs.planted(dataset) if any(s["kind"] == "first" for s in d["meta"]["spans"]))
    m = plant_llm.manifest_for(doc, plans[doc["doc_id"]], dialogues[doc["doc_id"]])
    good = sealed_answer(doc, m, dialogues[doc["doc_id"]])
    assert plant_llm.validate(good, m, dialogues[doc["doc_id"]])[1] == []
    # a name outside the category list
    bad = json.loads(json.dumps(good)); bad["student_name"] = "Zorblax Quux"
    assert plant_llm.validate(bad, m, dialogues[doc["doc_id"]])[1]
    # an edited original turn (a character of the original replaced in place)
    bad = json.loads(json.dumps(good)); t = bad["turns"][0]["text"]
    orig0 = next(str(x["text"]) for x in dialogues[doc["doc_id"]] if x["turn_idx"] == bad["turns"][0]["turn_idx"])
    j = t.find(orig0) + 3
    bad["turns"][0]["text"] = t[:j] + ("X" if t[j] != "X" else "Y") + t[j + 1:]
    assert plant_llm.validate(bad, m, dialogues[doc["doc_id"]])[1]
    # offsets off by one are repaired by locating the surface form inside the inserted material
    bad = json.loads(json.dumps(good)); bad["turns"][0]["spans"][0]["start"] += 1
    rebuilt, errs = plant_llm.validate(bad, m, dialogues[doc["doc_id"]])
    assert not errs and rebuilt["text"] == doc["text"]
    # a surface form that is not in the inserted material (the name hidden inside the original text) is rejected
    bad = json.loads(json.dumps(good)); bad["turns"][0]["spans"][0]["text"] = "the"
    assert plant_llm.validate(bad, m, dialogues[doc["doc_id"]])[1]
    # a deleted character of the original is rejected even when the span is fine
    bad = json.loads(json.dumps(good)); t = bad["turns"][0]["text"]
    orig = next(str(x["text"]) for x in dialogues[doc["doc_id"]] if x["turn_idx"] == bad["turns"][0]["turn_idx"])
    i = t.find(orig) + len(orig) // 2
    bad["turns"][0]["text"] = t[:i] + t[i + 1:]
    assert plant_llm.validate(bad, m, dialogues[doc["doc_id"]])[1]
    # spans omitted but the names written: located in code, accepted
    bad = json.loads(json.dumps(good)); bad["turns"][0]["spans"] = []
    rebuilt, errs = plant_llm.validate(bad, m, dialogues[doc["doc_id"]])
    assert not errs and rebuilt["gold_spans"] == doc["gold_spans"]
    # a slot genuinely left unfilled (the turn returned unchanged) is rejected
    bad = json.loads(json.dumps(good)); bad["turns"][0]["spans"] = []; bad["turns"][0]["text"] = orig0
    assert plant_llm.validate(bad, m, dialogues[doc["doc_id"]])[1]


def test_build_requests_cover_every_slot():
    requests, manifests = plant_llm.build_requests()
    n_slots = sum(len(m["slots"]) for m in manifests.values())
    n_persona = sum(len(m["persona"]["spans"]) for m in manifests.values() if m["persona"])
    log = gs.plant_log()
    total = sum(sum(d["spans_by_kind"].values()) for d in log["datasets"].values() if "spans_by_kind" in d)
    assert n_slots + n_persona == total
    assert all(r["params"]["system"][-1]["cache_control"] == {"type": "ephemeral"} for r in requests)
    assert len({r["custom_id"] for r in requests}) == len(requests)
