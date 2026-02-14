from tradeforge.strategies.fibsdontlie import Candle, FibsDontLie, FibsDontLieConfig
from tradeforge.strategies.base import StrategyContext


def seed_strategy() -> FibsDontLie:
    strat = FibsDontLie()
    strat.candles = [
        Candle(100, 101, 99, 100),
        Candle(100, 102, 99, 101),
        Candle(101, 103, 100, 102),
    ]
    return strat


def test_smart_flip_cancels_prior_setup():
    strat = seed_strategy()

    # Bullish break creates first pending setup
    strat.on_candle(Candle(102, 106, 103, 105))
    assert strat.active_setup is not None
    assert strat.active_setup.direction == "bullish"

    # Opposite break occurs before entry -> setup flips to bearish
    strat.on_candle(Candle(94, 105, 93, 96))
    assert strat.position is None
    assert strat.active_setup is not None
    assert strat.active_setup.direction == "bearish"


def test_partial_tp_reduces_size_and_locks_realized_pnl():
    cfg = FibsDontLieConfig(tp_rr=3.0, partial_tp_rr=1.0, partial_close_fraction=0.5)
    strat = FibsDontLie(cfg)
    strat.active_setup = strat._build_setup("bullish", impulse_high=110, impulse_low=100)

    # Entry candle (touches zone and bullish close)
    strat.on_candle(Candle(104.0, 105.0, 102.0, 104.5))
    assert strat.position is not None

    # Hit partial TP and BE threshold but not full TP
    strat.on_candle(Candle(104.0, 109.0, 105.0, 108.0))
    assert strat.position is not None
    assert strat.position.partial_taken is True
    assert strat.position.remaining_volume == 0.5
    assert strat.position.realized_pnl == 2.25


def test_breakeven_sl_modification_happens_at_threshold():
    cfg = FibsDontLieConfig(tp_rr=3.0, breakeven_after_rr=1.0, breakeven_offset=0.25)
    strat = FibsDontLie(cfg)
    strat.active_setup = strat._build_setup("bullish", impulse_high=110, impulse_low=100)

    strat.on_candle(Candle(104.0, 105.0, 102.0, 104.5))
    assert strat.position is not None
    entry = strat.position.entry_price

    strat.on_candle(Candle(104.0, 109.0, 105.0, 108.0))
    assert strat.position is not None
    assert strat.position.breakeven_moved is True
    assert strat.position.stop_loss == entry + 0.25


def test_spread_filter_blocks_entry():
    cfg = FibsDontLieConfig(spread_limit=0.2)
    strat = FibsDontLie(cfg)
    strat.active_setup = strat._build_setup("bullish", impulse_high=110, impulse_low=100)

    strat.on_candle(Candle(104.0, 105.0, 102.0, 104.0), ctx=StrategyContext(spread=0.5))
    assert strat.position is None


def test_deterministic_run_repeatability():
    cfg = FibsDontLieConfig(tp_rr=2.5, partial_tp_rr=0.8)
    candles = [
        Candle(102, 106, 101, 105),
        Candle(105, 105, 98, 100),
        Candle(100, 103, 97, 102),
        Candle(102, 108, 101, 107),
        Candle(107, 109, 103, 104),
    ]

    def run_once():
        strat = seed_strategy()
        strat.config = cfg
        for c in candles:
            strat.on_candle(c, StrategyContext(spread=0.1))
        setup = strat.active_setup.direction if strat.active_setup else None
        if strat.position:
            pos = (
                strat.position.direction,
                strat.position.entry_price,
                strat.position.stop_loss,
                strat.position.take_profit,
                strat.position.remaining_volume,
                strat.position.realized_pnl,
                strat.position.partial_taken,
                strat.position.breakeven_moved,
            )
        else:
            pos = None
        return (setup, pos)

    assert run_once() == run_once()
