# Driver check of the agent's patches

edshield checkout `a568e73`; allowed paths: `edshield/rules.py`, `edshield/gazetteer/*`.

- `round_1.patch`: applies cleanly; touches ['edshield/rules.py']
- `round_2.patch`: applies cleanly; touches ['edshield/rules.py']

## Independent re-score of `round_2.patch` vs the agent's `round_2/summary.json`

| number | agent | driver | diff |
|---|---|---|---|
| rules.py sha256 | 8e252dc0d1f5 | 8e252dc0d1f5 | same |
| deterministic all_identifiers recall | 95.18% | 95.18% | +0.00 pp |
| deterministic student_names recall | 94.29% | 94.29% | +0.00 pp |
| llm all_identifiers recall | 96.49% | 96.49% | +0.00 pp |
| llm student_names recall | 95.48% | 95.48% | +0.00 pp |
| control comta flags/1k | 0.503 | 0.503 | +0.000 |
| control mathdial flags/1k | 15.102 | 15.102 | +0.000 |

Largest discrepancy: 0.00 (tolerance 0.5). **Matches within rounding.**
