from __future__ import annotations

from copy import deepcopy
from typing import List

from centaur.models import BlockExecutionResult, State, Transition, TransitionEvent
from centaur.rules import TransitionRules


class TransitionEngine:
    """Executes deterministic state transitions.

    The engine is responsible for Task 1 of the assignment:
    applying individual transitions and ordered transition blocks while
    emitting a complete event log. It deliberately delegates the rule semantics
    to TransitionRules, keeping orchestration separate from transition logic.
    """

    def apply_transition(
        self,
        state: State,
        transition: Transition,
    ) -> TransitionEvent:
        """Apply one transition and return a logged transition event.

        Args:
            state: Portfolio state before the transition.
            transition: Transition to apply.

        Returns:
            TransitionEvent containing state_before, transition and state_after.
            The event is emitted even when the transition does not change state.
        """

        state_before = deepcopy(state)
        state_after = TransitionRules.apply(state_before, transition)

        return TransitionEvent(
            block_id=transition.block_id,
            transition_i=transition.transition_i,
            state_before=state_before,
            transition=transition,
            state_after=state_after,
        )

    def apply_block(
        self,
        initial_state: State,
        transitions: List[Transition],
    ) -> BlockExecutionResult:
        """Apply an ordered transition block sequentially.

        Each transition operates on the state produced by the previous
        transition. This is why transition order matters: the block represents
        function composition, not a commutative set of operations.

        Args:
            initial_state: State before the block starts.
            transitions: Ordered transitions belonging to one block.

        Returns:
            BlockExecutionResult containing the initial state, final state and
            transition event log.

        Raises:
            ValueError: If the block is empty or contains mixed block IDs.
        """

        if not transitions:
            raise ValueError("Cannot apply empty block.")

        block_id = transitions[0].block_id
        current_state = deepcopy(initial_state)
        events: List[TransitionEvent] = []

        for transition in transitions:
            if transition.block_id != block_id:
                raise ValueError("All transitions in a block must have the same block_id.")

            event = self.apply_transition(current_state, transition)
            events.append(event)
            current_state = event.state_after

        return BlockExecutionResult(
            block_id=block_id,
            initial_state=deepcopy(initial_state),
            final_state=current_state,
            events=events,
            trades=[],
        )

    def execute_pipeline(
        self,
        initial_state: State,
        transitions: List[Transition],
    ) -> BlockExecutionResult:
        """Run the engine's main workflow for one transition block."""

        return self.apply_block(initial_state, transitions)