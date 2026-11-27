# Data sources

Raw files live in `data/raw/<name>/` and are never committed (`.gitignore`);
`download.py` fetches each at the pinned commit or revision and writes the
sha256 of every file to `data/raw/<name>/SHA256SUMS`. Publishers scrubbed PII
before release; every identifier scored here was planted by `plant.py` from
`names/*.txt`.

| Dataset | What | Source (pinned) | License | Status (v1 2026-10-14; v2 2026-11-27) |
|---|---|---|---|---|
| CoMTA | 188 real student ↔ Khanmigo math dialogues, elementary to calculus (Khan Academy; Miller & DiCerbo 2024, "LLM Based Math Tutoring: Challenges and Dataset") | `https://github.com/Khan/tutoring-accuracy-dataset`, commit `fbbeff86b5c1a689161b8f6092a6be7d0532a6dd`, file `CoMTA_dataset.json` (sha256 `6937272dc10aea3545fcb15c97c07bf9f4ade7edf7199a67333e7c0754e68e37`). The brief's URL `github.com/Khan/tutoring-datasets` returns 404; this repository is the one Khan Academy's release post links to. | Khan Academy "Evaluation Dataset License" (internal use for evaluating AI models; see `data/raw/comta/LICENSE`, sha256 `53cf7aa7…`). Not redistributed here. | downloaded |
| MathDial | 2,861 tutoring dialogues, LLM-simulated students with a persona name, human tutors (ETH Zürich; Macina et al. 2023). Official test split used: 599 dialogues. | `https://github.com/eth-nlped/mathdial`, commit `b06c020a0a1f57a87577fec33e657b63e7eb476e`, file `data/test.jsonl` (sha256 `3ec54ee8ab921dc6191bf5e2ee766d4e7916b4264394eb17a6be9b3fe486e50b`) | CC BY 4.0 (per the repository README) | downloaded |
| StudyChat | Real university students ↔ ChatGPT in a CS course (UMass Amherst; McNichols et al. 2025) | `https://huggingface.co/datasets/wmcnicho/StudyChat`, revision `24d7987d9fbb30d9da12acc53455a10f1cdd2d7f`, file `data.jsonl` | CC BY 4.0 (dataset card) | **blocked in v1 and again in v2 (2026-11-27)**: gated repository; the Hugging Face account used is not on its access list (`GatedRepo`, 403). Loader, the deterministic ≤600-dialogue sample (`loaders.sample_dialogues`) and download are in place and untested against the real file; request access on the dataset page and rerun `make v2`. |
| TSCC v2 | Cambridge ESL chatroom lessons, 13 students, 7 first languages | by request form (Caines et al.) | per request agreement | not received (v1, v2); `loaders.load_tscc` accepts files dropped into `data/raw/tscc/` |
| PIILO holdout | 680 held-out PIILO essays, the in-domain reference | the repo's `EDSHIELD_EVIDENCE_PIILO` validation.json (sha256 `bc5d0958b72eee52a7fd38b84ac4c775128eefae6f9e8acee5dbc710cea1ecf8`); not in the repo | see edshield | v1: local copy. v2 (run in a cloud container without that file): rebuilt, see below |

Model: `edshield/piilo-deberta-v3-small` from the Hugging Face Hub, the weights the live demo uses; revision and sha256 recorded in `results/run_meta.json`.

Note on MathDial: the simulated student carries a persona first name that
already appears in 362 of 599 test dialogues ("Hi Mariana, ..."). `plant.py`
replaces every whole-word occurrence with the planted name, so each planted
dialogue carries exactly one student name. In the untouched control those
persona names remain and flags on them are reported under their own tag, not
as over-redaction. Names of word-problem characters ("Julia bought 12 spoons")
are likewise tagged separately in both sets.

## v2 additions (BRIEF_v2.md)

**PIILO holdout, rebuilt.** The v2 run had no copy of `validation.json`. `rebuild_piilo.py`
selects the 680 held-out essays from the public PIILO corpus by the document ids the committed
baseline bundle records (`evidence/reports/2026-10-04-6c0f163/01_piilo_holdout_model_python.bundle.json`)
and accepts the result only if every essay's whitespace-token count and gold-token positions
equal the bundle's `word` view: 680 essays, 427,681 tokens, 294 gold tokens, all equal. The
rebuilt file is not byte-identical to the original (sha256 `bc5d0958…`); its own sha256 is in
`results/v2/metrics.json` under `run._piilo`. With `EDSHIELD_EVIDENCE_PIILO` set, the local
file is used instead.

| Source | What | Pinned | License |
|---|---|---|---|
| PIILO corpus, public copy | `train.json` of the Kaggle competition "The Learning Agency Lab - PII Data Detection" (6,807 essays; names are the publisher's surrogates) | `https://huggingface.co/datasets/melaniasala/PII_Data_Detection`, revision `4d5200883df788426d9fa609d41328fd2f099bd4`, `train.json` sha256 `8276cd44f3b2eb357dfb405b3c5d8e9f821388e984cbf66e92e7df03f1b13117` (a third-party mirror; `hardikpatel/PII_data_kaggle` holds the same bytes). Not committed. | CC BY 4.0 (The Learning Agency Lab / Vanderbilt University) |
| English word list | `names/english_words.txt`: the 63,875 lowercase, purely alphabetic entries of SCOWL `american-english` (the Unix `/usr/share/dict/words`), used for `is_dict_word` | Ubuntu package `wamerican_2020.12.07-2_all.deb` (`https://archive.ubuntu.com/ubuntu/pool/main/s/scowl/`, sha256 `68dbe031e3fe3a63c50f7fd5d63c320879dab5a35ba86dd5ddd83905b080b0b4`); derived file sha256 `a43c50614fda43658df3e60aa07e8cc37f657d969fcf89938731bf059db16d16`. Committed. | SCOWL licence, Copyright 2000-2011 Kevin Atkinson and others; full notice in `names/english_words.LICENSE.txt` |

**Detectors.** Exact versions are in `requirements-v2.txt` and, per detector, in `results/v2/metrics.json` under `run`.

| id | Model | Pinned | License |
|---|---|---|---|
| `edshield` | `edshield/piilo-deberta-v3-small`, edshield 0.2.0 rules + model, policy `coppa` | revision `5effafd0299ac576b6c5b3a91b3f26800ce89e62`, weights sha256 `71af3248048b619a346e73a0c27cada4fead138ea9becb4d7abad1d1102cb50a` (same as v1) | see edshield |
| `presidio` | Microsoft Presidio Analyzer, default recognizers, spaCy `en_core_web_lg` | `presidio-analyzer` 2.2.366, `en_core_web_lg` 3.8.0 | MIT (Presidio, spaCy model) |
| `spacy_trf` | spaCy `en_core_web_trf` NER (RoBERTa-base) | `en_core_web_trf` 3.8.0, spaCy 3.8.18 | MIT |
| `hf_pii` | `iiiorg/piiranha-v1-detect-personal-information` (mDeBERTa-v3-base token classifier; 249,618 downloads in the 30 days to 2026-11-27) | revision `255acde67a2f34cf452eb42e365b24d2957352fc` | CC BY-NC-ND 4.0 (used unmodified, for evaluation) |
| `gpt4o_mini` | OpenAI `gpt-4o-mini`, temperature 0, seed 0, JSON mode, prompt `detectors/gpt_prompt.txt` | served snapshot and system fingerprint are in every `cache/gpt/*.json` | OpenAI API terms |

Text sent to the OpenAI API: the planted and control dialogues (CoMTA, MathDial) and the 680
PIILO essays. `cache/gpt/` holds, per document, the validated span offsets and labels only; no
document text and no returned strings are stored.
