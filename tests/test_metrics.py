"""Unit tests for performance metrics, risk ratios, and benchmarks."""

import pandas as pd
import pytest

from tradelab.backtesting.benchmark import calculate_buy_and_hold_benchmark
from tradelab.backtesting.engine import BacktestConfig, BacktestEngine
from tradelab.backtesting.metrics import calculate_metrics
from tradelab.services.backtest_service import BacktestService
from tradelab.strategies.base import Strategy


class MockTradeStrategy(Strategy):
    """Produces specific BUY and SELL triggers."""

    def __init__(self, signals: list[int]):
        self._signals = signals

    @property
    def name(self) -> str:
        return "Mock Signals"

    def generate_signals(self, candles: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {"Signal": pd.Series(self._signals, index=candles.index)}, index=candles.index
        )


@pytest.fixture
def candle_dataset() -> pd.DataFrame:
    """10-day dataset for metrics testing."""
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    opens = [100.0, 110.0, 120.0, 90.0, 80.0, 85.0, 115.0, 105.0, 100.0, 95.0]
    highs = [p + 5.0 for p in opens]
    lows = [p - 5.0 for p in opens]
    closes = opens  # simplified
    volumes = [500000] * 10

    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
        index=pd.DatetimeIndex(dates, name="Date"),
    )


def test_zero_trades_metrics(candle_dataset: pd.DataFrame) -> None:
    """When zero trades occur, win rate and trade P&L must be None, not 0%."""
    signals = [0] * 10
    strat = MockTradeStrategy(signals)
    cfg = BacktestConfig(initial_cash=10000.0)

    res = BacktestEngine.run(candle_dataset, strat, cfg)
    bench = calculate_buy_and_hold_benchmark(candle_dataset, cfg)
    metrics = calculate_metrics(res, bench)

    assert metrics.total_trades == 0
    assert metrics.win_rate is None
    assert metrics.avg_trade_pnl is None
    assert metrics.total_return == 0.0
    assert metrics.max_drawdown == 0.0
    assert metrics.sharpe_ratio is None  # Flat equity curve -> zero volatility


def test_round_trip_win_rate_and_pnl(candle_dataset: pd.DataFrame) -> None:
    """Verify closed round trip pairing, win rate, and net P&L with fees."""
    # Bar 0: BUY signal -> fills Bar 1 Open ($110)
    # Bar 2: SELL signal -> fills Bar 3 Open ($90) -> Loss!
    # Bar 4: BUY signal -> fills Bar 5 Open ($85)
    # Bar 6: SELL signal -> fills Bar 7 Open ($105) -> Win!
    signals = [1, 0, -1, 0, 1, 0, -1, 0, 0, 0]
    strat = MockTradeStrategy(signals)
    cfg = BacktestConfig(initial_cash=10000.0, fee=5.0, slippage_bps=0.0)

    res = BacktestEngine.run(candle_dataset, strat, cfg)
    bench = calculate_buy_and_hold_benchmark(candle_dataset, cfg)
    metrics = calculate_metrics(res, bench)

    assert metrics.total_trades == 2
    assert metrics.winning_trades == 1
    assert metrics.losing_trades == 1
    assert metrics.win_rate == 0.5
    assert metrics.total_fees == 20.0  # 4 fills * $5 fee
    assert len(metrics.closed_trades) == 2

    trade1 = metrics.closed_trades[0]
    assert trade1.is_win is False
    assert trade1.entry_price == 110.0
    assert trade1.exit_price == 90.0

    trade2 = metrics.closed_trades[1]
    assert trade2.is_win is True
    assert trade2.entry_price == 85.0
    assert trade2.exit_price == 105.0


def test_max_drawdown_calculation(candle_dataset: pd.DataFrame) -> None:
    """Verify max drawdown tracks the minimum drawdown from running peak."""
    # Buy on bar 0 (fills at 110 on bar 1), hold through crash at bar 4 ($80)
    signals = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    strat = MockTradeStrategy(signals)
    cfg = BacktestConfig(initial_cash=10000.0, slippage_bps=0.0)

    res = BacktestEngine.run(candle_dataset, strat, cfg)
    bench = calculate_buy_and_hold_benchmark(candle_dataset, cfg)
    metrics = calculate_metrics(res, bench)

    # Peak equity is at bar 2 (price 120), trough is at bar 4 (price 80)
    # (80 - 120) / 120 = -33.33% drop on position
    assert metrics.max_drawdown < -0.30


def test_backtest_service_run_workflow(candle_dataset: pd.DataFrame) -> None:
    """Verify BacktestService integrates all components cleanly."""
    from tradelab.strategies.sma_crossover import SMACrossoverConfig, SMACrossoverStrategy

    service = BacktestService()
    strat = SMACrossoverStrategy(SMACrossoverConfig(fast_window=2, slow_window=4))
    output = service.run_backtest(
        candles=candle_dataset,
        strategy=strat,
        config=BacktestConfig(initial_cash=10000.0),
        symbol="AAPL",
    )

    assert output.result is not None
    assert output.benchmark is not None
    assert output.metrics is not None
    assert output.result.symbol == "AAPL"
    assert "total_return" in output.metrics.to_dict()
