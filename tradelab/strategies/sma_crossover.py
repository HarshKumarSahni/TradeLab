"""Simple Moving Average (SMA) crossover strategy implementation."""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from tradelab.exceptions import StrategyError
from tradelab.strategies.base import SignalType, Strategy


@dataclass(frozen=True)
class SMACrossoverConfig:
    """Validated parameters for the SMA crossover strategy."""

    fast_window: int = 20
    slow_window: int = 50

    def __post_init__(self) -> None:
        if not isinstance(self.fast_window, int) or not isinstance(self.slow_window, int):
            raise StrategyError("SMA windows must be integers.")
        if self.fast_window < 2:
            raise StrategyError(f"Fast SMA window must be >= 2, got {self.fast_window}.")
        if self.slow_window <= self.fast_window:
            raise StrategyError(
                f"Slow SMA window ({self.slow_window}) must be strictly greater than "
                f"Fast SMA window ({self.fast_window})."
            )


class SMACrossoverStrategy(Strategy):
    """Simple Moving Average (SMA) crossover strategy.

    Rules:
    - BUY (1)  at bar t when fast[t] > slow[t] and fast[t-1] <= slow[t-1]
    - SELL (-1) at bar t when fast[t] < slow[t] and fast[t-1] >= slow[t-1]
    - HOLD (0)  otherwise or during warmup period
    """

    def __init__(self, config: Optional[SMACrossoverConfig] = None):
        self.config = config or SMACrossoverConfig()

    @property
    def name(self) -> str:
        return f"SMA Crossover ({self.config.fast_window}/{self.config.slow_window})"

    def generate_signals(self, candles: pd.DataFrame) -> pd.DataFrame:
        """Compute rolling moving averages and exact crossover events."""
        if candles.empty:
            raise StrategyError("Cannot generate strategy signals on an empty DataFrame.")

        min_required_bars = self.config.slow_window + 2
        if len(candles) < min_required_bars:
            raise StrategyError(
                f"Insufficient data for SMA({self.config.fast_window}/{self.config.slow_window}): "
                f"dataset contains {len(candles)} bars, but at least {min_required_bars} are required."
            )

        if "Close" not in candles.columns:
            raise StrategyError("Candles DataFrame must contain a 'Close' price column.")

        close = candles["Close"].astype(float)
        fast_sma = close.rolling(window=self.config.fast_window).mean()
        slow_sma = close.rolling(window=self.config.slow_window).mean()

        prev_fast = fast_sma.shift(1)
        prev_slow = slow_sma.shift(1)

        # Detect crossover transitions
        buy_cross = (fast_sma > slow_sma) & (prev_fast <= prev_slow)
        sell_cross = (fast_sma < slow_sma) & (prev_fast >= prev_slow)

        # Build signal series: 1 for BUY, -1 for SELL, 0 for HOLD
        signals = pd.Series(int(SignalType.HOLD), index=candles.index, dtype=int)
        signals[buy_cross] = int(SignalType.BUY)
        signals[sell_cross] = int(SignalType.SELL)

        # Mask any signals occurring during indicator NaN warmup
        warmup_mask = fast_sma.isna() | slow_sma.isna() | prev_fast.isna() | prev_slow.isna()
        signals[warmup_mask] = int(SignalType.HOLD)

        return pd.DataFrame(
            {
                "Close": close,
                "SMA_fast": fast_sma,
                "SMA_slow": slow_sma,
                "Signal": signals,
            },
            index=candles.index,
        )
