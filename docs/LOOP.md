# The experiment loop this repo supports

This document describes the bounded loop; nothing here is automated yet.
edshield is the system under test and lives in its own repository. This repo
is the protected bench: it measures, it never trains, and it never computes a
verdict itself (the judge CLI does).

## The loop

```
evaluate ──► diagnose ──► change edshield ──► regression here ──► acceptance (human-triggered, fresh sealed set)
   ▲                                                                              │
   └──────────────────────────── stop? ◄──────────────────────────────────────────┘
```

1. **Evaluate.** `scripts/baseline.sh` (or the regression workflow) runs the
   full `deidentify()` pipeline on the regression sets and writes
   `evidence/reports/<id>/` with bundles, verdicts, diagnostics and a
   `summary.md`. One ledger row per step.
2. **Diagnose.** An agent reads the regression reports: partial residuals by
   label, the label-confusion table, the over-redaction sample, the residual
   examples. It never reads a sealed set, a sealed verdict's row ids, or the
   acceptance report of a set that has not yet been moved to the regression
   role.
3. **Change edshield**, in this cost order: rules → span handling → policy →
   model. The change is a pull request in the edshield repository with its own
   tests. The bench pins the edshield version; a candidate is measured by
   installing it (`pip install <wheel or git ref>`) and running the exporter
   with the resulting `recipe_sha256` (the installed `rules.py` hash and the
   policy fingerprint are part of it, so a rules change is visible).
4. **Regression here.** The exporter and the judge against
   `policies/regression.json`: must not worsen on PIILO holdout or k12_hard
   (targets are the pinned baseline). A candidate that fails regression does
   not go to acceptance.
5. **Acceptance.** A human dispatches `acceptance.yml` with a fresh sealed set
   (`A1`, then `A2`, …). One decision per set. The report is committed; the
   manifest records `used_for_decision`; the set moves to the regression role
   and the next set is drafted.

## Stop conditions (per cycle)

- the judge returns **pass** on a sealed set under `policies/acceptance.json`;
- **12 experiments** or **20 GPU-hours** have been spent;
- **two consecutive** experiments gain **< 0.5 pt** identifier recall on the
  regression sets;
- the judge returns **insufficient** on **more than two** `type:*` views: fix
  the set (more documents of those labels), not the model.

## Roles and what each cannot touch

| role | does | may change | must not touch |
|---|---|---|---|
| diagnoser (agent) | reads `evidence/reports/*/` for regression sets, proposes the next change and its expected effect | nothing in this repo (writes proposals in the edshield repo or an issue) | `evidence/sets/*.enc`, `evidence/sets/*.manifest.json`, any report of a sealed set whose manifest still says `role: acceptance`, `policies/`, `edshield_evidence/residual.py`, `judge` |
| data agent | drafts new acceptance sets with `scripts/gen_acceptance_draft.py`; writes `evidence/sets/A<n>.draft.jsonl` and `A<n>.draft.review.md` | `scripts/gen_acceptance_draft.py` (new templates, never copied from edshield's `eval/k12_bench.py`), the draft files | sealing (`A<n>.jsonl.enc`, `A<n>.sha256`, `A<n>.manifest.json`), `policies/`, `edshield_evidence/`, `evidence/reports/` |
| experiment agent | implements the change in the edshield repository, runs regression here with the candidate installed | the edshield repository; `evidence/reports/<id>/` and `evidence/ledger.md` only through `scripts/baseline.sh` / `ledger append` | `policies/`, `evidence/sets/`, `edshield_evidence/residual.py`, `edshield_evidence/export_views.py` row definitions, `judge`, `.gitmodules`, `evidence/ledger.md` by hand, `python -m edshield_evidence.ledger pin` |
| scorer-as-code | `edshield_evidence/residual.py`, `export_views.py`, `judge/` | changed only by a pull request reviewed by the human (CODEOWNERS); never during a cycle | — |
| human | reviews and seals sets, ratifies criteria (`ratify:` commits), runs `ledger pin`, dispatches acceptance, opens a sealed verdict for diagnosis (which retires the set) | everything, with the branch protection on `main` | — |

Paths that are read-only for every agent: `policies/`, `evidence/sets/`,
`edshield_evidence/residual.py`, `judge/`, `.gitmodules`, `CODEOWNERS`,
`evidence/ledger.md` (append only through the ledger module, never edit).

## Why these boundaries

- The scorer is code shared by every experiment; if an experiment could edit
  it, "better" would mean "scored differently".
- The sealed set is the only measurement that nobody tuned against; opening it
  spends it.
- The judge is task-blind and pinned by tag; a verdict is a function of rows
  and a policy file with a sha256, nothing else.
