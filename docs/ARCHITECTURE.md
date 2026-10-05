# How the agents, the bench and the judge fit together

State on 2026-10-05. This page shows who does what in the edshield improvement
loop, what moves between them, and which steps still need a person. The rules
each role works under are in [LOOP.md](LOOP.md).

![edshield agent loop: two AI agents change the system, each try runs through edshield and the measurement bench, a fixed judge gives the verdict, guardrails keep the loop honest, and a sealed test plus human review gate any release](edshield-agent-loop.png)

Two Claude Code agents do the work. Neither decides whether edshield is good
enough: a pinned, task-blind judge does that from rows and a policy file, and
a human reviewer owns the pass marks, the sealed sets and every merge.

## 1. Who does what

```mermaid
flowchart TB
    H["Human review<br/>sets the pass marks, approves merges,<br/>holds the seal key, triggers acceptance"]

    subgraph CLOUD["Cloud agent: Claude Code in a cloud session"]
        C1["Builds and maintains the bench"]
        C2["Reads reports, writes the diagnosis"]
        C3["Proposes edshield changes on a branch"]
    end

    subgraph GH["GitHub: the shared state"]
        E["edshield<br/>rules, model code, candidate branches"]
        B["edshield-evidence<br/>bench code, policies, reports,<br/>ledger, sealed sets"]
    end

    subgraph PC["PC agent: Claude Code on the GPU machine"]
        P1["Writes training text, trains the model"]
        P2["Installs a candidate and measures it"]
        P3["Reads reports, plans the next experiment"]
        P4["Seals acceptance sets after review"]
    end

    subgraph LOCAL["On the PC only, never uploaded"]
        D["PIILO holdout: 680 real essays"]
        M["Model checkpoints and the GPU"]
        S["Readable text of sealed sets, the seed"]
    end

    J["Judge: model-evidence CLI<br/>pinned by tag, deterministic,<br/>knows nothing about edshield"]

    C1 -- "bench code, tests" --> B
    C2 -- "diagnosis notes" --> B
    C3 -- "candidate branch" --> E
    CLOUD -. "task message, one way" .-> PC
    E -- "pull candidate" --> P2
    B -- "pull bench" --> P2
    D --> P2
    M --> P1
    P1 -- "candidate branch" --> E
    P2 -- "rows + policy" --> J
    J -- "pass, fail or insufficient" --> P2
    P2 -- "report, ledger row" --> B
    P4 -- "encrypted set" --> B
    S --> P4
    H -- "approve, merge, ratify" --> GH
    H -- "review draft, store key" --> P4
```

## 2. One cycle of the loop

```mermaid
sequenceDiagram
    autonumber
    participant H as Human review
    participant PC as PC agent
    participant J as Judge
    participant GH as GitHub
    participant CL as Cloud agent

    PC->>PC: run edshield on the practice sets
    PC->>J: rows and the regression policy
    J-->>PC: verdict per view
    PC->>GH: report folder and ledger rows
    Note over PC,CL: diagnose, either agent reads the report
    CL->>GH: diagnosis note, or a rules change on a branch
    PC->>PC: or new training text and a retrained model
    PC->>GH: candidate branch
    PC->>PC: install the candidate, measure again
    PC->>J: rows and the regression policy
    J-->>PC: verdict, must not be worse than the release
    PC->>GH: candidate report, marked CANDIDATE
    Note over PC,CL: repeat until the practice sets reach the pass mark or a stop rule hits
    PC->>H: ready for the sealed set
    H->>GH: merge decision, then trigger acceptance on a sealed set
    GH->>J: rows from the sealed set and the acceptance policy
    J-->>H: pass or fail, the set is now used
```

## 3. What happens inside one measurement

```mermaid
flowchart LR
    A["Documents with known identifiers<br/>PIILO holdout, k12_hard, or a sealed set"]
    X["edshield.deidentify<br/>rules + model + policy coppa"]
    R["Residual scoring<br/>is each identifier still in the output?"]
    V["Bundle of 0/1 rows<br/>per identifier, document, word, type"]
    P["Policy for this set<br/>targets with a sha256"]
    J["Judge"]
    O["verdict.json"]
    S["summary.md and one ledger row"]
    G["diagnostics.json<br/>counts by label, examples<br/>for practice sets only"]

    A --> X --> R --> V --> J
    P --> J
    J --> O --> S
    R --> G --> S
```

The scorer looks only at the final text edshield returns. An identifier counts
as handled when its text no longer occurs whole in the output, whatever label
edshield gave it.

## 4. What is automated and what is not

| Step | Who or what does it today |
|---|---|
| Run edshield on a set, score residuals, call the judge, write the report and ledger row | One script, `scripts/baseline.sh`, started by the PC agent |
| Pass or fail | The judge, from the rows and a policy file. No agent computes a verdict |
| Reading a report and choosing the next change | An agent (cloud or PC) |
| Rules changes, training text, model training | An agent, on a candidate branch |
| Measuring a candidate against the release | The PC agent, without asking |
| Uploading candidate branches and candidate reports | The PC agent, without asking, since 2026-10-05 |
| Handing work from the cloud agent to the PC | A one-way message. The PC agent answers through GitHub; there is no direct reply channel, so a person has carried replies by hand |
| Merging into edshield `main`, releasing | Human review |
| Reviewing a draft set, storing the seal key | Human review |
| Ratifying the pass marks (they are still PROVISIONAL) | Human review |
| Running acceptance on a sealed set | A human triggers it; each set can be used once |
| Starting cycles on a schedule with no session open | Not built. A cycle runs while an agent session is working |

## 5. Where the loop stands

| Measurement under policy `coppa` | Identifiers removed | Source |
|---|---|---|
| Release 0.2.0, PIILO holdout, rules + model | 165 of 165 | report `2026-10-04-6c0f163` |
| Release 0.2.0, k12_hard, rules + model | 1,099 of 1,433 (76.7%) | report `2026-10-04-6c0f163` |
| Candidate rules `c7be261`, PIILO holdout | 165 of 165, word false-alarm rate 0.08% | report `2026-10-05-f368ecb-cand-c7be261` |
| Candidate rules `c7be261`, k12_hard, rules + model | 1,268 of 1,433 (88.5%) | report `2026-10-05-f368ecb-cand-c7be261` |
| Model experiment 1 (learns town, school and street names), PIILO holdout | 165 of 165, word false-alarm rate 0.08% | report `2026-10-05-754e392-cand-928f50a` |
| Model experiment 1, k12_hard, rules + model | 1,425 of 1,433 (99.4%) | report `2026-10-05-754e392-cand-928f50a` |
| Model experiment 2 (adds names before 's), PIILO holdout | 165 of 165, word false-alarm rate 0.08% | report `2026-10-05-b145ba2-cand-3dc1431` |
| Model experiment 2, k12_hard, rules + model | 1,432 of 1,433 (99.9%), word false-alarm rate 0.23% | report `2026-10-05-b145ba2-cand-3dc1431` |
| Sealed set A1 | sealed 2026-10-05, not yet used | `evidence/sets/A1.manifest.json` |

The acceptance policy asks for 99.5% of identifiers removed overall and 98%
for every type, on a sealed set. The k12_hard gain from the candidate rules is
a check and not independent evidence, because those rules were shaped from
that set's misses. A pass on a sealed set shows that edshield meets these
redaction criteria on that set; it is not a legal finding about any law.
