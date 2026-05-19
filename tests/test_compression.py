import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from centaur.compression import BlockCompressor
from centaur.models import (
    Direction,
    ExposureChange,
    Transition,
    TransitionType,
)


ASSETS = ["BTC", "ETH", "SOL"]


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


def test_equivalent_blocks_have_same_fingerprint():
    compressor = BlockCompressor(assets=ASSETS)

    original = [
        make_special(TransitionType.FLIP_ALL, i=1),
        make_special(TransitionType.FLIP_ALL, i=2),
    ]

    compressed = []

    assert compressor.equivalent(original, compressed)


def test_flip_all_twice_compresses_to_empty_block():
    compressor = BlockCompressor(assets=ASSETS)

    transitions = [
        make_special(TransitionType.FLIP_ALL, i=1),
        make_special(TransitionType.FLIP_ALL, i=2),
    ]

    compressed = compressor.compress(transitions)

    assert compressed == []


def test_repeated_open_compresses_to_one_transition():
    compressor = BlockCompressor(assets=ASSETS)

    transitions = [
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=1),
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=2),
    ]

    compressed = compressor.compress(transitions)

    assert len(compressed) == 1
    assert compressed[0].transition_i in {1, 2}
    assert compressor.equivalent(transitions, compressed)


def test_no_change_regular_transition_compresses_to_empty_block():
    compressor = BlockCompressor(assets=ASSETS)

    transitions = [
        make_regular("SOL", Direction.UNCLEAR, ExposureChange.NO_CHANGE, i=1),
    ]

    compressed = compressor.compress(transitions)

    assert compressed == []

def test_blocks_with_different_global_effects_are_not_equivalent():
    compressor = BlockCompressor(assets=ASSETS)

    left = [
        make_special(TransitionType.CLOSE_ALL, i=1),
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=2),
    ]

    right = [
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=2),
    ]

    assert not compressor.equivalent(left, right)


def test_compression_preserves_behavior_for_all_states():
    compressor = BlockCompressor(assets=ASSETS)

    transitions = [
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=1),
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=2),
        make_special(TransitionType.FLIP_ALL, i=3),
        make_special(TransitionType.FLIP_ALL, i=4),
    ]

    compressed = compressor.compress(transitions)

    assert compressor.equivalent(transitions, compressed)
    assert len(compressed) < len(transitions)


def test_order_preserving_subsequence_is_returned():
    compressor = BlockCompressor(assets=ASSETS)

    transitions = [
        make_regular("BTC", Direction.LONG, ExposureChange.INCREASE, i=1),
        make_regular("ETH", Direction.SHORT, ExposureChange.INCREASE, i=2),
        make_special(TransitionType.CLOSE_LONGS, i=3),
    ]

    compressed = compressor.compress(transitions)
    compressed_indices = [transition.transition_i for transition in compressed]

    assert compressed_indices == sorted(compressed_indices)
    assert compressor.equivalent(transitions, compressed)