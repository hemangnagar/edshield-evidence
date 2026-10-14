# Data sources

Raw files live in `data/raw/<name>/` and are never committed (`.gitignore`);
`download.py` fetches each at the pinned commit or revision and writes the
sha256 of every file to `data/raw/<name>/SHA256SUMS`. Publishers scrubbed PII
before release; every identifier scored here was planted by `plant.py` from
`names/*.txt`.

| Dataset | What | Source (pinned) | License | Status 2026-10-14 |
|---|---|---|---|---|
| CoMTA | 188 real student ↔ Khanmigo math dialogues, elementary to calculus (Khan Academy; Miller & DiCerbo 2024, "LLM Based Math Tutoring: Challenges and Dataset") | `https://github.com/Khan/tutoring-accuracy-dataset`, commit `fbbeff86b5c1a689161b8f6092a6be7d0532a6dd`, file `CoMTA_dataset.json` (sha256 `6937272dc10aea3545fcb15c97c07bf9f4ade7edf7199a67333e7c0754e68e37`). The brief's URL `github.com/Khan/tutoring-datasets` returns 404; this repository is the one Khan Academy's release post links to. | Khan Academy "Evaluation Dataset License" (internal use for evaluating AI models; see `data/raw/comta/LICENSE`, sha256 `53cf7aa7…`). Not redistributed here. | downloaded |
| MathDial | 2,861 tutoring dialogues, LLM-simulated students with a persona name, human tutors (ETH Zürich; Macina et al. 2023). Official test split used: 599 dialogues. | `https://github.com/eth-nlped/mathdial`, commit `b06c020a0a1f57a87577fec33e657b63e7eb476e`, file `data/test.jsonl` (sha256 `3ec54ee8ab921dc6191bf5e2ee766d4e7916b4264394eb17a6be9b3fe486e50b`) | CC BY 4.0 (per the repository README) | downloaded |
| StudyChat | Real university students ↔ ChatGPT in a CS course (UMass Amherst; McNichols et al. 2025) | `https://huggingface.co/datasets/wmcnicho/StudyChat`, revision `24d7987d9fbb30d9da12acc53455a10f1cdd2d7f`, file `data.jsonl` | CC BY 4.0 (dataset card) | **blocked**: gated repository; the Hugging Face account used is not on its access list (403). Loader and download are in place; request access on the dataset page and rerun `make data`. |
| TSCC v2 | Cambridge ESL chatroom lessons, 13 students, 7 first languages | by request form (Caines et al.) | per request agreement | not yet received; `loaders.load_tscc` accepts files dropped into `data/raw/tscc/` |
| PIILO holdout | 680 held-out PIILO essays, the in-domain reference | the repo's `EDSHIELD_EVIDENCE_PIILO` validation.json (sha256 `bc5d0958b72eee52a7fd38b84ac4c775128eefae6f9e8acee5dbc710cea1ecf8`); not in the repo | see edshield | local copy |

Model: `edshield/piilo-deberta-v3-small` from the Hugging Face Hub, the weights the live demo uses; revision and sha256 recorded in `results/run_meta.json`.

Note on MathDial: the simulated student carries a persona first name that
already appears in 362 of 599 test dialogues ("Hi Mariana, ..."). `plant.py`
replaces every whole-word occurrence with the planted name, so each planted
dialogue carries exactly one student name. In the untouched control those
persona names remain and flags on them are reported under their own tag, not
as over-redaction. Names of word-problem characters ("Julia bought 12 spoons")
are likewise tagged separately in both sets.
