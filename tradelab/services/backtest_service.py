"""Backtest simulation orchestration service."""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from tradelab.backtesting.benchmark import BenchmarkResult, calculate_buy_and_hold_benchmark
from tradelab.backtesting.engine import BacktestConfig, BacktestEngine, BacktestResult
from tradelab.backtesting.metrics import PerformanceMetrics, calculate_metrics
from tradelab.config import Settings, get_settings
from tradelab.data.validation import validate_ohlcv_dataframe
from tradelab.strategies.base import Strategy
from tradelab.strategies.sma_crossover import SMACrossoverConfig, SMACrossoverStrategy


@dataclass
class BacktestRunOutput:
    """Consolidated outputs from a complete backtest execution."""

    result: BacktestResult
    benchmark: BenchmarkResult
    metrics: PerformanceMetrics


class BacktestService:
    """Service orchestrating strategy execution, simulation, and metrics evaluation."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def run_backtest(
        self,
        candles: pd.DataFrame,
        strategy: Optional[Strategy] = None,
        config: Optional[BacktestConfig] = None,
        symbol: str = "ASSET",
    ) -> BacktestRunOutput:
        """Execute a full simulation workflow and compute performance metrics.

        Parameters
        ----------
        candles : pd.DataFrame
            Canonical OHLCV DataFrame
        strategy : Optional[Strategy]
            Strategy instance (defaults to standard SMA 20/50 crossover)
        config : Optional[BacktestConfig]
            Backtest parameters (defaults to $10,000 cash, 5 bps slippage, 0 fee)
        symbol : str
            Ticker identifier

        Returns
        -------
        BacktestRunOutput
            Contains BacktestResult, BenchmarkResult, and PerformanceMetrics
        """
        candles = validate_ohlcv_dataframe(candles, min_bars=5)
        strat = strategy or SMACrossoverStrategy(SMACrossoverConfig(fast_window=20, slow_window=50))
        cfg = config or BacktestConfig()

        # 1. Run simulation engine
        sim_result = BacktestEngine.run(
            candles=candles,
            strategy=strat,
            config=cfg,
            symbol=symbol,
        )

        # 2. Run benchmark comparison
        benchmark_result = calculate_buy_and_hold_benchmark(
            candles=candles,
            config=cfg,
            symbol=symbol,
        )

        # 3. Calculate analytics & trade metrics
        perf_metrics = calculate_metrics(
            result=sim_result,
            benchmark=benchmark_result,
        )

        return BacktestRunOutput(
            result=sim_result,
            benchmark=benchmark_result,
            metrics=perf_metrics,
        )
