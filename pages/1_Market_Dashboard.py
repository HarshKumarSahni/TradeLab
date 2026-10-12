"""Page 1: Market Dashboard & Historical Price Explorer."""

from datetime import date, timedelta

import streamlit as st

from tradelab.config import get_settings
from tradelab.exceptions import DataValidationError, MarketDataError
from tradelab.services.market_service import MarketDataService
from tradelab.ui.charts import create_candlestick_chart
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
    subtitle="Inspect historical daily OHLCV price action, volume trends, and return distributions.",
    icon="📊",
)


@st.cache_data(ttl=1800, show_spinner=False)
def load_market_data(
    symbol: str,
    start: date,
    end: date,
    provider: str,
):
    """Cached wrapper around MarketDataService to optimize dashboard reruns."""
    service = MarketDataService()
    return service.fetch_history(
        symbol=symbol,
        start_date=start,
        end_date=end,
        provider_name=provider,
        allow_fallback=True,
    )


# Parameter Controls Bar
with st.container(border=True):
    col1, col2, col3, col4, col5 = st.columns([1.8, 1.5, 1.5, 1.5, 1.2])

    with col1:
        current_symbol = st.session_state.get("selected_symbol", "AAPL")
        symbol_input = (
            st.text_input(
                "Ticker Symbol",
                value=current_symbol,
                max_chars=10,
                help="US Equity or ETF ticker symbol (e.g., AAPL, MSFT, SPY)",
            )
            .strip()
            .upper()
        )
        if symbol_input:
            st.session_state["selected_symbol"] = symbol_input

    with col2:
        start_date = st.date_input(
            "Start Date",
            value=st.session_state.get("start_date", date.today() - timedelta(days=365)),
        )
        st.session_state["start_date"] = start_date

    with col3:
        end_date = st.date_input(
            "End Date",
            value=st.session_state.get("end_date", date.today()),
        )
        st.session_state["end_date"] = end_date

    with col4:
        provider_options = ["yahoo", "fixture"]
        current_provider = (
            settings.market_data_provider
            if settings.market_data_provider in provider_options
            else "yahoo"
        )
        selected_provider = st.selectbox(
            "Data Provider",
            options=provider_options,
            index=provider_options.index(current_provider),
            format_func=lambda x: (
                "Yahoo Finance (Online)" if x == "yahoo" else "Offline Fixtures (Sandbox)"
            ),
        )

    with col5:
        st.write("")
        st.write("")
        fetch_clicked = st.button("Fetch Data", type="primary", use_container_width=True)

# Quick Symbol Presets
st.markdown("**Quick Symbols:**")
q_cols = st.columns(6)
presets = ["AAPL", "MSFT", "NVDA", "SPY", "QQQ", "TSLA"]
for i, preset in enumerate(presets):
    if q_cols[i].button(preset, use_container_width=True):
        st.session_state["selected_symbol"] = preset
        st.rerun()

st.write("")

# Data Fetching & Visualization
target_symbol = st.session_state.get("selected_symbol", "AAPL")

try:
    with st.spinner(f"Fetching historical bars for {target_symbol}..."):
        df, meta = load_market_data(
            symbol=target_symbol,
            start=st.session_state["start_date"],
            end=st.session_state["end_date"],
            provider=selected_provider,
        )

    # Top KPI Metrics Row
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    with kpi_col1:
        st.metric(
            label="Latest Close",
            value=f"${meta.latest_close:,.2f}",
            delta=f"{meta.price_change:+,.2f} ({meta.pct_change:+.2f}%)",
        )
    with kpi_col2:
        st.metric(
            label="52W / Period Range",
            value=f"${meta.min_price:,.2f} - ${meta.max_price:,.2f}",
        )
    with kpi_col3:
        st.metric(
            label="Trading Observations",
            value=f"{meta.bar_count:,} bars",
        )
    with kpi_col4:
        st.metric(
            label="Average Daily Volume",
            value=f"{meta.avg_volume / 1_000_000:,.1f}M",
        )
    with kpi_col5:
        st.metric(
            label="Data Source",
            value=meta.source.capitalize(),
        )

    st.write("")

    # Visual Tabs
    tab_chart, tab_table, tab_meta = st.tabs(
        ["📈 Interactive Chart", "📋 Historical Data Table", "ℹ️ Metadata & Provenance"]
    )

    with tab_chart:
        fig = create_candlestick_chart(df, symbol=target_symbol, show_volume=True)
        st.plotly_chart(fig, use_container_width=True)

    with tab_table:
        st.markdown("#### **Historical Daily OHLCV Price Records**")
        st.dataframe(
            df.sort_index(ascending=False).style.format(
                {
                    "Open": "${:,.2f}",
                    "High": "${:,.2f}",
                    "Low": "${:,.2f}",
                    "Close": "${:,.2f}",
                    "Volume": "{:,.0f}",
                }
            ),
            use_container_width=True,
            height=400,
        )

        csv_data = df.to_csv().encode("utf-8")
        st.download_button(
            label="📥 Download Historical CSV",
            data=csv_data,
            file_name=f"{target_symbol}_ohlcv_{meta.start_date}_{meta.end_date}.csv",
            mime="text/csv",
        )

    with tab_meta:
        st.markdown("#### **Dataset Integrity Details**")
        st.json(
            {
                "symbol": meta.symbol,
                "source": meta.source,
                "first_date": str(meta.start_date),
                "last_date": str(meta.end_date),
                "total_observations": meta.bar_count,
                "minimum_price": meta.min_price,
                "maximum_price": meta.max_price,
                "latest_close": meta.latest_close,
                "period_net_change": meta.price_change,
                "period_pct_change": f"{meta.pct_change:.2f}%",
                "average_volume": int(meta.avg_volume),
                "retrieved_at_utc": meta.fetched_at_utc.isoformat(),
            }
        )

except DataValidationError as e:
    st.error(f"⚠️ **Data Validation Error:** {e}")
    render_empty_state(
        title="Invalid Data Request",
        message="Please check your ticker symbol or ensure the start date is before the end date.",
        icon="⚠️",
    )
except MarketDataError as e:
    st.error(f"❌ **Market Data Provider Error:** {e}")
    render_empty_state(
        title="Price Data Unavailable",
        message="Unable to retrieve data for this symbol. You can switch the Data Provider to 'Offline Fixtures (Sandbox)' to explore demo data.",
        icon="🔌",
    )
except Exception as e:
    st.error(f"❌ **Unexpected Error:** {e}")

render_disclaimer()
