# Findings v2: five PII detectors on planted tutoring dialogue

Names from four lists planted into 188 CoMTA and 599 MathDial dialogues under five seeds: 12,046 name mentions, caught when NAME spans cover at least half their characters. Intervals are 95% Wilson over pooled seeds; the seeds replant the same dialogues, so they are optimistic.

**Fallbacks.** StudyChat is still gated to this account (403) and TSCC was not received: two genres and two ordered pairs, not three and six. The PIILO holdout was rebuilt from the public corpus and matches the committed bundle token for token. gpt-4o-mini cost $0.93; its offsets were right for 428 of 18,387 spans, so spans are placed by the string it returned, and 45 of 5,166 documents ended as no-flag. Other deviations: `results/v2/README.md`.

**1. Is the drop general?** No. Three detectors lose about ten points, one is flat, one gains.

| detector | PIILO essays (143 names) | dialogue | SD over seeds (pts) |
|---|---|---|---|
| edshield 0.2.0 | 100% [97.4, 100] | 89.4% [88.9, 90.0] | 0.58 |
| Presidio | 84.6% [77.8, 89.6] | 74.3% [73.5, 75.1] | 0.77 |
| spaCy trf | 90.2% [84.2, 94.1] | 95.5% [95.2, 95.9] | 0.41 |
| Piiranha (HF) | 53.1% [45.0, 61.1] | 54.3% [53.4, 55.2] | 0.68 |
| gpt-4o-mini | 72.0% [64.2, 78.7] | 62.2% [61.3, 63.0] | 0.30 |

Only edshield was trained on PIILO. CoMTA (real students) is below MathDial for every detector except gpt-4o-mini. None reaches 99.5% on dialogue.

**2. Do misses follow form?** Yes for all five, in different forms. Initials ("R.", 843 mentions): edshield 0.4%, Piiranha 0.1%, gpt-4o-mini 10.6%, Presidio 17.1%, spaCy 72.1%; without them edshield is at 96.2%. Dictionary-word names: Presidio 54.2% against 81.2% for other names. Lowercase dictionary-word names in student turns are the weakest cell for edshield (58.7%), Presidio (29.0%) and spaCy (74.6%). Piiranha catches 0 of 519 lowercase and 2 of 383 all-caps names. gpt-4o-mini lists a name once: first mentions 91.7%, later ones 37.7%; flagging every occurrence of its returned strings gives 82.9%.

**3. Floor transfer.** Primary strata, five detectors, two pairs: mean absolute error 4.0 points, against 6.0 unstratified. CoMTA→MathDial averages 1.9; MathDial→CoMTA 6.1, because MathDial has no lowercase names and 20.8% of CoMTA's mentions fall in strata it never observed. Worst pair: Piiranha MathDial→CoMTA, +12.3. The predicted floor held in 9 of 10, and four of the five MathDial→CoMTA floors hold only because unobserved strata count as zero. Caught-only mix: bias +1.3 points on average, +4.0 at most; floors hold in 8 of 10. `case` alone brings the error to 3.9 and finer strata do not lower it; all ten floors hold only with `× category` or `× is_initial`, where caught-only bias reaches +2.5 and +4.8. A 99.5% floor needs 600 clean mentions per stratum; no stratum was clean for any detector.

**4. Over-redaction** (NAME flags per 1,000 control tokens, CoMTA / MathDial): edshield 0.26 / 15.7; Presidio 2.01 / 16.6; spaCy 0.96 / 18.0; Piiranha 0.07 / 2.3; gpt-4o-mini 0.12 / 8.5. On MathDial 90 to 98% of flags are word-problem characters or the simulated student's persona name. One dialogue flag in all fell on a curricular term.

**5. Misses shared by all five** (268 mentions; 1,544 missed by three or more, 816 of them initials):
- `the hexagon problem Tutor: You're close, [[T.]] . Alright! If you're finished with`
- `Student: hey its [[vee]] . Can you provide me with`
- `Keep going, [[Summer]] . Student: There would be 4*60 = 240 trucks overall.`

**6. Reading.** Supported: every detector's misses on dialogue concentrate in surface forms (initials, lowercase, word-like names, repeat mentions), and stratifying by case predicts recall across the two genres to about four points. Not supported: a 99.5% floor for any detector, a drop general across detectors, or floor transfer to a genre with forms the probe genre lacks.
