criteria PROVISIONAL, not ratified

# Report 2026-10-04-6c0f163

System under test: edshield 0.2.0 (source commit a568e73). Judge: model-evidence v2.0.0. Steps: 4 run, 0 skipped.

Residuals are measured on the final output of `edshield.deidentify(verify=False)`: an identifier counts as handled only when its normalized text no longer occurs whole. A surrogate that equals a gold string counts as a residual (known conservative bias). The verdicts come from the judge CLI; nothing here computes pass/fail.

## 01_piilo_holdout_model_python

edshield 0.2.0 (rules+model, python) **meets** defined redaction criteria on evidence set piilo_holdout (sha256 bc5d0958b72eee52a7fd38b84ac4c775128eefae6f9e8acee5dbc710cea1ecf8) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **PASS**.

Policy entries dropped because the bundle has no such view: type:PHONE_NUM.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 99 | recall | 100.00% | 96.26% – 100.00% | ≥ 100.00% | pass | pass |
| identifier | 165 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| word | 427681 | fpr | 0.07% | 0.05% – 0.08% | ≤ 5.00% | pass | pass |
| type:EMAIL | 4 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:ID_NUM | 7 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:NAME_STUDENT | 143 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:STREET_ADDRESS | 1 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:URL_PERSONAL | 8 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:USERNAME | 2 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |

Axes — document: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; identifier: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; word: performance pass, stability pass (fpr, spread 0.00 pp), reproducibility pass, agreement 1.0000.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:NAME_STUDENT. Policy sha256 b1246ce7473d480ca2cc97f3d29e9ba820ee35be4e7579e6f23a3d762fc61de7; input sha256 db89e821e0e73e30037762215e626a9024540b7ec88be6257bdaf990baa107dc.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 0 of 165 | 1 | 100.00% | 0.07% | 71af3248048b | 377.85 |
| seed-1 | 1 | 0 of 165 | 1 | 100.00% | 0.07% | 71af3248048b | 386.36 |
| seed-2 | 2 | 0 of 165 | 1 | 100.00% | 0.07% | 71af3248048b | 381.39 |
| seed-0-repeat | 0 | 0 of 165 | 1 | 100.00% | 0.07% | 71af3248048b | 381.22 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

0 of 165 gold identifiers survive whole in the output (identifier recall 100.00%); 1 more survive partially (a token of ≥ 3 characters). Word view: 281 of 427387 non-identifier tokens were removed (fpr 0.07%). edshield's own leak check reported 5 leaks; alignment failures 0.

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

## 02_piilo_holdout_model_parity

edshield 0.2.0 (rules+model, python,onnx) **has insufficient evidence for** defined redaction criteria on evidence set piilo_holdout (sha256 bc5d0958b72eee52a7fd38b84ac4c775128eefae6f9e8acee5dbc710cea1ecf8) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **INSUFFICIENT**.

Parity bundle: the two runs are the python and onnx runtimes on the same documents. The judge's stability and reproducibility axes need seeds and are insufficient by construction; read the gates on the selected run and the agreement figure.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 99 | recall | 100.00% | 96.26% – 100.00% | ≥ 99.00% | pass | insufficient |
| identifier | 165 | recall | 100.00% | 100.00% – 100.00% | ≥ 99.00% | pass | insufficient |
| word | 427681 | fpr | 0.07% | 0.05% – 0.09% | ≤ 5.00% | pass | insufficient (not required) |
| type:EMAIL | 4 | (no policy) | | | | | insufficient |
| type:ID_NUM | 7 | (no policy) | | | | | insufficient |
| type:NAME_STUDENT | 143 | (no policy) | | | | | insufficient |
| type:STREET_ADDRESS | 1 | (no policy) | | | | | insufficient |
| type:URL_PERSONAL | 8 | (no policy) | | | | | insufficient |
| type:USERNAME | 2 | (no policy) | | | | | insufficient |

Axes — document: performance pass, stability insufficient (recall, spread 0.00 pp), reproducibility insufficient, agreement 1.0000; identifier: performance pass, stability insufficient (recall, spread 0.00 pp), reproducibility insufficient, agreement 1.0000; word: performance pass, stability insufficient (fpr, spread 0.00 pp), reproducibility insufficient, agreement 1.0000.

Runs: python, onnx. Required views: document, identifier, type:EMAIL, type:ID_NUM, type:NAME_STUDENT, type:STREET_ADDRESS, type:URL_PERSONAL, type:USERNAME. Policy sha256 8f8f3e2d32ea818fc218bc2a752c24ad40fda66a19c5e2e308d0a0271b6357ec; input sha256 d4a82fae520d705eb544de190770a5fc43651724f4e86e7ca09a5659b0647dcf.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| python |  | 0 of 165 | 1 | 100.00% | 0.07% | 71af3248048b | 393.29 |
| onnx |  | 0 of 165 | 1 | 100.00% | 0.07% | 7f4dd8e5a58c | 328.64 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run python

0 of 165 gold identifiers survive whole in the output (identifier recall 100.00%); 1 more survive partially (a token of ≥ 3 characters). Word view: 281 of 427387 non-identifier tokens were removed (fpr 0.07%). edshield's own leak check reported 5 leaks; alignment failures 0.

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

## 03_k12_hard_model_python

edshield 0.2.0 (rules+model, python) **meets** defined redaction criteria on evidence set k12_hard (sha256 3da490d78315057c13668263b779ffd408f06471c8a567ff939a24b28aa1149c) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **PASS**.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 393 | recall | 48.35% | 43.45% – 53.28% | ≥ 40.00% | pass | pass |
| identifier | 1433 | recall | 76.69% | 73.85% – 79.13% | ≥ 70.00% | pass | pass |
| word | 22932 | fpr | 0.13% | 0.08% – 0.18% | ≤ 5.00% | pass | pass |
| type:AGE | 205 | recall | 53.17% | 45.25% – 60.87% | ≥ 50.00% | pass | pass |
| type:DATE | 71 | recall | 46.48% | 34.72% – 57.90% | ≥ 40.00% | pass | pass |
| type:EMAIL | 90 | recall | 100.00% | 100.00% – 100.00% | ≥ 0.00% | pass | pass |
| type:ID_NUM | 57 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:LOCATION | 122 | recall | 31.97% | 23.14% – 41.18% | ≥ 0.00% | pass | pass |
| type:NAME_RELATED | 240 | recall | 100.00% | 100.00% – 100.00% | ≥ 10.00% | pass | pass |
| type:NAME_STUDENT | 351 | recall | 97.44% | 95.08% – 99.41% | ≥ 70.00% | pass | pass |
| type:PHONE_NUM | 75 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:SCHOOL | 116 | recall | 36.21% | 26.89% – 45.69% | ≥ 0.00% | pass | pass |
| type:STREET_ADDRESS | 34 | recall | 0.00% | 0.00% – 0.00% | ≥ 0.00% | pass | pass (not required) |
| type:USERNAME | 72 | recall | 100.00% | 100.00% – 100.00% | ≥ 0.00% | pass | pass |

Axes — document: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; identifier: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; word: performance pass, stability pass (fpr, spread 0.00 pp), reproducibility pass, agreement 1.0000.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:AGE, type:DATE, type:EMAIL, type:ID_NUM, type:LOCATION, type:NAME_RELATED, type:NAME_STUDENT, type:PHONE_NUM, type:SCHOOL, type:USERNAME. Policy sha256 44563b06b3c64295399685552abafb9b70c21de62ed23f5bd6f88bafa4189a74; input sha256 aaee41bb59424323acf11b34174389f06e845285195c8892125681ad654b0706.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 334 of 1433 | 24 | 76.69% | 0.13% | 71af3248048b | 43.52 |
| seed-1 | 1 | 334 of 1433 | 24 | 76.69% | 0.13% | 71af3248048b | 34.62 |
| seed-2 | 2 | 334 of 1433 | 24 | 76.69% | 0.13% | 71af3248048b | 34.61 |
| seed-0-repeat | 0 | 334 of 1433 | 24 | 76.69% | 0.13% | 71af3248048b | 34.94 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

334 of 1433 gold identifiers survive whole in the output (identifier recall 76.69%); 24 more survive partially (a token of ≥ 3 characters). Word view: 27 of 20839 non-identifier tokens were removed (fpr 0.13%). edshield's own leak check reported 2 leaks; alignment failures 0.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| AGE | 205 | 96 | 0 | 53.17% |
| DATE | 71 | 38 | 0 | 46.48% |
| EMAIL | 90 | 0 | 3 | 100.00% |
| ID_NUM | 57 | 0 | 0 | 100.00% |
| LOCATION | 122 | 83 | 18 | 31.97% |
| NAME_RELATED | 240 | 0 | 0 | 100.00% |
| NAME_STUDENT | 351 | 9 | 0 | 97.44% |
| PHONE_NUM | 75 | 0 | 0 | 100.00% |
| SCHOOL | 116 | 74 | 0 | 36.21% |
| STREET_ADDRESS | 34 | 34 | 0 | 0.00% |
| USERNAME | 72 | 0 | 3 | 100.00% |

Label confusion (gold label → labels of acted-on entities touching it; `none` = untouched):

| gold \ acted | AGE | DATE | EMAIL | ID_NUM | NAME_RELATED | NAME_STUDENT | PHONE_NUM | STREET_ADDRESS | USERNAME | none |
|---|---|---|---|---|---|---|---|---|---|---|
| AGE | 121 |  | 1 | 1 |  |  |  |  |  | 82 |
| DATE |  | 31 |  |  |  | 2 |  |  |  | 38 |
| EMAIL |  |  | 90 |  |  |  |  |  |  |  |
| ID_NUM |  |  |  | 57 |  |  |  |  |  |  |
| LOCATION |  |  |  | 1 |  | 25 |  | 3 | 11 | 83 |
| NAME_RELATED |  |  |  |  | 40 | 200 |  |  |  |  |
| NAME_STUDENT |  |  |  |  |  | 343 |  |  |  | 8 |
| PHONE_NUM |  |  |  | 72 |  |  | 3 |  |  |  |
| SCHOOL |  |  |  |  |  | 42 |  |  |  | 74 |
| STREET_ADDRESS |  |  |  |  |  |  |  |  |  | 34 |
| USERNAME |  |  |  | 2 |  | 10 |  |  | 68 |  |

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

- `k12h-9` LOCATION `west alicia` → `west` survives (touched: NAME_STUDENT)
- `k12h-12` LOCATION `west amyside` → `west` survives (touched: USERNAME)
- `k12h-48` LOCATION `new jamesbury` → `new` survives (touched: USERNAME)
- `k12h-66` LOCATION `north stephen` → `north` survives (touched: NAME_STUDENT)
- `k12h-96` LOCATION `West Leslie` → `west` survives (touched: NAME_STUDENT)
- `k12h-121` LOCATION `East Gabrieltown` → `east` survives (touched: STREET_ADDRESS)
- `k12h-137` LOCATION `Lake Natalie` → `lake` survives (touched: NAME_STUDENT)
- `k12h-143` LOCATION `port george` → `port` survives (touched: NAME_STUDENT)
- `k12h-172` LOCATION `port samantha` → `port` survives (touched: NAME_STUDENT)
- `k12h-179` LOCATION `new samantha` → `new` survives (touched: NAME_STUDENT)
- `k12h-179` LOCATION `new samantha` → `new` survives (touched: NAME_STUDENT)
- `k12h-206` LOCATION `South Tylerport` → `south` survives (touched: STREET_ADDRESS)
- `k12h-212` EMAIL `patriciagarcia at gmail dot com` → `gmail` survives (touched: EMAIL)
- `k12h-212` EMAIL `patriciagarcia at gmail dot com` → `gmail` survives (touched: EMAIL)
- `k12h-235` LOCATION `east lisa` → `east` survives (touched: NAME_STUDENT)
- `k12h-248` LOCATION `North Emily` → `north` survives (touched: NAME_STUDENT)
- `k12h-248` LOCATION `North Emily` → `north` survives (touched: NAME_STUDENT)
- `k12h-251` LOCATION `new lukeberg` → `new` survives (touched: USERNAME)
- `k12h-255` LOCATION `new daniel` → `new` survives (touched: NAME_STUDENT)
- `k12h-265` USERNAME `heather.xd65` → `xd65` survives (touched: ID_NUM, NAME_STUDENT)
- `k12h-265` USERNAME `heather.xd65` → `xd65` survives (touched: ID_NUM, NAME_STUDENT)
- `k12h-265` USERNAME `heather.xd65` → `xd65` survives (touched: NAME_STUDENT)
- `k12h-316` EMAIL `kristenoconnor at gmail dot com` → `gmail` survives (touched: EMAIL)
- `k12h-396` LOCATION `Port Michael` → `port` survives (touched: NAME_STUDENT)

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

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:AGE, type:DATE, type:EMAIL, type:ID_NUM, type:LOCATION, type:NAME_RELATED, type:NAME_STUDENT, type:PHONE_NUM, type:SCHOOL, type:USERNAME. Policy sha256 d03b0edb9832a6f7f69a1c6672388b0924edc5415e04d7a0ef371586149dc708; input sha256 953aaacc1f5a266ee6b82004ea96b85bd41e46cab65fadd94b8d6fb1f48aec03.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 1115 of 1433 | 1 | 22.19% | 0.00% | 8e7f0fdf14a3 | 1.99 |
| seed-1 | 1 | 1115 of 1433 | 1 | 22.19% | 0.00% | 8e7f0fdf14a3 | 1.98 |
| seed-2 | 2 | 1115 of 1433 | 1 | 22.19% | 0.00% | 8e7f0fdf14a3 | 1.99 |
| seed-0-repeat | 0 | 1115 of 1433 | 1 | 22.19% | 0.00% | 8e7f0fdf14a3 | 1.97 |

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
