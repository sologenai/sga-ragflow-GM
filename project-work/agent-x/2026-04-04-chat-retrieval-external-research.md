# Chat Retrieval External Research

Date: 2026-04-04
Owner: agent-x
Status: completed

## Research Goal

Investigate how mixed chat plus knowledge-base systems should handle retrieval more effectively than a forced "always retrieve from KB" strategy.

## High-Level Conclusion

Recent research consistently points away from a rigid "always retrieve first" design.

The more effective direction is:

1. decide whether retrieval is needed
2. evaluate whether retrieved evidence is good enough
3. escalate to deeper or iterative retrieval only when needed
4. separately control graph retrieval and deep reasoning

## Strong Signals From Primary Sources

### 1. Do not retrieve indiscriminately

Source:
- Self-RAG: https://arxiv.org/abs/2310.11511

Key point:
- indiscriminate fixed retrieval hurts versatility and can introduce unhelpful generations
- retrieval should happen on demand

### 2. Route by query complexity

Source:
- Adaptive-RAG: https://arxiv.org/abs/2403.14403

Key point:
- the system should dynamically select among:
  - no retrieval
  - single-step retrieval
  - multi-step retrieval
- based on query complexity rather than using one fixed strategy for every question

### 3. Judge retrieval quality before trusting context

Source:
- CRAG: https://arxiv.org/abs/2401.15884

Key point:
- a lightweight retrieval evaluator should assess the quality of retrieved documents
- the result should trigger different actions such as:
  - accept
  - correct / rewrite / expand
  - treat as ambiguous

### 4. Retrieval can actively harm generation when not needed

Source:
- SeaKR: https://arxiv.org/abs/2406.19215

Key point:
- retrieval should be triggered when the model is uncertain
- SeaKR reports that forcing retrieval each step degrades both simple QA and complex QA
- retrieved information can mislead the model when external knowledge is unnecessary or poorly aligned

### 5. Long-form or multi-hop tasks benefit from iterative retrieval

Source:
- Active Retrieval Augmented Generation / FLARE: https://arxiv.org/abs/2305.06983

Key point:
- one-shot retrieve-then-generate is limiting for longer or more knowledge-intensive generation
- retrieval should be iterative and confidence-aware for these cases

### 6. Modern adaptive RAG is moving toward lightweight evidence sufficiency control

Source:
- ReflectiveRAG: https://www.amazon.science/publications/reflectiverag-rethinking-adaptivity-in-retrieval-augmented-generation

Key point:
- static heuristics and fixed top-k retrieval degrade under noise
- a small decision controller can iteratively evaluate evidence sufficiency
- contrastive filtering can remove redundant or tangential passages

### 7. Evaluation must separately diagnose retrieval and generation

Sources:
- RAGChecker: https://www.amazon.science/publications/ragchecker-a-fine-grained-framework-for-diagnosing-retrieval-augmented-generation
- VERA: https://www.amazon.science/publications/vera-validation-and-evaluation-of-retrieval-augmented-systems
- Automated evaluation of retrieval-augmented language models with task-specific exam generation: https://www.amazon.science/publications/automated-evaluation-of-retrieval-augmented-language-models-with-task-specific-exam-generation

Key point:
- retrieval problems and generation problems should not be mixed into one vague "answer quality" metric
- retrieval algorithm choice can matter more than simply upgrading the language model

## What This Means For Our Project

The current local behavior should not be optimized further around "force all chat through KB".

Instead, retrieval policy should be explicitly separated into at least three decisions:

1. Should we retrieve?
2. If yes, what retrieval mode should we use?
3. If retrieved evidence is weak, what correction or escalation should happen?

## Recommended Product Direction

### Recommended model

Introduce a retrieval strategy field, separate from prompt wording and separate from the Thinking button.

Suggested values:

- `auto`
- `always`
- `off`

For `auto`, use a staged policy:

1. classify the question
   - small talk / rewriting / translation / generic reasoning -> no retrieval
   - factual KB question -> single-step retrieval
   - multi-hop / comparison / synthesis / cross-document analysis -> deep retrieval

2. evaluate retrieval sufficiency
   - if strong enough -> answer
   - if weak -> query rewrite or second-pass retrieval
   - if still weak -> fallback answer without forced KB anchoring

3. keep knowledge graph as an independent enhancement switch
   - do not let `use_kg` pretend to be the main retrieval switch

4. keep deep research as an independent escalation policy
   - do not make answer quality depend on whether the user manually clicks the Thinking button

## Recommended Delivery Plan

### Phase 1: stop the main damage

- stop treating default chat as mandatory KB-first mode
- add an explicit retrieval strategy setting
- make `Thinking` no longer the hidden gate to "better knowledge retrieval"

### Phase 2: add retrieval gating

- implement lightweight routing:
  - no retrieval
  - standard retrieval
  - deep retrieval

### Phase 3: add retrieval quality correction

- retrieval evaluator
- query rewrite
- redundant chunk filtering

### Phase 4: add evaluation harness

- build a task-specific benchmark on our own customer corpus
- measure:
  - retrieval hit quality
  - grounded answer quality
  - latency
  - fallback quality when KB is weak

## Project Manager View

This should be treated as a product behavior redesign, not a prompt tweak.

The right future state is:

- prompt controls answer style
- retrieval strategy controls whether and how to retrieve
- knowledge graph switch controls graph enhancement
- deep research controls multi-step escalation

These should not be hidden inside one another.
