Floor transfer with the primary strata: B's name recall predicted from A's per-stratum recall and B's stratum mix. Error = predicted - measured. Floor valid = predicted floor <= measured.

| A -> B | detector | measured on B | predicted (oracle mix) | error (pts) | predicted floor | floor valid | predicted (caught-only mix) | error (pts) | predicted floor | floor valid | caught-only bias (pts) | B weight in strata A lacks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| comta -> mathdial | edshield | 90.31% | 88.39% | -1.92 | 86.05% | yes | 88.60% | -1.70 | 86.26% | yes | +0.21 | 0.0% |
| mathdial -> comta | edshield | 86.16% | 89.99% | +3.83 | 70.49% | yes | 90.20% | +4.04 | 71.95% | yes | +0.21 | 20.8% |
| comta -> mathdial | presidio | 75.28% | 73.56% | -1.72 | 70.37% | yes | 75.71% | +0.44 | 72.70% | yes | +2.15 | 0.0% |
| mathdial -> comta | presidio | 70.71% | 75.17% | +4.47 | 58.44% | yes | 77.27% | +6.56 | 62.22% | yes | +2.10 | 20.8% |
| comta -> mathdial | spacy_trf | 96.06% | 94.88% | -1.18 | 93.08% | yes | 94.91% | -1.15 | 93.12% | yes | +0.03 | 0.0% |
| mathdial -> comta | spacy_trf | 93.54% | 96.03% | +2.49 | 75.49% | yes | 96.06% | +2.52 | 76.43% | yes | +0.03 | 20.8% |
| comta -> mathdial | hf_pii | 56.91% | 56.29% | -0.62 | 52.63% | yes | 56.80% | -0.10 | 53.21% | yes | +0.52 | 0.0% |
| mathdial -> comta | hf_pii | 44.42% | 56.74% | +12.31 | 43.67% | yes | 57.20% | +12.78 | 55.64% | NO | +0.46 | 20.8% |
| comta -> mathdial | gpt4o_mini | 60.85% | 64.95% | +4.09 | 61.92% | NO | 68.96% | +8.11 | 65.95% | NO | +4.01 | 0.0% |
| mathdial -> comta | gpt4o_mini | 67.17% | 59.71% | -7.47 | 46.07% | yes | 63.34% | -3.83 | 45.76% | yes | +3.64 | 20.8% |
| comta -> mathdial | gpt4o_mini_propagated | 83.55% | 80.50% | -3.04 | 77.68% | yes | 80.86% | -2.69 | 78.02% | yes | +0.36 | 0.0% |
| mathdial -> comta | gpt4o_mini_propagated | 80.38% | 83.21% | +2.83 | 64.93% | yes | 83.57% | +3.19 | 64.51% | yes | +0.36 | 20.8% |
