# results/v2: protocol notes and deviations from BRIEF_v2.md

Everything here except this file and `meta/` is written by `score_v2.py` and `plot_v2.py`
(`make v2-score`). Definitions used by the numbers are also in `metrics.json` under `definitions`.

**Not run.** StudyChat (gated repository, 403 on 2026-11-27) and TSCC (no files in
`data/raw/tscc/`). Floor transfer therefore has two ordered pairs, CoMTA→MathDial and
MathDial→CoMTA. The loaders and the 600-dialogue sample are in place; rerun `make v2` once
the data is there.

**Scoring.**
- A gold name is caught when the union of predicted NAME spans covers at least 50% of its
  characters (one span is not required). Exact-match and any-label recall are secondary columns in T1.
- v1 scored by the residual rule (the identifier no longer occurs in the redacted output), so
  v1 and v2 recall for edshield differ slightly.
- Pooled Wilson intervals treat the five seeds as independent. They replant the same dialogues,
  so the intervals are too narrow; the SD over seeds is reported next to them.
- Clopper–Pearson lower bounds are one-sided 95%.

**Strata.** `case` is recorded with three levels (lower, cap, allcaps) and folded to two
(lower, upper) in the primary stratum, which gives the brief's 8 strata. MathDial has no lowercase
names (4 strata), CoMTA has no lowercase names in tutor turns (6 strata). The ablation adds one set
the brief does not list, `primary x is_initial`. In a transfer A→B, a stratum of B that A never
observed has no rate: the point prediction renormalises over the strata A covers and the floor
counts it as 0. T6 (probe cost) is an extra table.

**Detectors.**
- `hf_pii` runs in 256-token windows with a 64-token overlap, the context length the model card
  gives. A first run passed whole documents (the tokenizer config sets no limit) and was discarded.
- `gpt4o_mini`: the prompt asks for the span text as well as the offsets. The offsets matched the
  text for 428 of 18,387 returned spans; 17,389 were moved to the occurrence of the returned text
  nearest the claimed offset and 570 were dropped. Output is capped at 2,000 tokens because JSON mode
  sometimes loops; a truncated answer is unparseable, is retried once and then scored as no flags
  (45 of 5,166 documents; recall without those documents is in `metrics.json` under
  `unparsed_documents`). The cache holds offsets and labels only. Spend: $0.93 of the $30 cap,
  served model `gpt-4o-mini-2024-07-18`.
- `gpt4o_mini_propagated` is a secondary detector built from the same responses: every whole-word
  occurrence of each returned string is flagged. It is in the tables and figures but not in the
  summary statistics over detectors.
- Presidio LOCATION/ORG and Piiranha USERNAME do not count as NAME (see `detectors/labelmap.py`).

**Data.**
- The PIILO holdout was rebuilt from the public corpus (`rebuild_piilo.py`); it is token- and
  gold-identical to the original, not byte-identical. PIILO precision counts NAME flags on names
  that are not the gold student name as false.
- `misses.csv` covers the five primary detectors and the dialogue sets only. CoMTA contexts are cut
  to 6 tokens either side because its licence does not allow redistribution; MathDial contexts are
  20 tokens.
- A regular-expression scan of the raw CoMTA and MathDial dialogues found no email address or
  phone number.

**Hardware.** CPU only (4 cores); versions and timings per detector are in `meta/` and in
`metrics.json` under `run`.
