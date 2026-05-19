from __future__ import annotations

from copy import deepcopy
from typing import Optional

from centaur.models import (
    Direction,
    ExposureChange,
    PositionDirection,
    State,
    Transition,
    TransitionType,
)


class TransitionRules:
    """Deterministic implementation of Centaur's state transition semantics.

    The rules convert a state plus one transition into a new state.

    State representation:
    - asset present in dict  -> open Long/Short position
    - asset absent from dict -> No Position
    """

    @staticmethod
    def apply(state: State, transition: Transition) -> State:
        """Apply either a regular transition or a special portfolio operator."""

        if transition.is_regular:
            return TransitionRules._apply_regular_transition(state, transition)

        return TransitionRules._apply_special_operator(state, transition.transition_type)

    @staticmethod
    def _apply_regular_transition(state: State, transition: Transition) -> State:
        """Apply an asset-specific transition to one asset."""

        if transition.asset is None:
            raise ValueError("Regular transition requires asset.")
        if transition.direction is None:
            raise ValueError("Regular transition requires direction.")
        if transition.exposure_change is None:
            raise ValueError("Regular transition requires exposure_change.")

        new_state = deepcopy(state)
        current_direction = new_state.get(transition.asset)

        next_direction = TransitionRules._next_position_direction(
            current_direction=current_direction,
            transition_direction=transition.direction,
            exposure_change=transition.exposure_change,
        )

        if next_direction is None:
            new_state.pop(transition.asset, None)
        else:
            new_state[transition.asset] = next_direction

        return new_state

    @staticmethod
    def _next_position_direction(
        current_direction: Optional[PositionDirection],
        transition_direction: Direction,
        exposure_change: ExposureChange,
    ) -> Optional[PositionDirection]:
        """Compute the next local state for one asset.

        Returns:
            PositionDirection.LONG/SHORT when a position remains open.
            None when the asset has No Position after the transition.
        """

        if transition_direction == Direction.UNCLEAR:
            return TransitionRules._apply_unclear_direction(
                current_direction=current_direction,
                exposure_change=exposure_change,
            )

        target_direction = TransitionRules._to_position_direction(transition_direction)

        if exposure_change == ExposureChange.INCREASE:
            return target_direction

        if exposure_change == ExposureChange.DECREASE_NONE:
            return None

        if exposure_change == ExposureChange.DECREASE_SOME:
            return target_direction

        if exposure_change == ExposureChange.NO_CHANGE:
            return target_direction

        raise ValueError(f"Unsupported exposure change: {exposure_change}")

    @staticmethod
    def _apply_unclear_direction(
        current_direction: Optional[PositionDirection],
        exposure_change: ExposureChange,
    ) -> Optional[PositionDirection]:
        """Apply a transition whose direction is unclear.

        An unclear transition cannot create a new directional position from
        No Position. If a position already exists, non-closing unclear
        transitions preserve the current direction; Decrease / None closes it.
        """

        if current_direction is None:
            return None

        if exposure_change == ExposureChange.DECREASE_NONE:
            return None

        if exposure_change in {
            ExposureChange.INCREASE,
            ExposureChange.DECREASE_SOME,
            ExposureChange.NO_CHANGE,
        }:
            return current_direction

        raise ValueError(f"Unsupported exposure change: {exposure_change}")

    @staticmethod
    def _apply_special_operator(
        state: State,
        transition_type: TransitionType,
    ) -> State:
        """Apply a portfolio-wide special operator."""

        new_state = deepcopy(state)

        if transition_type == TransitionType.CLOSE_ALL:
            return {}

        if transition_type == TransitionType.CLOSE_LONGS:
            return {
                asset: direction
                for asset, direction in new_state.items()
                if direction != PositionDirection.LONG
            }

        if transition_type == TransitionType.CLOSE_SHORTS:
            return {
                asset: direction
                for asset, direction in new_state.items()
                if direction != PositionDirection.SHORT
            }

        if transition_type == TransitionType.FLIP_ALL:
            return {
                asset: TransitionRules._flip_direction(direction)
                for asset, direction in new_state.items()
            }

        if transition_type == TransitionType.FLIP_LONGS:
            return {
                asset: (
                    PositionDirection.SHORT
                    if direction == PositionDirection.LONG
                    else direction
                )
                for asset, direction in new_state.items()
            }

        if transition_type == TransitionType.FLIP_SHORTS:
            return {
                asset: (
                    PositionDirection.LONG
                    if direction == PositionDirection.SHORT
                    else direction
                )
                for asset, direction in new_state.items()
            }

        raise ValueError(f"Unsupported transition type: {transition_type}")

    @staticmethod
    def _flip_direction(direction: PositionDirection) -> PositionDirection:
        """Flip Long to Short and Short to Long."""

        if direction == PositionDirection.LONG:
            return PositionDirection.SHORT
        if direction == PositionDirection.SHORT:
            return PositionDirection.LONG

        raise ValueError(f"Unsupported position direction: {direction}")

    @staticmethod
    def _to_position_direction(direction: Direction) -> PositionDirection:
        """Convert extracted transition direction to concrete position direction."""

        if direction == Direction.LONG:
            return PositionDirection.LONG
        if direction == Direction.SHORT:
            return PositionDirection.SHORT

        raise ValueError(f"Cannot convert {direction} to PositionDirection")