"""Buy-and-hold benchmark evaluation."""

from dataclasses import dataclass

import pandas as pd

from tradelab.backtesting.engine import BacktestConfig


@dataclass(frozen=True)
class BenchmarkResult:
    """Benchmark performance result."""

    symbol: str
    initial_cash: float
    final_equity: float
    total_return: float
    equity_curve: pd.Series


def calculate_buy_and_hold_benchmark(
    candles: pd.DataFrame,
    config: BacktestConfig,
    symbol: str = "BENCHMARK",
) -> BenchmarkResult:
    """Simulate a realistic buy-and-hold benchmark starting at the first available open bar.

    Applies the same initial cash, transaction fee, and adverse slippage assumptions as the backtest.
    """
    if candles.empty:
        raise ValueError("Cannot compute benchmark on empty candles.")

    slippage_factor = config.slippage_bps / 10000.0
    first_open = float(candles["Open"].iloc[0])
    fill_price = first_open * (1.0 + slippage_factor)

    available_cash = config.initial_cash - config.fee
    if available_cash <= 0 or fill_price <= 0:
        # Fallback if initial cash cannot cover fee
        equity_series = pd.Series(config.initial_cash, index=candles.index, name="Benchmark_Equity")
        return BenchmarkResult(
            symbol=symbol,
            initial_cash=config.initial_cash,
            final_equity=config.initial_cash,
            total_return=0.0,
            equity_curve=equity_series,
        )

    if config.allow_fractional:
        shares = available_cash / fill_price
    else:
        shares = float(int(available_cash // fill_price))

    remaining_cash = available_cash - (shares * fill_price)

    close_series = candles["Close"].astype(float)
    benchmark_equity = remaining_cash + (shares * close_series)
    final_equity = float(benchmark_equity.iloc[-1])
    total_return = (final_equity / config.initial_cash) - 1.0

    return BenchmarkResult(
        symbol=symbol,
        initial_cash=config.initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        equity_curve=benchmark_equity,
    )
