# Findings: edshield 0.2.0 on real tutoring dialogue with planted identifiers

Preliminary. PyPI release 0.2.0, model `edshield/piilo-deberta-v3-small` rev `5effafd`, coppa policy, no tuning. Names from four lists planted into 188 CoMTA (real students ↔ Khanmigo) and 599 MathDial test (simulated students, human tutors) dialogues, seed 20261014. StudyChat is gated to this account; TSCC v2 not yet received. Recall is the residual rule: the identifier no longer occurs whole in the output. 95% Wilson intervals; tables in `results/`.

**1. In-domain vs real dialogue.** PIILO holdout: 165 of 165 identifiers, 100% [97.7, 100]. Planted dialogue, pooled: 90.3% [89.2, 91.4] of 2,841 identifiers; student names 88.4% [87.0, 89.8] of 2,014. CoMTA 85.3% [82.3, 87.9], MathDial 91.7% [90.5, 92.8]. Counting a surviving surname as a miss: 85.9%.

**2. What fails.** Initials dominate: "R." was caught 2 times in 168 (1.2% [0.3, 4.2]); ALL-CAPS and truncated forms held at 93–95%. Base-form names, pooled: Anglo 99.3%, nicknames-as-names 98.6%, non-Anglo 97.5%, name-word collisions 90.9% [87.7, 93.3]. CoMTA, the only real-student text, is worse in every category: Anglo 96.9%, non-Anglo 92.0%, collisions 70.7% [59.6, 79.8] (Art, May, Summer, Fourier, Bayes). Lowercase names in student turns: 74.6% vs 89.4% capitalised. School names without a "School/Academy/Elementary" token: 0 of 22. Email and phone: 100%.

**3. Over-redaction on the untouched control.** CoMTA: 0.50 flags per 1,000 tokens (21 flags: word-problem characters, "Khan Academy", two numbers), none on curricular terms. MathDial: 16.2 per 1,000, of which 2,407 are word-problem characters and 446 the simulated student's own name; none curricular. PIILO: 0.41 per 1,000 non-gold flags, 2 curricular. Newton, Taylor, Pascal, Euler, Riemann, mean and mode were never flagged.

**4. Verbatim misses (planted names only).**
- `Tutor: Let's look at that together, G. Great! Let's break this down` — initial, untouched.
- `Student: hi im summer from Hillcrest Middle School. how can I plot 3x + 2y = -4` — lowercase collision name, untouched; the school was caught.
- `Student: hi im chidi okafor integrate sin(x)cos(x) dx` — lowercase non-Anglo name, untouched; the later "Chinedu" was masked.

**5. Implication.** On an unseen genre this 44M-parameter model recalls about 9 in 10 planted student names, and the interval excludes 99.5% for every slice except capitalised base-form Anglo names on the simulated-student set; a certified 99.5% floor on an unseen genre is not supported. It fails on short forms, lowercase and word-like names before it fails on name origin.

Limits: whole transcripts scored as one document; MathDial student turns are LLM-written; one seed.
