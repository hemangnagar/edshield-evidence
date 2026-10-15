# Agent-assisted diagnosis: how this branch is laid out and run

Companion to `docs/BRIEF-agent-diagnose.md`. The brief was written before the
sealed run's layout existed; this maps its names to the real paths.

| Brief | Here | Notes |
|---|---|---|
| branch `exp/agent-diagnose` | `claude/compassionate-ritchie-tpkgv9` | the branch this cloud session was pinned to; it contains `exp/genre-shift-planted` (merged, unchanged) |
| `data/normalized/` | `experiments/genre_shift/data/raw/` + `loaders.py` | pinned raw files, never committed; `make raw` fetches them |
| `data/planted/`, slot manifest | `experiments/genre_shift/data/planted/` (git-ignored, licensed text) + `data/plant_log.json` (committed) | `make plant-check` rebuilds the planted set with seed 20261014 and verifies the log byte for byte |
| `results/failure_table.jsonl` | `experiments/genre_shift/results/misses.csv` → `results/deterministic/failure_table.jsonl` | `scripts/build_failure_table.py` adds the ±3-turn window and span offsets |
| `data/planted_llm/` | `data/planted_llm/<ds>.jsonl` (git-ignored) + `<ds>.spans.jsonl`, `plant_llm_log.json` (committed) | |
| `results/llm_view/` | `results/llm_view/{llm,control}/metrics.json`, `results/llm_view/llm/misses.csv`, `summary.json` | `make score-llm-view` |
| `make eval-candidate` | root `Makefile` → `scripts/run_views.py --out results/candidate/round_$(ROUND)` | both views + control with the *installed* edshield |
| `edshield/rules/` | `edshield/rules.py` (edshield 0.2.0 has one rules module and no gazetteer) + new files under `edshield/gazetteer/` | the only paths the agent may change; `scripts/enforce_patches.py` rejects others |

## Components

- **Key check:** `python scripts/key_check.py` → `runs/KEY_CHECK.md`.
- **A, LLM-planted view:** `scripts/plant_llm.py {build,dry-run,submit,collect}` → `data/planted_llm/`; then `make score-llm-view`, `python scripts/build_failure_table.py llm`, `make view-comparison`.
- **B, diagnosis:** `scripts/diagnose.py {build,dry-run,submit,collect}` → `results/diagnosis/{causes.jsonl,summary.md}`. Rubric `prompts/diagnose_system.md`; its sha256 is frozen at first submission.
- **C, improve loop:** `scripts/run_agent_loop.py` (Managed Agents: `agents/rule_proposer.md`, `environments/eval.yaml`, `prompts/agent_*.md`) → `proposals/`, `results/candidate/`, `runs/<ts>-agent/`; then `python scripts/enforce_patches.py` → `proposals/DRIVER_CHECK.md`.
- **Reports:** `results/view_comparison.md`, `results/diagnosis/summary.md`, `proposals/PROPOSAL.md`, `results/agent_findings.md`, `runs/<ts>-cost/COST.md` (`python scripts/cost.py`).

Every API call goes through `scripts/platform_api.py`, which reads the platform key from `EDSHIELD_PLATFORM_API_KEY` (or `ANTHROPIC_API_KEY`), pins the official API base URL and logs request and result JSONL under `runs/<ts>-<tag>/`. Files that carry the licensed dialogue text (full requests/results, planted documents, raw model outputs) are git-ignored; text-free `.index.jsonl` siblings with usage and cost are committed.

## Design decisions worth knowing

- The LLM view keeps the sealed run's slot decisions *and* name forms (full name / first name / initial / all-caps / truncated, lowercase and typo flags) per slot; only the wording around each identifier and the choice of name within the category change. The validator rejects any other surface form, so the two views differ in exactly one variable.
- MathDial persona-name substitutions are mechanical and are done in code after the model answers, in the sealed forms, so they are not a source of variation either.
- The diagnoser never sees the sealed run's heuristic `reason` tag.
- The agent's tool permission policy is `always_allow`: the sandbox holds public code and synthetic identifiers only, and nobody attends the run.
- Baseline numbers for the deterministic view are read from the desktop's committed `experiments/genre_shift/results/metrics.json`; this branch never re-runs that view as a baseline. Candidate rounds compare against it and against round 0 in the same sandbox.

## Status (2026-10-15)

Everything in the brief ran. Key check, both batches, the Managed Agents session (`sesn_01SpV798Yfa2nmVUmZX6fJTr`, two rounds, $3.77) and the fresh-container verification session (`sesn_01JVPjSwZ9qiT5pE4WtsiFFm`, $0.13) are done; nothing is still running on the platform. Deviations from the brief, all recorded in the files: the sandbox scored with the INT8 ONNX runtime because torch wheels are unreachable there (round 0 is 0.35 pp under the sealed GPU baseline); the planting validator accepts insert-only edits, a case change of the original's first letter after a prepended phrase, and locates surface forms itself; the LLM view is 724 of 738 dialogues. The findings note is `results/agent_findings.md`; spend is in `runs/20261015T144955Z-cost/COST.md`.
