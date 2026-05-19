import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from centaur.execution import TradeExecutor
from centaur.models import (
    Direction,
    ExposureChange,
    PositionDirection,
    TradeAction,
    Transition,
    TransitionType,
)


def make_regular(asset, direction, exposure_change, i=1):
    return Transition(
        block_id=1,
        transition_i=i,
        transition_type=TransitionType.REGULAR,
        asset=asset,
        direction=direction,
        exposure_change=exposure_change,
    )


def test_open_position_creates_open_trade():
    executor = TradeExecutor()

    trades = executor.trades_between_states(
        state_before={},
        state_after={"BTC": PositionDirection.LONG},
        block_id=1,
        transition_i=1,
    )

    assert len(trades) == 1
    assert trades[0].asset == "BTC"
    assert trades[0].action == TradeAction.OPEN
    assert trades[0].direction == PositionDirection.LONG


def test_close_position_creates_close_trade():
    executor = TradeExecutor()

    trades = executor.trades_between_states(
        state_before={"BTC": PositionDirection.LONG},
        state_after={},
        block_id=1,
        transition_i=1,
    )

    assert len(trades) == 1
    assert trades[0].asset == "BTC"
    assert trades[0].action == TradeAction.CLOSE
    assert trades[0].direction == PositionDirection.LONG


def test_flip_position_creates_close_then_open():
    executor = TradeExecutor()

    trades = executor.trades_between_states(
        state_before={"BTC": PositionDirection.LONG},
        state_after={"BTC": PositionDirection.SHORT},
        block_id=1,
        transition_i=1,
    )

    assert len(trades) == 2
    assert trades[0].action == TradeAction.CLOSE
    assert trades[0].direction == PositionDirection.LONG
    assert trades[1].action == TradeAction.OPEN
    assert trades[1].direction == PositionDirection.SHORT


def test_unchanged_position_creates_no_trade():
    executor = TradeExecutor()

    trades = executor.trades_between_states(
        state_before={"BTC": PositionDirection.LONG},
        state_after={"BTC": PositionDirection.LONG},
        block_id=1,
        transition_i=1,
    )

    assert trades == []


def test_naive_trades_count_intermediate_changes():
    executor = TradeExecutor()

    transitions = [
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=1),
        make_regular("BTC", Direction.LONG, ExposureChange.DECREASE_NONE, i=2),
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=3),
    ]

    trades = executor.naive_trades(initial_state={}, transitions=transitions)

    assert len(trades) == 3
    assert [trade.action for trade in trades] == [
        TradeAction.OPEN,
        TradeAction.CLOSE,
        TradeAction.OPEN,
    ]


def test_optimal_trades_only_reconcile_initial_to_final_state():
    executor = TradeExecutor()

    transitions = [
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=1),
        make_regular("BTC", Direction.LONG, ExposureChange.DECREASE_NONE, i=2),
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=3),
    ]

    trades = executor.optimal_trades(initial_state={}, transitions=transitions)

    assert len(trades) == 1
    assert trades[0].action == TradeAction.OPEN
    assert trades[0].direction == PositionDirection.LONG


def test_efficiency_gain():
    executor = TradeExecutor()

    naive = [
        make_dummy_trade(TradeAction.OPEN),
        make_dummy_trade(TradeAction.CLOSE),
        make_dummy_trade(TradeAction.OPEN),
    ]
    optimal = [make_dummy_trade(TradeAction.OPEN)]

    assert executor.efficiency_gain(naive, optimal) == 66.66666666666667


def make_dummy_trade(action):
    from centaur.models import Trade

    return Trade(
        block_id=1,
        transition_i=1,
        asset="BTC",
        action=action,
        direction=PositionDirection.LONG,
    )