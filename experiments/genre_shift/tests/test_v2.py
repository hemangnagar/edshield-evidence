"""Checks on the v2 definitions the paper quotes. Run from experiments/genre_shift:

    python -m pytest tests/test_v2.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_detectors as rd
import score_v2 as sv
import strata
from detectors import labelmap


def mention(case="cap", speaker="tutor", dict_word=False, category="anglo_common", initial=False, hit=True):
    return {"case": case, "speaker": speaker, "is_dict_word": dict_word, "category": category,
            "is_initial": initial, "hit": hit}


def test_case_and_dict_word():
    assert [strata.case_of(t) for t in ("summer", "Summer", "SUMMER", "R.", "JJ", "chidi okafor")] == \
        ["lower", "cap", "allcaps", "cap", "allcaps", "lower"]
    assert strata.is_dict_word("summer") and strata.is_dict_word("Grace Miller") and strata.is_dict_word("HOPE")
    assert not strata.is_dict_word("Priya") and not strata.is_dict_word("R.") and not strata.is_dict_word("Min-jun")


def test_primary_stratum_has_eight_levels_and_folds_allcaps():
    assert len(strata.PRIMARY_STRATA) == 8
    assert strata.primary_stratum(mention(case="allcaps")) == strata.primary_stratum(mention(case="cap")) == "upper|tutor|nondict"
    assert strata.primary_stratum(mention(case="lower", speaker="student", dict_word=True)) == "lower|student|dict"


def test_coverage_is_the_union_of_name_spans():
    preds = [(0, 5, "NAME"), (6, 12, "NAME"), (20, 30, "OTHER")]
    assert sv.covered(0, 12, preds, "NAME") == 11 / 12   # "Chidi" + "Okafor", the space uncovered
    assert sv.covered(20, 30, preds, "NAME") == 0 and sv.covered(20, 30, preds, None) == 1
    assert sv.covered(0, 12, [(0, 5, "NAME")], "NAME") < 0.5


def test_clopper_pearson_matches_the_three_over_n_rule():
    assert abs((1 - sv.cp_lower(600, 600)) - 3 / 600) < 2e-5
    assert sv.cp_lower(0, 10) == 0 and sv.cp_lower(0, 0) == 0


def test_transfer_exact_when_strata_explain_everything():
    a = [mention(speaker="student", hit=True)] * 50 + [mention(speaker="tutor", hit=False)] * 50
    b = [mention(speaker="student", hit=True)] * 90 + [mention(speaker="tutor", hit=False)] * 10
    t = sv.transfer(a, b, strata.STRATA_SETS["case x speaker"])
    assert abs(t["oracle"]["error_pts"]) < 1e-9 and t["oracle"]["floor_valid"]
    # the caught-only mix sees no missed tutor mentions, so it over-predicts: the MNAR bias
    assert abs(t["caught_only"]["predicted_point"] - 1.0) < 1e-9 and abs(t["caught_only_bias_pts"] - 10) < 1e-9
    none = sv.transfer(a, b, strata.STRATA_SETS["none"])
    assert abs(none["oracle"]["error_pts"] - (50 - 90)) < 1e-9


def test_transfer_reports_strata_a_never_saw():
    a = [mention(case="cap")] * 10
    b = [mention(case="cap")] * 8 + [mention(case="lower", hit=False)] * 2
    t = sv.transfer(a, b, strata.STRATA_SETS["case"])
    assert abs(t["oracle"]["uncovered_weight"] - 0.2) < 1e-9
    assert t["oracle"]["predicted_floor"] <= 0.8  # an unseen stratum contributes 0 to the floor


def test_gpt_spans_are_checked_against_the_text():
    text = "Student: hi im Pat. Tutor: Nice work, Pat. Patience helps."
    spans, counts = rd.resolve_gpt_spans(text, [
        {"start": 15, "end": 18, "label": "NAME", "text": "Pat"},      # exact
        {"start": 99, "end": 102, "label": "name", "text": "Pat"},     # wrong offsets: moved to the unused occurrence
        {"start": 0, "end": 3, "label": "NAME", "text": "Zed"},        # not in the document: dropped
        {"start": 500, "end": 510, "label": "NAME"}])                  # out of range, no text: dropped
    assert spans == [{"start": 15, "end": 18, "label": "NAME"}, {"start": 38, "end": 41, "label": "NAME"}]
    assert counts == {"exact": 1, "relocated": 1, "offsets_only": 0, "dropped": 2}
    assert rd.occurrences(text, "Pat") == [15, 38]                     # not the "Pat" inside "Patience"
    assert len(rd.propagate(text, spans[:1])) == 2


def test_labelmap():
    doc = "i go to Jefferson High btw. I live in Springfield."
    assert labelmap.to_class("spacy_trf", "ORG", doc, 8, 22) == "SCHOOL"
    assert labelmap.to_class("presidio", "LOCATION", doc, 38, 49) == "OTHER"
    assert labelmap.to_class("hf_pii", "GIVENNAME", doc, 0, 1) == "NAME"
    assert labelmap.to_class("edshield", "USERNAME", doc, 0, 1) == "OTHER"
