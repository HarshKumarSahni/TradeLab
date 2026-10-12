"""Unit tests for the event-driven backtesting simulator and state invariants."""

import pandas as pd
import pytest

from tradelab.backtesting.engine import BacktestConfig, BacktestEngine
from tradelab.models import OrderSide
from tradelab.strategies.base import Strategy
from tradelab.strategies.sma_crossover import SMACrossoverConfig, SMACrossoverStrategy


class MockSignalStrategy(Strategy):
    """Custom strategy returning a fixed list of signals for testing."""

    def __init__(self, signals: list[int]):
        self._signals = signals

    @property
    def name(self) -> str:
        return "Mock Signals"

    def generate_signals(self, candles: pd.DataFrame) -> pd.DataFrame:
        signals_series = pd.Series(self._signals, index=candles.index)
        return pd.DataFrame({"Signal": signals_series}, index=candles.index)


@pytest.fixture
def ten_bar_candles() -> pd.DataFrame:
    """Construct 10 daily candles with known Open/Close."""
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    opens = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0, 114.0, 116.0, 118.0]
    highs = [p + 2.0 for p in opens]
    lows = [p - 2.0 for p in opens]
    closes = [p + 1.0 for p in opens]
    volumes = [1000000] * 10

    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
        index=pd.DatetimeIndex(dates, name="Date"),
    )


def test_zero_lookahead_execution(ten_bar_candles: pd.DataFrame) -> None:
    """Verify signal at bar t fills at the Open of bar t+1, never on bar t."""
    # Signal BUY at bar 2 (index 2)
    signals = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
    strat = MockSignalStrategy(signals)
    cfg = BacktestConfig(initial_cash=10000.0, fee=0.0, slippage_bps=0.0)

    result = BacktestEngine.run(ten_bar_candles, strat, cfg)

    assert len(result.fills) == 1
    fill = result.fills[0]

    # Signal was on index 2 (2023-01-03) -> Fill must be on index 3 (2023-01-04)
    expected_fill_date = ten_bar_candles.index[3]
    assert fill.timestamp == expected_fill_date
    assert fill.side == OrderSide.BUY

    # Fill price must be Open of bar 3 (106.0)
    assert fill.fill_price == 106.0


def test_slippage_and_fees(ten_bar_candles: pd.DataFrame) -> None:
    """Verify execution prices include adverse slippage and fees are deducted."""
    # Signal BUY on bar 0, SELL on bar 2
    signals = [1, 0, -1, 0, 0, 0, 0, 0, 0, 0]
    strat = MockSignalStrategy(signals)
    # 10 bps slippage = 0.1%, fee = $10
    cfg = BacktestConfig(initial_cash=10000.0, fee=10.0, slippage_bps=10.0, allow_fractional=True)

    result = BacktestEngine.run(ten_bar_candles, strat, cfg)
    assert len(result.fills) == 2

    buy_fill = result.fills[0]
    # Bar 1 Open is 102.0. Slippage = 102.0 * 1.001 = 102.102
    assert buy_fill.timestamp == ten_bar_candles.index[1]
    assert round(buy_fill.fill_price, 3) == 102.102
    assert buy_fill.fee == 10.0

    sell_fill = result.fills[1]
    # Bar 3 Open is 106.0. Slippage = 106.0 * (1 - 0.001) = 105.894
    assert sell_fill.timestamp == ten_bar_candles.index[3]
    assert round(sell_fill.fill_price, 3) == 105.894
    assert sell_fill.fee == 10.0


def test_final_bar_pending_signal(ten_bar_candles: pd.DataFrame) -> None:
    """A signal on the final bar cannot be filled and must be marked pending."""
    # Signal BUY on the very last bar (index 9)
    signals = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    strat = MockSignalStrategy(signals)
    cfg = BacktestConfig()

    result = BacktestEngine.run(ten_bar_candles, strat, cfg)

    # Zero fills executed
    assert len(result.fills) == 0
    # Pending signal recorded
    assert result.pending_signal == OrderSide.BUY


def test_cash_and_equity_invariants(ten_bar_candles: pd.DataFrame) -> None:
    """Verify cash >= 0 and equity = cash + quantity * close on every bar."""
    signals = [1, 0, 0, -1, 0, 1, 0, -1, 0, 0]
    strat = MockSignalStrategy(signals)
    cfg = BacktestConfig(initial_cash=5000.0, fee=5.0, slippage_bps=5.0)

    result = BacktestEngine.run(ten_bar_candles, strat, cfg)
    curve = result.equity_curve

    for _idx, row in curve.iterrows():
        assert row["Cash"] >= 0.0
        assert row["Quantity"] >= 0.0
        expected_equity = row["Cash"] + (row["Quantity"] * row["Close"])
        assert abs(row["Equity"] - expected_equity) < 1e-4


def test_insufficient_cash_warning(ten_bar_candles: pd.DataFrame) -> None:
    """If initial cash is insufficient to buy 1 share, order is safely skipped with a warning."""
    signals = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    strat = MockSignalStrategy(signals)
    # $50 cash is less than share price ($102)
    cfg = BacktestConfig(initial_cash=50.0, fee=0.0)

    result = BacktestEngine.run(ten_bar_candles, strat, cfg)
    assert len(result.fills) == 0
    assert len(result.warnings) > 0
    assert "Insufficient cash" in result.warnings[0]


def test_deterministic_repeatability(ten_bar_candles: pd.DataFrame) -> None:
    """Identical inputs must produce identical results."""
    strat = SMACrossoverStrategy(SMACrossoverConfig(fast_window=2, slow_window=4))
    cfg = BacktestConfig(initial_cash=10000.0)

    res1 = BacktestEngine.run(ten_bar_candles, strat, cfg)
    res2 = BacktestEngine.run(ten_bar_candles, strat, cfg)

    assert res1.final_equity == res2.final_equity
    assert len(res1.fills) == len(res2.fills)
