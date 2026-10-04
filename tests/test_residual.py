"""Hand-built cases for residual scoring (brief §3)."""

from edshield_evidence.residual import (find_residual, normalize, partial_residual, score_document)


class Ent:
    def __init__(self, label, text, start, end):
        self.label, self.text, self.start, self.end = label, text, start, end


class Result:
    def __init__(self, output, entities, replacements=None, leaks=()):
        self.deidentified_text = output
        self.entities = entities
        self.replacements = replacements or {}
        self.leaks = list(leaks)


def score(text, gold, output, entities, replacements=None):
    return score_document("d", text, gold, Result(output, entities, replacements))


def test_normalize_nfkc_casefold_whitespace_and_offsets():
    norm, omap = normalize("  Hello\tWORLD\n\n ﬁne ")
    assert norm == "hello world fine"
    # the ligature at index 15 expands to two normalized characters, both mapped back to it
    assert omap[norm.index("fi")] == 16 and omap[norm.index("fi") + 1] == 16
    assert omap[0] == 2 and omap[norm.index("world")] == 8


def test_full_name_fully_removed():
    text = "Hi im Maya Chen, see you"
    s = score(text, [(6, 15, "NAME_STUDENT")], "Hi im [CHILD], see you", [Ent("NAME_STUDENT", "Maya Chen", 6, 15)])
    i = s.identifiers[0]
    assert i.full_residual is False and i.partial is None and i.y_pred == 1
    assert s.document_handled


def test_first_name_removed_surname_survives():
    text = "Hi im Maya Chen, see you"
    s = score(text, [(6, 15, "NAME_STUDENT")], "Hi im [CHILD] Chen, see you", [Ent("NAME_STUDENT", "Maya", 6, 10)])
    i = s.identifiers[0]
    # the full gold string no longer occurs whole, so the identifier counts as handled at the
    # identifier level (y_pred = 1); the surviving surname is the partial residual, reported not gated
    assert i.full_residual is False and i.y_pred == 1
    assert i.partial == "chen"
    assert i.touched == ["NAME_STUDENT"]


def test_ann_is_not_inside_annual():
    assert find_residual("Ann", normalize("the Annual report")[0]) is None
    assert find_residual("Ann", normalize("thanks, Ann.")[0]) is not None
    assert find_residual("ann", normalize("ANN wrote it")[0]) is not None


def test_phone_with_dashes_matches_digits_and_spaces():
    assert find_residual("415-555-0199", normalize("call 4155550199 later")[0]) is not None
    assert find_residual("415-555-0199", normalize("call 415 555 0199 later")[0]) is not None
    assert find_residual("415-555-0199", normalize("call (415) 555-0199 later")[0]) is not None
    assert find_residual("415-555-0199", normalize("id 94155550199 is not it")[0]) is None
    assert find_residual("415-555-0199", normalize("call [PHONE_NUM] later")[0]) is None


def test_email_and_spoken_email():
    assert find_residual("maya.c@gmail.com", normalize("mail maya.c@gmail.com now")[0]) is not None
    assert find_residual("maya.c@gmail.com", normalize("mail [EMAIL] now")[0]) is None
    assert find_residual("maya at gmail dot com", normalize("maya  at gmail dot com")[0]) is not None


def test_surrogate_equal_to_gold_counts_as_residual():
    # Known conservative bias: the surrogate for another name happens to be the gold string.
    text = "Lee met Amanda at lunch"
    out = "Amanda met Lee at lunch"  # replace: Lee -> Amanda, Amanda -> Lee
    ents = [Ent("NAME_STUDENT", "Lee", 0, 3), Ent("NAME_RELATED", "Amanda", 8, 14)]
    s = score(text, [(0, 3, "NAME_STUDENT"), (8, 14, "NAME_RELATED")], out, ents, {"Lee": "Amanda", "Amanda": "Lee"})
    assert all(i.full_residual for i in s.identifiers)
    assert not s.document_handled


def test_word_view_alignment_and_over_redaction_sample():
    text = "Hi im Maya Chen, call 415-555-0199 ok bye"
    out = "Hi im [CHILD] Chen, call [PHONE_NUM] ok [CHILD]"
    ents = [Ent("NAME_STUDENT", "Maya", 6, 10), Ent("PHONE_NUM", "415-555-0199", 22, 34), Ent("NAME_STUDENT", "bye", 38, 41)]
    s = score(text, [(6, 15, "NAME_STUDENT"), (22, 34, "PHONE_NUM")], out, ents,
              {"Maya": "[CHILD]", "415-555-0199": "[PHONE_NUM]", "bye": "[CHILD]"})
    assert s.aligned
    got = [(w.text, w.y_true, w.y_pred) for w in s.words]
    assert got == [("Hi", 0, 0), ("im", 0, 0), ("Maya", 1, 1), ("Chen,", 1, 0), ("call", 0, 0),
                   ("415-555-0199", 1, 1), ("ok", 0, 0), ("bye", 0, 1)]
    assert len(s.over_redactions) == 1 and s.over_redactions[0]["token"] == "bye"
    assert "ok bye" in s.over_redactions[0]["context"]


def test_word_view_falls_back_to_overlap_when_output_does_not_align():
    text = "a b c"
    # offsets claim b was replaced but the output was rewritten wholesale
    s = score(text, [(2, 3, "AGE")], "zzz", [Ent("AGE", "b", 2, 3)])
    assert not s.aligned
    # without alignment only the overlap rule applies: the token inside the removed region is 1
    assert [w.y_pred for w in s.words] == [0, 1, 0]


def test_kept_entity_is_not_removed():
    text = "see Maya now"
    s = score(text, [(4, 8, "NAME_STUDENT")], "see Maya now", [Ent("NAME_STUDENT", "Maya", 4, 8)], {"Maya": "Maya"})
    assert s.identifiers[0].full_residual
    assert [w.y_pred for w in s.words] == [0, 0, 0]


def test_partial_residual_ignores_short_tokens():
    assert partial_residual("Jo Li", normalize("jo and li went")[0]) is None
    assert partial_residual("16th of February", normalize("[DATE] of the year")[0]) is None
    assert partial_residual("Jessica Hill", normalize("jessica [STREET_ADDRESS]")[0]) == "jessica"
