from dataclasses import dataclass

from market.clock import SimulationClock
from market.feed import TickFeed
from market.replay import ReplayController


@dataclass(frozen=True)
class Tick:
    timestamp_ms: int
    price: float


def _build_controller() -> ReplayController[Tick]:
    ticks = [
        Tick(timestamp_ms=1000, price=10.0),
        Tick(timestamp_ms=1100, price=10.2),
        Tick(timestamp_ms=1300, price=10.1),
        Tick(timestamp_ms=1600, price=10.4),
    ]
    return ReplayController(feed=TickFeed(ticks=ticks), clock=SimulationClock())


def test_step_tick_advances_exactly_one_tick() -> None:
    replay = _build_controller()

    first = replay.step_tick()
    assert first is not None
    assert first.timestamp_ms == 1000
    assert replay.feed.index == 1
    assert replay.clock.current_timestamp_ms == 1000

    second = replay.step_tick()
    assert second is not None
    assert second.timestamp_ms == 1100
    assert replay.feed.index == 2
    assert replay.clock.current_timestamp_ms == 1100


def test_jump_lands_on_first_tick_greater_or_equal_timestamp() -> None:
    replay = _build_controller()

    tick = replay.jump_to_timestamp(1150)
    assert tick is not None
    assert tick.timestamp_ms == 1300
    assert replay.feed.index == 2
    assert replay.clock.current_timestamp_ms == 1300


def test_replay_sequence_identical_across_runs() -> None:
    run_one = _build_controller().play()
    run_two = _build_controller().play()

    seq_one = [tick.timestamp_ms for tick in run_one]
    seq_two = [tick.timestamp_ms for tick in run_two]

    assert seq_one == [1000, 1100, 1300, 1600]
    assert seq_one == seq_two
