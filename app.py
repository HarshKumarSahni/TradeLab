"""TradeLab - Algorithmic Trading & Paper Trading Workbench.

Main entry point and landing hub.
"""

import streamlit as st

from tradelab.config import get_settings
from tradelab.ui.components import render_disclaimer, render_header, render_sidebar
from tradelab.ui.state import init_session_state

st.set_page_config(
    page_title="TradeLab | Algorithmic Trading Workbench",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
render_sidebar()
settings = get_settings()

render_header(
    title="TradeLab Algorithmic Trading Workbench",
    subtitle="An interactive Python workbench for market exploration, strategy backtesting, and safe paper trading.",
    icon="📈",
)

# Top Metrics / Quick Info Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("App Mode", settings.app_mode.capitalize())
with col2:
    st.metric("Active Symbol", st.session_state.get("selected_symbol", "AAPL"))
with col3:
    st.metric("Data Provider", settings.market_data_provider.upper())
with col4:
    st.metric("Paper Trading", "Available" if settings.has_alpaca_credentials else "Mock / Offline")

st.write("")

# Navigation & Features Overview
st.markdown("### 🧭 **Explore Modules**")

nav_col1, nav_col2 = st.columns(2)

with nav_col1:
    with st.container(border=True):
        st.markdown("#### 📊 **1. Market Dashboard**")
        st.write(
            "Inspect US stock and ETF historical price action, interactive candlestick charts, "
            "volume overlays, and summary return metrics."
        )
        st.page_link("pages/1_Market_Dashboard.py", label="Open Market Dashboard", icon="📊")

    with st.container(border=True):
        st.markdown("#### 🧪 **2. Backtest Lab**")
        st.write(
            "Simulate moving-average crossover strategies with deterministic next-bar execution, "
            "configurable transaction fees, slippage models, and benchmark comparisons."
        )
        st.page_link("pages/2_Backtest_Lab.py", label="Launch Backtest Lab", icon="🧪")

with nav_col2:
    with st.container(border=True):
        st.markdown("#### 💼 **3. Paper Trading**")
        st.write(
            "Connect an Alpaca paper-trading account in sandbox mode. Review account balances, "
            "preview proposed orders, and monitor simulated execution with safety risk gates."
        )
        st.page_link("pages/3_Paper_Trading.py", label="Enter Paper Trading", icon="💼")

    with st.container(border=True):
        st.markdown("#### 📜 **4. Trade History & Reports**")
        st.write(
            "Audit saved backtest runs and paper execution fills. Inspect metrics and export "
            "clean CSV reports without sensitive credentials."
        )
        st.page_link("pages/4_Trade_History.py", label="View Trade History", icon="📜")

# Educational & Architecture Highlights
st.write("")
st.markdown("### 🛡️ **Core Architectural Guarantees**")

feat_col1, feat_col2, feat_col3 = st.columns(3)
with feat_col1:
    st.markdown("**No Lookahead Bias**")
    st.caption(
        "Signals computed on completed bar $t$ execute exclusively on the open of bar $t+1$. "
        "The final bar's signal remains marked as pending."
    )
with feat_col2:
    st.markdown("**Paper-Only Safety Gates**")
    st.caption(
        "TradeLab is hardcoded to reject live money endpoints. Only Alpaca sandbox paper "
        "credentials are accepted to guarantee zero capital risk."
    )
with feat_col3:
    st.markdown("**Reproducible Offline Mode**")
    st.caption(
        "Deterministic local fixtures and mock brokers allow full offline testing, grading, "
        "and demonstration without external API keys."
    )

render_disclaimer()
