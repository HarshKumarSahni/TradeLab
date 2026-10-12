"""Yahoo Finance historical market data adapter using yfinance."""

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from tradelab.data.base import MarketDataProvider
from tradelab.data.validation import validate_date_range, validate_ohlcv_dataframe, validate_symbol
from tradelab.exceptions import MarketDataError


class YahooMarketDataProvider(MarketDataProvider):
    """Market data provider fetching historical daily bars via Yahoo Finance."""

    @property
    def name(self) -> str:
        return "yahoo"

    def get_history(
        self,
        symbol: str,
        start: date,
        end: date,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Fetch historical bars from Yahoo Finance, normalize schema, and validate invariants."""
        symbol = validate_symbol(symbol)
        validate_date_range(start, end)

        # yfinance end date is exclusive for daily bars, so extend by 1 day
        start_str = start.strftime("%Y-%m-%d")
        end_inclusive = end + timedelta(days=1)
        end_str = end_inclusive.strftime("%Y-%m-%d")

        try:
            ticker = yf.Ticker(symbol)
            # auto_adjust=True provides split/dividend adjusted Open, High, Low, Close
            raw_df = ticker.history(
                start=start_str,
                end=end_str,
                interval=interval,
                auto_adjust=True,
                raise_errors=False,
            )
        except Exception as e:
            raise MarketDataError(
                f"Network or provider error fetching data for '{symbol}' from Yahoo Finance: {e}"
            ) from e

        if raw_df is None or raw_df.empty:
            raise MarketDataError(
                f"No price data returned for '{symbol}' between {start_str} and {end_str}. "
                "The symbol may be invalid, delisted, or market data may be unavailable for this period."
            )

        # Handle potential MultiIndex columns
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.get_level_values(0)

        # Select canonical columns
        expected_cols = ["Open", "High", "Low", "Close", "Volume"]
        missing = [col for col in expected_cols if col not in raw_df.columns]
        if missing:
            raise MarketDataError(
                f"Yahoo Finance returned incomplete columns for '{symbol}': missing {missing}"
            )

        df = raw_df[expected_cols].copy()

        # Normalize DatetimeIndex: remove timezone awareness and normalize to date timestamps
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_convert(None)
        df.index = pd.to_datetime(df.index).normalize()
        df.index.name = "Date"

        # Ensure sorted ascending
        df = df.sort_index()

        # Remove duplicate index entries if any
        if df.index.has_duplicates:
            df = df[~df.index.duplicated(keep="last")]

        # Validate canonical OHLCV invariants
        return validate_ohlcv_dataframe(df, min_bars=2)
