"""Unit tests for configuration, credentials masking, and exceptions."""

import pytest
from pydantic import ValidationError

from tradelab.config import Settings
from tradelab.exceptions import (
    BacktestError,
    BrokerError,
    ConfigError,
    DataValidationError,
    MarketDataError,
    RiskLimitViolationError,
    StrategyError,
    TradeLabException,
)
from tradelab.ui.state import DEFAULTS


def test_default_settings(default_settings: Settings) -> None:
    """Verify default settings values and offline safety."""
    assert default_settings.app_mode == "demo"
    assert default_settings.market_data_provider == "yahoo"
    assert default_settings.alpaca_paper is True
    assert default_settings.has_alpaca_credentials is False
    assert default_settings.masked_alpaca_key == "Not Set"
    assert "Demo Mode" in default_settings.status_label


def test_paper_credentials_masked(paper_settings: Settings) -> None:
    """Verify paper credentials are detected and masked without leaking secrets."""
    assert paper_settings.has_alpaca_credentials is True
    assert paper_settings.masked_alpaca_key.startswith("PKT")
    assert paper_settings.masked_alpaca_key.endswith("890")
    assert "SKTEST" not in paper_settings.masked_alpaca_key
    assert "Connected Paper Account" in paper_settings.status_label


def test_prohibit_live_alpaca_endpoint() -> None:
    """Enforce that ALPACA_PAPER=False is strictly rejected with a validation error."""
    with pytest.raises((ConfigError, ValidationError)):
        Settings(alpaca_paper=False)


def test_exception_hierarchy() -> None:
    """Verify domain exceptions inherit from base TradeLabException."""
    exceptions = [
        ConfigError,
        MarketDataError,
        DataValidationError,
        StrategyError,
        BacktestError,
        BrokerError,
        RiskLimitViolationError,
    ]
    for exc in exceptions:
        assert issubclass(exc, TradeLabException)


def test_session_state_defaults() -> None:
    """Verify session state defaults dictionary contains required keys."""
    expected_keys = {
        "selected_symbol",
        "start_date",
        "end_date",
        "fast_window",
        "slow_window",
        "initial_cash",
        "fee",
        "slippage_bps",
        "last_run_id",
    }
    assert expected_keys.issubset(set(DEFAULTS.keys()))
