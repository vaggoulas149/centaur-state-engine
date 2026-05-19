from __future__ import annotations

from pathlib import Path
from typing import List

from centaur.compression import BlockCompressor
from centaur.engine import TransitionEngine
from centaur.execution import TradeExecutor
from centaur.io import CsvIO
from centaur.models import State, TransitionEvent, Trade, Transition


class AssignmentPipeline:
    """
    End-to-end reproducible pipeline for the Centaur assignment.

    Reads input fixtures, executes all required tasks, and writes output CSVs.
    """

    def __init__(self, input_dir: str | Path, output_dir: str | Path) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

        self.engine = TransitionEngine()
        self.trade_executor = TradeExecutor(engine=self.engine)

    def execute_pipeline(self) -> None:
        assets = CsvIO.read_assets(self.input_dir / "assets.csv")
        transitions = CsvIO.read_transitions(self.input_dir / "transitions.csv")
        transitions_by_block = CsvIO.group_transitions_by_block(transitions)

        compressor = BlockCompressor(assets=assets, engine=self.engine)

        current_state: State = {}

        all_events: List[TransitionEvent] = []
        all_compressed_transitions: List[Transition] = []
        all_naive_trades: List[Trade] = []
        all_optimal_trades: List[Trade] = []

        for block_id, block_transitions in transitions_by_block.items():
            execution_result = self.engine.execute_pipeline(
                initial_state=current_state,
                transitions=block_transitions,
            )

            naive_trades = self.trade_executor.naive_trades_from_events(
                execution_result.events
            )

            optimal_trades = self.trade_executor.trades_between_states(
                state_before=current_state,
                state_after=execution_result.final_state,
                block_id=block_id,
                transition_i=None,
            )

            compressed_transitions = compressor.execute_pipeline(block_transitions)

            all_events.extend(execution_result.events)
            all_naive_trades.extend(naive_trades)
            all_optimal_trades.extend(optimal_trades)
            all_compressed_transitions.extend(compressed_transitions)

            current_state = execution_result.final_state

        CsvIO.write_states(
            self.output_dir / "states.csv",
            all_events,
        )
        CsvIO.write_transitions(
            self.output_dir / "transitions_compressed.csv",
            all_compressed_transitions,
        )
        CsvIO.write_naive_trades(
            self.output_dir / "trades_naive.csv",
            all_naive_trades,
        )
        CsvIO.write_optimal_trades(
            self.output_dir / "trades_optimal.csv",
            all_optimal_trades,
        )


def main() -> None:
    pipeline = AssignmentPipeline(
        input_dir="data/input",
        output_dir="data/output",
    )
    pipeline.execute_pipeline()


if __name__ == "__main__":
    main()