"""Component A: an LLM-planted second view of the genre-shift dialogues (brief §2).

    python scripts/plant_llm.py build                      # requests only, no API call
    python scripts/plant_llm.py dry-run [--n 1]            # one request through messages.create
    python scripts/plant_llm.py submit                     # the batch
    python scripts/plant_llm.py collect [--run DIR]        # poll, validate, requeue once, write data/planted_llm/
    python scripts/plant_llm.py status [--run DIR]

Slot decisions (which dialogue gets which identifier kinds, in which turns and
forms, and the name category) come from the sealed deterministic run and are
reused unchanged. The model chooses only the wording and which name from the
category list. Output has the same schema as experiments/genre_shift/plant.py,
so the fixed scorer runs on it unchanged.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import genre_shift_data as gs  # noqa: E402
import platform_api as api  # noqa: E402

ROOT = api.ROOT
OUT = ROOT / "data" / "planted_llm"
PROMPT = (ROOT / "prompts" / "plant_system.md").read_text(encoding="utf-8")
MODEL = api.MODELS["plant"]
MAX_TOKENS = 6000
DOMAINS = ("gmail.com", "yahoo.com", "outlook.com", "icloud.com")
SPEAKER_TAG = {"student": "Student", "tutor": "Tutor"}
NAME_KINDS = ("first", "later", "nickname")

SCHEMA = {
    "type": "object",
    "properties": {
        "student_name": {"type": "string"},
        "related_name": {"type": ["string", "null"]},
        "school": {"type": ["string", "null"]},
        "turns": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "turn_idx": {"type": "integer"},
                "text": {"type": "string"},
                "spans": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"slot_id": {"type": "integer"}, "text": {"type": "string"},
                                   "start": {"type": "integer"}, "end": {"type": "integer"}},
                    "required": ["slot_id", "text", "start", "end"], "additionalProperties": False}},
            },
            "required": ["turn_idx", "text", "spans"], "additionalProperties": False}},
    },
    "required": ["student_name", "related_name", "school", "turns"], "additionalProperties": False,
}


# --- manifest from the sealed run ------------------------------------------------

def name_form(text: str, full: str) -> Tuple[str, bool]:
    """(form, lowercase) of a planted name surface form from the deterministic view.
    Exact match against every form the sealed planter can produce, then a
    one-slip (typo) match, since plant.py applies the typo after choosing the form."""
    first = full.split(" ", 1)[0]
    k = max(2, min(4, len(first) - 1))
    cands = [("full_name", False, full), ("full_name", True, full.lower()), ("initial", False, first[0].upper() + "."),
             ("initial", True, first[0].lower() + "."), ("first_name", False, first), ("first_name", True, first.lower()),
             ("all_caps", False, first.upper()), ("all_caps", True, first.upper().lower()),
             ("truncated", False, first[:k]), ("truncated", True, first[:k].lower())]
    for form, low, c in cands:
        if text == c:
            return form, low
    for form, low, c in cands:
        if _dl1(text, c):
            return form, low
    raise ValueError(f"cannot classify planted form {text!r} of {full!r}")


def manifest_for(doc: dict, plan: dict, dialogue: list) -> dict:
    """Slots the model fills, from the deterministic doc's spans. Persona-name
    occurrences (MathDial) are not slots: the code substitutes them afterwards
    with the model's chosen name in the same forms the sealed run used.

    plant.py never puts a tutor-address slot on a persona turn, and an intro
    phrase is always prepended, so in a persona turn the inserted mention (if
    any) is the first name span and the persona occurrences are the rest."""
    full = plan["name"]
    persona = doc["meta"].get("persona_name")
    turn_text = {t["turn_idx"]: str(t["text"]) for t in dialogue}
    persona_counts: Dict[int, int] = {}
    if persona:
        pat = re.compile(r"\b" + re.escape(persona) + r"\b")
        persona_counts = {i: len(pat.findall(txt)) for i, txt in turn_text.items() if pat.search(txt)}
    plan_slots = {(s["turn"], s["kind"]): s for s in plan["slots"]}
    slots, persona_spans = [], []
    by_turn: Dict[int, List[dict]] = {}
    for s in doc["meta"]["spans"]:
        by_turn.setdefault(s["turn_idx"], []).append(s)
    for i, spans in sorted(by_turn.items()):
        spans = sorted(spans, key=lambda s: s["start"])
        name_spans = [s for s in spans if s["kind"] in NAME_KINDS]
        n_persona = persona_counts.get(i, 0)
        n_inserted = len(name_spans) - n_persona
        expected = int((i, "intro") in plan_slots) + int((i, "tutor_address") in plan_slots)
        if n_inserted != expected:
            raise AssertionError(f"{doc['doc_id']} turn {i}: {len(name_spans)} name spans, {n_persona} persona, plan {expected}")
        inserted = set(id(s) for s in name_spans[:n_inserted])
        for j, s in enumerate(name_spans[n_inserted:]):
            form, low = name_form(s["text"], full)
            persona_spans.append({"turn_idx": i, "occurrence": j, "kind": s["kind"], "form": form, "lowercase": low})
        for s in spans:
            if s["kind"] in NAME_KINDS:
                if id(s) not in inserted:
                    continue
                form, low = name_form(s["text"], full)
                src_slot = plan_slots.get((i, "intro")) or plan_slots.get((i, "tutor_address")) or {}
                slot = {"slot_id": len(slots), "turn_idx": i, "speaker": s["speaker"], "kind": "name",
                        "det_kind": s["kind"], "form": form, "lowercase": low, "typo": False}
                if form == "truncated":
                    slot["k"] = max(2, min(4, len(full.split(" ", 1)[0]) - 1))
                # plant.py's typo() leaves words under 4 characters unchanged even when the plan says typo
                slot["typo"] = bool(src_slot.get("typo")) and len(expected_name(full, slot)) >= 4
                slots.append(slot)
            elif s["kind"] == "related":
                slots.append({"slot_id": len(slots), "turn_idx": i, "speaker": s["speaker"], "kind": "related",
                              "det_kind": "related", "form": "first_name", "lowercase": s["text"][:1].islower(),
                              "typo": bool(plan_slots.get((i, "related"), {}).get("typo"))
                              and len(plan["related"].split(" ", 1)[0]) >= 4})
            else:
                slots.append({"slot_id": len(slots), "turn_idx": i, "speaker": s["speaker"], "kind": s["kind"],
                              "det_kind": s["kind"]})
    return {"dialogue_id": doc["doc_id"], "dataset": doc["meta"]["dataset"], "category": plan["category"],
            "slots": slots, "persona": {"name": persona, "spans": persona_spans} if persona_spans else None,
            "det_name": full, "det_related": plan["related"]}


# --- requests ----------------------------------------------------------------------

def register_anchors(dialogues: list, dataset: str, n: int = 3) -> List[str]:
    rng = random.Random(f"anchors:{dataset}")
    cands = [str(t["text"]) for d in dialogues for t in d if t["speaker"] == "student" and 20 <= len(str(t["text"])) <= 200]
    return rng.sample(cands, min(n, len(cands)))


def build_requests() -> Tuple[List[dict], dict]:
    log = gs.plant_log()
    dialogues = gs.dialogues()
    requests, manifests = [], {}
    for ds in gs.DATASETS:
        if ds not in dialogues:
            continue
        plans = {p["dialogue_id"]: p for p in log["datasets"][ds]["plans"]}
        reg = log["datasets"][ds]["register"]
        by_id = {str(d[0]["dialogue_id"]): d for d in dialogues[ds]}
        anchors = register_anchors(dialogues[ds], ds)
        system = api.cached_system([PROMPT, "Dataset `%s`. Register of student turns: %.0f%% start in lowercase, %.0f%% have no end punctuation. "
                                    "Example student turns from this dataset, verbatim:\n%s" % (
                                        ds, 100 * reg["lowercase_start"], 100 * reg["no_terminal_punct"],
                                        "\n".join(f"- {a}" for a in anchors))])
        for doc in gs.planted(ds):
            did = doc["doc_id"]
            plan, dlg = plans[did], by_id[did]
            m = manifest_for(doc, plan, dlg)
            manifests[did] = m
            if not m["slots"] and not m["persona"]:
                continue
            user = {
                "dialogue_id": did, "category": m["category"],
                "allowed_names": gs.names(m["category"]), "schools": gs.names("schools"),
                "register": reg,
                "turns": [{"turn_idx": t["turn_idx"], "speaker": t["speaker"], "text": t["text"]} for t in dlg],
                "slots": [{k: v for k, v in s.items() if k != "det_kind"} for s in m["slots"]],
            }
            if not m["slots"]:
                # persona-only dialogue: the model just picks the name; no turn is rewritten
                user["note"] = "No slots: choose student_name and related_name from allowed_names and return turns: []."
            requests.append({"custom_id": f"plant-{ds}-{did}", "dataset": ds, "dialogue_id": did,
                             "params": {"model": MODEL, "max_tokens": MAX_TOKENS, "system": system,
                                        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
                                        "messages": [{"role": "user", "content": json.dumps(user, ensure_ascii=False)}]}})
    return requests, manifests


# --- validation ----------------------------------------------------------------------

def _dl1(a: str, b: str) -> bool:
    """Damerau-Levenshtein distance exactly 1 (one swap, drop or double)."""
    if a == b:
        return False
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    if abs(len(a) - len(b)) != 1:
        return False
    s, l = (a, b) if len(a) < len(b) else (b, a)
    return any(l[:i] + l[i + 1:] == s for i in range(len(l)))


def inserted_blocks(orig: str, new: str) -> Optional[List[Tuple[int, int]]]:
    """(start, end) ranges in `new` that were inserted into `orig`, or None when
    the edit is not insert-only (a character of the original changed or vanished).
    One tolerated deviation: the first letter of the original may change case
    when material was prepended ("Priya, how much is 33-28?"); the models do
    this despite the instruction and it alters nothing but that letter's case."""
    import difflib
    sm = difflib.SequenceMatcher(None, orig, new, autojunk=False)
    blocks = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and i1 == 0 and i2 == 1 and j2 - j1 >= 1 and orig[0].isalpha() \
                and new[j2 - 1].lower() == orig[0].lower() and new[j2 - 1] != orig[0]:
            # prepended text plus the case-changed first letter: the insertion is everything before that letter
            if j2 - 1 > j1:
                blocks.append((j1, j2 - 1))
            continue
        if tag != "insert":
            return None
        blocks.append((j1, j2))
    return blocks


def locate(surf: str, text: str, start: int, end: int, blocks: List[Tuple[int, int]], taken: set) -> Optional[Tuple[int, int]]:
    """Where the surface form sits inside inserted material: the model's offsets
    when they resolve there, else the unique whole-word occurrence inside the
    inserted blocks that no other slot has claimed."""
    def inside(a: int, b: int) -> bool:
        return any(x <= a and b <= y for x, y in blocks)

    if 0 <= start < end <= len(text) and text[start:end] == surf and inside(start, end) and (start, end) not in taken:
        return start, end
    cands = [(m.start(), m.end()) for m in re.finditer(r"(?<![\w'’])" + re.escape(surf) + r"(?!\w)", text)
             if inside(m.start(), m.end()) and (m.start(), m.end()) not in taken]
    if len(cands) == 1:
        return cands[0]
    return None


def expected_name(full: str, slot: dict) -> str:
    first = full.split(" ", 1)[0]
    f = slot["form"]
    if f == "full_name":
        s = full
    elif f == "initial":
        s = first[0].upper() + "."
    elif f == "all_caps":
        s = first.upper()
    elif f == "truncated":
        s = first[:slot["k"]]
    else:
        s = first
    return s.lower() if slot.get("lowercase") else s


def validate(resp: dict, m: dict, dialogue: list) -> Tuple[Optional[dict], List[str]]:
    """Check one response against its manifest. Returns (doc, errors)."""
    errs: List[str] = []
    allowed = set(gs.names(m["category"]))
    firsts = {n.split(" ", 1)[0] for n in allowed}
    lasts = {n.split(" ", 1)[1] for n in allowed if " " in n}

    def name_ok(n: str) -> bool:
        # the category is a property of the first name; a full name may pair any first and last name of the list
        if n in allowed:
            return True
        parts = n.split(" ", 1)
        return len(parts) == 2 and parts[0] in firsts and parts[1] in lasts

    schools = set(gs.names("schools"))
    student = resp.get("student_name") or ""
    related = resp.get("related_name")
    if not name_ok(student):
        errs.append(f"student_name {student!r} not in allowed_names")
    need_related = any(s["kind"] == "related" for s in m["slots"])
    if need_related and (not related or not name_ok(related) or related.split(" ")[0] == student.split(" ")[0]):
        errs.append(f"related_name {related!r} invalid")
    first = student.split(" ", 1)[0] if student else ""
    last = student.split(" ", 1)[1] if " " in student else ""
    rfirst = (related or "").split(" ", 1)[0]
    turn_text = {t["turn_idx"]: str(t["text"]) for t in dialogue}
    speaker = {t["turn_idx"]: t["speaker"] for t in dialogue}
    slots = {s["slot_id"]: s for s in m["slots"]}
    slot_turn = {s["slot_id"]: s["turn_idx"] for s in m["slots"]}
    need_turns = set(slot_turn.values())
    got_turns = {t["turn_idx"] for t in resp.get("turns", [])}
    if got_turns != need_turns:
        errs.append(f"turns returned {sorted(got_turns)} != slots' turns {sorted(need_turns)}")
    seen_slots = set()
    new_turns: Dict[int, Tuple[str, List[tuple]]] = {}
    for t in resp.get("turns", []):
        i, text = t["turn_idx"], t["text"]
        if i not in turn_text:
            errs.append(f"turn {i} does not exist")
            continue
        orig = turn_text[i]
        blocks = inserted_blocks(orig, text)
        n_slots_here = sum(1 for sid, ti in slot_turn.items() if ti == i)
        if blocks is None:
            errs.append(f"turn {i}: original text not preserved verbatim")
            continue
        if len(blocks) > n_slots_here + 1:
            errs.append(f"turn {i}: {len(blocks)} separate insertions for {n_slots_here} slots")
            continue
        local: List[tuple] = []
        taken: set = set()
        for sp in t["spans"]:
            sid = sp["slot_id"]
            if sid not in slots or slot_turn[sid] != i:
                errs.append(f"turn {i}: unknown slot {sid}")
                continue
            if sid in seen_slots:
                errs.append(f"slot {sid} filled twice")
                continue
            seen_slots.add(sid)
            surf = sp["text"]
            loc = locate(surf, text, sp["start"], sp["end"], blocks, taken)
            if loc is None:
                errs.append(f"slot {sid}: surface {surf!r} not found exactly once inside the inserted material of turn {i}")
                continue
            s, e = loc
            taken.add(loc)
            slot = slots[sid]
            k = slot["kind"]
            if k in ("name", "related"):
                exp = expected_name(student if k == "name" else related or "", slot) if (k == "name" or related) else ""
                if slot.get("typo"):
                    ok = _dl1(surf, exp) and surf != exp
                else:
                    ok = surf == exp
                if not ok:
                    errs.append(f"slot {sid}: surface {surf!r} != expected form {exp!r} (typo={slot.get('typo', False)})")
            elif k == "school":
                if surf not in schools:
                    errs.append(f"slot {sid}: school {surf!r} not in list")
            elif k == "email":
                mm = re.fullmatch(r"[A-Za-z0-9._+-]+@([A-Za-z0-9.-]+)", surf)
                frag = any(x and x.lower()[:3] in surf.lower() for x in (first, last))
                if not mm or mm.group(1).lower() not in DOMAINS or not frag:
                    errs.append(f"slot {sid}: email {surf!r} invalid")
            elif k == "username":
                frag = any(x and x.lower()[:3] in surf.lower() for x in (first, last))
                if not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", surf) or "@" in surf or not frag:
                    errs.append(f"slot {sid}: username {surf!r} invalid")
            elif k == "phone":
                digits = re.sub(r"\D", "", surf)
                digits = digits[1:] if len(digits) == 11 and digits[0] == "1" else digits
                if len(digits) != 10 or not ((digits[3:6] == "555" and digits[6:8] == "01") or digits[:3] == "555"):
                    errs.append(f"slot {sid}: phone {surf!r} not a fictional 555 number")
            local.append((s, e, slot["det_kind"], surf, sid))
        # slots the model filled in the text but left out of `spans`: locate the expected surface form ourselves
        for sid, ti in slot_turn.items():
            if ti != i or sid in seen_slots:
                continue
            slot = slots[sid]
            k = slot["kind"]
            cand: Optional[str] = None
            if k in ("name", "related"):
                who = student if k == "name" else related
                cand = expected_name(who, slot) if who and not slot.get("typo") else None
            elif k == "school":
                hits = [sc for sc in schools if locate(sc, text, -1, -1, blocks, taken)]
                cand = hits[0] if len(hits) == 1 else None
            else:
                pat = {"email": r"[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "phone": r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
                       "username": r"@?[A-Za-z0-9_.-]{3,30}"}[k]
                hits = [mm.group().lstrip("@") for mm in re.finditer(pat, text)
                        if any(x <= mm.start() and mm.end() <= y for x, y in blocks)]
                if k == "username":
                    hits = [h for h in hits if any(x and x.lower()[:3] in h.lower() for x in (first, last)) and "@" not in h]
                cand = hits[0] if len(hits) == 1 else None
            if cand:
                loc = locate(cand, text, -1, -1, blocks, taken)
                if loc:
                    seen_slots.add(sid)
                    taken.add(loc)
                    local.append((loc[0], loc[1], slot["det_kind"], cand, sid))
                    # contact values still go through the format checks below
                    if k == "email":
                        mm = re.fullmatch(r"[A-Za-z0-9._+-]+@([A-Za-z0-9.-]+)", cand)
                        if not mm or mm.group(1).lower() not in DOMAINS:
                            errs.append(f"slot {sid}: email {cand!r} invalid")
                    elif k == "phone":
                        digits = re.sub(r"\D", "", cand)
                        if len(digits) != 10 or not ((digits[3:6] == "555" and digits[6:8] == "01") or digits[:3] == "555"):
                            errs.append(f"slot {sid}: phone {cand!r} not a fictional 555 number")
        new_turns[i] = (text, local)
    typo_slots = {s["slot_id"] for s in m["slots"] if s.get("typo")}
    missing = set(slots) - seen_slots
    if missing:
        errs.append(f"slots not filled: {sorted(missing)}")
    if errs:
        return None, errs
    # persona substitution (MathDial): every whole-word occurrence becomes the chosen name in the sealed forms
    persona_local: Dict[int, List[tuple]] = {}
    if m.get("persona"):
        pname = m["persona"]["name"]
        pat = re.compile(r"\b" + re.escape(pname) + r"\b")
        forms = {}
        for ps in m["persona"]["spans"]:
            forms.setdefault(ps["turn_idx"], []).append(ps)
        for i, plist in forms.items():
            text, local = new_turns.get(i, (turn_text[i], []))
            out, posn, spans2, j = "", 0, [], 0
            shifts = []
            for mt in pat.finditer(text):
                ps = plist[j] if j < len(plist) else plist[-1]
                shown = expected_name(student, {"form": ps["form"], "lowercase": ps["lowercase"], "k": max(2, min(4, len(first) - 1))})
                out += text[posn:mt.start()]
                spans2.append((len(out), len(out) + len(shown), ps["kind"], shown, None))
                shifts.append((mt.start(), len(shown) - (mt.end() - mt.start())))
                out += shown
                posn = mt.end()
                j += 1
            out += text[posn:]
            if j != len(plist):
                return None, [f"turn {i}: persona occurrences {j} != sealed {len(plist)}"]
            # shift the model's spans in this turn past replaced occurrences
            adj = []
            for s, e, kind, surf, sid in local:
                delta = sum(d for p, d in shifts if p < s)
                adj.append((s + delta, e + delta, kind, surf, sid))
            new_turns[i] = (out, adj + spans2)
    # assemble exactly like plant.py
    parts, gold, meta_spans, offset = [], [], [], 0
    for t in dialogue:
        i = t["turn_idx"]
        text, local = new_turns.get(i, (turn_text[i], []))
        tag = SPEAKER_TAG[str(t["speaker"])]
        line = f"{tag}: {text}"
        head = len(tag) + 2
        for s, e, kind, surf, sid in sorted(local):
            gs_, ge = offset + head + s, offset + head + e
            gold.append([gs_, ge, gs.LABELS[kind]])
            meta_spans.append({"start": gs_, "end": ge, "label": gs.LABELS[kind], "kind": kind, "text": surf,
                               "speaker": t["speaker"], "turn_idx": i, "typo": sid in typo_slots})
        parts.append(line)
        offset += len(line) + 1
    doc_text = "\n".join(parts)
    for g, ms in zip(gold, meta_spans):
        if doc_text[g[0]:g[1]] != ms["text"]:
            return None, [f"assembly offset mismatch at {g}"]
    meta0 = dialogue[0].get("meta") or {}
    return {"doc_id": m["dialogue_id"], "text": doc_text, "gold_spans": gold,
            "meta": {"dataset": m["dataset"], "category": m["category"], "name": student, "related": related,
                     "spans": meta_spans, "persona_name": meta0.get("persona_name"),
                     "problem_names": meta0.get("problem_names", []), "view": "llm", "model": MODEL}}, []


# --- modes ------------------------------------------------------------------------------

def save_requests(requests: List[dict], manifests: dict, run_dir: Path) -> None:
    api.write_jsonl(requests, run_dir / "plant_requests_built.jsonl")
    (run_dir / "plant_manifests.json").write_text(json.dumps(manifests, ensure_ascii=False), encoding="utf-8")
    n_slots = sum(len(m["slots"]) for m in manifests.values())
    est_in = sum(len(json.dumps(r["params"]["messages"])) for r in requests) / 4 + len(PROMPT) / 4
    print(f"built {len(requests)} requests, {n_slots} slots; ~{est_in / 1e3:.0f}k input tokens before caching")


def cmd_build(args) -> int:
    run_dir = Path(args.run) if args.run else api.new_run_dir("plant")
    requests, manifests = build_requests()
    save_requests(requests, manifests, run_dir)
    print(f"run dir {run_dir}")
    return 0


def cmd_dry_run(args) -> int:
    run_dir = Path(args.run) if args.run else api.new_run_dir("plant-dryrun")
    requests, manifests = build_requests()
    save_requests(requests, manifests, run_dir)
    client = api.make_client()
    dialogues = gs.dialogues()
    rng = random.Random(0)
    for req in rng.sample(requests, args.n):
        row = api.dry_run(client, req, run_dir, f"plant-{req['dialogue_id']}")
        resp = api.extract_json(row["text"])
        by_id = {str(d[0]["dialogue_id"]): d for d in dialogues[req["dataset"]]}
        doc, errs = validate(resp, manifests[req["dialogue_id"]], by_id[req["dialogue_id"]])
        print("validation:", "OK" if doc else errs)
        if doc:
            print(json.dumps({"doc_id": doc["doc_id"], "name": doc["meta"]["name"], "spans": doc["meta"]["spans"]}, ensure_ascii=False)[:1500])
    return 0


def cmd_submit(args) -> int:
    run_dir = Path(args.run) if args.run else api.new_run_dir("plant")
    requests, manifests = build_requests()
    save_requests(requests, manifests, run_dir)
    client = api.make_client()
    api.submit_batch(client, requests, run_dir, "plant")
    return 0


def cmd_collect(args) -> int:
    run_dir = Path(args.run) if args.run else api.latest_run_dir("plant")
    if run_dir is None:
        raise SystemExit("no plant run directory")
    client = api.make_client()
    manifests = json.loads((run_dir / "plant_manifests.json").read_text(encoding="utf-8"))
    requests = {r["custom_id"]: r for r in api.read_jsonl(run_dir / "plant_requests_built.jsonl")}
    dialogues = gs.dialogues()
    docs: Dict[str, List[dict]] = {ds: [] for ds in gs.DATASETS}
    rejects: List[dict] = []
    accepted: Dict[str, dict] = {}

    def handle(results: Dict[str, dict], attempt: int) -> List[dict]:
        retry = []
        for cid, row in results.items():
            req = requests[cid]
            did, ds = req["dialogue_id"], req["dataset"]
            by_id = {str(d[0]["dialogue_id"]): d for d in dialogues[ds]}
            errs: List[str]
            doc = None
            if row["type"] != "succeeded":
                errs = [f"batch result {row['type']}: {row.get('error')}"]
            else:
                try:
                    resp = api.extract_json(row["text"])
                    doc, errs = validate(resp, manifests[did], by_id[did])
                except Exception as exc:  # noqa: BLE001
                    errs = [f"unparseable output: {exc}"]
            if doc:
                accepted[did] = doc
            elif attempt == 0:
                r2 = json.loads(json.dumps(req))
                r2["custom_id"] = cid + "-retry"
                r2["params"]["messages"][0]["content"] += "\n\nA previous attempt was rejected by the validator: " + "; ".join(errs)[:1500]
                requests[r2["custom_id"]] = r2
                retry.append(r2)
            else:
                rejects.append({"custom_id": cid, "dialogue_id": did, "dataset": ds, "errors": errs, "attempt": attempt})
        return retry

    meta = api.batch_meta(run_dir, "plant")
    api.wait_batch(client, meta["id"], poll_seconds=args.poll)
    results = api.collect_batch(client, meta["id"], run_dir, "plant", MODEL)
    retry = handle(results, 0)
    if retry:
        if (run_dir / "batch_plant-retry.json").exists():
            bid = api.batch_meta(run_dir, "plant-retry")["id"]
            print(f"{len(retry)} dialogues still rejected; retry batch {bid} was already submitted, collecting it")
        else:
            print(f"re-queueing {len(retry)} rejected dialogues once")
            bid = api.submit_batch(client, retry, run_dir, "plant-retry")
        api.wait_batch(client, bid, poll_seconds=args.poll)
        results2 = api.collect_batch(client, bid, run_dir, "plant-retry", MODEL)
        results2 = {k[:-len("-retry")]: v for k, v in results2.items()}
        # map back to the original request ids for validation
        for cid, row in results2.items():
            requests[cid + "-retry"]["dialogue_id"] = requests[cid]["dialogue_id"]
        handle({k + "-retry": v for k, v in results2.items()}, 1)
    api.write_jsonl(rejects, run_dir / "plant_rejects.jsonl")
    for did, doc in accepted.items():
        docs[doc["meta"]["dataset"]].append(doc)
    OUT.mkdir(parents=True, exist_ok=True)
    log = {"view": "llm", "model": MODEL, "run_dir": str(run_dir.relative_to(ROOT)), "batch_ids": [meta["id"]],
           "prompt_sha256": api.sha256_text(PROMPT), "dropped": len(rejects), "datasets": {}}
    if retry:
        log["batch_ids"].append(api.batch_meta(run_dir, "plant-retry")["id"])
    for ds in gs.DATASETS:
        rows = sorted(docs[ds], key=lambda d: d["doc_id"])
        if not rows and ds not in dialogues:
            continue
        api.write_jsonl(rows, OUT / f"{ds}.jsonl")
        api.write_jsonl([{"doc_id": d["doc_id"], "category": d["meta"]["category"], "name": d["meta"]["name"],
                          "related": d["meta"]["related"], "spans": d["meta"]["spans"],
                          "text_sha256": api.sha256_text(d["text"])} for d in rows], OUT / f"{ds}.spans.jsonl")
        kinds: Dict[str, int] = {}
        for d in rows:
            for s in d["meta"]["spans"]:
                kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
        cats: Dict[str, int] = {}
        for d in rows:
            cats[d["meta"]["category"]] = cats.get(d["meta"]["category"], 0) + 1
        log["datasets"][ds] = {"dialogues": len(rows), "dropped": sum(1 for r in rejects if r["dataset"] == ds),
                               "spans_by_kind": kinds, "dialogues_by_category": cats}
        print(f"{ds:10s} dialogues {len(rows):4d}  gold spans {sum(kinds.values()):5d}  {kinds}")
    (OUT / "plant_llm_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(f"dropped {len(rejects)} dialogues after one retry -> {run_dir / 'plant_rejects.jsonl'}")
    return 0


def cmd_status(args) -> int:
    run_dir = Path(args.run) if args.run else api.latest_run_dir("plant")
    client = api.make_client()
    for name in ("plant", "plant-retry"):
        if (run_dir / f"batch_{name}.json").exists():
            b = client.messages.batches.retrieve(api.batch_meta(run_dir, name)["id"])
            print(name, b.id, b.processing_status, b.request_counts)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["build", "dry-run", "submit", "collect", "status"])
    ap.add_argument("--run", help="run directory (default: new, or latest for collect/status)")
    ap.add_argument("--n", type=int, default=1, help="dry-run: how many requests")
    ap.add_argument("--poll", type=int, default=60)
    args = ap.parse_args(argv)
    return {"build": cmd_build, "dry-run": cmd_dry_run, "submit": cmd_submit, "collect": cmd_collect, "status": cmd_status}[args.mode](args)


if __name__ == "__main__":
    raise SystemExit(main())
