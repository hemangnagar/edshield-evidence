criteria PROVISIONAL, not ratified

# Report 2026-10-05-754e392-cand-928f50a

System under test: edshield 0.2.0 at commit 928f50a (CANDIDATE, not the pinned release). Judge: model-evidence v2.0.0. Steps: 2 run, 0 skipped.

Residuals are measured on the final output of `edshield.deidentify(verify=False)`: an identifier counts as handled only when its normalized text no longer occurs whole. A surrogate that equals a gold string counts as a residual (known conservative bias). The verdicts come from the judge CLI; nothing here computes pass/fail.

## 01_piilo_holdout_model_python

edshield 0.2.0 (rules+model, python) **meets** defined redaction criteria on evidence set piilo_holdout (sha256 bc5d0958b72eee52a7fd38b84ac4c775128eefae6f9e8acee5dbc710cea1ecf8) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **PASS**.

Policy entries dropped because the bundle has no such view: type:PHONE_NUM.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 99 | recall | 100.00% | 96.26% – 100.00% | ≥ 100.00% | pass | pass |
| identifier | 165 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| word | 427681 | fpr | 0.08% | 0.06% – 0.10% | ≤ 0.60% | pass | pass |
| type:EMAIL | 4 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:ID_NUM | 7 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:NAME_STUDENT | 143 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:STREET_ADDRESS | 1 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:URL_PERSONAL | 8 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:USERNAME | 2 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |

Axes — document: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; identifier: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; word: performance pass, stability pass (fpr, spread 0.00 pp), reproducibility pass, agreement 1.0000.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:NAME_STUDENT. Policy sha256 5641206d95587269a02a27695c5e630c5ce3435e332cf9416bd65ad0a8a08da6; input sha256 29d738001ea58de83f661105898e3de6fe777ad1bc447a94c340bd57f1cec279.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 0 of 165 | 2 | 100.00% | 0.08% | 3af296ac9c56 | 401.59 |
| seed-1 | 1 | 0 of 165 | 2 | 100.00% | 0.08% | 3af296ac9c56 | 387.92 |
| seed-2 | 2 | 0 of 165 | 2 | 100.00% | 0.08% | 3af296ac9c56 | 384.07 |
| seed-0-repeat | 0 | 0 of 165 | 2 | 100.00% | 0.08% | 3af296ac9c56 | 391.78 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

0 of 165 gold identifiers survive whole in the output (identifier recall 100.00%); 2 more survive partially (a token of ≥ 3 characters). Word view: 354 of 427387 non-identifier tokens were removed (fpr 0.08%). edshield's own leak check reported 8 leaks; alignment failures 0.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| EMAIL | 4 | 0 | 0 | 100.00% |
| ID_NUM | 7 | 0 | 0 | 100.00% |
| NAME_STUDENT | 143 | 0 | 2 | 100.00% |
| STREET_ADDRESS | 1 | 0 | 0 | 100.00% |
| URL_PERSONAL | 8 | 0 | 0 | 100.00% |
| USERNAME | 2 | 0 | 0 | 100.00% |

Label confusion (gold label → labels of acted-on entities touching it; `none` = untouched):

| gold \ acted | EMAIL | ID_NUM | NAME_STUDENT | PHONE_NUM | STREET_ADDRESS | URL_PERSONAL | USERNAME |
|---|---|---|---|---|---|---|---|
| EMAIL | 4 |  |  |  |  |  |  |
| ID_NUM |  | 6 |  | 1 |  |  |  |
| NAME_STUDENT |  |  | 143 |  |  |  |  |
| STREET_ADDRESS |  |  |  |  | 1 |  |  |
| URL_PERSONAL |  |  |  |  |  | 8 |  |
| USERNAME |  |  |  |  |  |  | 2 |

Over-redaction sample and residual text withheld: this set's text is not reproduced in reports.

## 03_k12_hard_model_python

edshield 0.2.0 (rules+model, python) **meets** defined redaction criteria on evidence set k12_hard (sha256 3da490d78315057c13668263b779ffd408f06471c8a567ff939a24b28aa1149c) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **PASS**.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 393 | recall | 97.96% | 96.04% – 98.96% | ≥ 48.30% | pass | pass |
| identifier | 1433 | recall | 99.44% | 99.02% – 99.79% | ≥ 76.60% | pass | pass |
| word | 22932 | fpr | 0.07% | 0.04% – 0.11% | ≤ 0.70% | pass | pass |
| type:AGE | 205 | recall | 99.51% | 98.48% – 100.00% | ≥ 53.10% | pass | pass |
| type:DATE | 71 | recall | 100.00% | 100.00% – 100.00% | ≥ 46.40% | pass | pass |
| type:EMAIL | 90 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:ID_NUM | 57 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:LOCATION | 122 | recall | 100.00% | 100.00% – 100.00% | ≥ 31.90% | pass | pass |
| type:NAME_RELATED | 240 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:NAME_STUDENT | 351 | recall | 98.01% | 96.38% – 99.19% | ≥ 97.40% | pass | pass |
| type:PHONE_NUM | 75 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:SCHOOL | 116 | recall | 100.00% | 100.00% – 100.00% | ≥ 36.20% | pass | pass |
| type:STREET_ADDRESS | 34 | recall | 100.00% | 100.00% – 100.00% | ≥ 0.00% | pass | pass (not required) |
| type:USERNAME | 72 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |

Axes — document: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; identifier: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; word: performance pass, stability pass (fpr, spread 0.00 pp), reproducibility pass, agreement 1.0000.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:AGE, type:DATE, type:EMAIL, type:ID_NUM, type:LOCATION, type:NAME_RELATED, type:NAME_STUDENT, type:PHONE_NUM, type:SCHOOL, type:USERNAME. Policy sha256 4f2d6dc5026cd28884af853ea56cf1b617f9a981b89fd78fe19128f3de228fb3; input sha256 2d7e8ea440c2c6e2ca62c915c641a632dcce3c9dc8e051e4b9ca25cb21bf3436.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 8 of 1433 | 23 | 99.44% | 0.07% | 3af296ac9c56 | 43.68 |
| seed-1 | 1 | 8 of 1433 | 23 | 99.44% | 0.07% | 3af296ac9c56 | 36.54 |
| seed-2 | 2 | 8 of 1433 | 23 | 99.44% | 0.07% | 3af296ac9c56 | 37.02 |
| seed-0-repeat | 0 | 8 of 1433 | 23 | 99.44% | 0.07% | 3af296ac9c56 | 36.76 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

8 of 1433 gold identifiers survive whole in the output (identifier recall 99.44%); 23 more survive partially (a token of ≥ 3 characters). Word view: 15 of 20839 non-identifier tokens were removed (fpr 0.07%). edshield's own leak check reported 0 leaks; alignment failures 0.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| AGE | 205 | 1 | 0 | 99.51% |
| DATE | 71 | 0 | 0 | 100.00% |
| EMAIL | 90 | 0 | 0 | 100.00% |
| ID_NUM | 57 | 0 | 0 | 100.00% |
| LOCATION | 122 | 0 | 0 | 100.00% |
| NAME_RELATED | 240 | 0 | 0 | 100.00% |
| NAME_STUDENT | 351 | 7 | 0 | 98.01% |
| PHONE_NUM | 75 | 0 | 0 | 100.00% |
| SCHOOL | 116 | 0 | 21 | 100.00% |
| STREET_ADDRESS | 34 | 0 | 2 | 100.00% |
| USERNAME | 72 | 0 | 0 | 100.00% |

Label confusion (gold label → labels of acted-on entities touching it; `none` = untouched):

| gold \ acted | AGE | DATE | EMAIL | ID_NUM | LOCATION | NAME_RELATED | NAME_STUDENT | PHONE_NUM | SCHOOL | STREET_ADDRESS | USERNAME | none |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AGE | 203 |  |  |  |  |  | 1 | 1 |  |  |  |  |
| DATE |  | 60 |  |  | 6 |  | 5 |  |  |  |  |  |
| EMAIL |  |  | 90 |  |  |  |  |  |  |  |  |  |
| ID_NUM |  |  |  | 57 |  |  |  |  |  |  |  |  |
| LOCATION |  |  |  |  | 122 |  |  |  |  |  |  |  |
| NAME_RELATED |  |  |  |  |  | 8 | 211 |  | 21 |  |  |  |
| NAME_STUDENT |  |  |  |  |  |  | 344 |  |  |  |  | 7 |
| PHONE_NUM |  |  |  |  |  |  |  | 75 |  |  |  |  |
| SCHOOL |  |  |  |  |  |  | 1 |  | 115 |  |  |  |
| STREET_ADDRESS |  |  |  |  |  |  |  |  |  | 34 |  |  |
| USERNAME |  |  |  |  |  |  |  |  |  |  | 72 |  |

Over-redaction sample (removed tokens outside any gold span, for human review):

- `k12h-69` `rn` as LOCATION: …riod 3 its john again lol im in carlton rn…
- `k12h-87` `r` as NAME_STUDENT: …ith my essay its due tmrw me and amanda r doing a project…
- `k12h-132` `rn` as LOCATION: …w do i cite a website im in stanleyfurt rn…
- `k12h-166` `7` as SCHOOL: … gym. Richard Nguyen Mr. Lindsey Period 7 Olivia and I built the volcano together…
- `k12h-169` `rn` as LOCATION: …im in lake jimmy rn text me 5712521746 my bday is feb 25 me…
- `k12h-169` `r` as NAME_STUDENT: …12521746 my bday is feb 25 me and brian r doing a project is it ok if my paragrap…
- `k12h-171` `rn` as LOCATION: …but idk where it is im in tannerchester rn…
- `k12h-218` `rn` as LOCATION: …ke it sound less boring im in thomaston rn…
- `k12h-235` `rn` as LOCATION: … it is my bday is feb 7 im in east lisa rn…
- `k12h-251` `r` as NAME_STUDENT: …it is add me monica.plays72 me and anna r doing a project…
- `k12h-255` `rn` as LOCATION: …ic but idk where it is im in new daniel rn 9 yr old and i still dont get it ok thx…
- `k12h-352` `rn` as LOCATION: …im in north christopherside rn i go to harvey academy can u help me wi…
- `k12h-359` `Dr.` as SCHOOL: …st time so we tried again. Kayla Howard Dr. Myers Period 5 Our class voted and most…
- `k12h-395` `Period` as SCHOOL: … tried again. Kristin Gordon Dr. Golden Period 7 When you are 12 like me you can not d…
- `k12h-397` `rn` as LOCATION: …ry about space 14m here im in tammieton rn ok thx that helps is it ok if my paragr…

Partial residuals (first 25):

- `k12h-7` SCHOOL `mosley middle school` → `school` survives (touched: SCHOOL)
- `k12h-7` SCHOOL `mosley middle school` → `school` survives (touched: SCHOOL)
- `k12h-8` STREET_ADDRESS `Ross Drive` → `drive` survives (touched: STREET_ADDRESS)
- `k12h-12` SCHOOL `griffith high school` → `school` survives (touched: SCHOOL)
- `k12h-18` SCHOOL `vazquez elementary school` → `school` survives (touched: SCHOOL)
- `k12h-30` SCHOOL `hernandez elementary school` → `school` survives (touched: SCHOOL)
- `k12h-69` SCHOOL `reese elementary school` → `school` survives (touched: SCHOOL)
- `k12h-90` SCHOOL `ross high school` → `school` survives (touched: SCHOOL)
- `k12h-138` SCHOOL `johnson middle school` → `school` survives (touched: SCHOOL)
- `k12h-180` SCHOOL `richards elementary school` → `school` survives (touched: SCHOOL)
- `k12h-212` SCHOOL `molina high school` → `school` survives (touched: SCHOOL)
- `k12h-213` SCHOOL `riley elementary school` → `school` survives (touched: SCHOOL)
- `k12h-228` SCHOOL `cooper elementary school` → `school` survives (touched: SCHOOL)
- `k12h-236` STREET_ADDRESS `Silva Drive` → `drive` survives (touched: STREET_ADDRESS)
- `k12h-256` SCHOOL `mcbride high school` → `school` survives (touched: SCHOOL)
- `k12h-259` SCHOOL `castaneda elementary school` → `school` survives (touched: SCHOOL)
- `k12h-309` SCHOOL `brown high school` → `school` survives (touched: SCHOOL)
- `k12h-325` SCHOOL `stone middle school` → `school` survives (touched: SCHOOL)
- `k12h-325` SCHOOL `stone middle school` → `school` survives (touched: SCHOOL)
- `k12h-338` SCHOOL `boyd elementary school` → `school` survives (touched: SCHOOL)
- `k12h-338` SCHOOL `boyd elementary school` → `school` survives (touched: SCHOOL)
- `k12h-358` SCHOOL `porter elementary school` → `school` survives (touched: SCHOOL)
- `k12h-368` SCHOOL `bishop high school` → `school` survives (touched: SCHOOL)
