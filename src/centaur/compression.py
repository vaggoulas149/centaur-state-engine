from __future__ import annotations

from itertools import combinations
from typing import Iterable, List, Optional, Tuple

from centaur.engine import TransitionEngine
from centaur.models import PositionDirection, State, Transition


Fingerprint = Tuple[Tuple[str, Tuple[Optional[str], Optional[str], Optional[str]]], ...]
"""Canonical behavioral signature of a block.

For each asset, the fingerprint records the final direction reached when the
asset starts from each of the three possible local states:
No Position, Long, Short.
"""


class BlockCompressor:
    """Finds the shortest behavior-preserving subsequence of a transition block.

    A block is treated as a deterministic transformation over the finite
    portfolio state space. Instead of comparing outputs for one concrete
    starting state, compression compares behavioral fingerprints. This ensures
    that the compressed block is equivalent to the original block for all
    possible starting states, while preserving the original transition order.
    """

    def __init__(
        self,
        assets: Iterable[str],
        engine: Optional[TransitionEngine] = None,
    ) -> None:
        """Initialize the compressor.

        Args:
            assets: Fixed asset universe for the assignment.
            engine: Optional transition engine dependency, mainly useful for
                testing or dependency injection.
        """

        self.assets = sorted(assets)
        self.engine = engine or TransitionEngine()

    def fingerprint(self, transitions: List[Transition]) -> Fingerprint:
        """Compute the behavioral fingerprint of a transition block.

        The fingerprint captures, for every asset, how the block maps each
        possible starting local state to a final local state. This is compact
        because each asset has only three possible states: No Position, Long,
        and Short.

        Args:
            transitions: Ordered transition block.

        Returns:
            Canonical tuple representation of the block behavior.
        """

        per_asset_results = []

        for asset in self.assets:
            outcomes = []

            for initial_direction in [
                None,
                PositionDirection.LONG,
                PositionDirection.SHORT,
            ]:
                initial_state: State = {}
                if initial_direction is not None:
                    initial_state[asset] = initial_direction

                if transitions:
                    result = self.engine.apply_block(initial_state, transitions)
                    final_direction = result.final_state.get(asset)
                else:
                    final_direction = initial_direction

                outcomes.append(
                    final_direction.value if final_direction is not None else None
                )

            per_asset_results.append((asset, tuple(outcomes)))

        return tuple(per_asset_results)

    def equivalent(
        self,
        left: List[Transition],
        right: List[Transition],
    ) -> bool:
        """Return whether two blocks have identical behavior for all states."""

        return self.fingerprint(left) == self.fingerprint(right)

    def compress(self, transitions: List[Transition]) -> List[Transition]:
        """Return the shortest order-preserving behavior-equivalent subsequence.

        The search enumerates candidate subsequences from shortest to longest.
        The first candidate whose fingerprint matches the original block is
        therefore guaranteed to be minimum-length. The order of transitions is
        always preserved because candidates are built from index combinations.

        Args:
            transitions: Original ordered transition block.

        Returns:
            Shortest behavior-preserving subsequence.

        Raises:
            RuntimeError: If no subsequence is found. This should be impossible
                because the original block itself is always a valid candidate.
        """

        target_fingerprint = self.fingerprint(transitions)

        for length in range(0, len(transitions) + 1):
            for indices in combinations(range(len(transitions)), length):
                candidate = [transitions[i] for i in indices]

                if self.fingerprint(candidate) == target_fingerprint:
                    return candidate

        raise RuntimeError("No behavior-preserving subsequence found.")

    def execute_pipeline(self, transitions: List[Transition]) -> List[Transition]:
        """Run the compressor's main workflow."""

        return self.compress(transitions)