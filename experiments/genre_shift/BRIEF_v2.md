# Handoff brief: genre-shift experiment v2 (baselines, seeds, floor transfer)

**Repo:** `hemangnagar/edshield-evidence`. Branch from `exp/genre-shift-planted` into **`exp/genre-shift-v2`**. Reuse `plant.py`, `score.py`, the four name lists and the normalised dialogue schema from v1; extend, don't rewrite.
**Do not modify** `edshield` or `model-evidence`. Pin `edshield==0.2.0`, model `edshield/piilo-deberta-v3-small` rev `5effafd`.
**Purpose:** turn the v1 finding ("our model drops on tutoring dialogue") into a paper-grade result: (a) the drop is general across PII detectors, (b) it is stable across seeds and corpora, (c) per-form recall floors measured on one genre predict recall on another. Output feeds an EDM 2027 submission (Feb 15) and an NSF portal response (Jan 10). Honest results in either direction are the deliverable; nothing is tuned.

## 1. Corpora

| | Dataset | Status | Notes |
|---|---|---|---|
| in-domain ref | PIILO held-out | have | same as v1 |
| G1 | CoMTA (188, real students ↔ Khanmigo) | have | |
| G2 | MathDial test split (599, human tutors, simulated students) | have | |
| G3 | **StudyChat** (`huggingface.co/datasets/wmcnicho/StudyChat`; real university students ↔ ChatGPT, CS course) | **add** | normalise to the v1 schema; sample ≤600 dialogues deterministically if larger |
| G4 | TSCC v2 (Cambridge ESL chatroom) | only if present in `data/raw/tscc/` | loader interface already exists; never block on it |

Record source URL, version/commit, license in `data/SOURCES.md`. Each raw download in its own directory; treat as untrusted.

## 2. Planting — five seeds

Run `plant.py` with seeds `20261014, 20261015, 20261016, 20261017, 20261018`. Same rules as v1 (natural slots, register-matched, one name category per dialogue, 1-in-4 later mentions as nickname/initial). Control (no-plant) is seed-independent; run once.

**Every planted mention gets a surface-form record** written to the gold file:
- `case`: `lower` / `cap` / `allcaps`
- `speaker`: `student` / `tutor`
- `position`: `first` / `later`
- `category`: `anglo_common` / `non_anglo` / `name_word_collision` / `nicknames_and_variants`
- `is_dict_word`: name (lowercased) is in an English word list (bool)
- `n_wordpieces`: DeBERTa-v3 tokenizer piece count for the name
- `is_initial`: bool

**Primary stratification** = `case × speaker × is_dict_word` (8 strata). Everything else is secondary analysis. Keep the stratum definition in one function; the paper will quote it.

## 3. Detectors (five)

All run on identical planted files. Evaluate **name recall** (gold = planted `NAME_STUDENT` + `NAME_RELATED` spans) as the primary metric; school/email/phone recall secondary. Map each detector's output to {NAME, SCHOOL, EMAIL, PHONE, OTHER} via a documented table in `detectors/labelmap.py`.

| id | Detector | Setup |
|---|---|---|
| `edshield` | edshield 0.2.0, rev 5effafd | as v1; no threshold change |
| `presidio` | Microsoft Presidio Analyzer, default recognizers, `en_core_web_lg` | PERSON → NAME; LOCATION/ORG → SCHOOL only if "school/academy/high/middle" token adjacent, else OTHER |
| `spacy_trf` | `en_core_web_trf` NER | PERSON → NAME |
| `hf_pii` | one public token-classification PII model from Hugging Face (e.g. `iiiorg/piiranha-v1-detect-personal-information`; pick one with >10k downloads, record exact id + revision) | its name labels → NAME |
| `gpt4o_mini` | `gpt-4o-mini` via OpenAI API, temperature 0, seed 0, JSON mode | prompt in `detectors/gpt_prompt.txt`: "Return every span that is a person's name, school name, email, phone, username as JSON [{start,end,label}]". Char offsets validated; unparseable → retry once, then count as no-flag and log. **Cache every response** to `cache/gpt/<sha256(text)>.json`. Hard cost cap `$30` via env `GPT_BUDGET_USD`; stop and report if hit. Key via `OPENAI_API_KEY`; never commit. |

Span matching: a gold span is caught if any predicted NAME span overlaps ≥50% of its characters (v1 rule). Also report exact-match recall as secondary.

## 4. Metrics (`results/v2/metrics.json`, one schema, all detectors)

Per detector × dataset, and pooled across G1–G3:
- name recall: per-seed values, **mean ± SD across seeds**, and pooled Wilson 95% CI over all seeds' mentions
- recall per primary stratum (pooled over seeds) with **exact binomial (Clopper–Pearson) 95% lower bound**
- recall by `category`, `position`, `n_wordpieces` (secondary)
- precision on planted set
- **over-redaction on control**: NAME flags per 1,000 tokens; share on curricular terms (v1 list); share on word-problem characters (MathDial) — per detector
- PIILO in-domain recall, same metrics, same detectors

## 5. Floor-transfer test (the new result — H1 in miniature)

For every ordered genre pair (A → B) over {G1, G2, G3} (+G4 if present) and every detector:

1. On A: per-stratum recall `r_s` and Clopper–Pearson lower bound `lb_s` (pooled over seeds).
2. On B: stratum mix `w_s` = share of B's gold mentions in stratum s.
3. **Predicted point** = Σ w_s·r_s. **Predicted floor** = Σ w_s·lb_s.
4. Compare to B's **measured** pooled recall. Report: error = predicted point − measured (percentage points); `floor_valid` = (predicted floor ≤ measured).

Two variants of step 2, both reported:
- **oracle mix**: `w_s` from B's gold mentions (what Phase I sealed sets would give)
- **caught-only mix**: `w_s` from B's *caught* mentions only — the only mix a deployed redactor can log. The gap between the two variants is the missing-not-at-random bias, in points. This number goes in the paper.

Ablation: repeat with coarser strata (`case` only; `case × speaker`) and finer (`× category`). Report error for each. This answers "do the strata suffice."

Probe cost: for each primary stratum, n required for a 99.5% floor at 95% (3/n rule) and the n observed; list strata that were zero-miss at the observed n.

## 6. Outputs — generated by scripts, nothing hand-made

Tables (CSV + Markdown in `results/v2/tables/`):
- T1 name recall, detector × dataset (mean ± SD, pooled CI)
- T2 recall by primary stratum, detector × stratum (pooled, with lower bounds)
- T3 floor-transfer matrix: A→B × detector → error, floor_valid, for oracle and caught-only mix
- T4 over-redaction, detector × dataset
- T5 stratum ablation: strata set → mean |error|

Figures (PNG 300 dpi + PDF, `results/v2/figures/`, matplotlib, neutral palette, colourblind-safe, direct labels not legends where possible):
- F1 grouped bars, recall by dataset with one bar per detector, PIILO leftmost, error bars = pooled CI
- F2 heatmap, primary stratum × detector, cell = recall, annotated
- F3 scatter, predicted vs measured recall, one point per (pair × detector), diagonal reference, hollow = caught-only mix, filled = oracle mix
- F4 over-redaction bars per detector (flags/1k tokens), curricular share stacked

`results/v2/misses.csv` as v1, now with detector column and the surface-form fields.

`findings_v2.md` ≤600 words, numbers first, in this order: (1) is the drop general — recall by detector on dialogue vs essays; (2) do misses follow form for every detector — the stratum heatmap in words; (3) floor transfer — mean error, worst pair, how much the caught-only mix is biased, which strata set is needed; (4) over-redaction by detector; (5) three verbatim miss examples that at least three detectors share; (6) one sentence each on what this supports and what it does not.

## 7. Constraints

- No real PII in the repo, ever. Names come only from the lists. If raw data contains an unscrubbed email/phone, report it in findings and don't commit it.
- Reproducible from `make v2` with the fixed seeds; `make v2-nogpt` skips the API detector. Log package versions, model revisions, GPU/CPU.
- spaCy trf and the HF model may want GPU; everything else CPU. Batch.
- Keep code small; extend v1 scripts rather than build a framework.
- Time box: three working days. If StudyChat's loader takes more than an hour, say so and continue with G1–G2.

## 8. Definition of done

`findings_v2.md`, `results/v2/{metrics.json, tables/, figures/, misses.csv}`, `data/SOURCES.md` updated, `detectors/labelmap.py` and `detectors/gpt_prompt.txt` committed, GPT cache committed (responses contain only planted names), on `exp/genre-shift-v2`, PR open against `main` whose description is finding (1) and finding (3) in two sentences each.
