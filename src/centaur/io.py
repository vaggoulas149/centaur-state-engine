from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Type

from centaur.models import (
    Direction,
    ExposureChange,
    PositionDirection,
    State,
    Trade,
    Transition,
    TransitionEvent,
    TransitionType,
)


class CsvIO:
    """CSV parser and writer for assignment input/output files."""

    @staticmethod
    def read_assets(path: str | Path) -> List[str]:
        """Read the fixed asset universe from assets.csv."""

        path = Path(path)
        with path.open("r", newline="") as file:
            reader = csv.DictReader(file)
            return [row["asset"].strip() for row in reader]

    @staticmethod
    def read_transitions(path: str | Path) -> List[Transition]:
        """Read transition rows and convert them into Transition objects."""

        path = Path(path)
        transitions: List[Transition] = []

        with path.open("r", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                transition_type = TransitionType(row["transition_type"].strip())

                transitions.append(
                    Transition(
                        block_id=int(row["block_id"]),
                        transition_i=int(row["transition_index"]),
                        transition_type=transition_type,
                        asset=CsvIO._clean_optional(row.get("asset")),
                        direction=CsvIO._parse_optional_enum(
                            row.get("direction"),
                            Direction,
                        ),
                        exposure_change=CsvIO._parse_optional_enum(
                            row.get("exposure_change"),
                            ExposureChange,
                        ),
                    )
                )

        return transitions

    @staticmethod
    def group_transitions_by_block(
        transitions: Iterable[Transition],
    ) -> Dict[int, List[Transition]]:
        """Group transitions by block_id and sort each block by transition index."""

        grouped: Dict[int, List[Transition]] = defaultdict(list)

        for transition in transitions:
            grouped[transition.block_id].append(transition)

        return {
            block_id: sorted(block_transitions, key=lambda transition: transition.transition_i)
            for block_id, block_transitions in sorted(grouped.items())
        }

    @staticmethod
    def parse_state(value: Optional[str]) -> State:
        """Parse serialized state format: 'BTC:Long;ETH:Short'."""

        if value is None:
            return {}

        value = value.strip()
        if value == "" or value.lower() == "nan":
            return {}

        state: State = {}

        for item in value.split(";"):
            asset, direction = item.split(":")
            state[asset.strip()] = PositionDirection(direction.strip())

        return state

    @staticmethod
    def serialize_state(state: State) -> str:
        """Serialize a State into the assignment CSV format."""

        if not state:
            return ""

        return ";".join(
            f"{asset}:{direction.value}"
            for asset, direction in sorted(state.items())
        )

    @staticmethod
    def write_states(path: str | Path, events: List[TransitionEvent]) -> None:
        """Write transition event state_before/state_after outputs."""

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["block_id", "transition_index", "state_before", "state_after"],
            )
            writer.writeheader()

            for event in events:
                writer.writerow(
                    {
                        "block_id": event.block_id,
                        "transition_index": event.transition_i,
                        "state_before": CsvIO.serialize_state(event.state_before),
                        "state_after": CsvIO.serialize_state(event.state_after),
                    }
                )

    @staticmethod
    def write_transitions(path: str | Path, transitions: List[Transition]) -> None:
        """Write compressed transition rows."""

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "block_id",
                    "transition_index",
                    "transition_type",
                    "asset",
                    "direction",
                    "exposure_change",
                ],
            )
            writer.writeheader()

            for transition in transitions:
                writer.writerow(
                    {
                        "block_id": transition.block_id,
                        "transition_index": transition.transition_i,
                        "transition_type": transition.transition_type.value,
                        "asset": transition.asset or "",
                        "direction": transition.direction.value if transition.direction else "",
                        "exposure_change": (
                            transition.exposure_change.value
                            if transition.exposure_change
                            else ""
                        ),
                    }
                )

    @staticmethod
    def write_naive_trades(path: str | Path, trades: List[Trade]) -> None:
        """Write trades emitted by transition-by-transition execution."""

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "block_id",
                    "transition_index_trigger",
                    "asset",
                    "action",
                    "direction",
                ],
            )
            writer.writeheader()

            for trade in trades:
                writer.writerow(
                    {
                        "block_id": trade.block_id,
                        "transition_index_trigger": trade.transition_i,
                        "asset": trade.asset,
                        "action": trade.action.value,
                        "direction": trade.direction.value,
                    }
                )

    @staticmethod
    def write_optimal_trades(path: str | Path, trades: List[Trade]) -> None:
        """Write minimum trades required to reconcile initial and final states."""

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["block_id", "asset", "action", "direction"],
            )
            writer.writeheader()

            for trade in trades:
                writer.writerow(
                    {
                        "block_id": trade.block_id,
                        "asset": trade.asset,
                        "action": trade.action.value,
                        "direction": trade.direction.value,
                    }
                )

    @staticmethod
    def _clean_optional(value: Optional[str]) -> Optional[str]:
        """Normalize empty CSV cells to None."""

        if value is None:
            return None

        value = value.strip()
        if value == "" or value.lower() == "nan":
            return None

        return value

    @staticmethod
    def _parse_optional_enum(value: Optional[str], enum_cls: Type):
        """Parse an optional enum value from a CSV cell."""

        cleaned = CsvIO._clean_optional(value)
        if cleaned is None:
            return None

        return enum_cls(cleaned)