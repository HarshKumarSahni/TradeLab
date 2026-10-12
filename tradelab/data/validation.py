"""OHLCV data schema, index, price consistency, and ticker validation."""

import re
from datetime import date

import numpy as np
import pandas as pd

from tradelab.exceptions import DataValidationError

REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
SYMBOL_REGEX = re.compile(r"^[A-Z0-9.\-]{1,10}$")


def validate_symbol(symbol: str) -> str:
    """Validate US equity / ETF symbol string and return normalized uppercase ticker."""
    if not symbol or not isinstance(symbol, str):
        raise DataValidationError("Symbol must be a non-empty string.")

    cleaned = symbol.strip().upper()
    if not SYMBOL_REGEX.match(cleaned):
        raise DataValidationError(
            f"Invalid ticker symbol '{symbol}'. Must be 1-10 alphanumeric characters, periods, or hyphens."
        )
    return cleaned


def validate_date_range(start_date: date, end_date: date) -> None:
    """Validate that start date is strictly before end date."""
    if not isinstance(start_date, (date, pd.Timestamp)) or not isinstance(
        end_date, (date, pd.Timestamp)
    ):
        raise DataValidationError("Start date and end date must be valid date objects.")

    if start_date >= end_date:
        raise DataValidationError(
            f"Invalid date range: start_date ({start_date}) must be strictly before end_date ({end_date})."
        )


def validate_ohlcv_dataframe(df: pd.DataFrame, min_bars: int = 1) -> pd.DataFrame:
    """Validate that DataFrame strictly satisfies canonical OHLCV requirements.

    Checks:
    - Not empty, sufficient observations >= min_bars
    - DatetimeIndex, sorted ascending, unique timestamps
    - Required numeric columns: Open, High, Low, Close, Volume
    - No null, NaN, or infinite values
    - Prices strictly positive (> 0)
    - Volume non-negative (>= 0)
    - Candle geometry: Low <= Open, Close <= High
    """
    if df is None or not isinstance(df, pd.DataFrame):
        raise DataValidationError("Input market data must be a pandas DataFrame.")

    if df.empty:
        raise DataValidationError("OHLCV DataFrame is empty.")

    if len(df) < min_bars:
        raise DataValidationError(
            f"Insufficient observations: dataset contains {len(df)} bars, but at least {min_bars} are required."
        )

    # Index checks
    if not isinstance(df.index, pd.DatetimeIndex):
        raise DataValidationError(
            f"DataFrame index must be a pd.DatetimeIndex, but got {type(df.index).__name__}."
        )

    if not df.index.is_monotonic_increasing:
        raise DataValidationError(
            "DataFrame index must be sorted in strictly ascending chronological order."
        )

    if df.index.has_duplicates:
        duplicate_count = df.index.duplicated().sum()
        raise DataValidationError(
            f"DataFrame index contains {duplicate_count} duplicate timestamps."
        )

    # Required column presence
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise DataValidationError(
            f"Missing required OHLCV columns: {missing_cols}. Found: {list(df.columns)}"
        )

    # Type & null checks
    for col in REQUIRED_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise DataValidationError(f"Column '{col}' must be numeric, got {df[col].dtype}.")

        if df[col].isna().any():
            nan_count = int(df[col].isna().sum())
            raise DataValidationError(f"Column '{col}' contains {nan_count} missing / NaN values.")

        if np.isinf(df[col]).any():
            raise DataValidationError(f"Column '{col}' contains infinite values.")

    # Price positivity
    for col in ["Open", "High", "Low", "Close"]:
        non_positive = df[df[col] <= 0]
        if not non_positive.empty:
            bad_val = non_positive[col].iloc[0]
            bad_date = non_positive.index[0]
            raise DataValidationError(
                f"Non-positive price found in '{col}': {bad_val} on {bad_date}."
            )

    # Volume non-negativity
    negative_vol = df[df["Volume"] < 0]
    if not negative_vol.empty:
        raise DataValidationError(
            f"Negative volume found: {negative_vol['Volume'].iloc[0]} on {negative_vol.index[0]}."
        )

    # Candle geometry: Low <= Open, Close <= High with small floating point epsilon
    eps = 1e-6
    if (df["Low"] > df["High"] + eps).any():
        bad_row = df[df["Low"] > df["High"] + eps].iloc[0]
        raise DataValidationError(
            f"Malformed candle: Low ({bad_row['Low']}) > High ({bad_row['High']})."
        )

    if (df["Open"] < df["Low"] - eps).any() or (df["Open"] > df["High"] + eps).any():
        bad_row = df[(df["Open"] < df["Low"] - eps) | (df["Open"] > df["High"] + eps)].iloc[0]
        raise DataValidationError(
            f"Malformed candle: Open ({bad_row['Open']}) outside Low ({bad_row['Low']}) / High ({bad_row['High']})."
        )

    if (df["Close"] < df["Low"] - eps).any() or (df["Close"] > df["High"] + eps).any():
        bad_row = df[(df["Close"] < df["Low"] - eps) | (df["Close"] > df["High"] + eps)].iloc[0]
        raise DataValidationError(
            f"Malformed candle: Close ({bad_row['Close']}) outside Low ({bad_row['Low']}) / High ({bad_row['High']})."
        )

    return df
