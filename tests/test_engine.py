import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from centaur.engine import TransitionEngine
from centaur.models import (
    Direction,
    ExposureChange,
    PositionDirection,
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


def make_special(transition_type, i=1):
    return Transition(
        block_id=1,
        transition_i=i,
        transition_type=transition_type,
    )


def test_no_position_long_increase_opens_long():
    engine = TransitionEngine()

    event = engine.apply_transition(
        state={},
        transition=make_regular(
            "BTC",
            Direction.LONG,
            ExposureChange.INCREASE,
        ),
    )

    assert event.state_before == {}
    assert event.state_after == {"BTC": PositionDirection.LONG}


def test_long_decrease_some_remains_long():
    engine = TransitionEngine()

    event = engine.apply_transition(
        state={"BTC": PositionDirection.LONG},
        transition=make_regular(
            "BTC",
            Direction.LONG,
            ExposureChange.DECREASE_SOME,
        ),
    )

    assert event.state_after == {"BTC": PositionDirection.LONG}


def test_long_decrease_none_closes_position():
    engine = TransitionEngine()

    event = engine.apply_transition(
        state={"BTC": PositionDirection.LONG},
        transition=make_regular(
            "BTC",
            Direction.LONG,
            ExposureChange.DECREASE_NONE,
        ),
    )

    assert event.state_after == {}


def test_short_long_increase_flips_to_long():
    engine = TransitionEngine()

    event = engine.apply_transition(
        state={"AAPL": PositionDirection.SHORT},
        transition=make_regular(
            "AAPL",
            Direction.LONG,
            ExposureChange.INCREASE,
        ),
    )

    assert event.state_after == {"AAPL": PositionDirection.LONG}


def test_short_long_decrease_some_flips_to_long():
    engine = TransitionEngine()

    event = engine.apply_transition(
        state={"AAPL": PositionDirection.SHORT},
        transition=make_regular(
            "AAPL",
            Direction.LONG,
            ExposureChange.DECREASE_SOME,
        ),
    )

    assert event.state_after == {"AAPL": PositionDirection.LONG}


def test_close_all_removes_all_positions():
    engine = TransitionEngine()

    event = engine.apply_transition(
        state={
            "BTC": PositionDirection.LONG,
            "ETH": PositionDirection.SHORT,
        },
        transition=make_special(TransitionType.CLOSE_ALL),
    )

    assert event.state_after == {}


def test_close_longs_only_removes_longs():
    engine = TransitionEngine()

    event = engine.apply_transition(
        state={
            "BTC": PositionDirection.LONG,
            "ETH": PositionDirection.SHORT,
            "SOL": PositionDirection.LONG,
        },
        transition=make_special(TransitionType.CLOSE_LONGS),
    )

    assert event.state_after == {"ETH": PositionDirection.SHORT}


def test_flip_all_flips_open_positions_only():
    engine = TransitionEngine()

    event = engine.apply_transition(
        state={
            "BTC": PositionDirection.LONG,
            "ETH": PositionDirection.SHORT,
        },
        transition=make_special(TransitionType.FLIP_ALL),
    )

    assert event.state_after == {
        "BTC": PositionDirection.SHORT,
        "ETH": PositionDirection.LONG,
    }


def test_apply_block_is_sequential():
    engine = TransitionEngine()

    transitions = [
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=1),
        make_regular("ETH", Direction.SHORT, ExposureChange.INCREASE, i=2),
        make_special(TransitionType.CLOSE_LONGS, i=3),
    ]

    result = engine.apply_block(initial_state={}, transitions=transitions)

    assert result.final_state == {"ETH": PositionDirection.SHORT}
    assert len(result.events) == 3
    assert result.events[0].state_after == {"BTC": PositionDirection.LONG}
    assert result.events[1].state_after == {
        "BTC": PositionDirection.LONG,
        "ETH": PositionDirection.SHORT,
    }
    assert result.events[2].state_after == {"ETH": PositionDirection.SHORT}


def test_order_matters():
    engine = TransitionEngine()

    close_then_open = [
        make_special(TransitionType.CLOSE_ALL, i=1),
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=2),
    ]

    open_then_close = [
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=1),
        make_special(TransitionType.CLOSE_ALL, i=2),
    ]

    initial_state = {"BTC": PositionDirection.LONG}

    result_a = engine.apply_block(initial_state, close_then_open)
    result_b = engine.apply_block(initial_state, open_then_close)

    assert result_a.final_state == {"BTC": PositionDirection.LONG}
    assert result_b.final_state == {}