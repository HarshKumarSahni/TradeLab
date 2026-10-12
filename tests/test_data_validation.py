"""Unit tests for market data validation, fixtures, and normalization."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from tradelab.data.fixtures import FixtureMarketDataProvider
from tradelab.data.validation import (
    validate_date_range,
    validate_ohlcv_dataframe,
    validate_symbol,
)
from tradelab.data.yahoo import YahooMarketDataProvider
from tradelab.exceptions import DataValidationError, MarketDataError
from tradelab.models import MarketDataMetadata
from tradelab.services.market_service import MarketDataService


@pytest.fixture
def valid_ohlcv_df() -> pd.DataFrame:
    """Construct a clean 5-day canonical OHLCV DataFrame."""
    dates = pd.date_range("2023-01-01", periods=5, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0, 102.0, 101.0, 103.0, 104.0],
            "High": [105.0, 106.0, 104.0, 107.0, 108.0],
            "Low": [98.0, 99.0, 97.0, 101.0, 102.0],
            "Close": [102.0, 101.0, 103.0, 104.0, 107.0],
            "Volume": [1000000, 1200000, 900000, 1100000, 1500000],
        },
        index=pd.DatetimeIndex(dates, name="Date"),
    )


# 1. Symbol validation tests
def test_validate_symbol_valid() -> None:
    assert validate_symbol("aapl") == "AAPL"
    assert validate_symbol("  msft ") == "MSFT"
    assert validate_symbol("BRK.B") == "BRK.B"
    assert validate_symbol("BF-B") == "BF-B"


@pytest.mark.parametrize("bad_symbol", ["", "   ", "TOOLONGTICKERNAME", "AAPL$@", "TS/LA"])
def test_validate_symbol_invalid(bad_symbol: str) -> None:
    with pytest.raises(DataValidationError):
        validate_symbol(bad_symbol)


# 2. Date range validation tests
def test_validate_date_range() -> None:
    validate_date_range(date(2023, 1, 1), date(2023, 1, 10))
    with pytest.raises(DataValidationError):
        validate_date_range(date(2023, 1, 10), date(2023, 1, 1))
    with pytest.raises(DataValidationError):
        validate_date_range(date(2023, 1, 5), date(2023, 1, 5))


# 3. Canonical OHLCV DataFrame validation tests
def test_validate_ohlcv_dataframe_success(valid_ohlcv_df: pd.DataFrame) -> None:
    res = validate_ohlcv_dataframe(valid_ohlcv_df, min_bars=3)
    assert len(res) == 5
    assert list(res.columns) == ["Open", "High", "Low", "Close", "Volume"]


def test_validate_ohlcv_dataframe_empty() -> None:
    with pytest.raises(DataValidationError, match="empty"):
        validate_ohlcv_dataframe(pd.DataFrame())


def test_validate_ohlcv_dataframe_non_datetime_index(valid_ohlcv_df: pd.DataFrame) -> None:
    df = valid_ohlcv_df.reset_index(drop=True)
    with pytest.raises(DataValidationError, match="DatetimeIndex"):
        validate_ohlcv_dataframe(df)


def test_validate_ohlcv_dataframe_unsorted_index(valid_ohlcv_df: pd.DataFrame) -> None:
    df = valid_ohlcv_df.iloc[::-1]
    with pytest.raises(DataValidationError, match="ascending"):
        validate_ohlcv_dataframe(df)


def test_validate_ohlcv_dataframe_duplicate_index(valid_ohlcv_df: pd.DataFrame) -> None:
    dates = list(valid_ohlcv_df.index)
    dates[1] = dates[0]  # Duplicate first date
    df = valid_ohlcv_df.copy()
    df.index = pd.DatetimeIndex(dates)
    with pytest.raises(DataValidationError, match="duplicate"):
        validate_ohlcv_dataframe(df)


def test_validate_ohlcv_dataframe_missing_column(valid_ohlcv_df: pd.DataFrame) -> None:
    df = valid_ohlcv_df.drop(columns=["Volume"])
    with pytest.raises(DataValidationError, match="Missing required OHLCV columns"):
        validate_ohlcv_dataframe(df)


def test_validate_ohlcv_dataframe_nan_values(valid_ohlcv_df: pd.DataFrame) -> None:
    df = valid_ohlcv_df.copy()
    df.loc[df.index[0], "Close"] = np.nan
    with pytest.raises(DataValidationError, match="missing / NaN"):
        validate_ohlcv_dataframe(df)


def test_validate_ohlcv_dataframe_negative_price(valid_ohlcv_df: pd.DataFrame) -> None:
    df = valid_ohlcv_df.copy()
    df.loc[df.index[0], "Low"] = -5.0
    with pytest.raises(DataValidationError, match="Non-positive price"):
        validate_ohlcv_dataframe(df)


def test_validate_ohlcv_dataframe_negative_volume(valid_ohlcv_df: pd.DataFrame) -> None:
    df = valid_ohlcv_df.copy()
    df.loc[df.index[0], "Volume"] = -100
    with pytest.raises(DataValidationError, match="Negative volume"):
        validate_ohlcv_dataframe(df)


def test_validate_ohlcv_dataframe_malformed_candle_low_high(valid_ohlcv_df: pd.DataFrame) -> None:
    df = valid_ohlcv_df.copy()
    df.loc[df.index[0], "Low"] = 120.0  # Low > High (105.0)
    with pytest.raises(DataValidationError, match="Malformed candle: Low"):
        validate_ohlcv_dataframe(df)


def test_validate_ohlcv_dataframe_malformed_candle_open_high(valid_ohlcv_df: pd.DataFrame) -> None:
    df = valid_ohlcv_df.copy()
    df.loc[df.index[0], "Open"] = 110.0  # Open > High (105.0)
    with pytest.raises(DataValidationError, match="Malformed candle: Open"):
        validate_ohlcv_dataframe(df)


def test_validate_ohlcv_dataframe_min_bars(valid_ohlcv_df: pd.DataFrame) -> None:
    with pytest.raises(DataValidationError, match="Insufficient observations"):
        validate_ohlcv_dataframe(valid_ohlcv_df, min_bars=20)


# 4. Fixture Provider tests
def test_fixture_provider_loads() -> None:
    provider = FixtureMarketDataProvider()
    df = provider.get_history(symbol="AAPL", start=date(2023, 1, 1), end=date(2023, 12, 31))
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert isinstance(df.index, pd.DatetimeIndex)


# 5. Metadata calculation tests
def test_market_data_metadata_calculation(valid_ohlcv_df: pd.DataFrame) -> None:
    meta = MarketDataMetadata.from_dataframe(valid_ohlcv_df, symbol="TEST", source="unit_test")
    assert meta.symbol == "TEST"
    assert meta.bar_count == 5
    assert meta.latest_close == 107.0
    assert meta.price_change == 5.0  # 107 - 102
    assert round(meta.pct_change, 2) == 4.90
    assert meta.min_price == 97.0
    assert meta.max_price == 108.0


# 6. Service tests with Mock Provider
def test_market_service_fetch_history_fixture() -> None:
    service = MarketDataService()
    df, meta = service.fetch_history(
        symbol="AAPL",
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
        provider_name="fixture",
    )
    assert not df.empty
    assert meta.symbol == "AAPL"
    assert meta.source == "fixture"


def test_yahoo_provider_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Yahoo provider raises MarketDataError when yfinance returns empty."""

    class FakeTicker:
        def __init__(self, symbol: str):
            pass

        def history(self, **kwargs: object) -> pd.DataFrame:
            return pd.DataFrame()

    import yfinance as yf

    monkeypatch.setattr(yf, "Ticker", FakeTicker)

    provider = YahooMarketDataProvider()
    with pytest.raises(MarketDataError, match="No price data returned"):
        provider.get_history("BADTICKER", date(2023, 1, 1), date(2023, 1, 10))
