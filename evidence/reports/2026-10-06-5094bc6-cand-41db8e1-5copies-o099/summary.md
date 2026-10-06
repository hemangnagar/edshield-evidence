criteria PROVISIONAL, not ratified

# Report 2026-10-06-5094bc6-cand-41db8e1-5copies-o099

System under test: edshield 0.2.0 at commit 41db8e1 (CANDIDATE, not the pinned release). Judge: model-evidence v2.0.0. Steps: 2 run, 0 skipped.

Residuals are measured on the final output of `edshield.deidentify(verify=False)`: an identifier counts as handled only when its normalized text no longer occurs whole. A surrogate that equals a gold string counts as a residual (known conservative bias). The verdicts come from the judge CLI; nothing here computes pass/fail.

## 01_piilo_holdout_model_python

edshield 0.2.0 (rules+model, python) **does not meet** defined redaction criteria on evidence set piilo_holdout (sha256 bc5d0958b72eee52a7fd38b84ac4c775128eefae6f9e8acee5dbc710cea1ecf8) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **FAIL**.

Policy entries dropped because the bundle has no such view: type:PHONE_NUM.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 99 | recall | 75.76% | 66.46% – 83.13% | ≥ 100.00% | fail | fail |
| identifier | 165 | recall | 79.39% | 69.93% – 87.36% | ≥ 100.00% | fail | fail |
| word | 427681 | fpr | 0.12% | 0.10% – 0.14% | ≤ 0.60% | pass | pass |
| type:EMAIL | 4 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:ID_NUM | 7 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:NAME_STUDENT | 143 | recall | 76.22% | 65.35% – 85.09% | ≥ 100.00% | fail | fail |
| type:STREET_ADDRESS | 1 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |
| type:URL_PERSONAL | 8 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | fail (not required) |
| type:USERNAME | 2 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass (not required) |

Axes — document: performance fail, stability fail (recall, spread 5.05 pp), reproducibility pass, agreement 0.9791; identifier: performance fail, stability fail (recall, spread 3.64 pp), reproducibility pass, agreement 0.9834; word: performance pass, stability pass (fpr, spread 0.03 pp), reproducibility pass, agreement 0.9997.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-3 (seed 3), seed-4 (seed 4), seed-0-repeat (seed 0). Required views: document, identifier, word, type:NAME_STUDENT. Policy sha256 5641206d95587269a02a27695c5e630c5ce3435e332cf9416bd65ad0a8a08da6; input sha256 586da4bc4802cbd98192a1ef3a21422bc4fe4ea111481f7657f1e6677e9a3b74.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 34 of 165 | 0 | 79.39% | 0.12% | 635201c6e1f7 | 71.18 |
| seed-1 | 1 | 30 of 165 | 1 | 81.82% | 0.09% | 284713e11636 | 63.01 |
| seed-2 | 2 | 36 of 165 | 0 | 78.18% | 0.11% | 7dcce48f5876 | 63.76 |
| seed-3 | 3 | 36 of 165 | 0 | 78.18% | 0.09% | 5c7d36979f4f | 63.08 |
| seed-4 | 4 | 33 of 165 | 1 | 80.00% | 0.10% | e420ac898ddc | 63.56 |
| seed-0-repeat | 0 | 34 of 165 | 0 | 79.39% | 0.12% | 635201c6e1f7 | 63.44 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

34 of 165 gold identifiers survive whole in the output (identifier recall 79.39%); 0 more survive partially (a token of ≥ 3 characters). Word view: 502 of 427387 non-identifier tokens were removed (fpr 0.12%). edshield's own leak check reported 52 leaks; alignment failures 31.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| EMAIL | 4 | 0 | 0 | 100.00% |
| ID_NUM | 7 | 0 | 0 | 100.00% |
| NAME_STUDENT | 143 | 34 | 0 | 76.22% |
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

edshield 0.2.0 (rules+model, python) **does not meet** defined redaction criteria on evidence set k12_hard (sha256 3da490d78315057c13668263b779ffd408f06471c8a567ff939a24b28aa1149c) under policy coppa (fingerprint 5831cb4332152883c9b00ccb0a58ee0a90f5e70f4de8b78a595456a9d5db27ad). Judge verdict: **FAIL**.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 393 | recall | 96.18% | 93.80% – 97.67% | ≥ 48.30% | pass | fail |
| identifier | 1433 | recall | 97.70% | 96.23% – 98.83% | ≥ 76.60% | pass | fail |
| word | 22932 | fpr | 0.42% | 0.31% – 0.55% | ≤ 0.70% | pass | pass |
| type:AGE | 205 | recall | 99.51% | 98.48% – 100.00% | ≥ 53.10% | pass | pass |
| type:DATE | 71 | recall | 100.00% | 100.00% – 100.00% | ≥ 46.40% | pass | pass |
| type:EMAIL | 90 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:ID_NUM | 57 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:LOCATION | 122 | recall | 100.00% | 100.00% – 100.00% | ≥ 31.90% | pass | pass |
| type:NAME_RELATED | 240 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:NAME_STUDENT | 351 | recall | 90.88% | 85.50% – 95.61% | ≥ 97.40% | fail | fail |
| type:PHONE_NUM | 75 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |
| type:SCHOOL | 116 | recall | 100.00% | 100.00% – 100.00% | ≥ 36.20% | pass | pass |
| type:STREET_ADDRESS | 34 | recall | 100.00% | 100.00% – 100.00% | ≥ 0.00% | pass | pass (not required) |
| type:USERNAME | 72 | recall | 100.00% | 100.00% – 100.00% | ≥ 100.00% | pass | pass |

Axes — document: performance pass, stability fail (recall, spread 1.27 pp), reproducibility pass, agreement 0.9947; identifier: performance pass, stability fail (recall, spread 0.84 pp), reproducibility pass, agreement 0.9967; word: performance pass, stability pass (fpr, spread 0.38 pp), reproducibility pass, agreement 0.9971.

Runs: seed-0 (seed 0), seed-1 (seed 1), seed-2 (seed 2), seed-3 (seed 3), seed-4 (seed 4), seed-0-repeat (seed 0). Required views: document, identifier, word, type:AGE, type:DATE, type:EMAIL, type:ID_NUM, type:LOCATION, type:NAME_RELATED, type:NAME_STUDENT, type:PHONE_NUM, type:SCHOOL, type:USERNAME. Policy sha256 4f2d6dc5026cd28884af853ea56cf1b617f9a981b89fd78fe19128f3de228fb3; input sha256 84f433e71eea54ed80f5c3ce824eb9cb998a3f0a546e26094059cf3c74baa025.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| seed-0 | 0 | 33 of 1433 | 24 | 97.70% | 0.42% | 635201c6e1f7 | 17.4 |
| seed-1 | 1 | 43 of 1433 | 24 | 97.00% | 0.04% | 284713e11636 | 10.67 |
| seed-2 | 2 | 31 of 1433 | 24 | 97.84% | 0.25% | 7dcce48f5876 | 10.71 |
| seed-3 | 3 | 35 of 1433 | 24 | 97.56% | 0.15% | 5c7d36979f4f | 10.59 |
| seed-4 | 4 | 31 of 1433 | 24 | 97.84% | 0.05% | e420ac898ddc | 11.33 |
| seed-0-repeat | 0 | 33 of 1433 | 24 | 97.70% | 0.42% | 635201c6e1f7 | 10.42 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run seed-0

33 of 1433 gold identifiers survive whole in the output (identifier recall 97.70%); 24 more survive partially (a token of ≥ 3 characters). Word view: 87 of 20839 non-identifier tokens were removed (fpr 0.42%). edshield's own leak check reported 18 leaks; alignment failures 15.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| AGE | 205 | 1 | 0 | 99.51% |
| DATE | 71 | 0 | 0 | 100.00% |
| EMAIL | 90 | 0 | 0 | 100.00% |
| ID_NUM | 57 | 0 | 0 | 100.00% |
| LOCATION | 122 | 0 | 0 | 100.00% |
| NAME_RELATED | 240 | 0 | 0 | 100.00% |
| NAME_STUDENT | 351 | 32 | 0 | 90.88% |
| PHONE_NUM | 75 | 0 | 0 | 100.00% |
| SCHOOL | 116 | 0 | 21 | 100.00% |
| STREET_ADDRESS | 34 | 0 | 2 | 100.00% |
| USERNAME | 72 | 0 | 1 | 100.00% |

Label confusion (gold label → labels of acted-on entities touching it; `none` = untouched):

| gold \ acted | AGE | DATE | EMAIL | ID_NUM | LOCATION | NAME_RELATED | NAME_STUDENT | PHONE_NUM | SCHOOL | STREET_ADDRESS | USERNAME |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AGE | 196 |  |  |  |  |  | 9 |  |  |  |  |
| DATE |  | 68 |  |  | 4 |  |  |  |  |  |  |
| EMAIL |  |  | 90 |  |  |  |  |  |  |  |  |
| ID_NUM |  |  |  | 57 |  |  |  |  |  |  |  |
| LOCATION |  |  |  |  | 122 |  |  |  |  |  |  |
| NAME_RELATED |  |  |  |  |  | 4 | 236 |  |  |  |  |
| NAME_STUDENT |  |  |  |  |  |  | 351 |  |  |  |  |
| PHONE_NUM |  |  |  |  |  |  |  | 75 |  |  |  |
| SCHOOL |  |  |  |  | 2 |  | 7 |  | 107 |  |  |
| STREET_ADDRESS |  |  |  |  |  |  |  |  |  | 34 |  |
| USERNAME |  |  |  |  |  |  |  |  |  |  | 72 |

Over-redaction sample (removed tokens outside any gold span, for human review):

- `k12h-1` `rn` as LOCATION: …im in woodtown rn can you make it sound less boring my te…
- `k12h-4` `tmrw` as NAME_STUDENT: … is can u help me with my essay its due tmrw text me 5710901610 CHARLES CLINE period…
- `k12h-9` `rn` as LOCATION: …im in west alicia rn can you make it sound less boring wait …
- `k12h-12` `rn` as EMAIL: …im in west amyside rn helenlittle at gmail dot com i go to gr…
- `k12h-13` `tmrw` as NAME_STUDENT: …ere can u help me with my essay its due tmrw my teacher said to use the rubric but i…
- `k12h-13` `tmrw` as NAME_STUDENT: …ect can u help me with my essay its due tmrw…
- `k12h-15` `tmrw` as NAME_STUDENT: …lol can u help me with my essay its due tmrw VICTORIA CAMPBELL period 3 11 yr old an…
- `k12h-24` `tmrw` as NAME_STUDENT: …d 3 can u help me with my essay its due tmrw whats a good hook for a story about spa…
- `k12h-27` `tmrw` as NAME_STUDENT: …btw can u help me with my essay its due tmrw text me 5715549031…
- `k12h-47` `rn` as LOCATION: …im in bergside rn wait how do i cite a website can u help…
- `k12h-47` `tmrw` as EMAIL: …ite can u help me with my essay its due tmrw susanmayer at gmail dot com im in bergs…
- `k12h-47` `rn` as LOCATION: …anmayer at gmail dot com im in bergside rn ok thx that helps can u help me with my…
- `k12h-47` `tmrw` as EMAIL: …lps can u help me with my essay its due tmrw susanmayer at gmail dot com 7 yr old an…
- `k12h-48` `rn` as EMAIL: …im in new jamesbury rn kathrynrocha at gmail dot com kathrynro…
- `k12h-50` `tmrw` as NAME_STUDENT: … is can u help me with my essay its due tmrw…
- `k12h-63` `again` as NAME_STUDENT: …ook for a story about space its timothy again lol timothychambers at gmail dot com…
- `k12h-66` `rn` as LOCATION: …l r doing a project im in north stephen rn my teacher said to use the rubric but i…
- `k12h-69` `rn` as LOCATION: …riod 3 its john again lol im in carlton rn…
- `k12h-73` `Mrs.` as NAME_STUDENT: …cess. By Michelle, age 11 Michelle Snow Mrs. Quinn Period 5 Our class voted and most…
- `k12h-78` `Mrs.` as NAME_STUDENT: …Mrs. Jackson Period 6 Mitchell Martinez Mrs. Jackson Period 6 I used three sources f…
- `k12h-87` `tmrw` as NAME_STUDENT: …s26 can u help me with my essay its due tmrw can u help me with my essay its due tmr…
- `k12h-87` `tmrw` as NAME_STUDENT: …mrw can u help me with my essay its due tmrw me and amanda r doing a project…
- `k12h-99` `rn` as LOCATION: …im in east reginaldmouth rn i dont get fractions at all lol JOHN ST…
- `k12h-108` `tmrw` as NAME_STUDENT: …ces can u help me with my essay its due tmrw text me 5714008023…
- `k12h-110` `tmrw` as NAME_STUDENT: …ect can u help me with my essay its due tmrw…
- `k12h-116` `tmrw` as EMAIL: …lps can u help me with my essay its due tmrw kevinmoore at gmail dot com is it ok if…
- `k12h-124` `tmrw` as NAME_STUDENT: …ace can u help me with my essay its due tmrw im kevin btw can u help me with my essa…
- `k12h-124` `tmrw` as NAME_STUDENT: …btw can u help me with my essay its due tmrw wait how do i cite a website 14 yr old …
- `k12h-129` `tmrw` as NAME_STUDENT: …ing can u help me with my essay its due tmrw…
- `k12h-132` `rn` as LOCATION: …w do i cite a website im in stanleyfurt rn…
- `k12h-163` `tmrw` as EMAIL: … it can u help me with my essay its due tmrw karenortega at gmail dot com…
- `k12h-169` `rn` as NAME_STUDENT: …im in lake jimmy rn text me 5712521746 my bday is feb 25 me…
- `k12h-171` `rn` as LOCATION: …but idk where it is im in tannerchester rn…
- `k12h-174` `tmrw` as NAME_STUDENT: …btw can u help me with my essay its due tmrw…
- `k12h-179` `rn` as LOCATION: …im in new samantha rn can u help me with my essay its due tmr…
- `k12h-179` `tmrw` as NAME_STUDENT: … rn can u help me with my essay its due tmrw can you make it sound less boring my te…
- `k12h-179` `rn` as LOCATION: …7 text me 5717192740 im in new samantha rn is it ok if my paragraph is only 4 sent…
- `k12h-191` `Mr.` as NAME_STUDENT: …he dog found his way home. Jose Sellers Mr. Hardy Period 2 First we planted the see…
- `k12h-192` `tmrw` as NAME_STUDENT: …can u help me with my essay its due tmrw 15 yr old and i still dont get it add m…
- `k12h-197` `tmrw` as NAME_STUDENT: …can u help me with my essay its due tmrw HAROLD CAMPBELL period 3 can you make i…
- `k12h-197` `tmrw` as NAME_STUDENT: …ing can u help me with my essay its due tmrw can you make it sound less boring my te…
- `k12h-199` `rn` as LOCATION: …e ok thx that helps im in butlerchester rn can u help me with my essay its due tmr…
- `k12h-213` `tmrw` as NAME_STUDENT: …ing can u help me with my essay its due tmrw BRIAN RUSSELL period 3 i go to riley el…
- `k12h-213` `tmrw` as NAME_STUDENT: …ite can u help me with my essay its due tmrw…
- `k12h-218` `rn` as STREET_ADDRESS: …ke it sound less boring im in thomaston rn…
- `k12h-223` `tmrw` as NAME_STUDENT: …d 3 can u help me with my essay its due tmrw 14m here ok thx that helps im cassandra…
- `k12h-232` `Dr.` as SCHOOL: …we watered them every day. Mary Schmidt Dr. Murray Period 6 Mary Schmidt Dr. Murray…
- `k12h-232` `Dr.` as SCHOOL: …chmidt Dr. Murray Period 6 Mary Schmidt Dr. Murray Period 6 Our house on Espinoza C…
- `k12h-235` `rn` as LOCATION: … it is my bday is feb 7 im in east lisa rn…
- `k12h-251` `r` as NAME_STUDENT: …it is add me monica.plays72 me and anna r doing a project…

Partial residuals (first 25):

- `k12h-7` SCHOOL `mosley middle school` → `school` survives (touched: SCHOOL)
- `k12h-7` SCHOOL `mosley middle school` → `school` survives (touched: SCHOOL)
- `k12h-8` STREET_ADDRESS `Ross Drive` → `drive` survives (touched: STREET_ADDRESS)
- `k12h-12` SCHOOL `griffith high school` → `school` survives (touched: SCHOOL)
- `k12h-18` SCHOOL `vazquez elementary school` → `school` survives (touched: SCHOOL)
- `k12h-30` SCHOOL `hernandez elementary school` → `school` survives (touched: SCHOOL)
- `k12h-69` SCHOOL `reese elementary school` → `school` survives (touched: SCHOOL)
- `k12h-87` USERNAME `robert.plays26` → `robert` survives (touched: USERNAME)
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
