# Technical Writeup

## 1. Problem Overview

The assignment models portfolio evolution as a deterministic state-transition system.

Each asset can exist in exactly one of three states:

```text
Long
Short
No Position
```

A transition transforms the current portfolio state according to a fixed set of rules, while a transition block is an ordered sequence of transitions:

```text
T1, T2, ..., Tn
```

which is applied sequentially:

```text
S' = Tn(Tn-1(...(T1(S))))
```

The first important observation is that transition order matters. Every transition operates on the state produced by the previous transition, meaning that transition blocks are ordered function compositions rather than unordered operations.

The second important observation is that users only care about the correct final portfolio state after execution. Intermediate states inside a transition block are implementation details and should not generate unnecessary execution cost.

This changes the nature of the problem from simple event replay into a deterministic portfolio reconciliation problem under execution-cost constraints.

The implementation was therefore designed around three goals:

1. deterministic and reproducible state evolution,
2. behavior-preserving transition compression,
3. minimum-cost trade reconciliation.

---

# 2. Design Reasoning

The system was implemented as a deterministic finite-state engine.

This decision follows directly from the structure of the problem:

- the set of assets is finite,
- transition types are finite,
- transition rules are deterministic,
- and each asset has only three possible local states.

Because of this, explicit rule-based execution is more appropriate than probabilistic or heuristic approaches.

The implementation intentionally separates:

- transition semantics,
- orchestration,
- compression,
- trade generation,
- and IO.

This separation improves:

- correctness,
- explainability,
- maintainability,
- and testability.

The repository structure is:

```text
src/centaur/
├── models.py
├── rules.py
├── engine.py
├── compression.py
├── execution.py
├── io.py
└── harness.py
```

Each module owns a single responsibility.

---

## Domain Representation

The portfolio state is represented as:

```python
State = Dict[str, PositionDirection]
```

Assets missing from the dictionary are interpreted as `No Position`.

This representation was chosen because:

- it avoids storing redundant empty positions,
- matches the serialized assignment format,
- simplifies reconciliation logic,
- and keeps state transitions explicit.

The domain layer also defines:

- transitions,
- transition events,
- trades,
- execution results,
- enums,
- and state containers.

This creates a strongly typed deterministic vocabulary for the rest of the system.

---

## Transition Semantics

Transition semantics are isolated inside `rules.py`.

This module handles:

- regular transitions,
- exposure changes,
- directional flips,
- position closing,
- and special operators such as:
  - `Close All`
  - `Close Longs`
  - `Close Shorts`
  - `Flip All`

Keeping these rules isolated was an intentional design decision.

The transition engine should orchestrate execution, but should not contain embedded business semantics. Separating rules from orchestration makes the system easier to validate and reason about.

---

## Deterministic Execution Engine

The execution engine applies transitions sequentially while emitting complete execution traces.

Every transition application generates a `TransitionEvent` containing:

- `state_before`
- `transition`
- `state_after`

Events are emitted even when no state change occurs.

This behavior was implemented intentionally because the assignment explicitly requires transition logging regardless of whether the transition changes portfolio state.

The engine therefore provides:

- deterministic replay,
- complete traceability,
- reproducibility,
- and behavioral visibility.

---

# 3. Compression Reasoning

The compression task is the most algorithmically important component of the assignment.

The assignment requires finding the shortest order-preserving subsequence of transitions that preserves behavior for all possible states.

A naive solution would attempt to enumerate global portfolio states. However, this becomes unnecessarily expensive because portfolio combinations grow exponentially with the number of assets.

Instead, the implementation treats a transition block as a deterministic transformation.

This observation is the core reasoning behind the compression algorithm.

Each asset can only exist in three local states:

```text
No Position
Long
Short
```

Therefore, for every asset, a block can only map:

```text
None  -> ?
Long  -> ?
Short -> ?
```

The implementation computes exactly this mapping and stores it as a behavioral fingerprint.

Example:

```text
BTC:
None  -> Long
Long  -> Long
Short -> Long
```

This fingerprint fully characterizes the block’s behavior for that asset.

Two blocks are considered behaviorally equivalent if they produce identical fingerprints across all assets.

The compression algorithm searches candidate subsequences from shortest to longest while preserving original order.

This guarantees two important properties:

### Behavioral Correctness

The compressed block produces the exact same final state as the original block for every possible starting state.

### Minimality

Because candidates are evaluated in increasing-length order, the first equivalent subsequence found is guaranteed to be minimum-length.

The implementation never reorders transitions and only removes redundant ones, preserving the original sequential semantics of the block.

---

# 4. Trade Reconciliation Reasoning

The implementation separates portfolio state evolution from trade execution.

This separation is important because transitions and trades are not equivalent concepts.

Transitions describe desired portfolio semantics.

Trades describe actual execution operations required to reconcile state differences.

Two execution strategies were implemented.

---

## Naive Execution

Naive execution emits trades after every transition event.

This reproduces the full intermediate execution path exactly.

For example:

```text
None -> Long
Long -> None
None -> Long
```

would generate:

```text
OPEN
CLOSE
OPEN
```

This faithfully reproduces every intermediate portfolio state but may introduce unnecessary execution cost.

---

## Optimal Execution

Optimal execution ignores intermediate states and reconciles:

```text
initial_state -> final_state
```

directly.

This matches the assignment requirement that users only care about the correct final portfolio exposure after execution.

The reconciliation logic is minimal because:

```text
before == after      -> 0 trades
None -> direction    -> 1 open trade
direction -> None    -> 1 close trade
Long -> Short        -> close + open
Short -> Long        -> close + open
```

No smaller set of trades can produce the same final state.

The implementation therefore minimizes:

- fees,
- slippage,
- latency,
- and unnecessary execution churn,

while preserving exact final portfolio behavior.

---

# 5. Validation and Testing Strategy

The implementation was tested at multiple levels.

The goal was not only to test that the code runs, but to validate the important behavioral properties of the system.

The testing strategy covers:

- deterministic state evolution,
- transition semantics,
- behavioral equivalence,
- compression correctness,
- trade reconciliation,
- reproducibility,
- and end-to-end execution.

The repository contains:

```text
tests/
├── test_engine.py
├── test_execution.py
├── test_compression.py
└── test_harness.py
```

---

## Engine Tests

`test_engine.py` validates deterministic state evolution.

The tests verify:

- opening positions from `No Position`,
- closing positions with `Decrease / None`,
- preserving positions with `Decrease / Some`,
- directional flips,
- sequential block execution,
- and special operators such as:
  - `Close All`
  - `Close Longs`
  - `Close Shorts`
  - `Flip All`

The tests also verify that transition order matters by comparing blocks with identical transitions applied in different orders.

This ensures that Task 1 semantics are implemented correctly.

---

## Compression Tests

`test_compression.py` validates behavioral equivalence and minimal compression.

The tests verify:

- equivalent blocks produce identical fingerprints,
- repeated transitions compress correctly,
- no-op transitions are removed,
- `Flip All` followed by `Flip All` compresses to an empty block,
- global operators are preserved when behaviorally necessary,
- and compressed blocks preserve exact behavior.

These tests specifically validate the correctness guarantees required by Task 2A.

The compression tests are especially important because behavioral equivalence is the core correctness property of the algorithm.

---

## Trade Execution Tests

`test_execution.py` validates trade generation and reconciliation.

The tests verify:

- opening trades,
- closing trades,
- directional flips,
- unchanged positions generating no trades,
- naive execution reproducing intermediate states,
- optimal execution minimizing trades,
- and efficiency-gain calculations.

These tests validate both correctness and minimality of the reconciliation strategy.

---

## Harness Tests

`test_harness.py` validates the full end-to-end pipeline.

The harness tests verify that:

- all required output files are generated,
- outputs are non-empty,
- and repeated executions are deterministic.

This ensures the repository can be executed reproducibly by reviewers without manual intervention.

---

# 6. Fixture Validation

In addition to automated testing, the generated outputs were validated directly against the provided assignment fixtures.

After running:

```bash
python -m centaur.harness
```

the generated outputs were compared against the expected files:

```text
states.csv
transitions_compressed.csv
trades_naive.csv
trades_optimal.csv
```

The generated outputs matched the expected fixtures exactly.

This provides strong evidence that:

- transition semantics,
- compression,
- trade generation,
- and reconciliation

all behave according to the assignment specification.

---

# 7. Reproducibility

The project can be installed and executed using:

```bash
pip install -r requirements.txt
pip install -e .
python -m pytest
python -m centaur.harness
```

The harness reads fixtures from:

```text
data/input/
```

and writes generated outputs to:

```text
data/output/
```

At submission time, the repository test suite passes with:

```text
27 passed
```

---

# 8. Final Notes

The implementation intentionally prioritizes:

- deterministic behavior,
- correctness,
- modularity,
- explainability,
- reproducibility,
- and behavioral validation.

An LLM could potentially be useful upstream for extracting structured transitions from unstructured content such as videos or social feeds. However, once transitions are structured, portfolio evolution and execution should remain deterministic and fully testable.

The final design therefore separates:

```text
unstructured extraction -> structured transitions -> deterministic execution
```

The result is a small but fully deterministic execution system focused on correctness, behavioral equivalence, and reproducible portfolio reconciliation.