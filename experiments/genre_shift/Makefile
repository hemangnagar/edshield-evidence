# Genre-shift experiment. Everything reproducible from `make experiment`.
# Needs: the repo venv with edshield==0.2.0 (PyPI) + torch, and
# EDSHIELD_EVIDENCE_PIILO pointing at the 680-document PIILO validation.json
# (sha256 bc5d0958…; not in the repo). First model fetch needs EDSHIELD_ALLOW_DOWNLOAD=1.
PY ?= ../../.venv/Scripts/python
SEED ?= 20261014
DEVICE ?= cuda
export HF_HUB_DISABLE_SYMLINKS_WARNING=1

.PHONY: experiment data plant run score clean

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
