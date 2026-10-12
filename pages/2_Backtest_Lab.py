"""Page 2: Backtest Lab - Strategy Simulation & Performance."""

import streamlit as st

from tradelab.config import get_settings
from tradelab.ui.components import (
    render_disclaimer,
    render_empty_state,
    render_header,
    render_sidebar,
)
from tradelab.ui.state import init_session_state

st.set_page_config(
    page_title="Backtest Lab | TradeLab",
    page_icon="🧪",
    layout="wide",
)

init_session_state()
render_sidebar()
settings = get_settings()

render_header(
    title="Backtest Lab",
    subtitle="Configure moving-average crossover strategies with zero lookahead bias.",
    icon="🧪",
)

symbol = st.session_state.get("selected_symbol", "AAPL")

# Strategy Configuration Form Panel
with st.container(border=True):
    st.markdown("#### ⚙️ **Strategy & Execution Parameters**")
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)

    with p_col1:
        fast_win = st.number_input(
            "Fast SMA Window",
            min_value=2,
            max_value=200,
            value=st.session_state.get("fast_window", 20),
            step=1,
            help="Number of bars for the fast simple moving average.",
        )
        st.session_state["fast_window"] = fast_win

    with p_col2:
        slow_win = st.number_input(
            "Slow SMA Window",
            min_value=3,
            max_value=500,
            value=st.session_state.get("slow_window", 50),
            step=1,
            help="Number of bars for the slow simple moving average (must be > fast window).",
        )
        st.session_state["slow_window"] = slow_win

    with p_col3:
        initial_cash = st.number_input(
            "Initial Capital ($)",
            min_value=100.0,
            max_value=10_000_000.0,
            value=st.session_state.get("initial_cash", 10000.0),
            step=1000.0,
        )
        st.session_state["initial_cash"] = initial_cash

    with p_col4:
        slippage_bps = st.number_input(
            "Slippage (bps)",
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.get("slippage_bps", 5.0),
            step=1.0,
            help="Execution slippage in basis points per trade side (5 bps = 0.05%).",
        )
        st.session_state["slippage_bps"] = slippage_bps

    if fast_win >= slow_win:
        st.error("⚠️ Invalid parameter: Fast SMA window must be strictly less than Slow SMA window.")

    run_clicked = st.button("Run Backtest", type="primary", use_container_width=True)

# Phase 1 Informative Shell
render_empty_state(
    title="Backtest Simulation Ready",
    message=(
        f"Configured for <strong>{symbol}</strong> with SMA({fast_win}/{slow_win}).<br>"
        "Next-bar open fill simulation, equity curve calculation, drawdown analysis, "
        "and benchmark comparisons will be active in Phase 3 & 4."
    ),
    icon="🧪",
)

render_disclaimer()
