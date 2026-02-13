from dataclasses import dataclass

from tradeforge.market import ReplayController, SimulationClock, TickFeed


@dataclass(frozen=True)
class Tick:
    timestamp_ms: int
    price: float


def build_ticks() -> list[Tick]:
    return [
        Tick(timestamp_ms=1_000, price=100.0),
        Tick(timestamp_ms=1_500, price=101.0),
        Tick(timestamp_ms=2_000, price=102.0),
        Tick(timestamp_ms=3_000, price=103.0),
    ]


def test_step_tick_advances_exactly_one_tick() -> None:
    replay = ReplayController(TickFeed(build_ticks()), SimulationClock())

    first = replay.step_tick()
    assert first is not None
    assert first.timestamp_ms == 1_000
    assert replay.clock.now_ms == 1_000
    assert replay.next_index == 1

    second = replay.step_tick()
    assert second is not None
    assert second.timestamp_ms == 1_500
    assert replay.clock.now_ms == 1_500
    assert replay.next_index == 2


def test_jump_to_timestamp_lands_on_first_tick_at_or_after_target() -> None:
    replay = ReplayController(TickFeed(build_ticks()), SimulationClock())

    jumped = replay.jump_to_timestamp(1_700)
    assert jumped is not None
    assert jumped.timestamp_ms == 2_000
    assert replay.clock.now_ms == 2_000
    assert replay.next_index == 2


def test_replay_sequence_identical_across_runs() -> None:
    feed = TickFeed(build_ticks())

    run1 = ReplayController(feed, SimulationClock())
    run2 = ReplayController(feed, SimulationClock())

    out1 = []
    out2 = []

    while (tick := run1.step_tick()) is not None:
        out1.append((tick.timestamp_ms, tick.price, run1.clock.now_ms))

    while (tick := run2.step_tick()) is not None:
        out2.append((tick.timestamp_ms, tick.price, run2.clock.now_ms))

    assert out1 == out2
