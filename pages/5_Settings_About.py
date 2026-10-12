"""Page 5: Settings, Architecture & Disclosures."""

import streamlit as st

from tradelab.config import get_settings
from tradelab.ui.components import render_disclaimer, render_header, render_sidebar
from tradelab.ui.state import init_session_state

st.set_page_config(
    page_title="Settings & About | TradeLab",
    page_icon="⚙️",
    layout="wide",
)

init_session_state()
render_sidebar()
settings = get_settings()

render_header(
    title="Settings & About TradeLab",
    subtitle="Configuration status, architectural guarantees, and regulatory disclosures.",
    icon="⚙️",
)

tab_cfg, tab_arch, tab_assumptions, tab_disclosures = st.tabs(
    ["⚙️ Configuration", "🏗️ Architecture", "📐 Model Assumptions", "⚖️ Disclosures"]
)

with tab_cfg:
    st.markdown("### 🛠️ **System Configuration**")
    st.caption("Values are loaded securely from environment variables or `.env` file.")

    with st.container(border=True):
        st.markdown("**Operational Flags**")
        st.code(
            f"APP_MODE = {settings.app_mode}\n"
            f"MARKET_DATA_PROVIDER = {settings.market_data_provider}\n"
            f"DATABASE_URL = {settings.database_url}\n"
            f"LOG_LEVEL = {settings.log_level}",
            language="bash",
        )

    with st.container(border=True):
        st.markdown("**Alpaca Paper Trading Integration**")
        if settings.has_alpaca_credentials:
            st.success("✅ Alpaca paper credentials detected.")
            st.write(f"- **Key ID:** `{settings.masked_alpaca_key}`")
            st.write("- **Secret:** `[Configured securely in environment]`")
            st.write(f"- **Paper Endpoint Enforced:** `{settings.alpaca_paper}`")
        else:
            st.info("ℹ️ No Alpaca credentials found in `.env`. Running in offline / demo mode.")
            st.markdown(
                """
                To connect Alpaca paper trading:
                1. Create a free account at [Alpaca Markets](https://alpaca.markets).
                2. Navigate to your **Paper Trading** dashboard and generate API keys.
                3. Add them to your local `.env` file:
                   ```dotenv
                   ALPACA_API_KEY=your_key_here
                   ALPACA_SECRET_KEY=your_secret_here
                   ALPACA_PAPER=true
                   ```
                """
            )

with tab_arch:
    st.markdown("### 🏛️ **System Architecture**")
    st.markdown(
        """
        TradeLab adheres to strict separation of concerns across tiers:
        - **UI Tier (`app.py`, `pages/`):** Streamlit views and Plotly charts. Contains zero trading logic.
        - **Service Tier (`tradelab/services/`):** Orchestrates data normalization, backtests, and broker interactions.
        - **Domain Tier (`tradelab/data/`, `tradelab/strategies/`, `tradelab/backtesting/`):** Pure Python business logic with deterministic unit tests.
        - **Broker Tier (`tradelab/brokers/`):** Isolated Alpaca paper SDK and mock adapters.
        - **Storage Tier (`tradelab/storage/`):** SQLite persistence using SQLAlchemy ORM.
        """
    )

with tab_assumptions:
    st.markdown("### 📐 **Backtest Engine Assumptions**")
    st.markdown(
        """
        1. **Zero Lookahead Bias:** A crossover event occurring at the close of trading day $t$
           is filled exclusively at the opening price of trading day $t+1$.
        2. **Slippage Modeling:** Fills incorporate adverse execution slippage (default 5 bps = 0.05% per side):
           - Buy price: $\\text{Open}_{t+1} \\times (1 + \\text{slippage})$
           - Sell price: $\\text{Open}_{t+1} \\times (1 - \\text{slippage})$
        3. **Cash Invariance:** Capital must remain $\\ge 0$ at all times. Long-only strategy with whole-share allocations.
        4. **Mark-to-Market:** Open positions are marked to market on each bar's close without hypothetical liquidation fees.
        """
    )

with tab_disclosures:
    st.markdown("### ⚖️ **Important Disclosures & Limitations**")
    st.markdown(
        """
        - **Educational Purpose:** TradeLab is designed as a software engineering and portfolio showcase. It does not provide financial or investment advice.
        - **No Guaranteed Returns:** Past simulated or paper performance does not guarantee future results.
        - **Data Source Caveats:** Free historical price feeds (e.g., Yahoo Finance) may contain adjustments, revisions, or missing ticks not suitable for high-frequency trading.
        """
    )

render_disclaimer()
