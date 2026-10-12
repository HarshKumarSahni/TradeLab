"""Page 1: Market Dashboard & Explorer."""

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
    page_title="Market Dashboard | TradeLab",
    page_icon="📊",
    layout="wide",
)

init_session_state()
render_sidebar()
settings = get_settings()

render_header(
    title="Market Dashboard",
    subtitle="Inspect historical OHLCV price action, trading volumes, and returns.",
    icon="📊",
)

symbol = st.session_state.get("selected_symbol", "AAPL")

# Parameter Controls Bar
with st.container(border=True):
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1.5])
    with col1:
        ticker_input = (
            st.text_input(
                "Symbol",
                value=symbol,
                max_chars=10,
                help="US Equity or ETF ticker symbol",
            )
            .strip()
            .upper()
        )
        if ticker_input:
            st.session_state["selected_symbol"] = ticker_input
    with col2:
        start_date = st.date_input("Start Date", value=st.session_state.get("start_date"))
        st.session_state["start_date"] = start_date
    with col3:
        end_date = st.date_input("End Date", value=st.session_state.get("end_date"))
        st.session_state["end_date"] = end_date
    with col4:
        st.write("")
        st.write("")
        fetch_clicked = st.button("Fetch Data", type="primary", use_container_width=True)

# Phase 1 Informative Shell / Placeholder
render_empty_state(
    title="Market Explorer Ready",
    message=(
        f"Selected symbol: <strong>{ticker_input or symbol}</strong>.<br>"
        "Historical OHLCV fetching and interactive Plotly candlestick charting will be active "
        "in Phase 2 data pipeline integration."
    ),
    icon="📊",
)

render_disclaimer()
