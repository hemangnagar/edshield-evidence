"""Raw dialogue files -> one schema.

Every loader returns a list of dialogues; a dialogue is a list of turns
    {"dialogue_id", "dataset", "turn_idx", "speaker": "student"|"tutor", "text"}
in order. System prompts and empty turns are dropped. Nothing is modified.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

RAW = Path(__file__).resolve().parent / "data" / "raw"
Turn = Dict[str, object]
Dialogue = List[Turn]


def _turns(dialogue_id: str, dataset: str, pairs) -> Dialogue:
    out: Dialogue = []
    for speaker, text in pairs:
        text = (text or "").strip()
        if not text:
            continue
        out.append({"dialogue_id": dialogue_id, "dataset": dataset, "turn_idx": len(out),
                    "speaker": speaker, "text": text})
    return out


def load_comta(raw: Path = RAW) -> List[Dialogue]:
    """CoMTA: 188 real student <-> Khanmigo math dialogues (Khan Academy)."""
    path = raw / "comta" / "CoMTA_dataset.json"
    if not path.exists():
        return []
    records = json.loads(path.read_text(encoding="utf-8"))
    role = {"user": "student", "assistant": "tutor"}
    out = []
    for i, rec in enumerate(records):
        pairs = [(role[m["role"]], m["content"]) for m in rec["data"] if m["role"] in role]
        d = _turns(f"comta-{i:03d}", "comta", pairs)
        if d:
            d[0]["meta"] = {"math_level": rec.get("math_level")}
            out.append(d)
    return out


_PERSONA = re.compile(r"^\s*([A-Z][\w'-]+)")
_NOT_NAMES = {"The", "How", "What", "If", "She", "He", "They", "There", "Each", "After", "When", "For", "In", "On",
              "At", "Her", "His", "Then", "This", "That", "One", "Two", "Three", "Later", "While", "Before", "Now",
              "Since", "Also", "But", "And", "Then", "Thus", "However", "Which", "Who", "Many", "Some", "All",
              "Suppose", "Assume", "Find", "Calculate", "Given", "During", "Every", "Today", "Yesterday", "Tomorrow",
              "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January", "February",
              "March", "April", "June", "July", "August", "September", "October", "November", "December", "Mrs",
              "Mr", "Ms", "Dr", "Both", "Half", "First", "Second", "Third", "Last", "Next", "Over", "Out", "Into",
              "With", "From", "Using", "Because", "Yet", "Still", "Only", "Just", "Can", "Will", "Would", "Should",
              "Does", "Did", "Was", "Were", "Has", "Have", "Had", "Let", "Say", "Take", "Make", "Use", "Not", "Per"}


def _problem_names(question: str):
    """Capitalised words of the problem statement minus common sentence
    starters: the word-problem's characters ("Julia bought 12 spoons")."""
    return sorted({w for w in re.findall(r"\b([A-Z][a-z]{2,})\b", question) if w not in _NOT_NAMES})


_TUTOR_TAG = re.compile(r"^\((generic|focus|probing|telling)\)\s*")


def load_mathdial(raw: Path = RAW, split: str = "test") -> List[Dialogue]:
    """MathDial official test split: LLM-simulated students, human tutors (ETH).
    The simulated student carries a persona name in `student_profile`; it is
    recorded in meta so flags on it can be told apart from over-redaction."""
    path = raw / "mathdial" / f"{split}.jsonl"
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            rec = json.loads(line)
            pairs = []
            for seg in rec["conversation"].split("|EOM|"):
                seg = seg.strip()
                if seg.startswith("Teacher:"):
                    pairs.append(("tutor", _TUTOR_TAG.sub("", seg[len("Teacher:"):].strip())))
                elif seg.startswith("Student:"):
                    pairs.append(("student", seg[len("Student:"):].strip()))
            d = _turns(f"mathdial-{split}-{i:03d}", "mathdial", pairs)
            if d:
                m = _PERSONA.match(rec.get("student_profile", ""))
                # names of the word-problem characters ("Julia bought 12 spoons"): not PII,
                # kept so flags on them in the control can be told apart from other false positives
                q = rec.get("question", "")
                problem_names = _problem_names(rec.get("question", ""))
                d[0]["meta"] = {"qid": rec.get("qid"), "persona_name": m.group(1) if m else None,
                                "problem_names": problem_names}
                out.append(d)
    return out


def load_studychat(raw: Path = RAW) -> List[Dialogue]:
    """StudyChat: real university students <-> ChatGPT in a CS course. One
    record per interaction; the record with the highest interactionCount in a
    chat holds the full message history."""
    path = raw / "studychat" / "data.jsonl"
    if not path.exists():
        return []
    best: Dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            cid = rec["chatId"]
            if cid not in best or rec["interactionCount"] > best[cid]["interactionCount"]:
                best[cid] = rec
    role = {"user": "student", "assistant": "tutor"}
    out = []
    for cid in sorted(best):
        rec = best[cid]
        pairs = [(role[m["role"]], m["content"]) for m in rec["messages"] if m["role"] in role]
        d = _turns(f"studychat-{cid}", "studychat", pairs)
        if d:
            d[0]["meta"] = {"semester": rec.get("semester"), "topic": rec.get("topic")}
            out.append(d)
    return out


def load_tscc(raw: Path = RAW) -> List[Dialogue]:
    """TSCC v2 (Cambridge ESL chatroom lessons) arrives by request form. Drop
    the released files into data/raw/tscc/. Until the exact release format is
    in hand this accepts one JSON file per lesson shaped as a list of
    {"role": "student"|"teacher", "text": ...} turns; adapt here when it lands."""
    d = raw / "tscc"
    if not d.is_dir():
        return []
    role = {"student": "student", "teacher": "tutor", "tutor": "tutor"}
    out = []
    for p in sorted(d.glob("*.json")):
        turns = json.loads(p.read_text(encoding="utf-8"))
        pairs = [(role[t["role"]], t["text"]) for t in turns if t.get("role") in role]
        dlg = _turns(f"tscc-{p.stem}", "tscc", pairs)
        if dlg:
            out.append(dlg)
    return out


LOADERS = {"comta": load_comta, "mathdial": load_mathdial, "studychat": load_studychat, "tscc": load_tscc}


def load_all(raw: Path = RAW) -> Dict[str, List[Dialogue]]:
    return {name: fn(raw) for name, fn in LOADERS.items()}


if __name__ == "__main__":
    import sys
    for name, dialogues in load_all().items():
        n_turns = sum(len(d) for d in dialogues)
        print(f"{name:10s} dialogues {len(dialogues):5d} turns {n_turns:6d}", file=sys.stderr)
