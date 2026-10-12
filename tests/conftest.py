"""Global pytest fixtures and test setup."""

import pytest

from tradelab.config import Settings


@pytest.fixture
def default_settings() -> Settings:
    """Fixture providing default demo settings."""
    return Settings(
        app_mode="demo",
        market_data_provider="yahoo",
        alpaca_api_key=None,
        alpaca_secret_key=None,
        alpaca_paper=True,
        database_url="sqlite:///:memory:",
        log_level="INFO",
    )


@pytest.fixture
def paper_settings() -> Settings:
    """Fixture providing configured paper trading settings."""
    return Settings(
        app_mode="paper",
        market_data_provider="yahoo",
        alpaca_api_key="PKTEST1234567890",
        alpaca_secret_key="SKTEST0987654321",
        alpaca_paper=True,
        database_url="sqlite:///:memory:",
        log_level="INFO",
    )
