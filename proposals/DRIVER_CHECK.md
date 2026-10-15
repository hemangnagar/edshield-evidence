# Driver check of the agent's patches

edshield checkout `a568e73`; allowed paths: `edshield/rules.py`, `edshield/gazetteer/*`.

- `round_1.patch`: applies cleanly; touches ['edshield/rules.py']
- `round_2.patch`: applies cleanly; touches ['edshield/rules.py']

## Independent re-score of `round_2.patch` vs the agent's `round_2/summary.json`

| number | agent | driver | diff |
|---|---|---|---|
| deterministic all_identifiers recall | 95.32% | 95.32% | +0.00 pp |
| deterministic student_names recall | 94.49% | 94.49% | +0.00 pp |
| llm all_identifiers recall | 97.07% | 97.07% | +0.00 pp |
| llm student_names recall | 96.29% | 96.29% | +0.00 pp |
| control comta flags/1k | 0.503 | 0.503 | +0.000 |
| control mathdial flags/1k | 15.102 | 15.102 | +0.000 |

Largest discrepancy: 0.00 (tolerance 0.5). **Matches within rounding.**
