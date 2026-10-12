"""Page 2: Backtest Lab - Strategy Simulation, Analytics & Fills Ledger."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from tradelab.backtesting.engine import BacktestConfig
from tradelab.config import get_settings
from tradelab.exceptions import BacktestError, DataValidationError, MarketDataError, StrategyError
from tradelab.services.backtest_service import BacktestService
from tradelab.services.market_service import MarketDataService
from tradelab.storage.repository import BacktestRepository
from tradelab.strategies.sma_crossover import SMACrossoverConfig, SMACrossoverStrategy
from tradelab.ui.charts import (
    create_backtest_chart,
    create_drawdown_chart,
    create_equity_curve_chart,
)
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
    subtitle="Simulate Moving-Average crossover strategies with zero lookahead bias and transparent execution costs.",
    icon="🧪",
)

# Configuration Form
with st.container(border=True):
    st.markdown("#### ⚙️ **Strategy & Execution Parameters**")

    r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
    with r1_col1:
        current_symbol = st.session_state.get("selected_symbol", "AAPL")
        symbol_input = (
            st.text_input(
                "Ticker Symbol",
                value=current_symbol,
                max_chars=10,
                help="US Equity or ETF ticker symbol",
            )
            .strip()
            .upper()
        )
        if symbol_input:
            st.session_state["selected_symbol"] = symbol_input

    with r1_col2:
        provider_options = ["yahoo", "fixture"]
        current_provider = (
            settings.market_data_provider
            if settings.market_data_provider in provider_options
            else "yahoo"
        )
        selected_provider = st.selectbox(
            "Market Data Provider",
            options=provider_options,
            index=provider_options.index(current_provider),
            format_func=lambda x: (
                "Yahoo Finance (Online)" if x == "yahoo" else "Offline Fixtures (Sandbox)"
            ),
        )

    with r1_col3:
        start_date = st.date_input(
            "Start Date",
            value=st.session_state.get("start_date", date.today() - timedelta(days=365)),
        )
        st.session_state["start_date"] = start_date

    with r1_col4:
        end_date = st.date_input(
            "End Date",
            value=st.session_state.get("end_date", date.today()),
        )
        st.session_state["end_date"] = end_date

    r2_col1, r2_col2, r2_col3, r2_col4, r2_col5 = st.columns(5)
    with r2_col1:
        fast_window = st.number_input(
            "Fast SMA Window",
            min_value=2,
            max_value=200,
            value=st.session_state.get("fast_window", 20),
            step=1,
            help="Short-term moving average window in daily bars.",
        )
        st.session_state["fast_window"] = fast_window

    with r2_col2:
        slow_window = st.number_input(
            "Slow SMA Window",
            min_value=3,
            max_value=500,
            value=st.session_state.get("slow_window", 50),
            step=1,
            help="Long-term moving average window (must be strictly > Fast SMA).",
        )
        st.session_state["slow_window"] = slow_window

    with r2_col3:
        initial_cash = st.number_input(
            "Initial Capital ($)",
            min_value=100.0,
            max_value=10_000_000.0,
            value=st.session_state.get("initial_cash", 10000.0),
            step=1000.0,
        )
        st.session_state["initial_cash"] = initial_cash

    with r2_col4:
        slippage_bps = st.number_input(
            "Adverse Slippage (bps)",
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.get("slippage_bps", 5.0),
            step=1.0,
            help="Slippage applied adversely per trade side (5 bps = 0.05%).",
        )
        st.session_state["slippage_bps"] = slippage_bps

    with r2_col5:
        fee_per_trade = st.number_input(
            "Fee per Trade ($)",
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.get("fee", 0.0),
            step=1.0,
            help="Flat brokerage fee deducted per order execution.",
        )
        st.session_state["fee"] = fee_per_trade

    run_clicked = st.button("🚀 Run Backtest", type="primary", use_container_width=True)

# Validation check before run
if fast_window >= slow_window:
    st.error("⚠️ Invalid parameter: Fast SMA window must be strictly less than Slow SMA window.")

# Execution or previous run retrieval
target_symbol = st.session_state.get("selected_symbol", "AAPL")

if run_clicked:
    if fast_window >= slow_window:
        st.stop()

    try:
        with st.spinner(f"Simulating SMA({fast_window}/{slow_window}) on {target_symbol}..."):
            # 1. Fetch Market Data
            market_service = MarketDataService()
            candles, meta = market_service.fetch_history(
                symbol=target_symbol,
                start_date=start_date,
                end_date=end_date,
                provider_name=selected_provider,
            )

            # 2. Run Backtest
            strategy = SMACrossoverStrategy(
                SMACrossoverConfig(fast_window=int(fast_window), slow_window=int(slow_window))
            )
            config = BacktestConfig(
                initial_cash=float(initial_cash),
                fee=float(fee_per_trade),
                slippage_bps=float(slippage_bps),
                allow_fractional=False,
            )
            backtest_service = BacktestService()
            run_output = backtest_service.run_backtest(
                candles=candles,
                strategy=strategy,
                config=config,
                symbol=target_symbol,
            )

            # 3. Persist Run to SQLite
            repo = BacktestRepository()
            saved_id = repo.save_run(
                result=run_output.result,
                metrics=run_output.metrics,
                fast_window=int(fast_window),
                slow_window=int(slow_window),
            )
            st.session_state["last_run_id"] = saved_id
            st.session_state["latest_output"] = run_output
            st.success(
                f"✅ Backtest completed and persisted to database! (Run ID: `{saved_id[:8]}...`)"
            )

    except (DataValidationError, StrategyError, BacktestError, MarketDataError) as e:
        st.error(f"⚠️ **Simulation Error:** {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ **Unexpected Error:** {e}")
        st.stop()

# Render Results
if "latest_output" in st.session_state:
    run_output = st.session_state["latest_output"]
    res = run_output.result
    bench = run_output.benchmark
    m = run_output.metrics

    # Top KPI Cards Row
    st.write("")
    st.markdown("### 📊 **Simulation Performance Summary**")

    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    with kpi1:
        st.metric(
            label="Total Return",
            value=f"{m.total_return * 100:+.2f}%",
            delta=f"${res.final_equity - res.initial_cash:+,.2f}",
        )
    with kpi2:
        st.metric(
            label="Buy & Hold Return",
            value=f"{bench.total_return * 100:+.2f}%",
            delta=f"Alpha: {m.alpha * 100:+.2f}%",
        )
    with kpi3:
        st.metric(
            label="Max Drawdown",
            value=f"{m.max_drawdown * 100:.2f}%",
            help="Maximum peak-to-trough drop in equity",
        )
    with kpi4:
        sharpe_str = f"{m.sharpe_ratio:.2f}" if m.sharpe_ratio is not None else "N/A"
        st.metric(
            label="Sharpe Ratio",
            value=sharpe_str,
            help="Annualized Sharpe ratio (risk-free rate = 0%). N/A if zero volatility.",
        )
    with kpi5:
        st.metric(
            label="Completed Trades",
            value=f"{m.total_trades}",
            delta=f"{m.winning_trades}W / {m.losing_trades}L",
        )
    with kpi6:
        win_rate_str = f"{m.win_rate * 100:.1f}%" if m.win_rate is not None else "N/A"
        st.metric(
            label="Win Rate",
            value=win_rate_str,
            help="Percentage of profitable completed round trips.",
        )

    if res.pending_signal:
        st.info(
            f"🔔 **Unexecuted Signal on Final Bar:** A **{res.pending_signal.value}** signal was triggered "
            f"on the final available bar ({res.end_date}). Per zero-lookahead rules, it is recorded as PENDING "
            f"and not filled.",
            icon="ℹ️",
        )

    if res.warnings:
        for w in res.warnings:
            st.warning(w)

    st.write("")

    # Visualizations Tabs
    tab_chart, tab_equity, tab_dd, tab_fills, tab_roundtrips = st.tabs(
        [
            "📈 Strategy & Fills",
            "💰 Equity vs Benchmark",
            "📉 Drawdown Curve",
            "📋 Order Fills Ledger",
            "🎯 Closed Round Trips",
        ]
    )

    with tab_chart:
        fig_bt = create_backtest_chart(
            candles=res.equity_curve[["Close"]].assign(
                Open=res.equity_curve["Close"],
                High=res.equity_curve["Close"],
                Low=res.equity_curve["Close"],
            )
            if "Open" not in res.equity_curve.columns
            else res.equity_curve,
            signals_df=res.signals_df,
            fills=res.fills,
            symbol=res.symbol,
            fast_window=st.session_state["fast_window"],
            slow_window=st.session_state["slow_window"],
        )
        st.plotly_chart(fig_bt, use_container_width=True)

    with tab_equity:
        fig_eq = create_equity_curve_chart(
            equity_df=res.equity_curve,
            benchmark_series=bench.equity_curve,
            symbol=res.symbol,
        )
        st.plotly_chart(fig_eq, use_container_width=True)

    with tab_dd:
        fig_dd = create_drawdown_chart(m.drawdown_series)
        st.plotly_chart(fig_dd, use_container_width=True)

    with tab_fills:
        st.markdown(f"#### **Executed Order Fills ({len(res.fills)} Total)**")
        if res.fills:
            fills_data = [
                {
                    "Timestamp": str(f.timestamp.date()),
                    "Side": f.side.value,
                    "Quantity": int(f.quantity),
                    "Fill Price": f"${f.fill_price:,.2f}",
                    "Fee": f"${f.fee:.2f}",
                    "Cash After": f"${f.cash_after:,.2f}",
                    "Position After": int(f.position_after),
                }
                for f in res.fills
            ]
            fills_df = pd.DataFrame(fills_data)
            st.dataframe(fills_df, use_container_width=True, height=350)

            csv_fills = (
                pd.DataFrame(
                    [
                        {
                            "Timestamp": f.timestamp.isoformat(),
                            "Side": f.side.value,
                            "Quantity": f.quantity,
                            "Fill_Price": f.fill_price,
                            "Fee": f.fee,
                            "Cash_After": f.cash_after,
                            "Position_After": f.position_after,
                        }
                        for f in res.fills
                    ]
                )
                .to_csv(index=False)
                .encode("utf-8")
            )

            st.download_button(
                label="📥 Export Fills Ledger CSV",
                data=csv_fills,
                file_name=f"{res.symbol}_fills_{res.start_date}_{res.end_date}.csv",
                mime="text/csv",
            )
        else:
            render_empty_state(
                title="No Executed Trades",
                message="No moving-average crossover events occurred during this observation window.",
                icon="ℹ️",
            )

    with tab_roundtrips:
        st.markdown("#### **Completed Round-Trip Trades (Paired Entries & Exits)**")
        if m.closed_trades:
            trips_data = [
                {
                    "Entry Date": str(t.entry_timestamp.date()),
                    "Exit Date": str(t.exit_timestamp.date()),
                    "Quantity": int(t.quantity),
                    "Entry Price": f"${t.entry_price:,.2f}",
                    "Exit Price": f"${t.exit_price:,.2f}",
                    "Total Fees": f"${t.total_fees:.2f}",
                    "Net P&L ($)": f"${t.net_pnl:+,.2f}",
                    "Return (%)": f"{t.return_pct * 100:+.2f}%",
                    "Outcome": "WIN ✅" if t.is_win else "LOSS ❌",
                }
                for t in m.closed_trades
            ]
            st.dataframe(pd.DataFrame(trips_data), use_container_width=True)
        else:
            render_empty_state(
                title="No Completed Round Trips",
                message="No paired BUY-to-SELL round-trip trades were closed.",
                icon="ℹ️",
            )

    # Detailed Assumptions & Disclosures Panel
    with st.expander("ℹ️ **Backtest Accounting Assumptions & Audit Details**"):
        st.markdown(
            f"""
            - **Symbol & Window:** `{res.symbol}` from `{res.start_date}` to `{res.end_date}`.
            - **SMA Configuration:** Fast SMA = `{st.session_state["fast_window"]}` days, Slow SMA = `{st.session_state["slow_window"]}` days.
            - **Zero Lookahead Rule:** Signal at bar $t$ close is strictly executed at bar $t+1$ Open.
            - **Costs Modeled:** Adverse slippage = `{res.config.slippage_bps}` bps per side; Fee = `${res.config.fee:.2f}` per trade.
            - **End of Dataset Holding:** `{res.final_quantity:,.0f}` shares held at end of data (Unrealized P&L: `${res.unrealized_pnl:+,.2f}`).
            """
        )

else:
    render_empty_state(
        title="Ready to Backtest",
        message="Configure your SMA parameters above and click <strong>Run Backtest</strong> to simulate execution.",
        icon="🧪",
    )

render_disclaimer()
