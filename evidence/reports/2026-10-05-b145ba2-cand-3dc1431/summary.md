criteria PROVISIONAL, not ratified

# Report 2026-10-05-b145ba2-cand-3dc1431

System under test: edshield 0.2.0 at commit 3dc1431 (CANDIDATE, not the pinned release). Judge: model-evidence v2.0.0. Steps: 2 run, 0 skipped.

Residuals are measured on the final output of `edshield.deidentify(verify=False)`: an identifier counts as handled only when its normalized text no longer occurs whole. A surrogate that equals a gold string counts as a residual (known conservative bias). The verdicts come from the judge CLI; nothing here computes pass/fail.

## 01_piilo_holdout_model_python

edshield 0.2.0 (rules+model, python) **meets** defined redaction criteria on evidence set piilo_holdout (sha256 bc5d0958b72eee52a7fd38b84ac4c775128eefae6f9e8acee5dbc710cea1ecf8) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **PASS**.

Policy entries dropped because the bundle has no such view: type:PHONE_NUM.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 99 | recall | 100.00% | 96.26% – 100.00% | ≥ 100.00% | pass | pass |
| identifier | 165 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| word | 427681 | fpr | 0.08% | 0.07% – 0.10% | ≤ 0.60% | pass | pass |
| type:EMAIL | 4 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:ID_NUM | 7 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:NAME_STUDENT | 143 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:STREET_ADDRESS | 1 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:URL_PERSONAL | 8 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:USERNAME | 2 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |

Axes — document: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; identifier: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; word: performance pass, stability pass (fpr, spread 0.00 pp), reproducibility pass, agreement 1.0000.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:NAME_STUDENT. Policy sha256 5641206d95587269a02a27695c5e630c5ce3435e332cf9416bd65ad0a8a08da6; input sha256 cc2e77d54f7f0e840932692a84e22f8045c6f9516aa7c2d0ee93793234eb0f19.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 0 of 165 | 2 | 100.00% | 0.08% | 635201c6e1f7 | 471.89 |
| seed-1 | 1 | 0 of 165 | 2 | 100.00% | 0.08% | 635201c6e1f7 | 437.51 |
| seed-2 | 2 | 0 of 165 | 2 | 100.00% | 0.08% | 635201c6e1f7 | 433.2 |
| seed-0-repeat | 0 | 0 of 165 | 2 | 100.00% | 0.08% | 635201c6e1f7 | 433.23 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

0 of 165 gold identifiers survive whole in the output (identifier recall 100.00%); 2 more survive partially (a token of ≥ 3 characters). Word view: 358 of 427387 non-identifier tokens were removed (fpr 0.08%). edshield's own leak check reported 3 leaks; alignment failures 0.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| EMAIL | 4 | 0 | 0 | 100.00% |
| ID_NUM | 7 | 0 | 0 | 100.00% |
| NAME_STUDENT | 143 | 0 | 2 | 100.00% |
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
| document | 393 | recall | 99.75% | 98.57% – 99.96% | ≥ 48.30% | pass | pass |
| identifier | 1433 | recall | 99.93% | 99.78% – 100.00% | ≥ 76.60% | pass | pass |
| word | 22932 | fpr | 0.23% | 0.14% – 0.32% | ≤ 0.70% | pass | pass |
| type:AGE | 205 | recall | 99.51% | 98.48% – 100.00% | ≥ 53.10% | pass | pass |
| type:DATE | 71 | recall | 100.00% | 100.00% – 100.00% | ≥ 46.40% | pass | pass |
| type:EMAIL | 90 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:ID_NUM | 57 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:LOCATION | 122 | recall | 100.00% | 100.00% – 100.00% | ≥ 31.90% | pass | pass |
| type:NAME_RELATED | 240 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:NAME_STUDENT | 351 | recall | 100.00% | 100.00% – 100.00% | ≥ 97.40% | pass | pass |
| type:PHONE_NUM | 75 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:SCHOOL | 116 | recall | 100.00% | 100.00% – 100.00% | ≥ 36.20% | pass | pass |
| type:STREET_ADDRESS | 34 | recall | 100.00% | 100.00% – 100.00% | ≥ 0.00% | pass | pass (not required) |
| type:USERNAME | 72 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |

Axes — document: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; identifier: performance pass, stability pass (recall, spread 0.00 pp), reproducibility pass, agreement 1.0000; word: performance pass, stability pass (fpr, spread 0.00 pp), reproducibility pass, agreement 1.0000.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-0-repeat (seed 0). Required views: document, identifier, word, type:AGE, type:DATE, type:EMAIL, type:ID_NUM, type:LOCATION, type:NAME_RELATED, type:NAME_STUDENT, type:PHONE_NUM, type:SCHOOL, type:USERNAME. Policy sha256 4f2d6dc5026cd28884af853ea56cf1b617f9a981b89fd78fe19128f3de228fb3; input sha256 681a7d0e817bc1e8399df531c4df5eadc8c98d86d3a3fb870acc36093275a53d.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 1 of 1433 | 23 | 99.93% | 0.23% | 635201c6e1f7 | 52.51 |
| seed-1 | 1 | 1 of 1433 | 23 | 99.93% | 0.23% | 635201c6e1f7 | 42.51 |
| seed-2 | 2 | 1 of 1433 | 23 | 99.93% | 0.23% | 635201c6e1f7 | 42.03 |
| seed-0-repeat | 0 | 1 of 1433 | 23 | 99.93% | 0.23% | 635201c6e1f7 | 41.52 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

1 of 1433 gold identifiers survive whole in the output (identifier recall 99.93%); 23 more survive partially (a token of ≥ 3 characters). Word view: 47 of 20839 non-identifier tokens were removed (fpr 0.23%). edshield's own leak check reported 1 leaks; alignment failures 0.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| AGE | 205 | 1 | 0 | 99.51% |
| DATE | 71 | 0 | 0 | 100.00% |
| EMAIL | 90 | 0 | 0 | 100.00% |
| ID_NUM | 57 | 0 | 0 | 100.00% |
| LOCATION | 122 | 0 | 0 | 100.00% |
| NAME_RELATED | 240 | 0 | 0 | 100.00% |
| NAME_STUDENT | 351 | 0 | 0 | 100.00% |
| PHONE_NUM | 75 | 0 | 0 | 100.00% |
| SCHOOL | 116 | 0 | 21 | 100.00% |
| STREET_ADDRESS | 34 | 0 | 2 | 100.00% |
| USERNAME | 72 | 0 | 0 | 100.00% |

Label confusion (gold label → labels of acted-on entities touching it; `none` = untouched):

| gold \ acted | AGE | DATE | EMAIL | ID_NUM | LOCATION | NAME_RELATED | NAME_STUDENT | PHONE_NUM | SCHOOL | STREET_ADDRESS | USERNAME |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AGE | 195 |  |  |  |  |  | 10 |  |  |  |  |
| DATE |  | 66 |  |  | 4 |  | 1 |  |  |  |  |
| EMAIL |  |  | 90 |  |  |  |  |  |  |  |  |
| ID_NUM |  |  |  | 57 |  |  |  |  |  |  |  |
| LOCATION |  |  |  |  | 122 |  |  |  |  |  |  |
| NAME_RELATED |  |  |  |  |  | 2 | 238 |  |  |  |  |
| NAME_STUDENT |  |  |  |  |  |  | 351 |  |  |  |  |
| PHONE_NUM |  |  |  |  |  |  |  | 75 |  |  |  |
| SCHOOL |  |  |  |  | 2 |  | 7 |  | 107 |  |  |
| STREET_ADDRESS |  |  |  |  |  |  |  |  |  | 34 |  |
| USERNAME |  |  |  |  |  |  |  |  |  |  | 72 |

Over-redaction sample (removed tokens outside any gold span, for human review):

- `k12h-1` `rn` as LOCATION: …im in woodtown rn can you make it sound less boring my te…
- `k12h-9` `rn` as LOCATION: …im in west alicia rn can you make it sound less boring wait …
- `k12h-12` `rn` as EMAIL: …im in west amyside rn helenlittle at gmail dot com i go to gr…
- `k12h-13` `tmrw` as NAME_STUDENT: …ere can u help me with my essay its due tmrw my teacher said to use the rubric but i…
- `k12h-13` `tmrw` as NAME_STUDENT: …ect can u help me with my essay its due tmrw…
- `k12h-27` `tmrw` as NAME_STUDENT: …btw can u help me with my essay its due tmrw text me 5715549031…
- `k12h-47` `rn` as LOCATION: …im in bergside rn wait how do i cite a website can u help…
- `k12h-47` `tmrw` as EMAIL: …ite can u help me with my essay its due tmrw susanmayer at gmail dot com im in bergs…
- `k12h-47` `rn` as LOCATION: …anmayer at gmail dot com im in bergside rn ok thx that helps can u help me with my…
- `k12h-47` `tmrw` as EMAIL: …lps can u help me with my essay its due tmrw susanmayer at gmail dot com 7 yr old an…
- `k12h-48` `rn` as EMAIL: …im in new jamesbury rn kathrynrocha at gmail dot com kathrynro…
- `k12h-66` `rn` as LOCATION: …l r doing a project im in north stephen rn my teacher said to use the rubric but i…
- `k12h-69` `rn` as LOCATION: …riod 3 its john again lol im in carlton rn…
- `k12h-87` `tmrw` as NAME_STUDENT: …s26 can u help me with my essay its due tmrw can u help me with my essay its due tmr…
- `k12h-87` `tmrw` as NAME_STUDENT: …mrw can u help me with my essay its due tmrw me and amanda r doing a project…
- `k12h-108` `tmrw` as NAME_STUDENT: …ces can u help me with my essay its due tmrw text me 5714008023…
- `k12h-116` `tmrw` as EMAIL: …lps can u help me with my essay its due tmrw kevinmoore at gmail dot com is it ok if…
- `k12h-124` `tmrw` as NAME_STUDENT: …btw can u help me with my essay its due tmrw wait how do i cite a website 14 yr old …
- `k12h-163` `tmrw` as EMAIL: … it can u help me with my essay its due tmrw karenortega at gmail dot com…
- `k12h-169` `rn` as NAME_STUDENT: …im in lake jimmy rn text me 5712521746 my bday is feb 25 me…
- `k12h-179` `rn` as LOCATION: …im in new samantha rn can u help me with my essay its due tmr…
- `k12h-179` `rn` as LOCATION: …7 text me 5717192740 im in new samantha rn is it ok if my paragraph is only 4 sent…
- `k12h-192` `tmrw` as NAME_STUDENT: …can u help me with my essay its due tmrw 15 yr old and i still dont get it add m…
- `k12h-197` `tmrw` as NAME_STUDENT: …can u help me with my essay its due tmrw HAROLD CAMPBELL period 3 can you make i…
- `k12h-197` `tmrw` as NAME_STUDENT: …ing can u help me with my essay its due tmrw can you make it sound less boring my te…
- `k12h-213` `tmrw` as NAME_STUDENT: …ing can u help me with my essay its due tmrw BRIAN RUSSELL period 3 i go to riley el…
- `k12h-213` `tmrw` as NAME_STUDENT: …ite can u help me with my essay its due tmrw…
- `k12h-218` `rn` as LOCATION: …ke it sound less boring im in thomaston rn…
- `k12h-223` `tmrw` as NAME_STUDENT: …d 3 can u help me with my essay its due tmrw 14m here ok thx that helps im cassandra…
- `k12h-235` `rn` as LOCATION: … it is my bday is feb 7 im in east lisa rn…
- `k12h-267` `tmrw` as NAME_STUDENT: …272 can u help me with my essay its due tmrw text me 5717772272 i dont get fractions…
- `k12h-267` `tmrw` as NAME_STUDENT: …lol can u help me with my essay its due tmrw…
- `k12h-301` `tmrw` as NAME_STUDENT: …can u help me with my essay its due tmrw its keith again lol my bday is apr 11 c…
- `k12h-301` `tmrw` as NAME_STUDENT: … 11 can u help me with my essay its due tmrw can you make it sound less boring ok th…
- `k12h-301` `tmrw` as NAME_STUDENT: …lps can u help me with my essay its due tmrw…
- `k12h-305` `rn` as LOCATION: …im in west ryanton rn can u help me with my essay its due tmr…
- `k12h-352` `rn` as LOCATION: …im in north christopherside rn i go to harvey academy can u help me wi…
- `k12h-357` `tmrw` as NAME_STUDENT: …lps can u help me with my essay its due tmrw my bday is mar 5 text me 5716083720 can…
- `k12h-357` `tmrw` as NAME_STUDENT: …720 can u help me with my essay its due tmrw wait how do i cite a website can u help…
- `k12h-357` `tmrw` as NAME_STUDENT: …ite can u help me with my essay its due tmrw im diane btw text me 5716083720…
- `k12h-358` `tmrw` as NAME_STUDENT: …ing can u help me with my essay its due tmrw can u help me with my essay its due tmr…
- `k12h-358` `tmrw` as NAME_STUDENT: …mrw can u help me with my essay its due tmrw is it ok if my paragraph is only 4 sent…
- `k12h-370` `tmrw` as NAME_STUDENT: …can u help me with my essay its due tmrw 16 yr old and i still dont get it whats…
- `k12h-374` `rn` as LOCATION: …actions at all lol im in south johnside rn i dont get fractions at all lol is it o…
- `k12h-374` `rn` as LOCATION: … story about space im in south johnside rn whats a good hook for a story about spa…
- `k12h-374` `rn` as LOCATION: … still dont get it im in south johnside rn…
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
