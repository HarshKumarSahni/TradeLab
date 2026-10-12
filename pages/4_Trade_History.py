"""Page 4: Trade History, Run Audit & Reports."""

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
    page_title="Trade History | TradeLab",
    page_icon="📜",
    layout="wide",
)

init_session_state()
render_sidebar()
settings = get_settings()

render_header(
    title="Trade History & Audit Log",
    subtitle="Inspect historical simulation runs, broker order audit trails, and export reports.",
    icon="📜",
)

# Tabs separating Backtest Simulations and Paper Execution Logs
tab_backtests, tab_paper = st.tabs(["🧪 Backtest Simulations", "💼 Paper Execution Orders"])

with tab_backtests:
    with st.container(border=True):
        f_col1, f_col2, f_col3 = st.columns([2, 2, 1])
        with f_col1:
            st.selectbox("Filter by Symbol", options=["All", "AAPL", "MSFT", "SPY"], index=0)
        with f_col2:
            st.selectbox(
                "Sort By", options=["Most Recent", "Highest Return", "Lowest Drawdown"], index=0
            )
        with f_col3:
            st.write("")
            st.write("")
            st.button("Refresh History", use_container_width=True)

    render_empty_state(
        title="No Saved Backtest Runs Yet",
        message="Completed backtest runs will be automatically persisted to SQLite in Phase 4.",
        icon="🧪",
    )

with tab_paper:
    render_empty_state(
        title="No Paper Trading Orders Yet",
        message="Paper orders submitted via Alpaca paper API will appear here with broker order IDs in Phase 5.",
        icon="💼",
    )

render_disclaimer()
