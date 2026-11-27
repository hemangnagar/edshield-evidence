"""Surface form of a name mention, and the strata built from it.

One record per planted mention (written by plant.py into the gold file):

  case          lower | cap | allcaps     first letter lowercase; first letter
                                          uppercase; two or more letters, all uppercase
  speaker       student | tutor           the turn the mention sits in
  position      first | later             first mention of that person in the dialogue,
                                          or any later one (nickname/initial forms are later;
                                          a classmate or relative is mentioned once, so first)
  category      the name list the dialogue drew from
  is_dict_word  the mention's first whitespace token, lowercased, is in
                names/english_words.txt (lowercase entries of SCOWL american-english,
                63,875 words); single letters are not words, so an initial is never one
  n_wordpieces  DeBERTa-v3 pieces of the mention text (tokenizer of the pinned model)
  is_initial    one letter and a period ("R.")

PRIMARY STRATUM = case x speaker x is_dict_word, with case folded to two
levels (lower | upper, upper = cap or allcaps): 2 x 2 x 2 = 8 strata. This is
the one definition the floor-transfer test uses; `primary_stratum` is it.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict

HERE = Path(__file__).resolve().parent
WORDLIST = HERE / "names" / "english_words.txt"
TOKENIZER_ID = "edshield/piilo-deberta-v3-small"
TOKENIZER_REV = "5effafd0299ac576b6c5b3a91b3f26800ce89e62"
_INITIAL = re.compile(r"^[A-Za-z]\.$")
_LETTERS = re.compile(r"[A-Za-z]+")


@lru_cache(maxsize=1)
def english_words() -> frozenset:
    return frozenset(WORDLIST.read_text(encoding="utf-8").split())


@lru_cache(maxsize=1)
def _tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(TOKENIZER_ID, revision=TOKENIZER_REV)


@lru_cache(maxsize=None)
def n_wordpieces(text: str) -> int:
    return len(_tokenizer().tokenize(text))


def case_of(text: str) -> str:
    letters = "".join(_LETTERS.findall(text))
    if not letters or letters[0].islower():
        return "lower"
    return "allcaps" if len(letters) > 1 and letters.isupper() else "cap"


def is_dict_word(text: str) -> bool:
    tokens = text.split()
    first = tokens[0].strip(".,'-").lower() if tokens else ""
    return len(first) > 1 and first in english_words()


def surface_form(text: str, speaker: str, kind: str, category: str) -> Dict[str, object]:
    """The surface-form record of one mention. `kind` is plant.py's
    first | later | nickname | related (for PIILO gold names: `gold`)."""
    return {"case": case_of(text), "speaker": speaker,
            "position": "later" if kind in ("later", "nickname") else "first",
            "category": category, "is_dict_word": is_dict_word(text),
            "n_wordpieces": n_wordpieces(text), "is_initial": bool(_INITIAL.match(text))}


def primary_stratum(m: Dict[str, object]) -> str:
    """case (lower | upper) x speaker x is_dict_word: the 8 primary strata."""
    case = "lower" if m["case"] == "lower" else "upper"
    return f"{case}|{m['speaker']}|{'dict' if m['is_dict_word'] else 'nondict'}"


PRIMARY_STRATA = [f"{c}|{s}|{d}" for c in ("upper", "lower") for s in ("student", "tutor") for d in ("nondict", "dict")]


def _case2(m) -> str:
    return "lower" if m["case"] == "lower" else "upper"


# Strata sets for the ablation, coarsest to finest. `primary` is the brief's;
# `primary x is_initial` is an addition (v1 found initials to be the dominant miss).
STRATA_SETS: Dict[str, Callable[[Dict[str, object]], str]] = {
    "none": lambda m: "all",
    "case": _case2,
    "case x speaker": lambda m: f"{_case2(m)}|{m['speaker']}",
    "primary (case x speaker x is_dict_word)": primary_stratum,
    "primary x category": lambda m: f"{primary_stratum(m)}|{m['category']}",
    "primary x is_initial": lambda m: f"{primary_stratum(m)}|{'initial' if m['is_initial'] else 'name'}",
}
PRIMARY = "primary (case x speaker x is_dict_word)"
