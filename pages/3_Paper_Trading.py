"""Page 3: Paper Trading Control & Simulated Execution."""

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
    page_title="Paper Trading | TradeLab",
    page_icon="💼",
    layout="wide",
)

init_session_state()
render_sidebar()
settings = get_settings()

render_header(
    title="Paper Trading Control",
    subtitle="Simulated order preview, risk gates, and Alpaca paper account monitoring.",
    icon="💼",
)

# Mandatory Safety Warning
st.warning(
    "🛡️ **SIMULATED PAPER TRADING ONLY** — TradeLab connects exclusively to Alpaca's paper endpoint. "
    "Live production trading and real money execution are strictly disabled.",
    icon="⚠️",
)

# Account Status Card
with st.container(border=True):
    st.markdown("#### 👤 **Account Status**")
    acc_col1, acc_col2, acc_col3, acc_col4 = st.columns(4)

    with acc_col1:
        st.metric(
            "Status", "Connected (Paper)" if settings.has_alpaca_credentials else "Mock / Offline"
        )
    with acc_col2:
        st.metric(
            "Portfolio Value",
            "$100,000.00" if not settings.has_alpaca_credentials else "Pending Sync",
        )
    with acc_col3:
        st.metric(
            "Cash Buying Power",
            "$100,000.00" if not settings.has_alpaca_credentials else "Pending Sync",
        )
    with acc_col4:
        st.metric("Active Positions", "0")

st.write("")

# Order Preview & Safety Controls
with st.container(border=True):
    st.markdown("#### 🔒 **Order Execution Safety Gates**")
    st.caption(
        "Automated bots require explicit two-step user authorization and idempotency tokens. "
        "Streamlit page reruns will never trigger duplicate orders."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.button("Run One Bot Cycle (Dry Run)", use_container_width=True, disabled=True)
    with col2:
        st.button(
            "🛑 Emergency Stop / Kill Switch",
            type="secondary",
            use_container_width=True,
            disabled=True,
        )

render_empty_state(
    title="Paper Broker Integration Ready",
    message=(
        "Alpaca paper trading client integration, account telemetry, and idempotency-backed "
        "order preview will be active in Phase 5."
    ),
    icon="💼",
)

render_disclaimer()
