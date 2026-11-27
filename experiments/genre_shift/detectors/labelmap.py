"""Each detector's own labels -> {NAME, SCHOOL, EMAIL, PHONE, OTHER}.

Name recall, the primary metric, counts only spans mapped to NAME here.
Anything a detector flags that is not in its table is OTHER.

| detector    | NAME                       | SCHOOL                                   | EMAIL         | PHONE        |
|-------------|----------------------------|------------------------------------------|---------------|--------------|
| edshield    | NAME_STUDENT, NAME_RELATED | SCHOOL                                   | EMAIL         | PHONE_NUM    |
| presidio    | PERSON                     | LOCATION, ORGANIZATION + school token    | EMAIL_ADDRESS | PHONE_NUMBER |
| spacy_trf   | PERSON                     | ORG, FAC, GPE, LOC + school token        | -             | -            |
| hf_pii      | GIVENNAME, SURNAME         | -                                        | EMAIL         | TELEPHONENUM |
| gpt4o_mini  | NAME                       | SCHOOL                                   | EMAIL         | PHONE        |

"+ school token": a place or organisation span counts as SCHOOL only when one
of school / academy / high / middle is a word inside the span or the word
directly before or after it; otherwise it is OTHER. (Presidio's default
recognizers do not emit ORGANIZATION; the row is there for completeness.)
USERNAME (edshield, hf_pii, gpt4o_mini) is OTHER: the brief's secondary labels
are school, email and phone.
"""
from __future__ import annotations

import re

CLASSES = ("NAME", "SCHOOL", "EMAIL", "PHONE", "OTHER")
SCHOOL_TOKENS = {"school", "academy", "high", "middle"}

DIRECT = {
    "edshield": {"NAME_STUDENT": "NAME", "NAME_RELATED": "NAME", "SCHOOL": "SCHOOL", "EMAIL": "EMAIL",
                 "PHONE_NUM": "PHONE"},
    "presidio": {"PERSON": "NAME", "EMAIL_ADDRESS": "EMAIL", "PHONE_NUMBER": "PHONE"},
    "spacy_trf": {"PERSON": "NAME"},
    "hf_pii": {"GIVENNAME": "NAME", "SURNAME": "NAME", "EMAIL": "EMAIL", "TELEPHONENUM": "PHONE"},
    "gpt4o_mini": {"NAME": "NAME", "SCHOOL": "SCHOOL", "EMAIL": "EMAIL", "PHONE": "PHONE"},
}
# place / organisation labels that become SCHOOL only next to a school token
SCHOOL_IF_ADJACENT = {
    "presidio": {"LOCATION", "ORGANIZATION"},
    "spacy_trf": {"ORG", "FAC", "GPE", "LOC"},
}
_WORD = re.compile(r"[A-Za-z]+")


def school_adjacent(text: str, start: int, end: int) -> bool:
    inside = {w.lower() for w in _WORD.findall(text[start:end])}
    before = _WORD.findall(text[max(0, start - 40):start])[-1:]
    after = _WORD.findall(text[end:end + 40])[:1]
    return bool((inside | {w.lower() for w in before + after}) & SCHOOL_TOKENS)


def to_class(detector: str, label: str, text: str, start: int, end: int) -> str:
    """The class of one predicted span; `text` is the whole document."""
    cls = DIRECT[detector].get(label)
    if cls:
        return cls
    if label in SCHOOL_IF_ADJACENT.get(detector, ()) and school_adjacent(text, start, end):
        return "SCHOOL"
    return "OTHER"
