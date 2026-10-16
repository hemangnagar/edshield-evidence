Set up the sandbox and measure the candidate; do not propose anything yet.

1. `export EDSHIELD_ALLOW_DOWNLOAD=1` and add it to `~/.bashrc`.
2. Clone the bench: `git clone --recurse-submodules --branch {branch} https://github.com/hemangnagar/edshield-evidence /workspace/edshield-evidence && pip install -e /workspace/edshield-evidence`.
3. Clone the candidate: `git clone https://github.com/hemangnagar/edshield /workspace/edshield && cd /workspace/edshield && git checkout main && git checkout -b candidate && git rev-parse HEAD`. Then `pip install -e /workspace/edshield` and confirm `python -c "import edshield, inspect; print(edshield.__version__, inspect.getfile(edshield))"` resolves under /workspace/edshield.
4. Copy the uploaded documents into place: `/mnt/session/uploads/planted/*.jsonl` -> `/workspace/edshield-evidence/experiments/genre_shift/data/planted/`, `/mnt/session/uploads/control/*.jsonl` -> `.../experiments/genre_shift/data/control/`, `/mnt/session/uploads/planted_llm/*.jsonl` -> `/workspace/edshield-evidence/data/planted_llm/`. Then in the bench root run `make raw` and `make plant-check`.
5. Round 0: `nohup make eval-candidate ROUND=0 RUNTIME={runtime} > /tmp/round0.log 2>&1 &` and poll the log with waits of at most 280 seconds until the process exits. Read `results/candidate/round_0/summary.json` and report identifier recall on both views, the control figures, the deltas against the baselines in the summary, and `sanity.within_tolerance`.
6. Copy `results/candidate/round_0/` (without `raw/`) into `/mnt/session/outputs/` and pack it into `/mnt/session/outputs/outputs.tar.gz` with paths relative to the bench root.

Reply with the status (candidate commit, where edshield resolves from, the round 0 numbers) and wait for the task message. Do not print dialogue text.
