"""Plant synthetic identifiers into real tutoring dialogue at natural slots.

    python plant.py --seed 20261014

Writes data/planted/<dataset>.jsonl (planted text + gold spans in edshield's
label schema), data/control/<dataset>.jsonl (the same dialogues untouched)
and data/plant_log.json (what was planted where). Every name comes from
names/*.txt; contact values are synthetic (555-01xx phones, made-up handles).

Document = one dialogue, turns joined as "Student: ..." / "Tutor: ..." lines.
Gold spans are character offsets into that document, plus meta per span:
kind      first | later | nickname | related | school | email | username | phone
speaker   student | tutor   (the turn the span sits in)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import loaders

HERE = Path(__file__).resolve().parent
NAMES = HERE / "names"
CATEGORIES = ("anglo_common", "non_anglo", "name_word_collision", "nicknames_and_variants")
SPEAKER_TAG = {"student": "Student", "tutor": "Tutor"}

INTRO = ["hi im {n}", "hey its {n}", "hello my name is {n}", "{n} here", "hi this is {n}", "im {n}"]
INTRO_SCHOOL = ["hi im {n} from {s}", "this is {n} from {s}", "im {n} and i go to {s}", "hi im {n}, {s}"]
SCHOOL_ONLY = ["i go to {s} btw", "im at {s}", "this is for my class at {s}"]
TUTOR_PRE = ["Nice work, {n}.", "Great question, {n}!", "{n}, what do you think the next step is?",
             "Good thinking, {n}.", "You're close, {n}.", "Let's look at that together, {n}."]
TUTOR_POST = ["Keep going, {n}.", "Does that make sense, {n}?", "Give it another try, {n}.", "Well done, {n}!"]
RELATED = ["my brother {r} said it was different", "me and {r} got different answers",
           "my friend {r} told me to try this", "{r} in my class got something else",
           "my sister {r} helped me with this one", "my cousin {r} says you have to flip it"]
EMAIL = ["you can email me at {v}", "my email is {v}", "send it to {v}"]
USERNAME = ["my username is {v}", "add me, im {v} on discord", "im {v} on the class forum"]
PHONE = ["my number is {v}", "text me at {v}", "you can reach me at {v}"]
DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com"]
AREA_CODES = ["312", "415", "617", "713", "202", "305", "503", "919"]

LABEL = {"first": "NAME_STUDENT", "later": "NAME_STUDENT", "nickname": "NAME_STUDENT",
         "related": "NAME_RELATED", "school": "SCHOOL", "email": "EMAIL", "username": "USERNAME",
         "phone": "PHONE_NUM"}

P_INTRO, P_TUTOR, P_RELATED, P_SCHOOL, P_CONTACT = 0.7, 0.8, 0.5, 0.3, 0.1
P_VARIANT, P_FULLNAME, P_TYPO = 0.25, 0.3, 0.05


def read_list(name: str) -> List[str]:
    return [l.strip() for l in (NAMES / f"{name}.txt").read_text(encoding="utf-8").splitlines() if l.strip()]


def register_stats(dialogues: List[loaders.Dialogue]) -> Dict[str, float]:
    """How student turns in this dataset are written: share starting lowercase,
    share without terminal punctuation. Planted student text follows them."""
    lower = nopunct = n = 0
    for d in dialogues:
        for t in d:
            if t["speaker"] != "student":
                continue
            s = str(t["text"]).strip()
            if not s or not s[0].isalpha():
                continue
            n += 1
            lower += s[0].islower()
            nopunct += s[-1] not in ".?!"
    return {"n_student_turns": n, "lowercase_start": lower / n if n else 0.0,
            "no_terminal_punct": nopunct / n if n else 0.0}


def typo(word: str, rng: random.Random) -> str:
    if len(word) < 4:
        return word
    i = rng.randrange(1, len(word) - 1)
    op = rng.choice(["swap", "drop", "double"])
    if op == "swap":
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if op == "drop":
        return word[:i] + word[i + 1:]
    return word[:i] + word[i] + word[i:]


def variant(first: str, rng: random.Random) -> str:
    """A nickname-or-initial form of the base first name for a later mention."""
    r = rng.random()
    if r < 0.5:
        return first[0].upper() + "."
    if r < 0.75:
        return first.upper()
    return first[: max(2, min(4, len(first) - 1))]


class Planter:
    def __init__(self, seed: int):
        self.seed = seed
        self.lists = {c: read_list(c) for c in CATEGORIES}
        self.schools = read_list("schools")

    def rng_for(self, dialogue_id: str) -> random.Random:
        return random.Random(f"{self.seed}:{dialogue_id}")

    # -- one dialogue -------------------------------------------------------

    def plant(self, dialogue: loaders.Dialogue, reg: Dict[str, float]) -> Tuple[dict, dict]:
        did = str(dialogue[0]["dialogue_id"])
        dataset = str(dialogue[0]["dataset"])
        rng = self.rng_for(did)
        category = rng.choice(CATEGORIES)
        full = rng.choice(self.lists[category])
        first, last = full.split(" ", 1)
        related_full = rng.choice([x for x in self.lists[category] if x != full])
        related_first = related_full.split(" ", 1)[0]
        persona = (dialogue[0].get("meta") or {}).get("persona_name")

        turns: List[dict] = [dict(t) for t in dialogue]
        # turn_idx -> [(where, phrase, [(value, kind)])]; filled after the mention order is known
        inserts: Dict[int, List[Tuple[str, str, List[Tuple[str, str]]]]] = {}
        plan = {"dialogue_id": did, "dataset": dataset, "category": category, "name": full,
                "related": related_full, "persona_replaced": 0, "slots": []}
        s_idx = [i for i, t in enumerate(turns) if t["speaker"] == "student"]
        t_idx = [i for i, t in enumerate(turns) if t["speaker"] == "tutor"]
        if not s_idx:
            return self._assemble(turns, {}, plan, reg, rng), plan

        def student_form(name: str) -> Tuple[str, bool]:
            """Match the register of student turns: lowercase and typos."""
            out, had_typo = name, False
            if rng.random() < reg["lowercase_start"]:
                out = out.lower()
            if rng.random() < P_TYPO:
                out, had_typo = typo(out, rng), True
            return out, had_typo

        def add(i: int, where: str, phrase: str, values: List[Tuple[str, str]]):
            inserts.setdefault(i, []).append((where, phrase, values))

        # --- decide the student-name mention slots, then order them by position
        use_school = rng.random() < P_SCHOOL
        school = rng.choice(self.schools) if use_school else None
        mentions: List[Tuple[int, int, str]] = []  # (turn, order-within-turn, source)
        if rng.random() < P_INTRO:
            mentions.append((s_idx[0], -1, "intro"))
        elif school:
            i = rng.choice(s_idx)
            add(i, "post", rng.choice(SCHOOL_ONLY).format(s=school), [(school, "school")])
            plan["slots"].append({"turn": i, "kind": "school"})
        persona_hits: Dict[int, int] = {}
        if persona:
            pat = re.compile(r"\b" + re.escape(persona) + r"\b")
            for i, t in enumerate(turns):
                n = len(pat.findall(str(t["text"])))
                if n:
                    persona_hits[i] = n
                    mentions += [(i, j, "persona") for j in range(n)]
        later_t = [i for i in t_idx if i > s_idx[0]] or t_idx
        tutor_slots: Dict[int, str] = {}
        if later_t and rng.random() < P_TUTOR:
            k = min(len(later_t), rng.choice([1, 2, 3]))
            for i in sorted(rng.sample(later_t, k)):
                if i in persona_hits:
                    continue
                where = rng.choice(["pre", "post"])
                tutor_slots[i] = where
                mentions.append((i, -1 if where == "pre" else 10_000, "tutor"))
        mentions.sort()

        # --- assign a form to each mention in document order
        forms: Dict[Tuple[int, int, str], Tuple[str, str, bool]] = {}  # -> (shown, kind, typo)
        for n, m in enumerate(mentions):
            turn_i, _, source = m
            if n == 0:
                shown, kind = (full if source == "intro" and rng.random() < P_FULLNAME else first), "first"
            elif rng.random() < P_VARIANT:
                shown, kind = variant(first, rng), "nickname"
            else:
                shown, kind = first, "later"
            had_typo = False
            if turns[turn_i]["speaker"] == "student":
                shown, had_typo = student_form(shown)
            forms[m] = (shown, kind, had_typo)

        # --- materialise: intro
        for m in mentions:
            turn_i, _, source = m
            shown, kind, had_typo = forms[m]
            if source == "intro":
                vals = [(shown, kind)]
                if school:
                    phrase = rng.choice(INTRO_SCHOOL).format(n=shown, s=school)
                    vals.append((school, "school"))
                else:
                    phrase = rng.choice(INTRO).format(n=shown)
                if rng.random() >= reg["no_terminal_punct"]:
                    phrase += "."
                add(turn_i, "pre", phrase, vals)
                plan["slots"].append({"turn": turn_i, "kind": "intro", "form": kind, "typo": had_typo})
            elif source == "tutor":
                where = tutor_slots[turn_i]
                phrase = rng.choice(TUTOR_PRE if where == "pre" else TUTOR_POST).format(n=shown)
                add(turn_i, where, phrase, [(shown, kind)])
                plan["slots"].append({"turn": turn_i, "kind": "tutor_address", "form": kind})
        # persona replacement (MathDial): the simulated student's name is already
        # in the text; every whole-word occurrence becomes the planted name so the
        # dialogue carries one student name and no un-gold name confounds scoring
        for i in persona_hits:
            pat = re.compile(r"\b" + re.escape(persona) + r"\b")
            text = str(turns[i]["text"])
            spans, out, pos = [], "", 0
            for j, mt in enumerate(pat.finditer(text)):
                shown, kind, _ = forms[(i, j, "persona")]
                out += text[pos:mt.start()]
                spans.append((len(out), len(out) + len(shown), kind, shown))
                out += shown
                pos = mt.end()
                plan["persona_replaced"] += 1
            out += text[pos:]
            turns[i]["text"] = out
            turns[i]["_pre_spans"] = spans

        # --- classmate or family reference in one student turn
        if rng.random() < P_RELATED:
            i = rng.choice(s_idx[1:] or s_idx)
            shown, had_typo = student_form(related_first)
            add(i, "post", rng.choice(RELATED).format(r=shown), [(shown, "related")])
            plan["slots"].append({"turn": i, "kind": "related", "typo": had_typo})

        # --- personal email, username, phone: 10% each, one student turn each
        contact = {
            "email": (EMAIL, self._email(first, last, rng)),
            "username": (USERNAME, self._username(first, last, rng)),
            "phone": (PHONE, self._phone(rng)),
        }
        for kind, (tpls, value) in contact.items():
            if rng.random() < P_CONTACT:
                i = rng.choice(s_idx)
                add(i, "post", rng.choice(tpls).format(v=value), [(value, kind)])
                plan["slots"].append({"turn": i, "kind": kind})
        return self._assemble(turns, inserts, plan, reg, rng), plan

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _email(first: str, last: str, rng: random.Random) -> str:
        f, l = first.lower(), last.lower().replace("'", "").replace("-", "")
        local = rng.choice([f"{f}.{l}", f"{f}{l}{rng.randint(1, 99)}", f"{f}{rng.randint(2008, 2014)}", f"{f[0]}{l}"])
        return f"{local}@{rng.choice(DOMAINS)}"

    @staticmethod
    def _username(first: str, last: str, rng: random.Random) -> str:
        f, l = first.lower(), last.lower().replace("'", "").replace("-", "")
        return rng.choice([f"{f}{rng.randint(10, 999)}", f"{f}_{l}", f"xX{first}Xx", f"{f}{l[0]}{rng.randint(100, 999)}",
                           f"{f}.{l}{rng.randint(1, 9)}"])

    @staticmethod
    def _phone(rng: random.Random) -> str:
        area, line = rng.choice(AREA_CODES), f"01{rng.randint(0, 99):02d}"
        return rng.choice([f"({area}) 555-{line}", f"{area}-555-{line}", f"{area}555{line}", f"{area}.555.{line}"])

    def _assemble(self, turns: List[dict], inserts, plan: dict, reg: Dict[str, float], rng: random.Random) -> dict:
        """Join turns into one document and compute gold character spans."""
        parts: List[str] = []
        gold: List[list] = []
        meta_spans: List[dict] = []
        offset = 0
        for i, t in enumerate(turns):
            text = str(t["text"])
            local: List[Tuple[int, int, str, str]] = list(t.get("_pre_spans", []))
            for where, phrase, values in inserts.get(i, []):
                if where == "pre":
                    shift = len(phrase) + 1
                    local = [(s + shift, e + shift, k, v) for s, e, k, v in local]
                    base = 0
                    text = phrase + " " + text
                else:
                    if text and text[-1] in ".?!":
                        sep = " "
                    else:
                        sep = " " if rng.random() < reg["no_terminal_punct"] else ". "
                    base = len(text) + len(sep)
                    text = text + sep + phrase
                pos = 0
                for value, kind in values:
                    j = phrase.find(value, pos)
                    assert j >= 0, (value, phrase)
                    local.append((base + j, base + j + len(value), kind, value))
                    pos = j + len(value)
            tag = SPEAKER_TAG[str(t["speaker"])]
            line = f"{tag}: {text}"
            head = len(tag) + 2
            for s, e, kind, value in sorted(local):
                gs, ge = offset + head + s, offset + head + e
                gold.append([gs, ge, LABEL[kind]])
                meta_spans.append({"start": gs, "end": ge, "label": LABEL[kind], "kind": kind, "text": value,
                                   "speaker": t["speaker"], "turn_idx": i})
            parts.append(line)
            offset += len(line) + 1  # "\n"
        doc_text = "\n".join(parts)
        for g, m in zip(gold, meta_spans):
            assert doc_text[g[0]:g[1]] == m["text"], (doc_text[g[0]:g[1]], m["text"])
        meta0 = turns[0].get("meta") or {}
        return {"doc_id": str(turns[0]["dialogue_id"]), "text": doc_text, "gold_spans": gold,
                "meta": {"dataset": turns[0]["dataset"], "category": plan["category"], "name": plan["name"],
                         "related": plan["related"], "spans": meta_spans,
                         "persona_name": meta0.get("persona_name"), "problem_names": meta0.get("problem_names", [])}}


def control_doc(dialogue: loaders.Dialogue) -> dict:
    parts = [f"{SPEAKER_TAG[str(t['speaker'])]}: {t['text']}" for t in dialogue]
    meta0 = dialogue[0].get("meta") or {}
    return {"doc_id": str(dialogue[0]["dialogue_id"]), "text": "\n".join(parts), "gold_spans": [],
            "meta": {"dataset": dialogue[0]["dataset"], "persona_name": meta0.get("persona_name"),
                     "problem_names": meta0.get("problem_names", [])}}


def write_jsonl(rows: List[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261014)
    ap.add_argument("--out", default=str(HERE / "data"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    planter = Planter(args.seed)
    log = {"seed": args.seed, "datasets": {}}
    for name, dialogues in loaders.load_all().items():
        if not dialogues:
            log["datasets"][name] = {"dialogues": 0, "note": "no raw data present"}
            continue
        reg = register_stats(dialogues)
        planted, plans = [], []
        for d in dialogues:
            doc, plan = planter.plant(d, reg)
            planted.append(doc)
            plans.append(plan)
        write_jsonl(planted, out / "planted" / f"{name}.jsonl")
        write_jsonl([control_doc(d) for d in dialogues], out / "control" / f"{name}.jsonl")
        kinds: Dict[str, int] = {}
        for doc in planted:
            for s in doc["meta"]["spans"]:
                kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
        cats: Dict[str, int] = {}
        for p in plans:
            cats[p["category"]] = cats.get(p["category"], 0) + 1
        log["datasets"][name] = {"dialogues": len(dialogues), "turns": sum(len(d) for d in dialogues),
                                 "register": reg, "spans_by_kind": kinds, "dialogues_by_category": cats,
                                 "persona_replaced": sum(p["persona_replaced"] for p in plans),
                                 "median_doc_chars": statistics.median(len(d["text"]) for d in planted),
                                 "plans": plans}
        print(f"{name:10s} dialogues {len(dialogues):4d}  gold spans {sum(kinds.values()):5d}  {kinds}")
    (out / "plant_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
