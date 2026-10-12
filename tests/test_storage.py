"""Unit tests for SQLite persistence, ORM models, and BacktestRepository."""

import json

import pandas as pd
import pytest

from tradelab.backtesting.benchmark import calculate_buy_and_hold_benchmark
from tradelab.backtesting.engine import BacktestConfig, BacktestEngine
from tradelab.backtesting.metrics import calculate_metrics
from tradelab.storage.repository import BacktestRepository
from tradelab.strategies.sma_crossover import SMACrossoverConfig, SMACrossoverStrategy


@pytest.fixture
def repo() -> BacktestRepository:
    """Provide repository backed by in-memory SQLite for testing."""
    return BacktestRepository(database_url="sqlite:///:memory:")


@pytest.fixture
def sample_backtest_output():
    """Run a small deterministic backtest to produce real result & metrics."""
    dates = pd.date_range("2023-01-01", periods=15, freq="D")
    prices = [10.0, 10.0, 10.0, 10.0, 20.0, 20.0, 5.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
    opens = prices
    highs = [p + 1.0 for p in opens]
    lows = [p - 1.0 for p in opens]
    closes = prices
    volumes = [100000] * 15

    candles = pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
        index=pd.DatetimeIndex(dates, name="Date"),
    )

    strat = SMACrossoverStrategy(SMACrossoverConfig(fast_window=2, slow_window=4))
    cfg = BacktestConfig(initial_cash=10000.0, fee=2.0, slippage_bps=5.0)

    result = BacktestEngine.run(candles, strat, cfg, symbol="AAPL")
    benchmark = calculate_buy_and_hold_benchmark(candles, cfg, symbol="AAPL")
    metrics = calculate_metrics(result, benchmark)

    return result, metrics


def test_save_and_get_run(repo: BacktestRepository, sample_backtest_output) -> None:
    """Verify backtest run and fills are persisted and retrievable."""
    result, metrics = sample_backtest_output
    run_id = repo.save_run(result, metrics, fast_window=2, slow_window=4)

    assert run_id is not None

    record = repo.get_run(run_id)
    assert record is not None
    assert record.symbol == "AAPL"
    assert record.fast_window == 2
    assert record.slow_window == 4
    assert record.initial_cash == 10000.0
    assert record.total_return == metrics.total_return
    assert record.max_drawdown == metrics.max_drawdown

    parsed_metrics = json.loads(record.metrics_json)
    assert "total_return" in parsed_metrics
    assert "win_rate" in parsed_metrics

    fills = repo.get_fills_for_run(run_id)
    assert len(fills) == len(result.fills)
    if fills:
        assert fills[0].side in ["BUY", "SELL"]
        assert fills[0].quantity > 0
        assert fills[0].fee == 2.0


def test_list_runs_with_filter(repo: BacktestRepository, sample_backtest_output) -> None:
    """Verify listing runs with and without symbol filters."""
    result, metrics = sample_backtest_output
    run_id = repo.save_run(result, metrics)

    all_runs = repo.list_runs()
    assert len(all_runs) >= 1

    aapl_runs = repo.list_runs(symbol="AAPL")
    assert len(aapl_runs) >= 1
    assert aapl_runs[0].id == run_id

    msft_runs = repo.list_runs(symbol="MSFT")
    assert len(msft_runs) == 0


def test_delete_run_cascades_fills(repo: BacktestRepository, sample_backtest_output) -> None:
    """Verify deleting a run cascades to remove associated fills."""
    result, metrics = sample_backtest_output
    run_id = repo.save_run(result, metrics)

    assert len(repo.get_fills_for_run(run_id)) > 0

    deleted = repo.delete_run(run_id)
    assert deleted is True

    assert repo.get_run(run_id) is None
    fills_after = repo.get_fills_for_run(run_id)
    assert len(fills_after) == 0
