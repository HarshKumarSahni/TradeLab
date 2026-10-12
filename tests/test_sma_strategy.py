"""Unit tests for SMA crossover strategy and signal generation."""

import pandas as pd
import pytest

from tradelab.exceptions import StrategyError
from tradelab.strategies.base import SignalType
from tradelab.strategies.sma_crossover import SMACrossoverConfig, SMACrossoverStrategy


def test_sma_config_validation() -> None:
    """Verify parameters validation in SMACrossoverConfig."""
    cfg = SMACrossoverConfig(fast_window=5, slow_window=10)
    assert cfg.fast_window == 5
    assert cfg.slow_window == 10

    # Fast window < 2
    with pytest.raises(StrategyError):
        SMACrossoverConfig(fast_window=1, slow_window=10)

    # Fast window >= slow window
    with pytest.raises(StrategyError):
        SMACrossoverConfig(fast_window=10, slow_window=10)
    with pytest.raises(StrategyError):
        SMACrossoverConfig(fast_window=20, slow_window=10)


def test_sma_insufficient_bars() -> None:
    """Verify error when bars are fewer than slow_window + 2."""
    strategy = SMACrossoverStrategy(SMACrossoverConfig(fast_window=3, slow_window=6))
    dates = pd.date_range("2023-01-01", periods=5, freq="D")
    df = pd.DataFrame({"Close": [10, 11, 12, 13, 14]}, index=dates)

    with pytest.raises(StrategyError, match="Insufficient data"):
        strategy.generate_signals(df)


def test_sma_warmup_no_signals() -> None:
    """Verify that during indicator warmup (first slow_window bars), all signals are HOLD (0)."""
    fast = 3
    slow = 6
    strategy = SMACrossoverStrategy(SMACrossoverConfig(fast_window=fast, slow_window=slow))

    dates = pd.date_range("2023-01-01", periods=20, freq="D")
    # Monotonically increasing prices
    prices = [10.0 + i for i in range(20)]
    df = pd.DataFrame({"Close": prices}, index=dates)

    res = strategy.generate_signals(df)
    # Warmup period check (index 0 to slow-1)
    for i in range(slow):
        assert res["Signal"].iloc[i] == int(SignalType.HOLD)


def test_known_crossover_events() -> None:
    """Construct a known series that produces a clean bullish then bearish crossover."""
    fast = 2
    slow = 4
    strategy = SMACrossoverStrategy(SMACrossoverConfig(fast_window=fast, slow_window=slow))

    # Pattern: flat low, sharp jump, then sharp drop
    # Index 0..3: [10, 10, 10, 10] -> slow SMA = 10, fast SMA = 10
    # Index 4: 20 -> fast = (10+20)/2 = 15, slow = (10+10+10+20)/4 = 12.5 -> Crossover BUY!
    # Index 5: 20 -> fast = 20, slow = (10+10+20+20)/4 = 15 -> fast > slow (already above, HOLD)
    # Index 6: 5  -> fast = (20+5)/2 = 12.5, slow = (10+20+20+5)/4 = 13.75 -> Crossover SELL!
    prices = [10.0, 10.0, 10.0, 10.0, 20.0, 20.0, 5.0, 5.0]
    dates = pd.date_range("2023-01-01", periods=len(prices), freq="D")
    df = pd.DataFrame({"Close": prices}, index=dates)

    res = strategy.generate_signals(df)

    # Bar 4 must be BUY
    assert res["Signal"].iloc[4] == int(SignalType.BUY)
    # Bar 5 is already above (no new cross) -> HOLD
    assert res["Signal"].iloc[5] == int(SignalType.HOLD)
    # Bar 6 must be SELL
    assert res["Signal"].iloc[6] == int(SignalType.SELL)


def test_flat_prices_no_crossovers() -> None:
    """Constant flat prices should never trigger a crossover signal."""
    strategy = SMACrossoverStrategy(SMACrossoverConfig(fast_window=3, slow_window=5))
    dates = pd.date_range("2023-01-01", periods=15, freq="D")
    df = pd.DataFrame({"Close": [100.0] * 15}, index=dates)

    res = strategy.generate_signals(df)
    assert (res["Signal"] == 0).all()
