"""Strategy interfaces and signal representations."""

from abc import ABC, abstractmethod
from enum import IntEnum

import pandas as pd


class SignalType(IntEnum):
    """Trading signal representation."""

    BUY = 1
    HOLD = 0
    SELL = -1


class Strategy(ABC):
    """Abstract base class for trading strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy human-readable identifier."""
        pass

    @abstractmethod
    def generate_signals(self, candles: pd.DataFrame) -> pd.DataFrame:
        """Compute indicator series and discrete crossover signals.

        Parameters
        ----------
        candles : pd.DataFrame
            Canonical OHLCV DataFrame with DatetimeIndex and Close column.

        Returns
        -------
        pd.DataFrame
            DataFrame indexed identically to `candles` containing:
            - 'Signal': SignalType integer (1 = BUY, -1 = SELL, 0 = HOLD)
            - Indicator columns specific to the strategy (e.g. SMA_fast, SMA_slow).
        """
        pass
