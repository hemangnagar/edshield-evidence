# Experiment ledger

Append-only. One row per report step. Regression targets are re-pinned from the latest row of each dataset/detector by `python -m edshield_evidence.ledger pin` (a human runs this). Identifier recall is 1 - full residuals / gold spans on the final output; edshield's own figures count a span as handled when any flag touches it, so the two are not comparable one to one.

| date | report id | dataset | policy | detector | runtime | edshield commit | recipe sha | identifier recall [interval] | document recall | word fpr | verdict | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-04 | 2026-10-04-c60e4e0 | k12_hard | coppa (5831cb43) | rules | python | 0.2.0 (a568e73) | 00fc9b1597c3 | 0.2219 [0.2001, 0.2427] | 0.0331 | 0.0000 | pass | 1115 of 1433 identifiers survive whole, 1 partially; edshield reports 1,100 of 1,433 got through |
