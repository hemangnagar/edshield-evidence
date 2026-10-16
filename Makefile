.PHONY: experiment raw plant-check score-llm-view eval-candidate failure-tables view-comparison agent-md test-agent-diagnose
experiment:
	$(MAKE) -C experiments/genre_shift experiment

# --- agent-diagnose branch (docs/BRIEF-agent-diagnose.md) ------------------------------------
PY ?= python3
ROUND ?= 0
RUNTIME ?= python
VIEWS ?= deterministic llm

raw:                      ## pinned CoMTA + MathDial raw files (never committed)
	cd experiments/genre_shift && $(PY) download.py comta mathdial

plant-check:              ## rebuild the sealed planted set and verify the plant log byte for byte
	$(PY) -c "import sys; sys.path.insert(0,'scripts'); import genre_shift_data as g; g.ensure_planted(); print('sealed planted set reproduced')"

score-llm-view:           ## brief §2: the fixed scorer over data/planted_llm with the installed edshield (0.2.0)
	$(PY) scripts/run_views.py --out results/llm_view --views llm --runtime $(RUNTIME)

eval-candidate:           ## brief §4.3: both views + control with the *installed* (candidate) edshield -> results/candidate/round_$(ROUND)
	$(PY) scripts/run_views.py --out results/candidate/round_$(ROUND) --views $(VIEWS) --runtime $(RUNTIME)

failure-tables:
	$(PY) scripts/build_failure_table.py deterministic llm

view-comparison:
	$(PY) scripts/view_comparison.py

agent-md:                 ## regenerate agents/rule_proposer.md body from prompts/agent_system.md
	$(PY) scripts/run_agent_loop.py --write-agent-md

test-agent-diagnose:
	$(PY) -m pytest -q tests/test_plant_llm.py tests/test_agent_diagnose.py
