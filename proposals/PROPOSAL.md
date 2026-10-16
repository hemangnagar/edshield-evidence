# edshield rule proposal: initials of detected names; short school names

**Nothing here is merged.** These are proposed patches against edshield commit `a568e73` (release 0.2.0). A human reviews `round_1.patch` and `round_2.patch` and decides whether to apply them. Both patches change only `edshield/rules.py`. No gazetteer file was added.

- **Final proposal:** `round_2.patch`. It is cumulative: round 1 plus round 2.
- **Rounds:** kept 1 and 2; none reverted (see `kept_rounds.json`).
- **Patches match what was measured.** Each patch was applied to a clean checkout of `a568e73`. The SHA-256 of the resulting `rules.py` equals the `edshield.rules_sha256` recorded in the matching summary:
  - round 1: `454a40da…`
  - round 2: `8e252dc0…`

## Setup and how it was measured

- **Candidate.** `/workspace/edshield`, branch `candidate` made from `main`, HEAD `a568e73a6c34d40335802235db81950e84004ab1`. It is installed editable; every summary records `installed_from: /workspace/edshield` and that commit.
- **Command.** From the bench root, `make eval-candidate ROUND=N RUNTIME=onnx`.
  - Runtime: INT8 ONNX on CPU (`model_sha256 7f4dd8e5…`). Torch is not installed in the sandbox.
- **Recall.** Span recall under the residual rule: the gold text no longer occurs whole in the output. Pooled over comta and mathdial.
- **Control.** Acted-on entities per 1,000 whitespace tokens on the untouched dialogues.
- **edshield test suite: not run.** `pytest` is not installed in the sandbox, and installing packages was out of scope.
  - What was run instead: `python -c "import edshield"` plus small hand checks of the new regexes ("U.S.", "a.m.", "A.M.", "e.g." are not matched; "In High School", "Junior High", "So High" are not schools).
- **Demo parity (needs a follow-up).** The project's CLAUDE.md requires `edshield/rules.py` and the JavaScript port in `demo/index.html` to stay in parity; `tests/test_demo_parity.py` enforces this. This session was allowed to change only `rules.py`, so applying either patch needs a matching change in `demo/index.html`. Until then that test is expected to fail.

## Round 0: sanity gate (unmodified checkout)

Source: `results/candidate/round_0/summary.json`.

- **Deterministic view, all identifiers:** 89.97% against the sealed 90.32%, delta −0.35 pp. `sanity.within_tolerance: true` (tolerance 0.5 pp).
  - The sealed run used the GPU and the Python runtime; this run uses ONNX INT8 on CPU.
- **LLM view, all identifiers:** 91.83%, delta 0.0 pp.
- **Control comta:** 0.503 flags per 1,000 tokens (21 flags), delta 0.0.
- **Control mathdial:** 15.102 flags per 1,000 tokens (2,794 flags), delta −1.113. This is a runtime difference: fewer `problem_name` flags under ONNX/INT8. It is the same in every round.

The summaries' `delta_pp` compares each round with the sealed run (deterministic view, control) or with `results/llm_view` (LLM view). The runtime differs from the sealed run, so the tables below also give the delta against round 0 / the previous kept round. That column isolates the patch.

## Round 1: initials of an already-detected name (kept)

**What it does.** It adds `_propagate_initials`, called at the end of `propagate_names`. It tags a standalone capital-plus-full-stop (`X.`), as in "Well done, V.!" or "Keep going, L..", but only when a name already detected in the same document begins with that letter.

- **Which names count.** The same set `propagate_names` already spreads: rule and propagated names, and model names with confidence ≥ 0.75.
- **What the tag gets.** The name's label, the name's confidence × 0.9, and `source="propagated"`.
- **Guards:**
  - No word character, `.` or apostrophe just before the letter.
  - Not followed by a word character, nor by `.` plus a word character. This excludes "U.S.", "a.m." and "e.g.", but accepts an initial followed by the sentence's own full stop ("L..").
  - Not after an arithmetic operator ("x = A.").
  - Not after a word that makes it a label: "point A.", "option B.", "answer C.", "angle", "side", "grade", "part", "step", "question", …
  - Not where the span overlaps an existing entity.

**Why in `propagate_names`, not `detect_rules`.** With a model loaded, `NAME_STUDENT` is under model authority and `detect_rules` is not run for it (`edshield/__init__.py`, `analyze_text`). A name rule in `detect_rules` would never fire in rules+model mode. `propagate_names` runs after the model.

**Causes addressed** (`results/diagnosis/causes.jsonl`, primary-order rows, joined to the failure tables):

- Form `nickname:initial`, primary TOKENIZATION, fix RULE:
  - 166 deterministic rows, mean confidence 0.78.
  - 164 LLM-view rows, mean confidence 0.77.
- This is the largest RULE cause in both views. It includes all ten "highest-confidence RULE / GAZETTEER misses" except "Summit Prep" in `results/diagnosis/summary.md`.

**Offline preview before the run** (re-applying the patched `propagate_names` to round 0's stored entities; an estimate only):

- 159 of 168 deterministic and 144 of 164 LLM-view gold initials newly tagged.
- 1 non-gold tag on the planted sets.
- 0 new tags on either control dataset.

**Numbers** (all from `results/candidate/round_1/summary.json`; round 0 from `results/candidate/round_0/summary.json`):

| metric | round 0 | round 1 | summary `delta_pp` | vs round 0 |
|---|---|---|---|---|
| deterministic, all identifiers (n=2841) | 89.97% | 94.40% [93.50, 95.19] | +4.08 pp | +4.44 pp |
| deterministic, student names (n=2014) | 88.03% | 94.29% | +5.86 pp | +6.26 pp |
| LLM view, all identifiers (n=2767) | 91.83% | 96.49% [95.74, 97.12] | +4.66 pp | +4.66 pp |
| LLM view, student names (n=1967) | 88.92% | 95.48% | +6.56 pp | +6.56 pp |
| control comta, flags per 1,000 tokens | 0.503 (21) | 0.503 (21) | 0.0 | +0.000 |
| control mathdial, flags per 1,000 tokens | 15.102 (2,794) | 15.102 (2,794) | −1.113 | +0.000 |

- **Misses** (from the `make eval-candidate` console output):
  - deterministic: 285 → 159
  - LLM view: 226 → 97
- **Name categories.** Every student-name category rises on both views against round 0:
  - deterministic: +5.13 to +7.21 pp
  - LLM view: +5.74 to +7.47 pp
- **Other labels.** All other labels are unchanged.
- **Control.** No regression against pinned baseline round 0 on either control dataset: identical flag counts.

**What it does not fix:**

- **Initials the scorer still counts as leaked: 33 deterministic, 15 LLM view** (reason `elsewhere` in `results/candidate/round_1/*/misses.csv`).
  - The mention itself is masked. The residual rule case-folds `A.` to `a` and searches for it as a whole word anywhere in the output, so the article "a", the pronoun "I" and contraction tails ("let's", "don't") hit `A.`, `I.`, `S.`, `T.`, `M.`.
  - Letters among all 40 remaining deterministic initial misses: A 11, S 8, M 6, I 5, T 4, …
  - No rule can recover these without masking ordinary words. The scorer is out of scope.
- **Initials with no usable anchor: 7 deterministic, 20 LLM view** (reason `nickname`).
  - Either the student's name was never detected, or only by the model below 0.75. Weak model guesses are not spread, by the existing design decision.
- **Risk outside the bench.** An unrelated standalone capital-plus-full-stop that shares a detected student's initial is masked in the same document (e.g. "it's in box A." when the student is Alex).
  - That is a false alarm, not a leak, and the project ranks recall first.
  - The measured control delta is +0.000, but a reviewer may want to extend the label-word list.

## Round 2: short school names "X High" and "X Prep" (kept)

**What it does.** It appends `High` and `Prep` as the last alternatives of `SCHOOL_TYPES`.

- The longer forms ("High School", "Junior High", "Preparatory School") stay earlier in the alternation, so they still match whole.
- The existing guards are unchanged: a sentence opener is stripped, and a name made only of kind words ("Junior High", "In High School", "So High") is skipped.
- `SCHOOL` is rules-only, so this works with or without the model.

**Causes addressed.** All 22 deterministic-view SCHOOL misses, primary SCHEMA_GAP:

- 20 rows fix RULE (mean confidence 0.67) and 2 rows fix GAZETTEER (0.80).
- Forms: "X High" 12, "X Prep" 10. Three distinct planted names.
- Includes "Summit Prep" (comta-014), the second-highest-confidence RULE miss in `results/diagnosis/summary.md`.
- The regex finds neither form anywhere in the control text (checked before the run).

**Numbers** (all from `results/candidate/round_2/summary.json`; round 1 from `results/candidate/round_1/summary.json`):

| metric | round 1 | round 2 | summary `delta_pp` | vs round 1 | vs round 0 |
|---|---|---|---|---|---|
| deterministic, all identifiers (n=2841) | 94.40% | 95.18% [94.33, 95.91] | +4.86 pp | +0.77 pp | +5.21 pp |
| deterministic, SCHOOL (n=218) | 89.91% | 100.0% | +10.09 pp | +10.09 pp | +10.09 pp |
| deterministic, student names (n=2014) | 94.29% | 94.29% | +5.86 pp | +0.00 pp | +6.26 pp |
| LLM view, all identifiers (n=2767) | 96.49% | 96.49% [95.74, 97.12] | +4.66 pp | +0.00 pp | +4.66 pp |
| LLM view, SCHOOL (n=213) | 100.0% | 100.0% | 0.0 pp | +0.00 pp | +0.00 pp |
| control comta, flags per 1,000 tokens | 0.503 (21) | 0.503 (21) | 0.0 | +0.000 | +0.000 |
| control mathdial, flags per 1,000 tokens | 15.102 (2,794) | 15.102 (2,794) | −1.113 | +0.000 | +0.000 |

- **Misses:** deterministic 159 → 137; LLM view unchanged at 97.
- **Control.** No regression against pinned baseline round 1 on either control dataset.

**What it does not fix, and caveats:**

- **The gain is on the deterministic view only.**
  - The LLM view's SCHOOL slice was already at 100%.
  - `results/view_comparison.md` lists SCHOOL among slices that move with phrasing alone.
  - The +0.77 pp reflects how the deterministic templates write school names (three names). How often short forms occur in real student chat is not measured here.
- **New false alarms.** A title-case phrase ending in "High" or "Prep" is now flagged as SCHOOL:
  - "Too High" (checked by hand: flagged)
  - "Test Prep" and "SAT Prep" (expected from the regex, not checked)

  Lower-case "high" and "prep" are unaffected.
- **Lower-case school names** ("jefferson high") remain uncovered.

## What the loop leaves unfixed

Round 2 misses, joined to `results/diagnosis/causes.jsonl`:

- **Deterministic view (137 misses):**
  - 40 `nickname:initial`: 33 are the scorer artefact above.
  - 30 + 4 + 3 + 2 NAME_WORD_COLLISION / REGISTER rows labelled MODEL (e.g. a name that is also an ordinary word). These need the model, not a rule.
  - 10 REGISTER lowercase-first-name rows labelled RULE.
  - 5 OTHER and 4 NAME_WORD_COLLISION capitalised rows labelled RULE.
  - The rest are small.
- **LLM view (97 misses):**
  - 35 initials.
  - 9 + 7 truncated nicknames (RULE / MODEL).
  - 8 + 9 collisions (RULE / MODEL).
  - 6 lowercase first names.
  - The rest are small.

## Why the loop stopped after round 2

**None of the listed stop conditions fired:**

- Round 1 improved deterministic identifier recall by +4.44 pp over round 0.
- Round 2 improved it by +0.77 pp over round 1. Both are above the 0.5 pp continuation bar.
- Neither round raised control over-redaction (+0.000 flags per 1,000 tokens on both datasets).
- Two of three rounds were used, and the budget was not reported as reached.

**I stopped by judgment, for this reason.** No single focused change left can clear the 0.5 pp bar on the deterministic view:

- The largest remaining RULE cause there that a rule could reach is lowercase first names (REGISTER / RULE, 10 rows). Recovering all of them would add at most 10 / 2841 = 0.35 pp.
- That cause is also the riskiest for the control ("im fine", "i'm good").
- The 33 `elsewhere` initials are a scorer artefact that no rule can reach.

A third round would therefore have been expected to end the loop under the "less than 0.5 pp" condition, at the cost of another full evaluation. Given the session's instruction to prefer fewer, better-measured rounds, I did not run it.
