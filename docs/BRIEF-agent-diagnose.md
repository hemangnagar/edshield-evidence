# Handoff brief: edshield agent-assisted diagnosis (`exp/agent-diagnose`)

**Repo:** `hemangnagar/edshield-evidence` — new branch `exp/agent-diagnose`, branched from `exp/genre-shift-planted` once that branch is pushed (see §1 and §5 for sequencing).
**Purpose:** take the deterministic genre-shift experiment already running on Hemang's desktop and add the three things it cannot produce on its own: (A) a second, LLM-planted view of the same dialogues that does not share a generator with the templates; (B) a cause label for every miss in the failure table; (C) one bounded, agent-run evaluate → diagnose → propose loop that yields rule-level fix proposals, re-scored against the pinned baseline, for human review. Output feeds the NSF Phase I response (3,500-character field) and the full proposal.
**Who pays for what:** this is the important constraint. The work that requires judgment — planting, diagnosis, the improve loop — must run as **API calls against the Claude Platform** (Message Batches API and Claude Managed Agents) using `ANTHROPIC_API_KEY` from the org holding the platform credits. Claude Code's job is to write the pipeline, run it, commit outputs, and open the PR. **Claude Code must not do the planting or the diagnosis itself by reading the data and reasoning in-session.** If a step is judgment-shaped and isn't an API call, it's in the wrong place.

Honest results in either direction are the deliverable. Do not tune anything to make numbers look better.

---

## 0. Non-negotiables

1. **Do not touch the sealed run.** `exp/genre-shift-planted` (deterministic `plant.py`, seed `20261014`, edshield 0.2.0 inference) is the reference. Nothing on this branch rewrites its planted sets, gold spans, scoring code, or ledger rows. Baseline numbers come from its outputs, never recomputed here.
2. **Do not modify `model-evidence` or `edshield` on their main branches.** Pins stay: `edshield==0.2.0` for every *baseline* number; `model-evidence` at the tag the repo already uses. Candidate patches (component C) live on a throwaway branch of a local edshield checkout and are delivered as `.patch` files, never pushed to `hemangnagar/edshield`.
3. **Fixed scoring code.** `edshield_evidence/` scorers, the planted sets under `data/planted/`, and anything under `data/sealed/` are read-only to the agent. The driver enforces this with a post-session diff check (§4.6).
4. **Every API call is logged.** Request and response JSONL for each batch and the full event log for the agent session go in `runs/<timestamp>/`. Reproducibility and auditability are the point.
5. **No `ledger pin`.** Reserved for Hemang. Leave targets unpinned.
6. **Deadline:** all batches submitted by **Oct 18**; agent session finished by **Oct 19**. Platform credits expire **Oct 20**. The NSF response does not wait on this branch — if something isn't done, it goes in the full proposal instead.

---

## 1. Setup

```bash
git clone --recurse-submodules https://github.com/hemangnagar/edshield-evidence
cd edshield-evidence
git fetch origin && git checkout exp/genre-shift-planted && git checkout -b exp/agent-diagnose
pip install -e '.[hf]' anthropic
```

If `exp/genre-shift-planted` is not on GitHub yet, stop at scaffolding (§2–§4 code, no submissions) and write `WAITING.md` saying what's needed: the pushed branch with `data/normalized/`, `data/planted/`, and `results/failure_table.jsonl`.

**Key check (do this first, it's cheap):**

```python
from anthropic import Anthropic
c = Anthropic()  # reads ANTHROPIC_API_KEY
m = c.messages.create(model="claude-haiku-5-5", max_tokens=5, messages=[{"role":"user","content":"ping"}])
print(m.usage)
```

Record the org/workspace this key belongs to in `runs/KEY_CHECK.md` (from the Console, Hemang will confirm it's the one with credits). If this key is the one Claude Code cloud already uses for other things, say so — spend has to land on the platform org, and Hemang will not notice a wrong key until the 20th.

**Model choices** (verified Oct 14, 2026 — batch prices are 50% of standard):

| Job | Model | Why |
|---|---|---|
| A — LLM planting | `claude-sonnet-5-5` | High volume, format-following, cheap in batch ($1/$5 per MTok) |
| B — miss diagnosis | `claude-opus-5-5` | Judgment quality matters more than volume ($2/$10 per MTok batch) |
| C — agent loop | `claude-opus-5-5` | Reads code, proposes patches; capped by session budget |

---

## 2. Component A — LLM-planted second view (Batch API)

`scripts/plant_llm.py` — produces `data/planted_llm/<dataset>.jsonl` with the **same schema** as the deterministic planter's output (dialogue_id, dataset, turn_idx, speaker, text, gold_spans with edshield 0.2.0 labels), so the fixed scorer runs on it unchanged.

**What stays deterministic (reuse from `plant.py`, do not reinvent):**
- Which dialogues get which identifier types (the 70/80/50/30/10/10 slot decisions) — read the slot manifest `plant.py` wrote, or call its slot-selection function with the same seed. The LLM never decides *whether* or *where*; only *how it's phrased* and *which name*.
- Name category assignment (anglo_common / non_anglo / name–word collisions) per dialogue.

**What the LLM does, per request (one request per dialogue):**
- Input: the normalized dialogue, the slot manifest for that dialogue (turn indices + identifier types + name category), and 2–3 example student turns from the *same dataset* as register anchors.
- Output: strict JSON — the rewritten turns only, each with the inserted identifier surface forms and character offsets. Instruct it to match the register of the surrounding turn (lowercase, missing punctuation, typos at the dataset's observed rate), to choose names from the required category, and to never alter any turn not in the manifest.
- Validate in code: offsets resolve to the claimed surface form; untouched turns are byte-identical; every manifest slot was filled; labels are from edshield's list. Reject and re-queue failures once; log persistent failures to `runs/<ts>/plant_rejects.jsonl` and drop them from the set (report the drop count).

**Batch mechanics** (`anthropic` Python SDK, verified):
- `client.messages.batches.create(requests=[{"custom_id": ..., "params": {...}}, ...])` — `custom_id` = `plant-<dataset>-<dialogue_id>`.
- Poll `client.messages.batches.retrieve(id).processing_status == "ended"`; stream `client.messages.batches.results(id)`; match on `custom_id`, never on order.
- Put the shared instructions + examples in `system` with `cache_control: {"type": "ephemeral"}` on every request so cache hits stack with the batch discount.
- Dry-run one request through `client.messages.create` first to catch validation errors (batch validation is asynchronous).
- Save `runs/<ts>/batch_plant_requests.jsonl` and `batch_plant_results.jsonl`.

**Expected spend:** ~800 dialogues (CoMTA 188 + MathDial test ~588; StudyChat only if the deterministic run included it) × ~1.5k in / ~0.8k out ≈ **$4–6**.

**Then score it:** run the *fixed* scorer (same code the sealed run used) over `data/planted_llm/` with edshield 0.2.0 → `results/llm_view/` with the same tables as the deterministic run (recall by dataset × name category, over-redaction on the no-plant control, failure table). Produce `results/view_comparison.md`: deterministic vs LLM-planted, per category, with confidence intervals. This is the template-overlap control as data.

---

## 3. Component B — miss diagnosis (Batch API)

`scripts/diagnose.py` — one request per row of **both** failure tables (deterministic + LLM view). Input: the missed gold span, the full dialogue window (±3 turns), what edshield *did* emit on that span (nothing / wrong label / partial), the name category, the dataset. Output: strict JSON.

**Cause taxonomy (closed set, one primary + optional secondary):**

| Code | Meaning |
|---|---|
| `REGISTER` | lowercase / no punctuation / typo defeated a capitalization- or pattern-dependent detector |
| `NAME_WORD_COLLISION` | name is also a common or curricular word (Grace, Will, Newton, Riemann) |
| `NON_ANGLO_NAME` | name outside the model's apparent name prior |
| `SCHEMA_GAP` | identifier type the label set doesn't cover well (school-as-lowercase phrase, obfuscated email, bare username) |
| `TOKENIZATION` | span boundary / subword split problem (partial detection) |
| `CONTEXT_CUE_MISSING` | no linguistic cue that this token is a person/school (bare name mid-sentence) |
| `AMBIGUOUS` | a human annotator could reasonably disagree with the gold span |
| `OTHER` | with a one-line reason |

Also required per row: `confidence` (0–1), `fix_class` ∈ {`RULE`, `GAZETTEER`, `MODEL`, `LABEL_SCHEMA`, `NONE`}, and `evidence` (≤ 25 words quoting the exact tokens that drove the call). The rubric goes in `prompts/diagnose_system.md` and is committed; it is not edited after the first submission.

**Mechanics:** same as §2 (batches, `cache_control` on the rubric, dry-run first, log everything). `custom_id` = `diag-<view>-<dataset>-<dialogue_id>-<span_idx>`. For a sample of 50 rows, submit twice with different ordering of the taxonomy in the prompt and report label agreement — a cheap consistency check that costs under a dollar.

**Expected spend:** 500–2,000 misses × ~1.2k in / ~0.3k out on Opus 5.5 ≈ **$5–12**.

**Output:** `results/diagnosis/causes.jsonl`, plus `results/diagnosis/summary.md`: cause distribution per view and per name category, `fix_class` distribution, the agreement number, and the ten highest-confidence `RULE`/`GAZETTEER` rows as a worked list. That table is the "why does it fail" paragraph for NSF.

---

## 4. Component C — bounded improve loop (Claude Managed Agents)

This is the production agent run. It must be a real Managed Agents session, not a script that calls `messages.create` in a loop, and not Claude Code reasoning in its own session.

### 4.1 Agent definition (`agents/rule_proposer.md`, applied with `ant apply` or `client.beta.agents.create`)

- `model: claude-opus-5-5`
- `tools: [{type: agent_toolset_20260401}]` (bash + file ops are enough; no web search needed — leave `allowed_hosts` for web tools empty).
- System prompt (commit it as `prompts/agent_system.md`), the gist:
  - You are proposing **rule-level and gazetteer-level** fixes to edshield's detector. You may edit only files under `edshield/rules/` (or whatever the actual rules/gazetteer module paths are — check `edshield` 0.2.0's layout and name them explicitly). You may not edit scoring code, planted data, model weights, training code, or anything under `edshield_evidence/`.
  - Inputs you have: `results/diagnosis/summary.md`, the failure tables, the view comparison.
  - Each round: (1) read the top `RULE`/`GAZETTEER` causes, (2) write one focused patch, (3) run `make eval-candidate`, (4) read `results/candidate/round_N/summary.json`, (5) decide: keep, revert, or stop.
  - **Stop when** any of: 3 rounds done; a round improves recall on the deterministic view by < 0.5 pp; over-redaction on the control rises by > 0.5 pp (revert that round and stop); the budget pauses you.
  - Final deliverable: `proposals/PROPOSAL.md` (what each patch does, numbers before/after on both views and on the control, which causes it addresses, what it does not fix and why) plus `proposals/round_N.patch` files from `git diff` on the edshield checkout. State explicitly that nothing is merged and a human reviews.
  - Report "no regression against pinned baseline <row>" language only; never "meets defined redaction criteria".

### 4.2 Environment (`environments/eval.yaml`)

```yaml
name: edshield-eval
config:
  type: cloud
  packages:
    pip: ["edshield==0.2.0", "onnxruntime", "anthropic"]
  networking:
    type: limited
    allow_package_managers: true   # covers github.com, pypi.org, files.pythonhosted.org
    allowed_hosts:
      - huggingface.co
      - "*.huggingface.co"         # bare host does not match subdomains; both are needed
```

If a model download 403s, the error names the blocked host — add it and recreate the environment. Set `EDSHIELD_ALLOW_DOWNLOAD=1` in the session's first message or a setup script, since edshield refuses downloads otherwise.

### 4.3 Sandbox contents

The session's first user message is a setup instruction: clone `edshield-evidence` at branch `exp/agent-diagnose` (public, reachable via the package-manager host list) and `edshield` at the pinned commit `a568e73`, `pip install -e` the edshield checkout as the *candidate*, and confirm `make eval-candidate` runs end to end on the unmodified checkout and reproduces the baseline within rounding (this is the sanity gate — if it doesn't, the agent stops and reports). Inference is CPU via the INT8 ONNX model; ~800 short dialogues ×2 views is fine on CPU.

`make eval-candidate` is yours to write on this branch: it runs the fixed scorer over both planted views and the control using the *candidate* edshield install, and writes `results/candidate/round_N/` with the same table shapes as the baseline. The agent calls it; it never edits it.

### 4.4 Session with a hard budget

```python
session = client.beta.sessions.create(
    agent=agent.id,
    environment_id=environment.id,
    title="edshield rule-proposal loop",
    budget={"type": "limit", "max_list_cost": {"amount": "3000", "currency": "USD"}},  # $30, in cents as a string
)
```

Budget is enforced at list price between model requests; the session goes idle with `stop_reason: budget_reached` rather than dying, so a cap mid-round is recoverable — but don't raise it without Hemang.

### 4.5 Driver (`scripts/run_agent_loop.py`)

Creates agent + environment (idempotent: reuse IDs from `runs/agent_ids.json` if present), creates the session, opens `client.beta.sessions.events.stream(session.id)`, sends the setup message then the task message via `client.beta.sessions.events.send(...)`, and writes **every** event to `runs/<ts>/agent_events.jsonl`. Exit on `session.status_idle`; record `stop_reason`, the `session.usage` event (tokens, `list_cost`, `active_seconds`), and whether the stop was a normal finish, a budget pause, or an error.

Retrieve `proposals/` and `results/candidate/` from the sandbox at the end (see the Managed Agents **files** docs: https://platform.claude.com/docs/en/managed-agents/files) and commit them to this branch. If pulling files proves awkward, fall back to instructing the agent to print `PROPOSAL.md` and each patch inside clearly delimited fenced blocks in its final message, and have the driver extract them from the event log — but files first.

### 4.6 Post-session enforcement

After retrieval, the driver applies each `round_N.patch` to a clean edshield checkout at `a568e73` and fails loudly if the diff touches any path outside the allowed rules/gazetteer modules. It also re-runs `make eval-candidate` once itself for the final kept patch set and compares to the agent's reported numbers; any discrepancy > rounding is reported, not silently overwritten. This is the "the work isn't grading itself" step.

**Expected spend:** session cap $30 (Opus 5.5 at standard rates plus $0.08/hr runtime). If it finishes under $15, that's fine — don't pad it.

---

## 5. Sequencing against the desktop run

| When | What |
|---|---|
| Now | Scaffold everything in §2–§4. Write `make eval-candidate`, `plant_llm.py`, `diagnose.py`, agent + env definitions, driver. Dry-run one request each through `messages.create`. Key check. |
| As soon as `data/normalized/` + slot manifest are pushed | Submit the planting batch (§2). Score the LLM view with 0.2.0. |
| As soon as `results/failure_table.jsonl` is pushed | Submit the diagnosis batch (§3) over both views. |
| After §3 results land | Run the agent session (§4). |
| Throughout | **Do not run edshield inference on the deterministic planted set while the desktop is still working on it.** Two baselines from two machines is exactly the confusion to avoid. Baseline numbers come from the desktop's pushed results. |

If you're blocked waiting on a push, write `WAITING.md` with the exact file paths you need and stop; Hemang will push and restart you.

---

## 6. Reports

- `results/view_comparison.md` — deterministic vs LLM-planted, per dataset × name category, with CIs; one chart.
- `results/diagnosis/summary.md` — cause distribution, fix-class distribution, agreement check, top-10 worked misses.
- `proposals/PROPOSAL.md` + `round_N.patch` — from the agent, plus the driver's independent re-score.
- `results/agent_findings.md` — **the quotable one**, written by Claude Code from the above, ≤ 400 words, numbers only from files on this branch: what share of misses are rule-fixable vs model-limited, what the second view showed about template dependence, what the bounded loop recovered and at what over-redaction cost, and what remains model work (the Phase I R&D claim). Every number cites the file it came from.
- `runs/<ts>/COST.md` — per-component spend from batch `usage` fields and the session's `session.usage` event, against the $71 budget.

---

## 7. Acceptance

- [ ] Key check recorded; spend visible in the platform Console under the right org.
- [ ] LLM-planted view scored with edshield 0.2.0 by the unchanged fixed scorer; drop count reported.
- [ ] Every miss in both failure tables has a cause row; rubric committed and unchanged after first submission; agreement check reported.
- [ ] Managed Agents session ran with a budget; event log committed; `stop_reason` recorded.
- [ ] Driver's diff check passed (or failure reported); driver's independent re-score matches the agent's within rounding (or discrepancy reported).
- [ ] No file under `data/planted/`, `data/sealed/`, `edshield_evidence/` scorers, or the deterministic results changed on this branch (`git diff exp/genre-shift-planted -- <those paths>` is empty).
- [ ] `agent_findings.md` and `COST.md` written; PR opened against `main` titled "exp: agent-assisted diagnosis on genre-shift results".
- [ ] All batches submitted by Oct 18; nothing still running on Oct 20.

---

## Prompt to paste into Claude Code cloud

> Read `docs/BRIEF-agent-diagnose.md` (this file — commit it there first) and execute it. The work that requires judgment — planting, diagnosis, the improve loop — runs as Batch API and Managed Agents calls against the platform key in `ANTHROPIC_API_KEY`; you build and drive the pipeline, you do not do that reasoning yourself. Start with the key check and scaffolding. If `exp/genre-shift-planted` or its results aren't pushed yet, scaffold, dry-run one request per component, write `WAITING.md`, and stop.
