criteria PROVISIONAL, not ratified

# Report 2026-10-05-f368ecb-cand-c7be261

System under test: edshield 0.2.0 at commit c7be261 (CANDIDATE, not the pinned release). Judge: model-evidence v2.0.0. Steps: 3 run, 0 skipped.

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

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:NAME_STUDENT. Policy sha256 5641206d95587269a02a27695c5e630c5ce3435e332cf9416bd65ad0a8a08da6; input sha256 a35d88094fa5b543dc5144342135f62e3c624c2f024bfbbfa636f99dd8f06e4e.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 0 of 165 | 1 | 100.00% | 0.08% | 71af3248048b | 372.38 |
| seed-1 | 1 | 0 of 165 | 1 | 100.00% | 0.08% | 71af3248048b | 372.17 |
| seed-2 | 2 | 0 of 165 | 1 | 100.00% | 0.08% | 71af3248048b | 371.98 |
| seed-0-repeat | 0 | 0 of 165 | 1 | 100.00% | 0.08% | 71af3248048b | 371.76 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

0 of 165 gold identifiers survive whole in the output (identifier recall 100.00%); 1 more survive partially (a token of ≥ 3 characters). Word view: 331 of 427387 non-identifier tokens were removed (fpr 0.08%). edshield's own leak check reported 5 leaks; alignment failures 0.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| EMAIL | 4 | 0 | 0 | 100.00% |
| ID_NUM | 7 | 0 | 0 | 100.00% |
| NAME_STUDENT | 143 | 0 | 1 | 100.00% |
| STREET_ADDRESS | 1 | 0 | 0 | 100.00% |
| URL_PERSONAL | 8 | 0 | 0 | 100.00% |
| USERNAME | 2 | 0 | 0 | 100.00% |

Label confusion (gold label → labels of acted-on entities touching it; `none` = untouched):

| gold \ acted | EMAIL | ID_NUM | NAME_STUDENT | STREET_ADDRESS | URL_PERSONAL | USERNAME |
|---|---|---|---|---|---|---|
| EMAIL | 4 |  |  |  |  |  |
| ID_NUM |  | 7 |  |  |  |  |
| NAME_STUDENT |  |  | 143 |  |  |  |
| STREET_ADDRESS |  |  |  | 1 |  |  |
| URL_PERSONAL |  |  |  |  | 8 |  |
| USERNAME |  |  |  |  |  | 2 |

Over-redaction sample and residual text withheld: this set's text is not reproduced in reports.

## 03_k12_hard_model_python

edshield 0.2.0 (rules+model, python) **meets** defined redaction criteria on evidence set k12_hard (sha256 3da490d78315057c13668263b779ffd408f06471c8a567ff939a24b28aa1149c) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **PASS**.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 393 | recall | 67.94% | 63.17% – 72.36% | ≥ 48.30% | pass | pass |
| identifier | 1433 | recall | 88.49% | 86.57% – 90.30% | ≥ 76.60% | pass | pass |
| word | 22932 | fpr | 0.13% | 0.08% – 0.18% | ≤ 0.70% | pass | pass |
| type:AGE | 205 | recall | 99.51% | 98.48% – 100.00% | ≥ 53.10% | pass | pass |
| type:DATE | 71 | recall | 100.00% | 100.00% – 100.00% | ≥ 46.40% | pass | pass |
| type:EMAIL | 90 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:ID_NUM | 57 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:LOCATION | 122 | recall | 31.97% | 23.14% – 41.18% | ≥ 31.90% | pass | pass |
| type:NAME_RELATED | 240 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:NAME_STUDENT | 351 | recall | 97.44% | 95.08% – 99.41% | ≥ 97.40% | pass | pass |
| type:PHONE_NUM | 75 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:SCHOOL | 116 | recall | 67.24% | 57.14% – 75.68% | ≥ 36.20% | pass | pass |
| type:STREET_ADDRESS | 34 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass (not required) |
| type:USERNAME | 72 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |

Axes — document: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; identifier: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; word: performance pass, stability pass (fpr, spread 0.00 pp), reproducibility pass, agreement 1.0000.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:AGE, type:DATE, type:EMAIL, type:ID_NUM, type:LOCATION, type:NAME_RELATED, type:NAME_STUDENT, type:PHONE_NUM, type:SCHOOL, type:USERNAME. Policy sha256 4f2d6dc5026cd28884af853ea56cf1b617f9a981b89fd78fe19128f3de228fb3; input sha256 b484fd6ae1bca21a5bae4fc63ec4e3c2fa8f458cbabb95ee0e1474953b794246.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 165 of 1433 | 45 | 88.49% | 0.13% | 71af3248048b | 42.5 |
| seed-1 | 1 | 165 of 1433 | 45 | 88.49% | 0.13% | 71af3248048b | 33.63 |
| seed-2 | 2 | 165 of 1433 | 45 | 88.49% | 0.13% | 71af3248048b | 33.91 |
| seed-0-repeat | 0 | 165 of 1433 | 45 | 88.49% | 0.13% | 71af3248048b | 34.12 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

165 of 1433 gold identifiers survive whole in the output (identifier recall 88.49%); 45 more survive partially (a token of ≥ 3 characters). Word view: 27 of 20839 non-identifier tokens were removed (fpr 0.13%). edshield's own leak check reported 2 leaks; alignment failures 0.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| AGE | 205 | 1 | 0 | 99.51% |
| DATE | 71 | 0 | 0 | 100.00% |
| EMAIL | 90 | 0 | 3 | 100.00% |
| ID_NUM | 57 | 0 | 0 | 100.00% |
| LOCATION | 122 | 83 | 18 | 31.97% |
| NAME_RELATED | 240 | 0 | 0 | 100.00% |
| NAME_STUDENT | 351 | 9 | 0 | 97.44% |
| PHONE_NUM | 75 | 0 | 0 | 100.00% |
| SCHOOL | 116 | 38 | 21 | 67.24% |
| STREET_ADDRESS | 34 | 34 | 0 | 0.00% |
| USERNAME | 72 | 0 | 3 | 100.00% |

Label confusion (gold label → labels of acted-on entities touching it; `none` = untouched):

| gold \ acted | AGE | DATE | EMAIL | ID_NUM | NAME_RELATED | NAME_STUDENT | PHONE_NUM | SCHOOL | STREET_ADDRESS | USERNAME | none |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AGE | 203 |  | 1 | 1 |  |  |  |  |  |  |  |
| DATE |  | 69 |  |  |  | 2 |  |  |  |  |  |
| EMAIL |  |  | 90 |  |  |  |  |  |  |  |  |
| ID_NUM |  |  |  | 57 |  |  |  |  |  |  |  |
| LOCATION |  |  |  | 1 |  | 25 |  |  | 3 | 11 | 83 |
| NAME_RELATED |  |  |  |  | 40 | 200 |  |  |  |  |  |
| NAME_STUDENT |  |  |  |  |  | 343 |  |  |  |  | 8 |
| PHONE_NUM |  |  |  | 72 |  |  | 3 |  |  |  |  |
| SCHOOL |  |  |  |  |  | 42 |  | 36 |  |  | 38 |
| STREET_ADDRESS |  |  |  |  |  |  |  |  |  |  | 34 |
| USERNAME |  |  |  | 2 |  | 10 |  |  |  | 68 |  |

Over-redaction sample (removed tokens outside any gold span, for human review):

- `k12h-4` `tmrw` as ID_NUM: … is can u help me with my essay its due tmrw text me 5710901610 CHARLES CLINE period…
- `k12h-12` `rn` as EMAIL: …im in west amyside rn helenlittle at gmail dot com i go to gr…
- `k12h-15` `tmrw` as NAME_STUDENT: …lol can u help me with my essay its due tmrw VICTORIA CAMPBELL period 3 11 yr old an…
- `k12h-25` `its` as EMAIL: … you explain how you got that? Student: its reneeward at gmail dot com Tutor: Nice …
- `k12h-27` `tmrw` as ID_NUM: …btw can u help me with my essay its due tmrw text me 5715549031…
- `k12h-47` `tmrw` as EMAIL: …ite can u help me with my essay its due tmrw susanmayer at gmail dot com im in bergs…
- `k12h-47` `tmrw` as NAME_STUDENT: …lps can u help me with my essay its due tmrw susanmayer at gmail dot com 7 yr old an…
- `k12h-48` `rn` as USERNAME: …im in new jamesbury rn kathrynrocha at gmail dot com kathrynro…
- `k12h-66` `rn` as NAME_STUDENT: …l r doing a project im in north stephen rn my teacher said to use the rubric but i…
- `k12h-87` `r` as NAME_STUDENT: …ith my essay its due tmrw me and amanda r doing a project…
- `k12h-108` `tmrw` as ID_NUM: …ces can u help me with my essay its due tmrw text me 5714008023…
- `k12h-116` `tmrw` as EMAIL: …lps can u help me with my essay its due tmrw kevinmoore at gmail dot com is it ok if…
- `k12h-129` `tmrw` as USERNAME: …ing can u help me with my essay its due tmrw…
- `k12h-132` `rn` as USERNAME: …w do i cite a website im in stanleyfurt rn…
- `k12h-143` `rn` as NAME_STUDENT: …3 add me shelley.xd99 im in port george rn is it ok if my paragraph is only 4 sent…
- `k12h-163` `tmrw` as EMAIL: … it can u help me with my essay its due tmrw karenortega at gmail dot com…
- `k12h-169` `rn` as NAME_STUDENT: …im in lake jimmy rn text me 5712521746 my bday is feb 25 me…
- `k12h-169` `r` as NAME_STUDENT: …12521746 my bday is feb 25 me and brian r doing a project is it ok if my paragrap…
- `k12h-192` `tmrw` as NAME_STUDENT: …can u help me with my essay its due tmrw 15 yr old and i still dont get it add m…
- `k12h-223` `tmrw` as USERNAME: …d 3 can u help me with my essay its due tmrw 14m here ok thx that helps im cassandra…
- `k12h-235` `rn` as NAME_STUDENT: … it is my bday is feb 7 im in east lisa rn…
- `k12h-255` `rn` as NAME_STUDENT: …ic but idk where it is im in new daniel rn 9 yr old and i still dont get it ok thx…
- `k12h-305` `tmrw` as NAME_STUDENT: … rn can u help me with my essay its due tmrw TIFFANY COLEMAN period 3 is it ok if my…
- `k12h-316` `rn` as EMAIL: …im in amandafort rn kristenoconnor at gmail dot com im kris…
- `k12h-351` `r` as NAME_STUDENT: …it how do i cite a website me and jason r doing a project is it ok if my paragrap…
- `k12h-375` `tmrw` as USERNAME: …ing can u help me with my essay its due tmrw ok thx that helps add me kristin_plays2…
- `k12h-393` `tmrw` as NAME_STUDENT: … it can u help me with my essay its due tmrw whats a good hook for a story about spa…

Partial residuals (first 25):

- `k12h-7` SCHOOL `mosley middle school` → `school` survives (touched: SCHOOL)
- `k12h-7` SCHOOL `mosley middle school` → `school` survives (touched: SCHOOL)
- `k12h-9` LOCATION `west alicia` → `west` survives (touched: NAME_STUDENT)
- `k12h-12` LOCATION `west amyside` → `west` survives (touched: USERNAME)
- `k12h-12` SCHOOL `griffith high school` → `school` survives (touched: SCHOOL)
- `k12h-18` SCHOOL `vazquez elementary school` → `school` survives (touched: SCHOOL)
- `k12h-30` SCHOOL `hernandez elementary school` → `school` survives (touched: SCHOOL)
- `k12h-48` LOCATION `new jamesbury` → `new` survives (touched: USERNAME)
- `k12h-66` LOCATION `north stephen` → `north` survives (touched: NAME_STUDENT)
- `k12h-69` SCHOOL `reese elementary school` → `school` survives (touched: SCHOOL)
- `k12h-90` SCHOOL `ross high school` → `school` survives (touched: SCHOOL)
- `k12h-96` LOCATION `West Leslie` → `west` survives (touched: NAME_STUDENT)
- `k12h-121` LOCATION `East Gabrieltown` → `east` survives (touched: STREET_ADDRESS)
- `k12h-137` LOCATION `Lake Natalie` → `lake` survives (touched: NAME_STUDENT)
- `k12h-138` SCHOOL `johnson middle school` → `school` survives (touched: SCHOOL)
- `k12h-143` LOCATION `port george` → `port` survives (touched: NAME_STUDENT)
- `k12h-172` LOCATION `port samantha` → `port` survives (touched: NAME_STUDENT)
- `k12h-179` LOCATION `new samantha` → `new` survives (touched: NAME_STUDENT)
- `k12h-179` LOCATION `new samantha` → `new` survives (touched: NAME_STUDENT)
- `k12h-180` SCHOOL `richards elementary school` → `school` survives (touched: SCHOOL)
- `k12h-206` LOCATION `South Tylerport` → `south` survives (touched: STREET_ADDRESS)
- `k12h-212` SCHOOL `molina high school` → `school` survives (touched: SCHOOL)
- `k12h-212` EMAIL `patriciagarcia at gmail dot com` → `gmail` survives (touched: EMAIL)
- `k12h-212` EMAIL `patriciagarcia at gmail dot com` → `gmail` survives (touched: EMAIL)
- `k12h-213` SCHOOL `riley elementary school` → `school` survives (touched: SCHOOL)

## 04_k12_hard_rules_python

edshield 0.2.0 (rules, python) **meets** defined redaction criteria on evidence set k12_hard (sha256 3da490d78315057c13668263b779ffd408f06471c8a567ff939a24b28aa1149c) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **PASS**.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 393 | recall | 6.87% | 4.76% – 9.81% | ≥ 3.30% | pass | pass |
| identifier | 1433 | recall | 34.12% | 31.72% – 36.48% | ≥ 22.10% | pass | pass |
| word | 22932 | fpr | 0.00% | 0.00% – 0.00% | ≤ 0.50% | pass | pass |
| type:AGE | 205 | recall | 99.51% | 98.48% – 100.00% | ≥ 52.10% | pass | pass |
| type:DATE | 71 | recall | 100.00% | 100.00% – 100.00% | ≥ 46.40% | pass | pass |
| type:EMAIL | 90 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass |
| type:ID_NUM | 57 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:LOCATION | 122 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass |
| type:NAME_RELATED | 240 | recall | 18.75% | 13.91% – 24.10% | ≥ 18.70% | pass | pass |
| type:NAME_STUDENT | 351 | recall | 0.28% | 0.00% – 0.87% | ≥ 0.20% | pass | pass |
| type:PHONE_NUM | 75 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:SCHOOL | 116 | recall | 31.03% | 22.12% – 39.48% | ≥ 0.00% | pass | pass |
| type:STREET_ADDRESS | 34 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass (not required) |
| type:USERNAME | 72 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass |

Axes — document: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; identifier: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; word: performance pass, stability pass (fpr, spread 0.00 pp), reproducibility pass, agreement 1.0000.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:AGE, type:DATE, type:EMAIL, type:ID_NUM, type:LOCATION, type:NAME_RELATED, type:NAME_STUDENT, type:PHONE_NUM, type:SCHOOL, type:USERNAME. Policy sha256 ba84826dfe470a6d3988e240b993d36123c175b6f39dc55eb88ea2d4fb6a2385; input sha256 0e362e2a3768f0c6adfaa490b70a10928b9c3551fb4817f0e7dd0bbc87f24a90.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 944 of 1433 | 22 | 34.12% | 0.00% | 1e603a8b6b83 | 2.08 |
| seed-1 | 1 | 944 of 1433 | 22 | 34.12% | 0.00% | 1e603a8b6b83 | 2.07 |
| seed-2 | 2 | 944 of 1433 | 22 | 34.12% | 0.00% | 1e603a8b6b83 | 2.08 |
| seed-0-repeat | 0 | 944 of 1433 | 22 | 34.12% | 0.00% | 1e603a8b6b83 | 2.05 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

944 of 1433 gold identifiers survive whole in the output (identifier recall 34.12%); 22 more survive partially (a token of ≥ 3 characters). Word view: 0 of 20839 non-identifier tokens were removed (fpr 0.00%). edshield's own leak check reported 0 leaks; alignment failures 0.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| AGE | 205 | 1 | 0 | 99.51% |
| DATE | 71 | 0 | 0 | 100.00% |
| EMAIL | 90 | 90 | 0 | 0.00% |
| ID_NUM | 57 | 0 | 0 | 100.00% |
| LOCATION | 122 | 122 | 0 | 0.00% |
| NAME_RELATED | 240 | 195 | 0 | 18.75% |
| NAME_STUDENT | 351 | 350 | 1 | 0.28% |
| PHONE_NUM | 75 | 0 | 0 | 100.00% |
| SCHOOL | 116 | 80 | 21 | 31.03% |
| STREET_ADDRESS | 34 | 34 | 0 | 0.00% |
| USERNAME | 72 | 72 | 0 | 0.00% |

Label confusion (gold label → labels of acted-on entities touching it; `none` = untouched):

| gold \ acted | AGE | DATE | ID_NUM | NAME_RELATED | PHONE_NUM | SCHOOL | STREET_ADDRESS | none |
|---|---|---|---|---|---|---|---|---|
| AGE | 204 |  |  |  |  |  | 1 |  |
| DATE |  | 71 |  |  |  |  |  |  |
| EMAIL |  |  |  |  |  |  |  | 90 |
| ID_NUM |  |  | 57 |  |  |  |  |  |
| LOCATION |  |  |  |  |  |  |  | 122 |
| NAME_RELATED |  |  |  | 45 |  |  |  | 195 |
| NAME_STUDENT |  |  |  |  |  |  | 1 | 350 |
| PHONE_NUM |  |  |  |  | 75 |  |  |  |
| SCHOOL |  |  |  |  |  | 36 |  | 80 |
| STREET_ADDRESS |  |  |  |  |  |  |  | 34 |
| USERNAME |  |  |  |  |  |  |  | 72 |

Partial residuals (first 25):

- `k12h-7` SCHOOL `mosley middle school` → `school` survives (touched: SCHOOL)
- `k12h-7` SCHOOL `mosley middle school` → `school` survives (touched: SCHOOL)
- `k12h-12` SCHOOL `griffith high school` → `school` survives (touched: SCHOOL)
- `k12h-18` SCHOOL `vazquez elementary school` → `school` survives (touched: SCHOOL)
- `k12h-30` SCHOOL `hernandez elementary school` → `school` survives (touched: SCHOOL)
- `k12h-69` SCHOOL `reese elementary school` → `school` survives (touched: SCHOOL)
- `k12h-90` SCHOOL `ross high school` → `school` survives (touched: SCHOOL)
- `k12h-138` SCHOOL `johnson middle school` → `school` survives (touched: SCHOOL)
- `k12h-158` NAME_STUDENT `Jessica Hill` → `jessica` survives (touched: STREET_ADDRESS)
- `k12h-180` SCHOOL `richards elementary school` → `school` survives (touched: SCHOOL)
- `k12h-212` SCHOOL `molina high school` → `school` survives (touched: SCHOOL)
- `k12h-213` SCHOOL `riley elementary school` → `school` survives (touched: SCHOOL)
- `k12h-228` SCHOOL `cooper elementary school` → `school` survives (touched: SCHOOL)
- `k12h-256` SCHOOL `mcbride high school` → `school` survives (touched: SCHOOL)
- `k12h-259` SCHOOL `castaneda elementary school` → `school` survives (touched: SCHOOL)
- `k12h-309` SCHOOL `brown high school` → `school` survives (touched: SCHOOL)
- `k12h-325` SCHOOL `stone middle school` → `school` survives (touched: SCHOOL)
- `k12h-325` SCHOOL `stone middle school` → `school` survives (touched: SCHOOL)
- `k12h-338` SCHOOL `boyd elementary school` → `school` survives (touched: SCHOOL)
- `k12h-338` SCHOOL `boyd elementary school` → `school` survives (touched: SCHOOL)
- `k12h-358` SCHOOL `porter elementary school` → `school` survives (touched: SCHOOL)
- `k12h-368` SCHOOL `bishop high school` → `school` survives (touched: SCHOOL)
