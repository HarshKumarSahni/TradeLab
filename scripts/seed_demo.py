"""Seed deterministic sample OHLCV data for offline demo and testing."""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
SAMPLE_CSV_PATH = FIXTURES_DIR / "sample_ohlcv.csv"


def generate_synthetic_ohlcv(
    start_date: date = date(2023, 1, 3),
    num_bars: int = 252,
    initial_price: float = 150.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic, deterministic daily OHLCV bars using geometric Brownian motion."""
    np.random.seed(seed)
    dt_index = []
    curr = start_date
    while len(dt_index) < num_bars:
        # Skip weekends (5=Saturday, 6=Sunday)
        if curr.weekday() < 5:
            dt_index.append(pd.Timestamp(curr))
        curr += timedelta(days=1)

    daily_returns = np.random.normal(0.0005, 0.015, num_bars)
    price_levels = initial_price * np.exp(np.cumsum(daily_returns))

    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []

    prev_close = initial_price
    for p in price_levels:
        open_price = round(prev_close * (1 + np.random.normal(0, 0.003)), 2)
        close_price = round(float(p), 2)
        spread = abs(close_price - open_price)
        high_price = round(
            max(open_price, close_price) + np.random.uniform(0.1, 0.8) + spread * 0.2, 2
        )
        low_price = round(
            min(open_price, close_price) - np.random.uniform(0.1, 0.8) - spread * 0.2, 2
        )
        volume = int(np.random.normal(50_000_000, 10_000_000))
        volume = max(volume, 5_000_000)

        # Enforce strict candle geometry
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)

        opens.append(open_price)
        highs.append(high_price)
        lows.append(low_price)
        closes.append(close_price)
        volumes.append(volume)
        prev_close = close_price

    df = pd.DataFrame(
        {
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes,
        },
        index=pd.DatetimeIndex(dt_index, name="Date"),
    )
    return df


def seed_fixtures() -> None:
    """Write sample OHLCV data to tests/fixtures/sample_ohlcv.csv."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_synthetic_ohlcv()
    df.to_csv(SAMPLE_CSV_PATH)
    print(f"Generated {len(df)} sample bars -> {SAMPLE_CSV_PATH}")


if __name__ == "__main__":
    seed_fixtures()
