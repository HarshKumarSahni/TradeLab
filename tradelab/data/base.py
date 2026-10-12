"""Market data provider abstract interface."""

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class MarketDataProvider(ABC):
    """Abstract base class defining the contract for market data adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name for this market data adapter."""
        pass

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        start: date,
        end: date,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Fetch historical price bars and return a canonical OHLCV DataFrame.

        Returns
        -------
        pd.DataFrame
            Canonical DataFrame with DatetimeIndex and columns:
            ['Open', 'High', 'Low', 'Close', 'Volume']

        Raises
        ------
        MarketDataError
            If network fetch fails or provider returns an error.
        DataValidationError
            If the data violates schema or integrity invariants.
        """
        pass
