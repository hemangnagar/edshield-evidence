You are diagnosing one miss of a student-privacy detector. The detector is edshield 0.2.0: a rule layer (regular expressions for emails, phones, usernames, IDs, addresses, dates, schools, cued names such as "my name is X" and "my brother X") under a small DeBERTa token-classification model trained on student essays (PIILO) that owns the NAME_STUDENT label; detected names are propagated to their other capitalised occurrences in the document; the coppa policy then masks every acted-on span. The text is real tutoring dialogue (students talking to a math tutor) into which synthetic identifiers were planted. The gold span was not removed from the output.

You receive: the dataset, the name category the planted name was drawn from, the gold span's label and planted form, a window of the dialogue with the missed span marked as [[...]], and what the detector did with that span (which labels, if any, touched it; whether this mention was masked; whether the same string was masked elsewhere in the document). Decide the primary cause from the closed taxonomy below, an optional secondary cause, how it could be fixed, and quote the tokens that drove your call.

Taxonomy (closed set; use the code exactly):

- REGISTER: lowercase, missing punctuation or a typo defeated a capitalisation- or pattern-dependent detector.
- NAME_WORD_COLLISION: the name is also a common or curricular word (Grace, Will, Summer, Newton, Riemann, product, tangent).
- NON_ANGLO_NAME: the name sits outside the model's apparent name prior (it is well formed and cued, yet missed).
- SCHEMA_GAP: the identifier type is not covered well by the rules or the label set (a school name without a School/Academy/High token, an obfuscated email, a bare username with no cue).
- TOKENIZATION: a span-boundary or sub-word problem, typically a partial detection (an initial like "R.", a truncated or all-caps form, a hyphenated or apostrophised name split by the tokenizer).
- CONTEXT_CUE_MISSING: nothing in the surrounding text signals that this token is a person or a place (a bare name mid-sentence, no "I'm", no greeting, no title).
- AMBIGUOUS: a careful human annotator could reasonably disagree that this span is an identifier here.
- OTHER: none of the above; give a one-line reason in `note`.

Fix class (one): RULE (a regular expression or cue rule would catch it), GAZETTEER (a name or school list lookup would catch it), MODEL (needs the neural model to change: training data, threshold, casing robustness), LABEL_SCHEMA (needs a new or redefined label), NONE (not fixable or should not be fixed).

Be concrete and honest. A miss can be TOKENIZATION even when the name is non-Anglo; pick the cause that most directly explains this miss, and put the other in `secondary`. Do not invent context that is not in the window. `confidence` is your probability (0 to 1) that the primary cause is right. `evidence` quotes at most 25 words from the window, verbatim. Output only the JSON object.
