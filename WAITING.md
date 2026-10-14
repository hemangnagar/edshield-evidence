# Waiting

Scaffolding for `docs/BRIEF-agent-diagnose.md` is complete and tested offline (`make test-agent-diagnose`). Nothing has been submitted to the platform. Two things block the next step; the first is the hard one.

## 1. `ANTHROPIC_API_KEY` is not set in this cloud environment

The key check (`runs/KEY_CHECK.md`) found no key, so no dry run, batch or agent session could be made. Add the platform org's key as an environment secret: cloud environment menu in the session title bar → Edit → Network secrets (or environment variables) → name it exactly `ANTHROPIC_API_KEY`. A new session picks it up. The scripts pin `https://api.anthropic.com` and refuse to run without this variable, so nothing can fall back to Claude Code's own credential.

Then restart with: "Read docs/BRIEF-agent-diagnose.md and continue from WAITING.md." The first actions will be `python scripts/key_check.py`, one dry run per component (`scripts/plant_llm.py dry-run`, `scripts/diagnose.py dry-run`, `scripts/run_agent_loop.py --dry-run`), then the planting batch.

## 2. `huggingface.co` is blocked by this environment's network policy

edshield's model (`edshield/piilo-deberta-v3-small`) downloads from huggingface.co, which this container's proxy refuses (403). Without it this session cannot run edshield inference, so it cannot score the LLM-planted view (brief §2) or run the sanity round of `make eval-candidate` here. Two ways out, either is fine:

- add `huggingface.co` and `cdn-lfs.huggingface.co` (plus `download.pytorch.org` for CPU torch) under Allowed domains in the environment's Network access settings, with package managers left allowed; or
- leave this container as is: the Managed Agents sandbox (`environments/eval.yaml`) has its own network policy that already allows these hosts, and the LLM view can be scored there as round 0 of the agent session. The driver would then run the diagnosis batch for the LLM view after that scoring lands, which costs one extra sequencing step.

Reference data is in place: `exp/genre-shift-planted` is pushed and merged into this branch unchanged; the pinned raw files download fine; the sealed planted set rebuilds byte-for-byte from `plant_log.json`; the deterministic failure table (275 misses) is built.

Nothing else is needed from the desktop run.
