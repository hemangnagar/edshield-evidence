import json

import pytest

from edshield_evidence.datasets import DatasetError, Document, load_jsonl, piilo_documents, rebuild_spans, write_jsonl


def test_rebuild_spans_single_spaces():
    text = "Hi Maya Chen here"
    spans = rebuild_spans(text, ["Hi", "Maya", "Chen", "here"], ["O", "B-NAME_STUDENT", "I-NAME_STUDENT", "O"])
    assert spans == [(3, 12, "NAME_STUDENT")]
    assert text[3:12] == "Maya Chen"


def test_rebuild_spans_with_newline_separators_and_whitespace_tokens():
    text = "mom: Ann\n\ncall 555 0199"
    tokens = ["mom", ":", "Ann", "\n\n", "call", "555", "0199"]
    labels = ["O", "O", "B-NAME_RELATED", "O", "O", "B-PHONE_NUM", "I-PHONE_NUM"]
    spans = rebuild_spans(text, tokens, labels)
    assert spans == [(5, 8, "NAME_RELATED"), (15, 23, "PHONE_NUM")]
    assert text[15:23] == "555 0199"


def test_rebuild_spans_breaks_on_label_change_and_stray_inside():
    text = "Ann Lee Bo"
    spans = rebuild_spans(text, ["Ann", "Lee", "Bo"], ["B-NAME_STUDENT", "B-NAME_STUDENT", "I-NAME_RELATED"])
    assert spans == [(0, 3, "NAME_STUDENT"), (4, 7, "NAME_STUDENT"), (8, 10, "NAME_RELATED")]


def test_rebuild_spans_rejects_misaligned_tokens():
    with pytest.raises(DatasetError):
        rebuild_spans("abc", ["x"], ["O"])


def test_piilo_documents_and_jsonl_round_trip(tmp_path):
    rec = {"document": 7, "full_text": "I am Bo", "tokens": ["I", "am", "Bo"], "trailing_whitespace": [True, True, False],
           "labels": ["O", "O", "B-NAME_STUDENT"], "genre": "chat"}
    docs = piilo_documents([rec], prefix="t-")
    assert docs[0].doc_id == "t-7" and docs[0].gold_spans == [(5, 7, "NAME_STUDENT")] and docs[0].meta == {"genre": "chat"}
    p = tmp_path / "x.jsonl"
    write_jsonl(docs, p)
    back = load_jsonl(p)
    assert back[0] == docs[0]
    assert json.loads(p.read_text().splitlines()[0])["gold_spans"] == [[5, 7, "NAME_STUDENT"]]
