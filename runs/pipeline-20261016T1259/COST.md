# Spend

Per component, from the per-request `usage` fields of every logged batch/dry-run result (batch requests at 50% of list price) and the agent session's `session.usage` event (list price, as the platform bills and caps it). Budget: $71.

| component | kind | requests | input tok | output tok | cache write | cache read | USD |
|---|---|---|---|---|---|---|---|
| agent | session sesn_01SpV798Yfa2nmVUmZX6fJTr, session sesn_01TqN2pLjWXhqgTbuXhJtDts | 2 | 250 | 85,495 | 0 | 5,202,923 | 6.18 |
| agent-verify | session sesn_01FK1D3ScnWBvy9LknQm3eVd, session sesn_01H9Eoposw3uCexp2fqj3pjY, session sesn_01JVPjSwZ9qiT5pE4WtsiFFm | 3 | 64 | 8,660 | 0 | 279,076 | 0.39 |
| diagnose | batch | 617 | 311,691 | 121,763 | 11,865 | 1,033,950 | 2.08 |
| diagnose-dryrun | dry-run | 1 | 453 | 126 | 1,695 | 0 | 0.01 |
| key-check | messages | 1 | 0 | 0 | 0 | 0 | 0.00 |
| plant | batch | 939 | 2,265,244 | 556,411 | 25,899 | 1,841,223 | 5.26 |
| plant-dryrun | dry-run | 4 | 9,879 | 1,306 | 5,839 | 1,994 | 0.05 |
| **total** | | | | | | | **13.97** |

Remaining of the $71 budget: $57.03.
agent: stop reason `end_turn`, active 3445.67 s (runtime is billed per active hour on top of tokens; the session list_cost includes it).
agent-verify: stop reason `end_turn`, active 924.874 s (runtime is billed per active hour on top of tokens; the session list_cost includes it).

The platform Console is the authority for what was actually charged; these are list-price reconstructions from the logs.
