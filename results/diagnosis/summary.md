# Miss diagnosis (Batch API, claude-opus-5-5)

Rubric `prompts/diagnose_system.md` sha256 `c242140c89c66464…`; 501 rows diagnosed, 0 rejected (see the run directory). Every number below is read from `results/diagnosis/causes.jsonl`.

## View: deterministic (275 misses)

| primary cause | n | share | mean confidence |
|---|---|---|---|
| TOKENIZATION | 176 | 64.0% | 0.76 |
| NAME_WORD_COLLISION | 43 | 15.6% | 0.72 |
| SCHEMA_GAP | 23 | 8.4% | 0.68 |
| REGISTER | 20 | 7.3% | 0.65 |
| OTHER | 10 | 3.6% | 0.48 |
| CONTEXT_CUE_MISSING | 2 | 0.7% | 0.53 |
| NON_ANGLO_NAME | 1 | 0.4% | 0.50 |

| fix class | n | share |
|---|---|---|
| RULE | 218 | 79.3% |
| MODEL | 48 | 17.5% |
| NONE | 7 | 2.5% |
| GAZETTEER | 2 | 0.7% |

Primary cause by name category:

| category | REGISTER | NAME_WORD_COLLISION | NON_ANGLO_NAME | SCHEMA_GAP | TOKENIZATION | CONTEXT_CUE_MISSING | AMBIGUOUS | OTHER |
|---|---|---|---|---|---|---|---|---|
| anglo_common | 1 | 2 | 0 | 6 | 45 | 0 | 0 | 1 |
| name_word_collision | 7 | 39 | 0 | 5 | 39 | 1 | 0 | 4 |
| nicknames_and_variants | 5 | 2 | 1 | 7 | 42 | 1 | 0 | 3 |
| non_anglo | 7 | 0 | 0 | 5 | 50 | 0 | 0 | 2 |

## View: llm (226 misses)

| primary cause | n | share | mean confidence |
|---|---|---|---|
| TOKENIZATION | 190 | 84.1% | 0.74 |
| NAME_WORD_COLLISION | 18 | 8.0% | 0.72 |
| REGISTER | 8 | 3.5% | 0.69 |
| OTHER | 8 | 3.5% | 0.50 |
| NON_ANGLO_NAME | 1 | 0.4% | 0.60 |
| SCHEMA_GAP | 1 | 0.4% | 0.50 |

| fix class | n | share |
|---|---|---|
| RULE | 190 | 84.1% |
| MODEL | 28 | 12.4% |
| NONE | 6 | 2.7% |
| LABEL_SCHEMA | 2 | 0.9% |

Primary cause by name category:

| category | REGISTER | NAME_WORD_COLLISION | NON_ANGLO_NAME | SCHEMA_GAP | TOKENIZATION | CONTEXT_CUE_MISSING | AMBIGUOUS | OTHER |
|---|---|---|---|---|---|---|---|---|
| anglo_common | 0 | 0 | 0 | 0 | 47 | 0 | 0 | 0 |
| name_word_collision | 5 | 17 | 0 | 1 | 45 | 0 | 0 | 5 |
| nicknames_and_variants | 1 | 0 | 0 | 0 | 43 | 0 | 0 | 0 |
| non_anglo | 2 | 1 | 1 | 0 | 55 | 0 | 0 | 3 |

## Consistency check

100 rows were submitted twice, the second time with the taxonomy listed in reverse order. Primary-cause agreement: **98/100 = 98%**; fix-class agreement: 95/100 = 95%.

## Ten highest-confidence RULE / GAZETTEER misses

| view | dataset | doc | span | cause | fix | conf | evidence |
|---|---|---|---|---|---|---|---|
| deterministic | mathdial | mathdial-test-172 | `V.` (nickname:initial) | TOKENIZATION | RULE | 0.82 | Give it another try, [[V.]]. |
| deterministic | comta | comta-014 | `Summit Prep` (school) | SCHEMA_GAP | RULE | 0.80 | hi im sam from [[Summit Prep]]. |
| deterministic | comta | comta-022 | `M.` (nickname:initial) | TOKENIZATION | RULE | 0.80 | Tutor: Great question, [[M.]]! No problem at all! |
| deterministic | comta | comta-029 | `B.` (nickname:initial) | TOKENIZATION | RULE | 0.80 | Well done, [[B.]]! |
| deterministic | comta | comta-030 | `L.` (nickname:initial) | TOKENIZATION | RULE | 0.80 | Let's look at that together, [[L.]]. Fantastic! |
| deterministic | comta | comta-058 | `I.` (nickname:initial) | TOKENIZATION | RULE | 0.80 | Keep going, [[I.]]. |
| deterministic | comta | comta-059 | `K.` (nickname:initial) | TOKENIZATION | RULE | 0.80 | Keep going, KARTHIK. ... What is \(12 \times 11\)? Well done, [[K.]]! |
| deterministic | comta | comta-063 | `G.` (nickname:initial) | TOKENIZATION | RULE | 0.80 | Does that make sense, [[G.]]? |
| deterministic | comta | comta-069 | `Z.` (nickname:initial) | TOKENIZATION | RULE | 0.80 | Well done, [[Z.]]! |
| deterministic | comta | comta-081 | `R.` (nickname:initial) | TOKENIZATION | RULE | 0.80 | Tutor: Good thinking, [[R.]]. That's right! |

Batch spend for this component: $2.00 (from the per-request `usage` fields, batch price).
