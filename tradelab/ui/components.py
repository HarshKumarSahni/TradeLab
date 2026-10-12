"""Shared UI components, sidebars, headers, and notices for TradeLab."""

import streamlit as st

from tradelab.config import get_settings
from tradelab.ui.state import init_session_state


def render_sidebar() -> None:
    """Render unified sidebar across all Streamlit pages."""
    init_session_state()
    settings = get_settings()

    with st.sidebar:
        st.markdown("## 📈 **TradeLab**")
        st.caption("Algorithmic Trading & Paper Trading Workbench")
        st.divider()

        # Operational Mode Badge
        st.markdown("### 🔌 **Environment**")
        if settings.app_mode == "demo":
            st.info(
                "🟡 **Mode:** Demo / Sandbox\n\n*Running offline without live brokerage dependencies.*"
            )
        elif settings.has_alpaca_credentials:
            st.success("🟢 **Mode:** Alpaca Paper Connected\n\n*Simulated execution only.*")
        else:
            st.warning(
                "⚪ **Mode:** Disconnected\n\n*Configure credentials in `.env` to enable paper broker.*"
            )

        st.caption(f"**Data Provider:** `{settings.market_data_provider.upper()}`")
        if settings.has_alpaca_credentials:
            st.caption(f"**Alpaca Key:** `{settings.masked_alpaca_key}`")

        st.divider()

        # Global Quick Settings
        st.markdown("### 🎯 **Active Symbol**")
        symbol = (
            st.text_input(
                "Ticker Symbol",
                value=st.session_state.get("selected_symbol", "AAPL"),
                max_chars=10,
                help="US Equities / ETFs (e.g. AAPL, MSFT, SPY, QQQ)",
            )
            .strip()
            .upper()
        )
        if symbol:
            st.session_state["selected_symbol"] = symbol

        st.divider()

        # Safety & Legal Notice
        st.markdown("### ⚠️ **Safety & Disclaimer**")
        st.caption(
            "Educational and demonstration use only. TradeLab MVP strictly forbids "
            "real-money trading. Past simulated returns are hypothetical and do not "
            "guarantee future results."
        )


def render_header(title: str, subtitle: str, icon: str = "📈") -> None:
    """Render standardized page header."""
    st.markdown(f"## {icon} {title}")
    st.markdown(f"*{subtitle}*")
    st.write("")


def render_empty_state(title: str, message: str, icon: str = "ℹ️") -> None:
    """Render informative empty state panel without fake or fabricated data."""
    st.markdown(
        f"""
        <div style="
            border: 1px dashed #3E4756;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            background-color: rgba(30, 34, 45, 0.4);
            margin: 15px 0;
        ">
            <h3 style="margin-top: 0;">{icon} {title}</h3>
            <p style="color: #9AA0A6; margin-bottom: 0;">{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_disclaimer() -> None:
    """Render footer disclaimer across pages."""
    st.divider()
    st.caption(
        "📌 **TradeLab Disclaimer:** Not financial or investment advice. "
        "All backtests execute on next-bar open to eliminate lookahead bias. "
        "Paper trading connects exclusively to Alpaca's paper endpoint."
    )
