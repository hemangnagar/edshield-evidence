This is a mechanical verification run, not a proposal task. Do exactly these steps and nothing else; do not edit any file.

1. `export EDSHIELD_ALLOW_DOWNLOAD=1`.
2. `git clone --recurse-submodules --branch claude/compassionate-ritchie-tpkgv9 https://github.com/hemangnagar/edshield-evidence /workspace/edshield-evidence && pip install -e /workspace/edshield-evidence` (edshield stays the pinned PyPI 0.2.0 release for now).
3. Copy the uploaded documents into place: `/mnt/session/uploads/planted/*.jsonl` -> `/workspace/edshield-evidence/experiments/genre_shift/data/planted/`, `/mnt/session/uploads/control/*.jsonl` -> `.../experiments/genre_shift/data/control/`, `/mnt/session/uploads/planted_llm/*.jsonl` -> `/workspace/edshield-evidence/data/planted_llm/`. Then `cd /workspace/edshield-evidence && make raw && make plant-check`.
4. Run the driver's check and independent re-score: `cd /workspace/edshield-evidence && nohup python scripts/enforce_patches.py --runtime onnx > /tmp/enforce.log 2>&1 &` and poll `/tmp/enforce.log` with waits of at most 280 seconds until the process exits (it clones edshield at the pinned commit into `runs/edshield-checkout`, applies the final kept patch, installs it, scores both views and the control, compares with the agent's round summary, and restores the pinned release). Do not intervene in it. If it fails, report the last 40 lines of the log and stop.
5. Copy `proposals/DRIVER_CHECK.md` and `results/candidate/driver_rescore/` (without `raw/`) into `/mnt/session/outputs/` and pack both into `/mnt/session/outputs/outputs.tar.gz` with paths relative to the bench root.

Reply with the contents of `proposals/DRIVER_CHECK.md` verbatim.
