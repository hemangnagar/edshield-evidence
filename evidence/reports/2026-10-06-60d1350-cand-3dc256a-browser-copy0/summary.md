criteria PROVISIONAL, not ratified

# Report 2026-10-06-60d1350-cand-3dc256a-browser-copy0

System under test: edshield 0.2.0 at commit 3dc256a (CANDIDATE, not the pinned release). Judge: model-evidence v2.0.0. Steps: 1 run, 0 skipped.

Residuals are measured on the final output of `edshield.deidentify(verify=False)`: an identifier counts as handled only when its normalized text no longer occurs whole. A surrogate that equals a gold string counts as a residual (known conservative bias). The verdicts come from the judge CLI; nothing here computes pass/fail.

## 02_piilo_holdout_model_parity

edshield 0.2.0 (rules+model, python,onnx) **has insufficient evidence for** defined redaction criteria on evidence set piilo_holdout (sha256 bc5d0958b72eee52a7fd38b84ac4c775128eefae6f9e8acee5dbc710cea1ecf8) under policy coppa (fingerprint 4d84a6e4008e20e91f4751366e7b2a4b5f97b76c7b9284f5f92c72adb1697ccf). Judge verdict: **INSUFFICIENT**.

Parity bundle: the two runs are the python and onnx runtimes on the same documents. The judge's stability and reproducibility axes need seeds and are insufficient by construction; read the gates on the selected run and the agreement figure.

| view | n | gate | point | 95% interval | target | result | view verdict |
|---|---|---|---|---|---|---|---|
| document | 99 | recall | 100.00% | 96.26% – 100.00% | ≥ 99.00% | pass | insufficient |
| identifier | 165 | recall | 100.00% | 100.00% – 100.00% | ≥ 99.00% | pass | insufficient |
| word | 427681 | fpr | 0.12% | 0.10% – 0.15% | ≤ 0.60% | pass | insufficient (not required) |
| type:EMAIL | 4 | (no policy) | | | | | insufficient |
| type:ID_NUM | 7 | (no policy) | | | | | insufficient |
| type:NAME_STUDENT | 143 | (no policy) | | | | | insufficient |
| type:STREET_ADDRESS | 1 | (no policy) | | | | | insufficient |
| type:URL_PERSONAL | 8 | (no policy) | | | | | insufficient |
| type:USERNAME | 2 | (no policy) | | | | | insufficient |

Axes — document: performance pass, stability insufficient (recall, spread 0.00 pp), reproducibility insufficient, agreement 1.0000; identifier: performance pass, stability insufficient (recall, spread 0.00 pp), reproducibility insufficient, agreement 1.0000; word: performance pass, stability insufficient (fpr, spread 0.01 pp), reproducibility insufficient, agreement 0.9999.

Runs: python, onnx. Required views: document, identifier, type:EMAIL, type:ID_NUM, type:NAME_STUDENT, type:STREET_ADDRESS, type:URL_PERSONAL, type:USERNAME. Policy sha256 ecb37ac44f80e2b8a51d77a72b369a7c01970884916e68b8eacab5cf093b1690; input sha256 6795fa4d67bfe3b3ff59bad1be67302be653dee004f67853707391f1259e95c0.

| run | seed | full residuals | partial | identifier recall | word fpr | model sha256 | seconds |
|---|---|---|---|---|---|---|---|
| python |  | 0 of 165 | 0 | 100.00% | 0.12% | 635201c6e1f7 | 371.94 |
| onnx |  | 0 of 165 | 0 | 100.00% | 0.12% | bbcbe4f51df1 | 323.88 |

Residual detail below is for the first run; the others differ only where the table says so.

### Residuals, run python

0 of 165 gold identifiers survive whole in the output (identifier recall 100.00%); 0 more survive partially (a token of ≥ 3 characters). Word view: 502 of 427387 non-identifier tokens were removed (fpr 0.12%). edshield's own leak check reported 14 leaks; alignment failures 0.

| label | n | full residual | partial residual | recall |
|---|---|---|---|---|
| EMAIL | 4 | 0 | 0 | 100.00% |
| ID_NUM | 7 | 0 | 0 | 100.00% |
| NAME_STUDENT | 143 | 0 | 0 | 100.00% |
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
