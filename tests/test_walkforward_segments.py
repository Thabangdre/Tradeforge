from backtest.walkforward import WalkForwardSegment, WalkForwardSpec, make_segments


def test_make_segments_expected_ranges_and_stop_boundary() -> None:
    spec = WalkForwardSpec(train_bars=30, test_bars=10, step_bars=10)

    segments = make_segments(n_bars=100, spec=spec)

    assert segments == [
        WalkForwardSegment(0, 0, 30, 30, 40),
        WalkForwardSegment(1, 10, 40, 40, 50),
        WalkForwardSegment(2, 20, 50, 50, 60),
        WalkForwardSegment(3, 30, 60, 60, 70),
        WalkForwardSegment(4, 40, 70, 70, 80),
        WalkForwardSegment(5, 50, 80, 80, 90),
        WalkForwardSegment(6, 60, 90, 90, 100),
    ]
    assert segments[-1].test_end == 100
