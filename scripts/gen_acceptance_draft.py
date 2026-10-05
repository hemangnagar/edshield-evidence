#!/usr/bin/env python3
"""Draft generator for sealed acceptance sets (A1, A2, ...).

Tutoring exchanges, chat messages and short reflections in a child's
register, with invented names, schools, towns, ages, dates, phones, emails,
usernames, IDs and street addresses, phrased without the cue words the rules
look for. Every sentence template here was written fresh for this repo; a
test shingles this file's string literals against edshield's own generator
at the pinned commit and fails on overlap. Faker supplies values only.

    python scripts/gen_acceptance_draft.py A1 --n 400 --seed 11

writes evidence/sets/A1.draft.jsonl (doc_id, text, gold_spans) and
evidence/sets/A1.draft.review.md with 50 random documents for human review.
The human edits or approves, then seals with `python -m edshield_evidence.seal`.
This script never seals.

A draft meant for sealing is generated on a private machine with a private
seed (omit --seed) and is never committed: the repository is public, so a
committed draft, or a committed seed with this generator, would make the
seal cosmetic. Drafts are ignored by git; only the sealed files are pushed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, List, Tuple

from faker import Faker

GENERATOR_VERSION = "a-draft-4"

HERE = Path(__file__).resolve().parent.parent
SETS_DIR = HERE / "evidence" / "sets"

LABELS = ["NAME_STUDENT", "NAME_RELATED", "SCHOOL", "LOCATION", "AGE", "DATE",
          "PHONE_NUM", "EMAIL", "USERNAME", "ID_NUM", "STREET_ADDRESS"]
MIN_PER_LABEL = 60

# --- Values ------------------------------------------------------------------------

STREET_WORDS = ["pine", "cedar", "maple", "birch", "willow", "hollow", "ridge", "orchard", "meadow", "harbor",
                "sunset", "lakeview", "quarry", "canyon", "foxglove", "juniper", "aspen", "linden"]
STREET_KINDS = ["street", "road", "lane", "avenue", "court", "drive", "way", "place"]
SCHOOL_KINDS = ["elementary", "middle school", "intermediate", "k-8", "academy", "charter", "prep"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
MONTH_SHORT = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
HANDLE_BITS = ["gamer", "draws", "reads", "skates", "codes", "bakes", "sings", "ftw", "xx", "lol", "yt", "tv",
               "plays", "builds", "kicks", "dances"]
MAIL_HOSTS = ["gmail", "yahoo", "outlook", "icloud", "proton"]


def lower_maybe(rng: random.Random, s: str, p: float = 0.55) -> str:
    return s.lower() if rng.random() < p else s


class Person:
    def __init__(self, fake: Faker, rng: random.Random):
        self.first = fake.first_name()
        self.last = fake.last_name()
        self.rng = rng
        self.age = rng.randint(7, 14)
        self.grade = max(1, self.age - 5)
        self.relative_first = fake.first_name()
        self.relative_last = fake.last_name()
        self.teacher_last = fake.last_name()
        self.friend = fake.first_name()
        self.town = fake.city()
        self.school = f"{fake.last_name()} {rng.choice(SCHOOL_KINDS)}"
        self.street = f"{rng.choice(STREET_WORDS)} {rng.choice(STREET_KINDS)}"
        self.house = rng.randint(3, 9800)
        self.phone_digits = "".join(rng.choice("0123456789") for _ in range(10))
        self.handle = self._handle()
        self.mail_user = self._mail_user()
        self.mail_host = rng.choice(MAIL_HOSTS)
        self.student_id = self._student_id()
        self.month = rng.randrange(12)
        self.day = rng.randint(1, 28)

    def _handle(self) -> str:
        r = self.rng
        base = r.choice([self.first.lower(), self.first.lower()[:3] + self.last.lower()[:3], self.last.lower()])
        sep = r.choice(["", "_", "."])
        return f"{base}{sep}{r.choice(HANDLE_BITS)}{r.choice(['', str(r.randint(2, 99)), str(r.randint(2010, 2019))])}"

    def _mail_user(self) -> str:
        r = self.rng
        return r.choice([f"{self.first.lower()}.{self.last.lower()}", f"{self.first.lower()}{r.randint(10, 99)}",
                         f"{self.first.lower()[0]}{self.last.lower()}{r.randint(1, 9)}"])

    def _student_id(self) -> str:
        r = self.rng
        return r.choice([f"{r.randint(1000000, 9999999)}", f"ST{r.randint(100000, 999999)}", f"{r.randint(20, 29)}-{r.randint(10000, 99999)}"])

    # --- rendered slots, each returns (text, label) ---------------------------------
    def slot(self, kind: str) -> Tuple[str, str]:
        r = self.rng
        if kind == "name":
            return lower_maybe(r, self.first), "NAME_STUDENT"
        if kind == "fullname":
            return lower_maybe(r, f"{self.first} {self.last}"), "NAME_STUDENT"
        if kind == "lastname":
            return lower_maybe(r, self.last, 0.3), "NAME_STUDENT"
        if kind == "relative":
            return lower_maybe(r, self.relative_first), "NAME_RELATED"
        if kind == "relative_full":
            return lower_maybe(r, f"{self.relative_first} {self.relative_last}", 0.3), "NAME_RELATED"
        if kind == "teacher":
            return lower_maybe(r, self.teacher_last, 0.3), "NAME_RELATED"
        if kind == "friend":
            return lower_maybe(r, self.friend), "NAME_RELATED"
        if kind == "school":
            return lower_maybe(r, self.school, 0.7), "SCHOOL"
        if kind == "town":
            return lower_maybe(r, self.town, 0.6), "LOCATION"
        if kind == "age":
            return str(self.age), "AGE"
        if kind == "age_words":
            return r.choice(["seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen"][self.age - 7:self.age - 6] or [str(self.age)]), "AGE"
        if kind == "date":
            m = self.month
            form = r.choice([
                f"{MONTH_SHORT[m]} {self.day}", f"{MONTHS[m]} {self.day}", f"the {self.day}{_ord(self.day)} of {MONTHS[m]}",
                f"{m + 1}/{self.day}", f"{self.day} {MONTH_SHORT[m]}",
            ])
            return form, "DATE"
        if kind == "phone":
            d = self.phone_digits
            form = r.choice([d, f"{d[:3]} {d[3:6]} {d[6:]}", f"{d[:3]}-{d[3:6]}-{d[6:]}", f"({d[:3]}) {d[3:6]} {d[6:]}", f"{d[:3]}.{d[3:6]}.{d[6:]}"])
            return form, "PHONE_NUM"
        if kind == "email":
            u, h = self.mail_user, self.mail_host
            form = r.choice([f"{u}@{h}.com", f"{u} at {h} dot com", f"{u} @ {h} . com", f"{u}@{h}.com", f"{u.replace('.', ' dot ')} at {h} dot com"])
            return form, "EMAIL"
        if kind == "handle":
            return r.choice([self.handle, "@" + self.handle, self.handle]), "USERNAME"
        if kind == "id":
            return self.student_id, "ID_NUM"
        if kind == "address":
            form = r.choice([f"{self.house} {self.street}", self.street, f"{self.house} {self.street}".title(), self.street.title()])
            return form, "STREET_ADDRESS"
        raise KeyError(kind)


def _ord(n: int) -> str:
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


# --- Templates ----------------------------------------------------------------------
# {slot} marks a value. Written fresh; no cue words like "my name is" / "I live in".

TUTOR_LINES: Dict[str, List[str]] = {
    "name": ["Student: it's {name} again, same as yesterday", "Tutor: nice work {name}, that one was tricky",
             "Student: {name} here. stuck on number 4", "Tutor: {name}, read the question once more for me",
             "Student: can you put {fullname} on the certificate thing", "Tutor: ok {name}, last one and then you're done"],
    "fullname": ["Student: {fullname}, period 3 class", "Tutor: logging this session for {fullname}",
                 "Student: the worksheet says {fullname} at the top"],
    "relative": ["Student: {relative} said the answer is 12 but idk", "Student: hold on {relative} is calling me for dinner",
                 "Student: {relative_full} is picking me up so i have 5 min", "Student: {teacher} gave us this and nobody gets it",
                 "Student: {friend} already finished and keeps bragging"],
    "school": ["Student: at {school} we do it the other way", "Tutor: does {school} use the same textbook",
               "Student: {school} has a test on this friday"],
    "town": ["Student: it snowed in {town} so no school tmrw", "Student: we went to the library in {town} for this",
             "Tutor: is {town} on the same time zone as me"],
    "age": ["Student: {age} and still counting on my fingers lol", "Student: everyone whos {age} already did fractions",
            "Tutor: for someone whos {age} this is really good", "Student: {age} next month actually, big party"],
    "date": ["Student: the project is due {date} and i havent started", "Student: my recital is {date} so cant do tuesday",
             "Tutor: we'll pick this up {date} then"],
    "phone": ["Student: text {phone} if the link breaks", "Student: dad said call {phone} when we're done",
              "Tutor: the office number on file is {phone}, is that still right"],
    "email": ["Student: send it to {email} pls", "Student: can you email {email}, thats the one i check",
              "Tutor: i'll forward the notes to {email}"],
    "handle": ["Student: add me, {handle}, i post my drawings there", "Student: {handle} is me on the math game leaderboard",
               "Student: im {handle} on the class discord"],
    "id": ["Student: the login wants a number, mine is {id}", "Student: {id} is what it says on the lunch card",
           "Tutor: type {id} where it asks for student number"],
    "address": ["Student: the bus drops me at {address}", "Student: we moved to {address} over the summer",
                "Tutor: so {address} is near the park you mentioned"],
}

CHAT_LINES: Dict[str, List[str]] = {
    "name": ["hey its {name} 👋", "{name} r u coming to practice", "lol {name} u forgot ur bag again",
             "this is {fullname} from the group project", "guys {name} said to meet at 3"],
    "fullname": ["{fullname} got picked for the team!!", "ask {fullname}, they had it last", "{fullname} isnt in our class anymore"],
    "relative": ["{relative} wont let me go ugh", "{relative_full} is driving us saturday", "{teacher} moved the quiz to monday",
                 "{friend} is being so annoying rn", "{relative} took my phone so i'm on the tablet"],
    "school": ["{school} lost again lol", "is {school} closed tmrw too", "the new kid came from {school}"],
    "town": ["we're in {town} till sunday", "{town} is sooo boring", "the tournament is in {town} this year"],
    "age": ["{age} not 5 stop treating me like a baby", "ur {age}?? i thought u were older", "cant, my mom says {age} is too young for that server",
            "{age_words} is old enough to stay home alone imo"],
    "date": ["party is {date} dont forget", "sleepover {date}?", "tryouts got moved to {date}"],
    "phone": ["new number {phone}", "txt me {phone}", "{phone} thats my moms if u need a ride"],
    "email": ["send the pics to {email}", "{email} for the google doc", "use {email} not the school one"],
    "handle": ["follow me {handle}", "im {handle} on there", "{handle} if u wanna play later", "my tag is {handle}"],
    "id": ["the wifi login is ur student number, mine is {id}", "{id} didnt work for the library site",
           "forgot my number again, its {id} right?"],
    "address": ["come to {address} after school", "we're at {address} now, the blue house", "{address}, ring twice"],
}

REFLECTION_LINES: Dict[str, List[str]] = {
    "name": ["Everyone calls me {name} even though it is not my real name.", "This reflection is by {fullname}.",
             "When the coach yelled {name} I knew I was in trouble.", "{name} is how I sign all my drawings."],
    "fullname": ["Spring portfolio, {fullname}, room 12.", "{fullname} - period 3",
                 "I am {fullname} and this is what I learned this year."],
    "relative": ["{relative} drives me to school when it rains.", "{relative_full} came to the science fair and took pictures.",
                 "{teacher} is the strictest teacher I have ever had.", "{friend} and I built the volcano together."],
    "school": ["Before this year I went to {school}, which was much smaller.", "The gym at {school} smells like old sneakers.",
               "Next year I will be at {school} and I am nervous."],
    "town": ["We drove all the way to {town} to see the eclipse.", "{town} is where my grandparents have their farm.",
             "Our team played a tournament in {town} and lost every game."],
    "age": ["Being {age} is harder than people think.", "I am {age} and I already have a job walking dogs.",
            "When you are {age_words} you do not get to decide much."],
    "date": ["The fair was on {date} and it rained the whole time.", "I remember {date} because that is when we got the puppy.",
             "Our last day of camp is {date}."],
    "phone": ["Call {phone} if you want to buy cookies for the fundraiser.", "The number for the lost dog poster was {phone}."],
    "email": ["Questions about the bake sale go to {email}.", "I made {email} just for school stuff."],
    "handle": ["I post my stop motion videos as {handle}.", "On the reading app I am {handle} and I have 40 badges."],
    "id": ["I have to type {id} every single time I log in to the chromebook.", "The number on my badge is {id}."],
    "address": ["We have lived at {address} since I was little.", "The lemonade stand will be at {address} on saturday."],
}

FILLER: Dict[str, List[str]] = {
    "tutor": ["Tutor: what do we do first with a fraction like this", "Student: multiply both sides?",
              "Tutor: close, think about what stays balanced", "Student: ohhh ok so it's 3", "Tutor: can you show the step you skipped",
              "Student: i dont get why the negative flips", "Tutor: let's draw the number line again", "Student: wait i think i see it",
              "Tutor: good, now try the next one on your own", "Student: is this going to be on the test",
              "Tutor: read the word problem out loud for me", "Student: the train one makes no sense"],
    "chat": ["did u do the hw", "nooo i forgot", "what page was it", "brb dinner", "lol same", "who has the notes",
             "im so bored", "that movie was mid", "can we play after", "my game keeps crashing", "ok ok im coming", "bring the charger"],
    "reflection": ["This year I learned that mistakes are part of practicing.", "The hardest part was staying patient.",
                   "I want to get better at reading out loud.", "Our group did not agree at first but we figured it out.",
                   "I liked the experiment with the plants the most.", "If I could do it again I would start earlier.",
                   "Science is my favorite because we get to build things.", "I think I improved at explaining my answers."],
}

GENRES = {"tutor": (TUTOR_LINES, "\n"), "chat": (CHAT_LINES, "\n"), "reflection": (REFLECTION_LINES, " ")}
SLOT_RE = re.compile(r"\{(\w+)\}")


def render(template: str, person: Person) -> Tuple[str, List[Tuple[int, int, str]]]:
    out, spans, pos = [], [], 0
    length = 0
    for m in SLOT_RE.finditer(template):
        out.append(template[pos:m.start()])
        length += m.start() - pos
        value, label = person.slot(m.group(1))
        spans.append((length, length + len(value), label))
        out.append(value)
        length += len(value)
        pos = m.end()
    out.append(template[pos:])
    return "".join(out), spans


def generate(n: int, seed: int, pii_rate: float = 0.5, name: str = "a") -> List[dict]:
    fake = Faker("en_US")
    fake.seed_instance(seed)
    rng = random.Random(seed)
    counts: Counter = Counter()
    docs = []
    for i in range(n):
        genre = rng.choice(list(GENRES))
        lines_by_kind, sep = GENRES[genre]
        person = Person(fake, rng)
        text_parts: List[str] = []
        spans: List[Tuple[int, int, str]] = []
        offset = 0
        used: set = set()  # no template twice in one document

        def pick(pool: List[str]) -> str:
            fresh = [t for t in pool if t not in used] or pool
            t = rng.choice(fresh)
            used.add(t)
            return t

        for _ in range(rng.randint(4, 8)):
            if rng.random() < pii_rate:
                # Favour the labels that are still short, so every type reaches a judgeable n.
                kinds = list(lines_by_kind)
                short = [k for k in kinds if counts[_kind_label(k)] < MIN_PER_LABEL]
                kind = rng.choice(short or kinds)
                line, line_spans = render(pick(lines_by_kind[kind]), person)
            else:
                line, line_spans = pick(FILLER[genre]), []
            if text_parts:
                offset += len(sep)
            text_parts.append(line)
            for s, e, l in line_spans:
                spans.append((offset + s, offset + e, l))
                counts[l] += 1
            offset += len(line)
        text = sep.join(text_parts)
        for s, e, l in spans:
            assert text[s:e], (i, s, e, l)
        docs.append({"doc_id": f"{name}-{i:04d}", "text": text, "gold_spans": [list(s) for s in spans],
                     "meta": {"genre": genre, "generator": GENERATOR_VERSION}})
    return docs


def _kind_label(kind: str) -> str:
    return {"name": "NAME_STUDENT", "fullname": "NAME_STUDENT", "lastname": "NAME_STUDENT", "relative": "NAME_RELATED",
            "relative_full": "NAME_RELATED", "teacher": "NAME_RELATED", "friend": "NAME_RELATED", "school": "SCHOOL",
            "town": "LOCATION", "age": "AGE", "age_words": "AGE", "date": "DATE", "phone": "PHONE_NUM", "email": "EMAIL",
            "handle": "USERNAME", "id": "ID_NUM", "address": "STREET_ADDRESS"}[kind]


def review_markdown(name: str, docs: List[dict], k: int, seed: int) -> str:
    rng = random.Random(seed + 1)
    sample = rng.sample(docs, min(k, len(docs)))
    counts = Counter(l for d in docs for _, _, l in d["gold_spans"])
    lines = [f"# {name} draft review", "",
             f"Generated {dt.date.today().isoformat()} by scripts/gen_acceptance_draft.py ({GENERATOR_VERSION}), seed {seed}, "
             f"{len(docs)} documents, {sum(counts.values())} gold spans. {len(sample)} random documents below with gold spans "
             f"marked as `[[LABEL: text]]`.", "",
             "Review for: spans that are wrong or incomplete; a label that misreads the sentence; phrasing that leaks the rule "
             "cues edshield looks for; anything that reads like a real person. Edit the draft jsonl directly, then seal it; "
             "this file and the draft are deleted by sealing.", "",
             "| label | n |", "|---|---|"]
    lines += [f"| {l} | {c} |" for l, c in sorted(counts.items(), key=lambda kv: -kv[1])]
    lines += ["", f"Labels under {MIN_PER_LABEL}: " + (", ".join(l for l in LABELS if counts[l] < MIN_PER_LABEL) or "none"), ""]
    for d in sample:
        text, spans = d["text"], sorted(d["gold_spans"])
        out, pos = [], 0
        for s, e, l in spans:
            out.append(text[pos:s])
            out.append(f"[[{l}: {text[s:e]}]]")
            pos = e
        out.append(text[pos:])
        marked = "".join(out).replace("\n", "  \n")
        lines += [f"## {d['doc_id']} ({d['meta']['genre']})", "", marked, ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="A1, A2, ...")
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=None,
                    help="omit for a fresh private seed (recommended for a set that will be sealed); "
                         "the seed is printed once and never written into the repo")
    ap.add_argument("--review", type=int, default=50)
    ap.add_argument("--out-dir", default=str(SETS_DIR))
    a = ap.parse_args(argv)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / f"{a.name}.jsonl.enc").exists():
        print(f"{a.name} is already sealed; draft the next set instead", file=sys.stderr)
        return 1
    if a.seed is None:
        import secrets

        a.seed = secrets.randbits(31)
        print(f"private seed {a.seed}: keep it with the seal key if you ever need to regenerate; do not commit it",
              file=sys.stderr)
    docs = generate(a.n, a.seed, name=a.name)
    draft = out_dir / f"{a.name}.draft.jsonl"
    with open(draft, "w", encoding="utf-8", newline="\n") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    review = out_dir / f"{a.name}.draft.review.md"
    review.write_text(review_markdown(a.name, docs, a.review, a.seed), encoding="utf-8")
    counts = Counter(l for d in docs for _, _, l in d["gold_spans"])
    print(f"wrote {draft} ({len(docs)} documents, {sum(counts.values())} spans) and {review}")
    for l in LABELS:
        print(f"  {l:16s} {counts[l]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
