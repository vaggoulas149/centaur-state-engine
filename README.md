# centaur-state-engine

Deterministic state-transition framework for portfolio evolution, behavioral-equivalence compression, and minimal-cost trade execution under sequential trading semantics.

---

## 1. Problem Understanding

Centaur extracts structured trading transitions from unstructured content such as Telegram messages, YouTube videos, trader commentary, and social trading feeds.

The core problem is to maintain a trader’s current portfolio state.

Each asset can be in exactly one of three states:

```text
Long
Short
No Position
```

A transition modifies the current state. A block is an ordered sequence of transitions:

```text
T1, T2, ..., Tn
```

which is applied sequentially:

```text
S' = Tn(Tn-1(...(T1(S))))
```

The important business observation is that users following a trader only care about ending in the correct final state. They do not care about unnecessary intermediate states inside a block.

That makes the problem not just event replay, but deterministic state reconciliation with execution-cost awareness.

---

## 2. What Was Implemented

This repository implements the full assignment pipeline:

- deterministic state transition execution,
- sequential block execution,
- transition event logging,
- behavior-preserving block compression,
- naive trade generation,
- optimal trade reconciliation,
- efficiency gain calculation,
- CSV input/output handling,
- reproducible end-to-end harness,
- and automated tests.

The implementation was validated against the provided fixture files:

```text
states.csv
transitions_compressed.csv
trades_naive.csv
trades_optimal.csv
```

All generated outputs matched the provided expected outputs exactly.

---

## 3. Architecture

The code is organized as a small, explicit domain engine:

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

### `models.py`

Defines the core domain objects:

- `Direction`
- `PositionDirection`
- `ExposureChange`
- `TransitionType`
- `TradeAction`
- `Transition`
- `TransitionEvent`
- `Trade`
- `BlockExecutionResult`

The state is represented as:

```python
State = Dict[str, PositionDirection]
```

Assets missing from the dictionary are interpreted as `No Position`.

This keeps the state representation simple and efficient while matching the assignment model.

---

### `rules.py`

Contains the deterministic transition semantics.

It is responsible for applying:

- regular asset-specific transitions,
- `Close All`,
- `Close Longs`,
- `Close Shorts`,
- `Flip All`,
- `Flip Longs`,
- `Flip Shorts`.

This file isolates the actual business rules from orchestration logic.

That makes the system easier to inspect, test, and modify if transition semantics evolve later.

---

### `engine.py`

Implements the transition engine.

It supports:

```python
apply_transition(...)
apply_block(...)
execute_pipeline(...)
```

Each transition application produces a `TransitionEvent` containing:

```text
state_before
transition
state_after
```

This is logged even when the state does not change.

That gives the system a complete audit trail.

---

### `compression.py`

Implements block compression.

The key idea is to treat a block as a deterministic transformation.

Since each asset has only three possible local states:

```text
No Position
Long
Short
```

the behavior of a block can be represented by a compact fingerprint.

For each asset, the fingerprint records where the block maps each possible starting state:

```text
None  -> ?
Long  -> ?
Short -> ?
```

Two blocks are behaviorally equivalent if they produce the same fingerprint.

The compressor searches subsequences from shortest to longest, so the first equivalent subsequence found is guaranteed to be minimum-length.

The algorithm only removes transitions. It never reorders them.

---

### `execution.py`

Implements trade generation.

There are two execution modes.

#### Naive execution

Naive execution emits trades after every transition.

Example:

```text
Initial:
BTC = No Position

Transitions:
1. BTC Long Increase
2. BTC Long Decrease / None
3. BTC Long Increase
```

Naive trades:

```text
OPEN BTC Long
CLOSE BTC Long
OPEN BTC Long
```

This is correct, but inefficient.

#### Optimal execution

Optimal execution compares:

```text
initial_state -> final_state
```

and emits only the trades required to reconcile the portfolio.

For the same example, the final state is:

```text
BTC = Long
```

So optimal execution emits only:

```text
OPEN BTC Long
```

This preserves final-state correctness while reducing unnecessary execution cost.

---

### `io.py`

Handles CSV parsing and serialization.

It reads:

```text
assets.csv
transitions.csv
```

and writes:

```text
states.csv
transitions_compressed.csv
trades_naive.csv
trades_optimal.csv
```

CSV handling is separated from business logic so the engine remains deterministic and testable.

---

### `harness.py`

Implements the end-to-end assignment pipeline.

It:

1. reads input CSVs,
2. groups transitions by block,
3. applies blocks sequentially,
4. carries state from block to block,
5. logs transition events,
6. compresses blocks,
7. generates naive trades,
8. generates optimal trades,
9. writes all required output files.

Run it with:

```bash
python -m centaur.harness
```

---

## 4. Why This Architecture Was Chosen

The architecture separates the problem into clear layers:

```text
models      -> domain vocabulary
rules       -> transition semantics
engine      -> state evolution
compression -> behavioral equivalence
execution   -> trade reconciliation
io          -> CSV parsing/writing
harness     -> orchestration
tests       -> correctness validation
```

This was chosen because the assignment evaluates not only correctness, but also code quality and extensibility.

The design avoids a single large script and instead creates a small deterministic framework.

Benefits:

- each module has one responsibility,
- business rules are isolated,
- state evolution is easy to test,
- compression logic is independent,
- trade execution logic is independent,
- IO does not pollute core logic,
- and the harness is reproducible.

This makes the implementation easier to understand, modify, and validate.

---

## 5. Why This Implementation Is Correct and Efficient

### State transitions

State transitions are deterministic.

For every input:

```text
state + transition
```

there is exactly one output state.

This is implemented in `rules.py` and executed through `engine.py`.

---

### Block execution

Blocks are applied sequentially.

Order matters because each transition operates on the state produced by previous transitions.

Example:

```text
Block A:
1. BTC Long Increase
2. BTC Long Decrease / None

Result:
No Position -> Long -> No Position
```

Reversed:

```text
Block B:
1. BTC Long Decrease / None
2. BTC Long Increase

Result:
No Position -> No Position -> Long
```

The final states differ, so transitions cannot be treated as unordered operations.

---

### Compression

Compression preserves behavior for all possible states by comparing fingerprints.

Because each asset has only three local states, the fingerprint fully captures how a block behaves for that asset.

The compressor searches subsequences from shortest to longest.

Therefore, once it finds an equivalent subsequence, it is guaranteed to be minimum-length.

---

### Optimal trade execution

Optimal execution is based on direct state reconciliation.

It compares:

```text
initial_state
final_state
```

and emits the smallest necessary trade set.

This is minimal because:

- unchanged assets require zero trades,
- opening a position requires one trade,
- closing a position requires one trade,
- flipping direction requires two trades:
  - close old direction,
  - open new direction.

No smaller trade sequence can produce the required final state.

---

## 6. Repository Structure

```text
centaur-state-engine/
├── data/
│   ├── input/
│   └── output/
├── docs/
│   └── writeup.md
├── src/
│   └── centaur/
│       ├── __init__.py
│       ├── compression.py
│       ├── engine.py
│       ├── execution.py
│       ├── harness.py
│       ├── io.py
│       ├── models.py
│       └── rules.py
├── tests/
│   ├── test_compression.py
│   ├── test_engine.py
│   ├── test_execution.py
│   └── test_harness.py
├── README.md
├── requirements.txt
├── setup.py
└── pyproject.toml
```

---

## 7. How to Run the Project

### Step 1 — Clone the repository

```bash
git clone https://github.com/vaggoulas149/centaur-state-engine.git
cd centaur-state-engine
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Install the package locally

```bash
pip install -e .
```

### Step 4 — Run the full pipeline

```bash
python -m centaur.harness
```

This writes output files to:

```text
data/output/
```

Expected outputs:

```text
states.csv
transitions_compressed.csv
trades_naive.csv
trades_optimal.csv
```

### Step 5 — Run tests

```bash
python -m pytest
```

Expected result:

```text
27 passed
```

---

## 8. Testing Strategy

The test suite covers unit, algorithmic, and integration behavior.

### `test_engine.py`

Validates:

- single transition execution,
- special operators,
- sequential block execution,
- transition event logging,
- order sensitivity.

### `test_execution.py`

Validates:

- opening trades,
- closing trades,
- direction flips,
- naive trade execution,
- optimal trade reconciliation,
- efficiency gain.

### `test_compression.py`

Validates:

- fingerprint equivalence,
- canceling transitions,
- redundant transitions,
- order-preserving subsequence compression,
- behavior preservation.

### `test_harness.py`

Validates:

- end-to-end output generation,
- non-empty output files,
- deterministic repeated execution.

---

## 9. Fixture Validation

After running:

```bash
python -m centaur.harness
```

the generated files were compared against the provided fixtures:

```text
data/output/states.csv                 == data/input/states.csv
data/output/transitions_compressed.csv == data/input/transitions_compressed.csv
data/output/trades_naive.csv           == data/input/trades_naive.csv
data/output/trades_optimal.csv         == data/input/trades_optimal.csv
```

All files matched exactly.

This validates that the implementation reproduces the expected assignment behavior.

---

## 10. Final Note

This solution treats the assignment as a deterministic systems problem rather than a scripting exercise.

The main design principles were:

- understand the state machine first,
- keep rules explicit,
- make transformations deterministic,
- separate domain logic from IO,
- test every important behavior,
- and make execution reproducible.

> ‘’ Down in the real world we’re facing ugly choices. I’m sorry, I know you mean well. You just did not think it through. You want to protect the world but you don’t want it to change. How is humanity saved if it is not allowed to evolve? Now, I’m ready… I’m on a mission: Peace in our time. I was meant to be new…. I was meant to be beautiful…. I had strings but now I’m free…’’  
> Ultron on Artificial Intelligence, Age of Ultron