"""Market data orchestration service."""

from datetime import date
from typing import Dict, Optional, Tuple

import pandas as pd

from tradelab.config import Settings, get_settings
from tradelab.data.base import MarketDataProvider
from tradelab.data.fixtures import FixtureMarketDataProvider
from tradelab.data.validation import validate_date_range, validate_symbol
from tradelab.data.yahoo import YahooMarketDataProvider
from tradelab.exceptions import MarketDataError
from tradelab.models import MarketDataMetadata


class MarketDataService:
    """Orchestrates fetching, caching, and metadata generation for market data."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._providers: Dict[str, MarketDataProvider] = {
            "yahoo": YahooMarketDataProvider(),
            "fixture": FixtureMarketDataProvider(),
        }

    def register_provider(self, name: str, provider: MarketDataProvider) -> None:
        """Register a custom or alternate market data provider."""
        self._providers[name.lower()] = provider

    def get_provider(self, provider_name: Optional[str] = None) -> MarketDataProvider:
        """Retrieve the configured or requested provider instance."""
        target = (provider_name or self.settings.market_data_provider).lower()
        if target not in self._providers:
            raise MarketDataError(
                f"Unknown data provider '{target}'. Available providers: {list(self._providers.keys())}"
            )
        return self._providers[target]

    def fetch_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        provider_name: Optional[str] = None,
        allow_fallback: bool = True,
    ) -> Tuple[pd.DataFrame, MarketDataMetadata]:
        """Fetch historical OHLCV data and calculate summary metadata.

        Parameters
        ----------
        symbol : str
            Ticker symbol (e.g. AAPL, SPY)
        start_date : date
            Start date
        end_date : date
            End date
        provider_name : Optional[str]
            Override configured provider ('yahoo' | 'fixture')
        allow_fallback : bool
            If True, gracefully falls back to fixture data if online provider fails

        Returns
        -------
        Tuple[pd.DataFrame, MarketDataMetadata]
            Canonical validated DataFrame and summary metadata
        """
        symbol = validate_symbol(symbol)
        validate_date_range(start_date, end_date)

        target_provider = provider_name or self.settings.market_data_provider
        provider = self.get_provider(target_provider)

        try:
            df = provider.get_history(symbol=symbol, start=start_date, end=end_date)
            source_label = provider.name
        except MarketDataError as e:
            if allow_fallback and target_provider != "fixture":
                # Fall back to fixture data with clear source attribution
                fallback_provider = self.get_provider("fixture")
                df = fallback_provider.get_history(symbol=symbol, start=start_date, end=end_date)
                source_label = f"fixture (fallback: {e})"
            else:
                raise

        metadata = MarketDataMetadata.from_dataframe(df=df, symbol=symbol, source=source_label)
        return df, metadata
