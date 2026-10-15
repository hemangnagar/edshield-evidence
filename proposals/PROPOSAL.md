# edshield rule proposal: initials of detected names, short school names

**Nothing here is merged.** These are proposed patches against edshield commit `a568e73` (the PyPI 0.2.0 release). A human reviews `round_1.patch` and `round_2.patch` and decides. Both patches change only `edshield/rules.py`. No gazetteer file was added.

- Final proposal: `round_2.patch`. It is cumulative: round 1 plus round 2.
- Rounds kept: 1 and 2. Rounds reverted: none. See `kept_rounds.json`.

## How it was measured

- **Command.** `make eval-candidate ROUND=N RUNTIME=onnx` from the bench root, with the candidate installed editable from `/workspace/edshield`. Every summary records `installed_from: /workspace/edshield`.
- **Runtime.** INT8 ONNX on CPU. Torch could not be installed in the sandbox, so the PyTorch runtime was not used.
- **Metric.** Span recall, scored by the residual rule: the identifier no longer occurs whole in the output. The deterministic and LLM views are pooled over comta and mathdial.
- **Control.** Acted-on entities per 1,000 whitespace tokens on the untouched dialogues.

### Which baseline the deltas use

The summaries compare each round with these baseline sources:

- **Deterministic view:** the sealed GPU/python run, `experiments/genre_shift/results/metrics.json`.
- **LLM view:** `results/llm_view/llm/metrics.json`.
- **Control:** the sealed run.

The sealed run used a different runtime from these rounds, so I report every number twice: against the sealed baseline as printed in the summary, and against round 0. Round 0 is the unmodified checkout under the same ONNX runtime. The round-0 column isolates the effect of the patch.

### Round 0 (sanity gate, unmodified checkout)

Source: `results/candidate/round_0/summary.json`.

- **Deterministic view:** identifier recall 89.97% against the sealed 90.32%, delta −0.35 pp. `sanity.within_tolerance` is `true` (tolerance 0.5 pp).
- **Control, mathdial:** 15.102 flags per 1,000 tokens against the sealed 16.215, delta −1.113. This is a runtime difference (fewer `problem_name` flags under ONNX/INT8), not a patch effect. It appears unchanged in every round below.
- **Control, comta:** 0.503 flags per 1,000 tokens, delta +0.000.

## Round 1: initials of an already-detected name (kept)

**What the patch does.** It adds a final step to `propagate_names`:

- For each name the document already contains with enough confidence (the same set that `propagate_names` already spreads: rule names, propagated names, model names with confidence ≥ 0.75), it takes the first letter of the first token.
- It then tags every standalone `X.` with that letter: "Well done, V.!", "Keep going, K.".
- The tagged initial gets the name's label, at the name's confidence × 0.9, with `source="propagated"`.
- **Guards:**
  - Not inside "U.S." or "A.M." (no word character or `.` just before, no word character just after).
  - Not after an arithmetic operator, so "x = A." and "S = 100 − C." are skipped (`INITIAL_MATH_BEFORE_RE`).
  - Not where the span overlaps an existing entity.

**Why it is in `propagate_names`.** With a model loaded, `NAME_STUDENT` is under model authority: `detect_rules` is not run for it (`edshield/__init__.py` lines 107–111). A new name rule inside `detect_rules` would therefore never fire in `rules+model` mode. `propagate_names` does run after the model.

**Cause codes addressed** (`results/diagnosis/causes.jsonl`, primary-order rows only):

- `nickname:initial` rows are TOKENIZATION / RULE: 166 deterministic rows (mean confidence 0.78) and 164 LLM-view rows (mean confidence 0.77).
- These are the largest RULE cause in both views, and recall on this form was 1.2% (deterministic) and 0.0% (LLM) according to `results/view_comparison.md`.
- In the planted data, 167 of 168 deterministic and 164 of 164 LLM-view initials belong to a student whose full name also appears in the same dialogue.

**Numbers** (all from `results/candidate/round_1/summary.json`):

| metric | round 1 | vs sealed / LLM baseline (summary `delta_pp`) | vs round 0 (`results/candidate/round_0/summary.json`) |
|---|---|---|---|
| deterministic, all identifiers (n=2841) | 94.54% [93.65, 95.32] | +4.22 pp | +4.58 pp (from 89.97%) |
| deterministic, student names (n=2014) | 94.49% | +6.06 pp | +6.45 pp |
| LLM view, all identifiers (n=2767) | 97.07% [96.38, 97.64] | +5.24 pp | +5.24 pp (from 91.83%) |
| LLM view, student names (n=1967) | 96.29% | +7.37 pp | +7.37 pp |
| control comta, flags per 1,000 tokens | 0.503 (21 flags) | +0.000 | +0.000 |
| control mathdial, flags per 1,000 tokens | 15.102 (2,794 flags) | −1.113 | +0.000 (same 2,794 flags) |

- **Misses:**
  - Deterministic view: 285 → 155.
  - LLM view: 226 → 81.
  - These counts are from the `make eval-candidate` console output, which matches the row counts of `results/candidate/round_{0,1}/{deterministic,llm}/misses.csv`.
- **Per category:** every student-name category rises on both views (deterministic +4.35 to +7.21 pp, LLM +6.69 to +8.69 pp against the summary baseline).
- **Control:** no regression against pinned baseline round 0 on either control dataset.
- **Unchanged slice:** deterministic NAME_RELATED is −0.52 pp against the sealed baseline in round 0, 1 and 2 alike. It is a runtime difference, not caused by this patch.

**What it does not fix:**

- **Initials where the scorer still finds the letter (33 deterministic, 17 LLM view).** All of these initials are masked at the mention itself, and the exact text "X." does not occur in the output. They are still counted as misses because the residual rule (`edshield_evidence/residual.py`, `find_residual`) case-folds the gold text and strips its edge punctuation. `A.` therefore becomes `a` and is searched as a whole word anywhere in the output. The article "a", the pronoun "I", and contraction tails ("let's", "don't", "I'm") hit `A.`, `I.`, `S.`, `T.`, `M.`:
  - Deterministic: A 11, S 8, I 5, T 4, L 2, M 2, Y 1.
  - LLM view: A 9, S 5, M 3.
  - No rule can recover these without masking ordinary words. I did not try, and the scorer is out of scope.
- **Initials of a name that was never detected (3 deterministic, 2 LLM view).** There is no anchor name to propagate from.
- **Initials of names the model found with confidence < 0.75.** They are not propagated, by the existing design decision that weak guesses are not spread.
- **Risk outside the bench.** An unrelated standalone capital plus full stop that shares the detected student's initial will be masked in the same document, for example "point A." in a geometry turn when the student is called Alex. On the control this happened once in 227k tokens before the operator guard and 0 times after it (offline estimate on the round 0 entities; the measured control delta is +0.000). It is a false alarm, not a leak, which fits the project's recall-first rule. A reviewer may still want a lookbehind for words like "point", "angle" and "option".

## Round 2: short school names "X High" and "X Prep" (kept)

**What the patch does.** It adds `High` and `Prep` as the last two alternatives of `SCHOOL_TYPES`. The longer forms ("High School", "Preparatory School", "Junior High") stay earlier in the alternation, so they still match whole. The existing guards are unchanged: a sentence opener is stripped, and a name made only of kind words ("Junior High", "So High") is skipped. `SCHOOL` is a rules-only label, so this rule runs with or without the model.

**Cause codes addressed.** SCHEMA_GAP (`results/diagnosis/causes.jsonl`), all 22 of them deterministic-view SCHOOL misses:

- 20 rows are SCHEMA_GAP / RULE and 2 are SCHEMA_GAP / GAZETTEER; mean confidence 0.68.
- The forms are "X High" (12) and "X Prep" (10).
- One of these, "Summit Prep" in comta-014, is the second-highest-confidence RULE miss in `results/diagnosis/summary.md`.

**Numbers** (all from `results/candidate/round_2/summary.json`):

| metric | round 2 | vs sealed / LLM baseline (summary `delta_pp`) | vs round 1 (`results/candidate/round_1/summary.json`) | vs round 0 |
|---|---|---|---|---|
| deterministic, all identifiers (n=2841) | 95.32% [94.48, 96.04] | +5.00 pp | +0.77 pp | +5.35 pp |
| deterministic, SCHOOL (n=218) | 100.0% | +10.09 pp | +10.09 pp (from 89.91%) | +10.09 pp |
| deterministic, student names | 94.49% | +6.06 pp | +0.00 pp | +6.45 pp |
| LLM view, all identifiers (n=2767) | 97.07% [96.38, 97.64] | +5.24 pp | +0.00 pp | +5.24 pp |
| LLM view, SCHOOL (n=213) | 100.0% | +0.00 pp | +0.00 pp | +0.00 pp |
| control comta, flags per 1,000 tokens | 0.503 (21 flags) | +0.000 | +0.000 | +0.000 |
| control mathdial, flags per 1,000 tokens | 15.102 (2,794 flags) | −1.113 | +0.000 | +0.000 |

- **Misses:** deterministic view 155 → 133; LLM view unchanged at 81.
- **Control:** no regression against pinned baseline round 1 on either control dataset. Neither form occurs in the control text at all (0 regex hits on either dataset before the run).

**What it does not fix, and caveats:**

- **The gain shows up on the deterministic view only.** The LLM view's SCHOOL slice was already at 100%, and `results/view_comparison.md` lists SCHOOL as a slice whose phrasing alone moves the number (non-overlapping CIs). The +0.77 pp reflects how the deterministic templates write school names. How common short forms are in real student chat is not measured here.
- **Possible false alarms.** "Test Prep" or "SAT Prep" written in title case, or a capitalised phrase ending in "High" ("Too High"), would now be flagged as SCHOOL. Lower-case "prep" and "high" are not affected.
- **Lower-case school names** ("jefferson high") remain uncovered, as before.

## Why the loop stopped after round 2

**None of the listed stop conditions fired:**

- Round 1 improved deterministic identifier recall by +4.58 pp against round 0.
- Round 2 improved it by +0.77 pp against round 1.
- Neither round raised control over-redaction (+0.000 flags per 1,000 tokens on both datasets).
- The session budget was not reported as reached.

**I stopped by choice instead of running round 3.** The best remaining RULE candidate was projected to fall under the "improves deterministic-view identifier recall by less than 0.5 percentage points" condition. Of the 133 remaining deterministic misses:

- 58 are name/word collisions that are mostly MODEL-class in the diagnosis.
- 40 are "elsewhere", including the 33 single-letter scorer cases above.
- 22 are nickname forms, 7 lowercase, 4 typo and 2 other.

An offline estimate on the round 2 entities for the largest remaining RULE idea gave a low payoff. The idea was case-insensitive propagation of detected names, for lowercase mentions (REGISTER). It would recover at most 4 deterministic misses (about +0.14 pp, under 0.5 pp) and add 17 control flags on mathdial. Truncated nicknames (7 deterministic rows) cannot reach 0.5 pp (14.2 spans) either. A third run would most likely have ended the loop through the <0.5 pp condition, at the cost of a full evaluation.

## Notes for the reviewer

- **Demo parity.** `demo/index.html` has a JavaScript port of `propagateNames` and of the school rule. `tests/test_demo_parity.py` checks that the port matches the Python. I was not allowed to edit `demo/`, so if these patches are accepted the JavaScript needs the same two changes. Otherwise the parity test may fail on any sentence that exercises them.
- **Tests not run.** edshield's pytest suite was not run, because pytest is not installed in the sandbox and installing it was not permitted. What I did run:
  - `import edshield` from the candidate.
  - Synthetic checks of both changes: `, M.!` and `Nice, M.` tagged; `U.S.`, `x = M.` and `100 - M.` not tagged; "Jefferson High" and "Summit Prep" caught; "Junior High", "So High" and "SAT prep" not caught.
  - The three bench evaluations.
- **Not tuned to the hard set.** The rules were written from the diagnosis rows and checked against the bench views. They were not tuned to `eval/k12_bench.py`'s hard set.
- **Runtime.** All numbers come from the INT8 ONNX runtime on CPU. The sealed baseline is GPU/python. The before/after comparisons that isolate each patch are the round-0 and round-1 columns.
- **Data handling.** The `raw/` subdirectories of `results/candidate/round_*` are not included in the outputs.
