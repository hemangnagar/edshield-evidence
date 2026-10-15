"""Component C driver: one bounded Managed Agents session (brief §4.4-4.5).

    python scripts/run_agent_loop.py --dry-run             # print what would be created/sent; no API call
    python scripts/run_agent_loop.py                        # create env+agent (idempotent), session with budget, drive it
    python scripts/run_agent_loop.py --resume SESSION_ID    # re-attach to a session and keep logging
    python scripts/run_agent_loop.py --retrieve SESSION_ID  # only pull /mnt/session/outputs/ into proposals/ and results/candidate/

Every event of the session is appended to runs/<ts>-agent/agent_events.jsonl.
SESSION.json records ids, stop_reason, the session.usage event (tokens,
list_cost, active_seconds) and how the session ended. The agent's deliverables
are retrieved through the Files API (outputs.tar.gz written to
/mnt/session/outputs/), with a fallback that extracts ```file:<path> blocks
from the agent's final messages.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Dict, List, Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_api as api  # noqa: E402

ROOT = api.ROOT
AGENT_MD = ROOT / "agents" / "rule_proposer.md"
SYSTEM_MD = ROOT / "prompts" / "agent_system.md"
ENV_YAML = ROOT / "environments" / "eval.yaml"
SETUP_MD = ROOT / "prompts" / "agent_setup_message.md"
TASK_MD = ROOT / "prompts" / "agent_task_message.md"
IDS = ROOT / "runs" / "agent_ids.json"
BETA = ["managed-agents-2026-04-01"]
UPLOADS = [("planted", ROOT / "experiments" / "genre_shift" / "data" / "planted"),
           ("control", ROOT / "experiments" / "genre_shift" / "data" / "control"),
           ("planted_llm", ROOT / "data" / "planted_llm")]
FILE_BLOCK = re.compile(r"```file:([^\s`]+)\n(.*?)```", re.S)


def frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise SystemExit(f"{path} has no YAML frontmatter")
    return yaml.safe_load(m.group(1)), m.group(2).lstrip("\n")


def write_agent_md() -> None:
    fm_raw = AGENT_MD.read_text(encoding="utf-8").split("\n---\n", 1)[0]
    AGENT_MD.write_text(fm_raw + "\n---\n\n" + SYSTEM_MD.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"regenerated {AGENT_MD}")


def agent_spec() -> dict:
    fm, body = frontmatter(AGENT_MD)
    system = SYSTEM_MD.read_text(encoding="utf-8")
    if body.strip() != system.strip():
        raise SystemExit("agents/rule_proposer.md body differs from prompts/agent_system.md; run `make agent-md`")
    return {"name": fm["name"], "description": fm.get("description"), "model": fm["model"], "system": system, "tools": fm["tools"]}


def env_spec() -> dict:
    return yaml.safe_load(ENV_YAML.read_text(encoding="utf-8"))


def spec_hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def current_branch() -> str:
    return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()


def ensure_resources(client, dry: bool) -> Dict[str, str]:
    """Environment and agent, reused from runs/agent_ids.json when their definitions are unchanged."""
    ids = json.loads(IDS.read_text(encoding="utf-8")) if IDS.exists() else {}
    a, e = agent_spec(), env_spec()
    ah, eh = spec_hash(a), spec_hash(e)
    out = {}
    if ids.get("environment", {}).get("hash") == eh:
        out["environment_id"] = ids["environment"]["id"]
    elif dry:
        out["environment_id"] = "env_DRYRUN"
    else:
        env = client.beta.environments.create(name=e["name"], config=e["config"])
        ids["environment"] = {"id": env.id, "hash": eh, "created_at": str(env.created_at)}
        out["environment_id"] = env.id
        print(f"created environment {env.id}")
    if ids.get("agent", {}).get("hash") == ah:
        out["agent_id"], out["agent_version"] = ids["agent"]["id"], ids["agent"]["version"]
    elif dry:
        out["agent_id"], out["agent_version"] = "agent_DRYRUN", 1
    else:
        if ids.get("agent"):
            ag = client.beta.agents.update(ids["agent"]["id"], name=a["name"], description=a["description"], model=a["model"],
                                           system=a["system"], tools=a["tools"])
            print(f"updated agent {ag.id} -> version {ag.version}")
        else:
            ag = client.beta.agents.create(name=a["name"], description=a["description"], model=a["model"], system=a["system"], tools=a["tools"])
            print(f"created agent {ag.id} version {ag.version}")
        ids["agent"] = {"id": ag.id, "version": ag.version, "hash": ah, "created_at": str(ag.created_at)}
        out["agent_id"], out["agent_version"] = ag.id, ag.version
    if not dry:
        IDS.parent.mkdir(exist_ok=True)
        IDS.write_text(json.dumps(ids, indent=1), encoding="utf-8")
    return out


def upload_inputs(client, dry: bool) -> List[dict]:
    resources = []
    for mount, d in UPLOADS:
        files = sorted(d.glob("*.jsonl"))
        if not files:
            msg = f"nothing to upload from {d} (run `make plant-check` / plant_llm.py collect first)"
            if dry:
                print("dry run:", msg)
                continue
            raise SystemExit(msg)
        for f in files:
            if dry:
                fid = f"file_DRYRUN_{f.stem}"
            else:
                with f.open("rb") as fh:
                    fid = client.beta.files.upload(file=fh).id
            resources.append({"type": "file", "file_id": fid, "mount_path": f"/{mount}/{f.name}"})
    print(f"{'would upload' if dry else 'uploaded'} {len(resources)} files")
    return resources


def event_record(ev) -> dict:
    try:
        return ev.to_dict()
    except Exception:  # noqa: BLE001
        return json.loads(json.dumps(ev, default=str))


def drive(client, session_id: str, run_dir: Path, messages: List[str], state: dict) -> dict:
    """Stream-first; send each message when the agent goes idle with end_turn; log every
    event. A dropped SSE stream is reconnected: the event history is re-read through
    events.list() and deduplicated on event id, so nothing is missed (lossless reconnect)."""
    log = run_dir / "agent_events.jsonl"
    pending = list(messages)
    final_texts: List[str] = []
    seen: set = set()
    sent_first = False

    def send(text: str) -> None:
        client.beta.sessions.events.send(session_id=session_id, events=[{"type": "user.message", "content": [{"type": "text", "text": text}]}])
        state["messages_sent"] = state.get("messages_sent", 0) + 1

    def handle(ev) -> Optional[str]:
        """Returns 'break' when the session is done, else None."""
        rec = event_record(ev)
        eid = rec.get("id")
        if eid and eid in seen:
            return None
        if eid:
            seen.add(eid)
        api.append_jsonl(rec, log)
        t = ev.type
        if t == "agent.message":
            txt = "".join(getattr(b, "text", "") for b in ev.content if getattr(b, "type", "") == "text")
            final_texts.append(txt)
            print(f"[agent] {txt[:300]}", file=sys.stderr)
        elif t in ("agent.tool_use", "agent.mcp_tool_use") and getattr(ev, "evaluated_permission", None) == "ask":
            client.beta.sessions.events.send(session_id=session_id, events=[{
                "type": "user.tool_confirmation", "tool_use_id": ev.id, "result": "deny",
                "deny_message": "This run is unattended; no human can approve tool calls. Use an approach that needs no confirmation or stop."}])
            state["denied_asks"] = state.get("denied_asks", 0) + 1
        elif t == "session.usage":
            state["usage"] = rec.get("usage") or {k: v for k, v in rec.items() if k not in ("type", "id")}
        elif t == "session.error":
            state.setdefault("errors", []).append(rec)
            print(f"[error] {rec}", file=sys.stderr)
        elif t == "session.status_idle":
            sr = rec.get("stop_reason") or {}
            srt = sr.get("type") if isinstance(sr, dict) else getattr(sr, "type", None)
            state["stop_reason"] = srt
            print(f"[idle] stop_reason={srt}", file=sys.stderr)
            if srt == "requires_action":
                return None
            if srt == "end_turn" and pending:
                send(pending.pop(0))
                return None
            state["ended"] = {"end_turn": "normal finish", "budget_reached": "budget pause", "retries_exhausted": "error"}.get(srt, srt)
            return "break"
        elif t == "session.status_terminated":
            state["ended"] = "terminated"
            return "break"
        return None

    attempts = 0
    while True:
        try:
            with client.beta.sessions.events.stream(session_id=session_id) as stream:
                if attempts:
                    # history first, then the live tail (dedup on id); only events of our own turns matter here
                    for ev in client.beta.sessions.events.list(session_id=session_id):
                        if handle(ev) == "break":
                            state["final_messages"] = final_texts[-3:]
                            return state
                if not sent_first and pending:
                    send(pending.pop(0))
                    sent_first = True
                for ev in stream:
                    if handle(ev) == "break":
                        state["final_messages"] = final_texts[-3:]
                        return state
            # the stream closed without a terminal event: reconnect unless the session is idle
            st = client.beta.sessions.retrieve(session_id=session_id).status
            print(f"[stream closed] session status {st}; reconnecting", file=sys.stderr)
            if st in ("terminated",):
                state["ended"] = "terminated"
                break
        except Exception as exc:  # noqa: BLE001
            print(f"[stream error] {exc}; reconnecting", file=sys.stderr)
        attempts += 1
        state["reconnects"] = attempts
        if attempts > 200:
            state["ended"] = "gave up reconnecting"
            break
        time.sleep(min(30, 5 * attempts))
    state["final_messages"] = final_texts[-3:]
    return state


def retrieve_outputs(client, session_id: str, run_dir: Path, final_texts: List[str]) -> dict:
    got = {"files": [], "extracted": [], "fallback_blocks": []}
    dest = run_dir / "outputs"
    dest.mkdir(exist_ok=True)
    for attempt in range(5):
        files = list(client.beta.files.list(scope_id=session_id, betas=BETA))
        if files:
            break
        time.sleep(3)
    import anthropic
    for f in files:
        try:
            content = client.beta.files.download(f.id, betas=BETA)
        except anthropic.BadRequestError as exc:
            # the session-scoped listing also holds the mounted input files, which are not downloadable
            got.setdefault("skipped", []).append({"file": f.filename, "id": f.id, "error": str(exc)[:120]})
            continue
        path = dest / f.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        content.write_to_file(str(path))
        got["files"].append(f.filename)
    tgz = dest / "outputs.tar.gz"
    if tgz.exists():
        with tarfile.open(tgz) as tf:
            for m in tf.getmembers():
                name = m.name.lstrip("./")
                if not (name.startswith("proposals/") or name.startswith("results/candidate/") or name.startswith("results/llm_view/")) or "/raw/" in name or ".." in name:
                    continue
                if m.isfile():
                    data = tf.extractfile(m).read()
                    target = ROOT / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    got["extracted"].append(name)
    if not got["extracted"]:
        for txt in final_texts:
            for path, body in FILE_BLOCK.findall(txt):
                if path.startswith("proposals/") and ".." not in path:
                    target = ROOT / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(body, encoding="utf-8")
                    got["fallback_blocks"].append(path)
    print(f"retrieved files {got['files']}, extracted {len(got['extracted'])} paths, fallback blocks {got['fallback_blocks']}")
    return got


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--write-agent-md", action="store_true")
    ap.add_argument("--phase", choices=["setup", "task", "both"], default="both",
                    help="setup: create the session, send the setup message, retrieve baselines; task: send the task message to --session")
    ap.add_argument("--session", metavar="SESSION_ID", help="existing session for --phase task")
    ap.add_argument("--resume", metavar="SESSION_ID")
    ap.add_argument("--message", metavar="TEXT_OR_FILE", help="with --session: send this follow-up message, stream to idle, retrieve outputs")
    ap.add_argument("--retrieve", metavar="SESSION_ID")
    ap.add_argument("--budget-cents", default="3000", help="hard session cap at list price, in cents (brief: $30)")
    ap.add_argument("--branch", default=None, help="edshield-evidence branch the sandbox clones (default: current)")
    ap.add_argument("--runtime", default="onnx", choices=["python", "onnx"],
                    help="onnx: INT8 export under onnxruntime (no torch needed); python: fp32 torch, closest to the sealed GPU run")
    ap.add_argument("--title", default="edshield rule-proposal loop")
    args = ap.parse_args(argv)
    if args.write_agent_md:
        write_agent_md()
        return 0
    branch = args.branch or current_branch()
    setup = SETUP_MD.read_text(encoding="utf-8").replace("{branch}", branch).replace("{runtime}", args.runtime)
    task = TASK_MD.read_text(encoding="utf-8").replace("{runtime}", args.runtime).replace("{budget_usd}", f"{int(args.budget_cents) / 100:.0f}")
    client = api.make_client(require_key=not args.dry_run)
    run_dir = api.new_run_dir("agent" + ("-dryrun" if args.dry_run else ""))
    state: dict = {"branch": branch, "runtime": args.runtime, "budget_cents": args.budget_cents, "run_dir": str(run_dir)}
    if args.retrieve:
        got = retrieve_outputs(client, args.retrieve, run_dir, [])
        (run_dir / "SESSION.json").write_text(json.dumps({"session_id": args.retrieve, "retrieved": got}, indent=1), encoding="utf-8")
        return 0
    if args.resume:
        session_id = args.resume
        state["session_id"] = session_id
        drive(client, session_id, run_dir, [], state)
    elif args.message:
        if not args.session:
            raise SystemExit("--message needs --session SESSION_ID")
        session_id = args.session
        text = Path(args.message).read_text(encoding="utf-8") if Path(args.message).exists() else args.message
        text = text.replace("{runtime}", args.runtime).replace("{branch}", branch)
        state["session_id"], state["phase"] = session_id, "message"
        (run_dir / "message.md").write_text(text, encoding="utf-8")
        drive(client, session_id, run_dir, [text], state)
    elif args.phase == "task":
        if not args.session:
            raise SystemExit("--phase task needs --session SESSION_ID")
        session_id = args.session
        state["session_id"] = session_id
        state["phase"] = "task"
        (run_dir / "task_message.md").write_text(task, encoding="utf-8")
        drive(client, session_id, run_dir, [task], state)
    else:
        ids = ensure_resources(client, args.dry_run)
        resources = upload_inputs(client, args.dry_run)
        state.update(ids)
        budget = {"type": "limit", "max_list_cost": {"amount": str(int(args.budget_cents)), "currency": "USD"}}
        (run_dir / "setup_message.md").write_text(setup, encoding="utf-8")
        (run_dir / "task_message.md").write_text(task, encoding="utf-8")
        if args.dry_run:
            print(json.dumps({"agent": {k: v for k, v in agent_spec().items() if k != "system"}, "environment": env_spec(),
                              "session": {"agent": ids, "budget": budget, "title": args.title, "resources": resources}}, indent=1))
            print("--- setup message ---\n" + setup + "\n--- task message ---\n" + task)
            (run_dir / "SESSION.json").write_text(json.dumps({**state, "dry_run": True}, indent=1), encoding="utf-8")
            return 0
        session = client.beta.sessions.create(
            agent={"type": "agent", "id": ids["agent_id"], "version": ids["agent_version"]},
            environment_id=ids["environment_id"], title=args.title, budget=budget, resources=resources,
            metadata={"branch": branch, "component": "C"})
        session_id = session.id
        state["session_id"] = session_id
        state["console"] = f"https://platform.claude.com/workspaces/default/sessions/{session_id}"
        print(f"session {session_id} status {session.status}; trace: {state['console']}")
        state["phase"] = args.phase
        (run_dir / "SESSION.json").write_text(json.dumps(state, indent=1), encoding="utf-8")
        drive(client, session_id, run_dir, [setup] if args.phase == "setup" else [setup, task], state)
    s = client.beta.sessions.retrieve(session_id=session_id)
    state["final_status"] = s.status
    if getattr(s, "usage", None):
        state["usage"] = s.usage.to_dict() if hasattr(s.usage, "to_dict") else dict(s.usage)
    state["retrieved"] = retrieve_outputs(client, session_id, run_dir, state.get("final_messages", []))
    (run_dir / "SESSION.json").write_text(json.dumps(state, indent=1, default=str), encoding="utf-8")
    md = [f"# Agent session {session_id}", "", f"- ended: **{state.get('ended')}** (stop_reason `{state.get('stop_reason')}`, status `{s.status}`)",
          f"- usage: `{json.dumps(state.get('usage'), default=str)}`", f"- budget: {int(args.budget_cents) / 100:.2f} USD at list price",
          f"- events log: `{(run_dir / 'agent_events.jsonl').relative_to(ROOT)}`", f"- retrieved: {state['retrieved']}",
          f"- console: {state.get('console', '')}", ""]
    (run_dir / "SESSION.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
