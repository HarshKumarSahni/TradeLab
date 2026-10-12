"""Session state initialization and helpers for Streamlit."""

from datetime import date, timedelta
from typing import Any, Dict

import streamlit as st

DEFAULT_SYMBOL = "AAPL"
DEFAULT_START_DATE = date.today() - timedelta(days=365)
DEFAULT_END_DATE = date.today()
DEFAULT_FAST_WINDOW = 20
DEFAULT_SLOW_WINDOW = 50
DEFAULT_INITIAL_CASH = 10000.0
DEFAULT_FEE = 0.0
DEFAULT_SLIPPAGE_BPS = 5.0

DEFAULTS: Dict[str, Any] = {
    "selected_symbol": DEFAULT_SYMBOL,
    "start_date": DEFAULT_START_DATE,
    "end_date": DEFAULT_END_DATE,
    "fast_window": DEFAULT_FAST_WINDOW,
    "slow_window": DEFAULT_SLOW_WINDOW,
    "initial_cash": DEFAULT_INITIAL_CASH,
    "fee": DEFAULT_FEE,
    "slippage_bps": DEFAULT_SLIPPAGE_BPS,
    "last_run_id": None,
    "active_tab": "Overview",
}


def init_session_state() -> None:
    """Ensure all core session state keys are initialized with safe defaults."""
    for key, val in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val


def get_state(key: str, default: Any = None) -> Any:
    """Get a value from session state with fallback."""
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    """Set a value in session state."""
    st.session_state[key] = value
