criteria PROVISIONAL, not ratified

# Report 2026-10-04-c60e4e0

System under test: edshield 0.2.0 (source commit a568e73). Judge: model-evidence v2.0.0. Steps: 1 run, 3 skipped.

- skipped `01_piilo_holdout_model_python`: torch/transformers are not installed (pip install -e '.[hf]'); the model steps run locally
- skipped `02_piilo_holdout_model_parity`: torch/transformers are not installed (pip install -e '.[hf]'); the model steps run locally
- skipped `03_k12_hard_model_python`: torch/transformers are not installed (pip install -e '.[hf]'); the model steps run locally

Residuals are measured on the final output of `edshield.deidentify(verify=False)`: an identifier counts as handled only when its normalized text no longer occurs whole. A surrogate that equals a gold string counts as a residual (known conservative bias). The verdicts come from the judge CLI; nothing here computes pass/fail.

## 04_k12_hard_rules_python

edshield 0.2.0 (rules, python) **meets** defined redaction criteria on evidence set k12_hard (sha256 3da490d78315057c13668263b779ffd408f06471c8a567ff939a24b28aa1149c) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **PASS**.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 393 | recall | 3.31% | 1.94% – 5.58% | ≥ 3.30% | pass | pass |
| identifier | 1433 | recall | 22.19% | 20.01% – 24.27% | ≥ 22.10% | pass | pass |
| word | 22932 | fpr | 0.00% | 0.00% – 0.00% | ≤ 0.50% | pass | pass |
| type:AGE | 205 | recall | 52.20% | 44.55% – 59.72% | ≥ 52.10% | pass | pass |
| type:DATE | 71 | recall | 46.48% | 34.72% – 57.90% | ≥ 46.40% | pass | pass |
| type:EMAIL | 90 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass |
| type:ID_NUM | 57 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:LOCATION | 122 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass |
| type:NAME_RELATED | 240 | recall | 18.75% | 13.91% – 24.10% | ≥ 18.70% | pass | pass |
| type:NAME_STUDENT | 351 | recall | 0.28% | 0.00% – 0.87% | ≥ 0.20% | pass | pass |
| type:PHONE_NUM | 75 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:SCHOOL | 116 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass |
| type:STREET_ADDRESS | 34 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass (not required) |
| type:USERNAME | 72 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass |

Axes — document: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; identifier: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; word: performance pass, stability pass (fpr, spread 0.00 pp), reproducibility pass, agreement 1.0000.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:AGE, type:DATE, type:EMAIL, type:ID_NUM, type:LOCATION, type:NAME_RELATED, type:NAME_STUDENT, type:PHONE_NUM, type:SCHOOL, type:USERNAME. Policy sha256 602391114c566235c8767069af678f12c425e46e2b99fda4ef615dfd6f5e3407; input sha256 845c4e34040c2c3cbeda1a3e88e401fba76f2133bb9d7d45b9c61851e79b064f.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 1115 of 1433 | 1 | 22.19% | 0.00% | 8e7f0fdf14a3 | 1.72 |
| seed-1 | 1 | 1115 of 1433 | 1 | 22.19% | 0.00% | 8e7f0fdf14a3 | 1.67 |
| seed-2 | 2 | 1115 of 1433 | 1 | 22.19% | 0.00% | 8e7f0fdf14a3 | 1.79 |
| seed-0-repeat | 0 | 1115 of 1433 | 1 | 22.19% | 0.00% | 8e7f0fdf14a3 | 1.83 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

1115 of 1433 gold identifiers survive whole in the output (identifier recall 22.19%); 1 more survive partially (a token of ≥ 3 characters). Word view: 0 of 20839 non-identifier tokens were removed (fpr 0.00%). edshield's own leak check reported 0 leaks; alignment failures 0.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| AGE | 205 | 98 | 0 | 52.20% |
| DATE | 71 | 38 | 0 | 46.48% |
| EMAIL | 90 | 90 | 0 | 0.00% |
| ID_NUM | 57 | 0 | 0 | 100.00% |
| LOCATION | 122 | 122 | 0 | 0.00% |
| NAME_RELATED | 240 | 195 | 0 | 18.75% |
| NAME_STUDENT | 351 | 350 | 1 | 0.28% |
| PHONE_NUM | 75 | 0 | 0 | 100.00% |
| SCHOOL | 116 | 116 | 0 | 0.00% |
| STREET_ADDRESS | 34 | 34 | 0 | 0.00% |
| USERNAME | 72 | 72 | 0 | 0.00% |

Label confusion (gold label → labels of acted-on entities touching it; `none` = untouched):

| gold \ acted | AGE | DATE | ID_NUM | NAME_RELATED | PHONE_NUM | STREET_ADDRESS | none |
|---|---|---|---|---|---|---|---|
| AGE | 120 |  |  |  |  | 1 | 84 |
| DATE |  | 33 |  |  |  |  | 38 |
| EMAIL |  |  |  |  |  |  | 90 |
| ID_NUM |  |  | 57 |  |  |  |  |
| LOCATION |  |  |  |  |  |  | 122 |
| NAME_RELATED |  |  |  | 45 |  |  | 195 |
| NAME_STUDENT |  |  |  |  |  | 1 | 350 |
| PHONE_NUM |  |  |  |  | 75 |  |  |
| SCHOOL |  |  |  |  |  |  | 116 |
| STREET_ADDRESS |  |  |  |  |  |  | 34 |
| USERNAME |  |  |  |  |  |  | 72 |

Partial residuals (first 25):

- `k12h-158` NAME_STUDENT `Jessica Hill` → `jessica` survives (touched: STREET_ADDRESS)
