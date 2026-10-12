"""Deterministic backtesting engine, benchmarks, and portfolio metrics."""

from tradelab.backtesting.benchmark import BenchmarkResult, calculate_buy_and_hold_benchmark
from tradelab.backtesting.engine import (
    BacktestConfig,
    BacktestEngine,
    BacktestResult,
    Fill,
    Order,
)
from tradelab.backtesting.metrics import ClosedTrade, PerformanceMetrics, calculate_metrics

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
    "Fill",
    "Order",
    "BenchmarkResult",
    "calculate_buy_and_hold_benchmark",
    "ClosedTrade",
    "PerformanceMetrics",
    "calculate_metrics",
]
