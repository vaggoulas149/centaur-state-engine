from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class Direction(str, Enum):
    """Direction extracted from a transition."""

    LONG = "Long"
    SHORT = "Short"
    UNCLEAR = "Unclear"


class PositionDirection(str, Enum):
    """Concrete direction of an open position in the portfolio state."""

    LONG = "Long"
    SHORT = "Short"


class ExposureChange(str, Enum):
    """How a transition changes exposure for an asset."""

    INCREASE = "Increase"
    DECREASE_NONE = "Decrease / None"
    DECREASE_SOME = "Decrease / Some"
    NO_CHANGE = "No Change"


class TransitionType(str, Enum):
    """Supported transition categories, including portfolio-wide operators."""

    REGULAR = "Regular"
    CLOSE_ALL = "Close All"
    CLOSE_LONGS = "Close Longs"
    CLOSE_SHORTS = "Close Shorts"
    FLIP_ALL = "Flip All"
    FLIP_LONGS = "Flip Longs"
    FLIP_SHORTS = "Flip Shorts"


class TradeAction(str, Enum):
    """Executable trade action."""

    OPEN = "Open"
    CLOSE = "Close"


State = Dict[str, PositionDirection]
"""Portfolio state represented as asset -> open position direction.

Assets absent from the dictionary are interpreted as No Position.
"""


@dataclass(frozen=True)
class Position:
    """Single open position in an asset."""

    asset: str
    direction: PositionDirection


@dataclass(frozen=True)
class Transition:
    """Structured transition extracted from a content block.

    Regular transitions are asset-specific and carry asset, direction and
    exposure_change. Special operators are portfolio-wide and do not require
    asset-specific fields.
    """

    block_id: int
    transition_i: int
    transition_type: TransitionType
    asset: Optional[str] = None
    direction: Optional[Direction] = None
    exposure_change: Optional[ExposureChange] = None

    @property
    def is_regular(self) -> bool:
        """Return True when this is an asset-specific transition."""

        return self.transition_type == TransitionType.REGULAR

    @property
    def is_special_operator(self) -> bool:
        """Return True when this transition affects multiple positions."""

        return not self.is_regular


@dataclass(frozen=True)
class TransitionEvent:
    """Audit log entry for a single transition application."""

    block_id: int
    transition_i: int
    state_before: State
    transition: Transition
    state_after: State


@dataclass(frozen=True)
class Trade:
    """Executable asset-specific trade emitted by the execution layer."""

    block_id: int
    transition_i: Optional[int]
    asset: str
    action: TradeAction
    direction: PositionDirection


@dataclass(frozen=True)
class BlockExecutionResult:
    """Result of applying an ordered transition block to an initial state."""

    block_id: int
    initial_state: State
    final_state: State
    events: List[TransitionEvent]
    trades: List[Trade]


@dataclass(frozen=True)
class PipelineResult:
    """Aggregated outputs produced by the end-to-end assignment pipeline."""

    events: List[TransitionEvent]
    compressed_transitions: List[Transition]
    naive_trades: List[Trade]
    optimal_trades: List[Trade]