from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional, Union

from centaur.engine import TransitionEngine
from centaur.models import State, Trade, TradeAction, Transition, TransitionEvent


class TradeExecutor:
    """Computes naive and optimal executable trades for transition blocks.

    The state transition engine determines semantic state evolution. The trade
    executor translates differences between states into executable operations.

    A change from Long to Short emits two trades:
    close Long, then open Short. A change from Long to Long emits no trade.
    """

    def __init__(self, engine: Optional[TransitionEngine] = None) -> None:
        """Initialize the executor with an optional transition engine."""

        self.engine = engine or TransitionEngine()

    def trades_between_states(
        self,
        state_before: State,
        state_after: State,
        block_id: int,
        transition_i: Optional[int],
    ) -> List[Trade]:
        """Return the trades required to reconcile two states.

        Args:
            state_before: State before execution.
            state_after: Target state after execution.
            block_id: Block identifier used for output traceability.
            transition_i: Transition index that triggered the trade. For
                optimal trades this is None because they reconcile the whole
                block rather than one transition.

        Returns:
            Minimal asset-specific open/close operations between the states.
        """

        trades: List[Trade] = []
        assets = sorted(set(state_before.keys()) | set(state_after.keys()))

        for asset in assets:
            before = state_before.get(asset)
            after = state_after.get(asset)

            if before == after:
                continue

            if before is not None:
                trades.append(
                    Trade(
                        block_id=block_id,
                        transition_i=transition_i,
                        asset=asset,
                        action=TradeAction.CLOSE,
                        direction=before,
                    )
                )

            if after is not None:
                trades.append(
                    Trade(
                        block_id=block_id,
                        transition_i=transition_i,
                        asset=asset,
                        action=TradeAction.OPEN,
                        direction=after,
                    )
                )

        return trades

    def naive_trades_from_events(
        self,
        events: List[TransitionEvent],
    ) -> List[Trade]:
        """Emit trades caused by each transition event in sequence."""

        trades: List[Trade] = []

        for event in events:
            trades.extend(
                self.trades_between_states(
                    state_before=event.state_before,
                    state_after=event.state_after,
                    block_id=event.block_id,
                    transition_i=event.transition_i,
                )
            )

        return trades

    def naive_trades(
        self,
        initial_state: State,
        transitions: List[Transition],
    ) -> List[Trade]:
        """Execute a block transition-by-transition and emit all intermediate trades."""

        execution_result = self.engine.apply_block(
            initial_state=initial_state,
            transitions=transitions,
        )
        return self.naive_trades_from_events(execution_result.events)

    def optimal_trades(
        self,
        initial_state: State,
        transitions: List[Transition],
    ) -> List[Trade]:
        """Emit the minimum trades needed to reach the block's final state.

        Users only care about ending in the correct final state, not about the
        intermediate states inside a block. Therefore the optimal execution
        reconciles the initial state directly to the final state.
        """

        execution_result = self.engine.apply_block(
            initial_state=initial_state,
            transitions=transitions,
        )

        return self.trades_between_states(
            state_before=deepcopy(initial_state),
            state_after=execution_result.final_state,
            block_id=execution_result.block_id,
            transition_i=None,
        )

    def efficiency_gain(
        self,
        naive_trades: List[Trade],
        optimal_trades: List[Trade],
    ) -> float:
        """Return percentage reduction from naive to optimal trade count."""

        if not naive_trades:
            return 0.0

        return 100.0 * (1.0 - (len(optimal_trades) / len(naive_trades)))

    def execute_pipeline(
        self,
        initial_state: State,
        transitions: List[Transition],
    ) -> Dict[str, Union[List[Trade], float]]:
        """Run the executor's main workflow for one transition block."""

        naive = self.naive_trades(initial_state, transitions)
        optimal = self.optimal_trades(initial_state, transitions)

        return {
            "naive_trades": naive,
            "optimal_trades": optimal,
            "efficiency_gain_pct": self.efficiency_gain(naive, optimal),
        }