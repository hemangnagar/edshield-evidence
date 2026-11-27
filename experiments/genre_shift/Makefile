# Genre-shift experiment. Everything reproducible from `make experiment`.
# Needs: the repo venv with edshield==0.2.0 (PyPI) + torch, and
# EDSHIELD_EVIDENCE_PIILO pointing at the 680-document PIILO validation.json
# (sha256 bc5d0958…; not in the repo). First model fetch needs EDSHIELD_ALLOW_DOWNLOAD=1.
PY ?= ../../.venv/Scripts/python
SEED ?= 20261014
DEVICE ?= cuda
export HF_HUB_DISABLE_SYMLINKS_WARNING=1

.PHONY: experiment data plant run score clean v2 v2-nogpt v2-data v2-plant v2-score

experiment: data plant run score

data:
	$(PY) download.py

plant:
	$(PY) plant.py --seed $(SEED)

run:
	$(PY) run.py --sets planted control piilo --device $(DEVICE)

score:
	$(PY) score.py

clean:
	rm -rf data/planted data/control data/plant_log.json results/raw results/metrics.json results/report.md results/misses.csv results/recall_by_category.png

# --- v2: five detectors, five seeds, floor transfer (BRIEF_v2.md) -------------------
# Needs, on top of the above: pip install -r requirements-v2.txt (spaCy, Presidio, the two
# spaCy models, scipy, openai). `make v2` also needs OPENAI_API_KEY; GPT_BUDGET_USD caps the
# spend (default 30) and cached responses in cache/gpt/ cost nothing. `make v2-nogpt` skips
# the API detector. The PIILO holdout comes from EDSHIELD_EVIDENCE_PIILO when set, otherwise
# it is rebuilt from the public corpus and checked against the committed baseline bundle.
SEEDS ?= 20261014 20261015 20261016 20261017 20261018
V2_DEVICE ?= cpu
V2_LOCAL = edshield presidio spacy_trf hf_pii
export EDSHIELD_ALLOW_DOWNLOAD ?= 1

v2: v2-data v2-plant
	$(PY) run_detectors.py --detectors $(V2_LOCAL) --device $(V2_DEVICE)
	$(PY) run_detectors.py --detectors gpt4o_mini --chunk 700
	$(MAKE) v2-score

v2-nogpt: v2-data v2-plant
	$(PY) run_detectors.py --detectors $(V2_LOCAL) --device $(V2_DEVICE)
	$(MAKE) v2-score

v2-data:
	$(PY) download.py comta mathdial studychat tscc
ifndef EDSHIELD_EVIDENCE_PIILO
	$(PY) download.py piilo_public
	$(PY) rebuild_piilo.py
endif

v2-plant:
	$(PY) plant.py --seeds $(SEEDS) --out data/v2

v2-score:
	$(PY) score_v2.py
	$(PY) plot_v2.py
