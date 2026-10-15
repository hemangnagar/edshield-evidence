# Spend

Per component, from the per-request `usage` fields of every logged batch/dry-run result (batch requests at 50% of list price) and the agent session's `session.usage` event (list price, as the platform bills and caps it). Budget: $71.

| component | kind | requests | input tok | output tok | cache write | cache read | USD |
|---|---|---|---|---|---|---|---|
| agent | session sesn_01SpV798Yfa2nmVUmZX6fJTr | 1 | 144 | 49,925 | 0 | 3,157,503 | 3.77 |
| diagnose | batch | 601 | 304,255 | 116,483 | 8,475 | 1,010,220 | 2.00 |
| diagnose-dryrun | dry-run | 1 | 453 | 126 | 1,695 | 0 | 0.01 |
| key-check | messages | 1 | 0 | 0 | 0 | 0 | 0.00 |
| plant | batch | 939 | 2,265,244 | 556,411 | 25,899 | 1,841,223 | 5.26 |
| plant-dryrun | dry-run | 4 | 9,879 | 1,306 | 5,839 | 1,994 | 0.05 |
| **total** | | | | | | | **11.09** |

Remaining of the $71 budget: $59.91.
agent: stop reason `end_turn`, active 4761.43 s (runtime is billed per active hour on top of tokens; the session list_cost includes it).

The platform Console is the authority for what was actually charged; these are list-price reconstructions from the logs.
