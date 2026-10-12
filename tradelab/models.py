"""Domain models, data contracts, and enums for TradeLab."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

import pandas as pd
from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    """Trading order side."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    """Lifecycle status of a paper or simulated order."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"


class MarketDataSource(str, Enum):
    """Historical market data source."""

    YAHOO = "yahoo"
    FIXTURE = "fixture"
    ALPHA_VANTAGE = "alpha_vantage"


class MarketDataRequest(BaseModel):
    """Validated market data request parameters."""

    symbol: str = Field(min_length=1, max_length=10)
    start_date: date
    end_date: date
    interval: str = Field(default="1d")


@dataclass(frozen=True)
class MarketDataMetadata:
    """Metadata describing a fetched and validated OHLCV dataset."""

    symbol: str
    source: str
    start_date: date
    end_date: date
    bar_count: int
    fetched_at_utc: datetime
    latest_close: float
    price_change: float
    pct_change: float
    min_price: float
    max_price: float
    avg_volume: float

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, symbol: str, source: str) -> "MarketDataMetadata":
        """Compute metadata summary from a canonical OHLCV DataFrame."""
        if df.empty:
            raise ValueError("Cannot construct MarketDataMetadata from an empty DataFrame")

        first_close = float(df["Close"].iloc[0])
        latest_close = float(df["Close"].iloc[-1])
        price_change = latest_close - first_close
        pct_change = (price_change / first_close) * 100.0 if first_close > 0 else 0.0

        dates = df.index.date if hasattr(df.index, "date") else df.index

        return cls(
            symbol=symbol.upper(),
            source=source,
            start_date=dates[0],
            end_date=dates[-1],
            bar_count=len(df),
            fetched_at_utc=datetime.now(timezone.utc),
            latest_close=latest_close,
            price_change=price_change,
            pct_change=pct_change,
            min_price=float(df["Low"].min()),
            max_price=float(df["High"].max()),
            avg_volume=float(df["Volume"].mean()),
        )
