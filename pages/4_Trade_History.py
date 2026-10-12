"""Page 4: Trade History, Run Audit & Reports."""

import json

import pandas as pd
import streamlit as st

from tradelab.config import get_settings
from tradelab.storage.repository import BacktestRepository
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
    subtitle="Audit persisted backtest simulation runs and broker paper orders directly from SQLite storage.",
    icon="📜",
)

repo = BacktestRepository()

tab_backtests, tab_paper = st.tabs(["🧪 Backtest Simulations", "💼 Paper Execution Orders"])

with tab_backtests:
    # 1. Filter and Controls
    with st.container(border=True):
        f_col1, f_col2, f_col3 = st.columns([2, 2, 1])

        with f_col1:
            symbol_filter = (
                st.text_input(
                    "Filter by Symbol",
                    value="ALL",
                    help="Type 'ALL' or a specific ticker (e.g. AAPL, SPY)",
                )
                .strip()
                .upper()
            )

        with f_col2:
            sort_by = st.selectbox(
                "Sort Results",
                options=["Most Recent", "Highest Return", "Lowest Drawdown"],
                index=0,
            )

        with f_col3:
            st.write("")
            st.write("")
            refresh_clicked = st.button("🔄 Refresh History", use_container_width=True)

    # 2. Query Runs
    runs = repo.list_runs(symbol=None if symbol_filter == "ALL" else symbol_filter, limit=100)

    # Sort in Python if requested
    if sort_by == "Highest Return":
        runs.sort(key=lambda r: r.total_return, reverse=True)
    elif sort_by == "Lowest Drawdown":
        runs.sort(
            key=lambda r: r.max_drawdown, reverse=True
        )  # Drawdown is negative, so max is lowest drop

    if not runs:
        render_empty_state(
            title="No Saved Backtest Runs Found",
            message="Go to <strong>Backtest Lab</strong>, run a strategy simulation, and it will be saved here automatically.",
            icon="🧪",
        )
    else:
        st.markdown(f"#### **Found {len(runs)} Stored Backtest Runs**")

        summary_rows = [
            {
                "Run ID": r.id[:8] + "...",
                "Date Created (UTC)": r.created_at_utc.strftime("%Y-%m-%d %H:%M"),
                "Symbol": r.symbol,
                "Period": f"{r.start_date} → {r.end_date}",
                "SMA": f"{r.fast_window} / {r.slow_window}",
                "Initial Cash": f"${r.initial_cash:,.0f}",
                "Total Return": f"{r.total_return * 100:+.2f}%",
                "Max Drawdown": f"{r.max_drawdown * 100:.2f}%",
            }
            for r in runs
        ]
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, height=280)

        st.divider()

        # 3. Detailed Inspector for a Selected Run
        st.markdown("### 🔍 **Inspect Run Details**")
        run_options = {
            f"{r.symbol} ({r.created_at_utc.strftime('%Y-%m-%d %H:%M')}) - {r.id[:8]}": r.id
            for r in runs
        }
        selected_label = st.selectbox("Select Run to Inspect:", options=list(run_options.keys()))
        selected_run_id = run_options[selected_label]

        selected_run = repo.get_run(selected_run_id)
        if selected_run:
            m_dict = json.loads(selected_run.metrics_json)
            cfg_dict = json.loads(selected_run.config_json)

            # Metrics Row
            m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
            with m_col1:
                st.metric("Total Return", f"{selected_run.total_return * 100:+.2f}%")
            with m_col2:
                bench_ret = m_dict.get("benchmark_return", 0.0)
                st.metric("Benchmark Return", f"{bench_ret * 100:+.2f}%")
            with m_col3:
                st.metric("Max Drawdown", f"{selected_run.max_drawdown * 100:.2f}%")
            with m_col4:
                sharpe = m_dict.get("sharpe_ratio")
                st.metric("Sharpe Ratio", f"{sharpe:.2f}" if sharpe is not None else "N/A")
            with m_col5:
                win_rate = m_dict.get("win_rate")
                st.metric("Win Rate", f"{win_rate * 100:.1f}%" if win_rate is not None else "N/A")

            # Fills Table for Selected Run
            fills = repo.get_fills_for_run(selected_run_id)
            st.markdown(f"#### **Executed Order Fills ({len(fills)} Fills)**")

            if fills:
                fills_data = [
                    {
                        "Timestamp": f.timestamp_utc.strftime("%Y-%m-%d"),
                        "Side": f.side,
                        "Quantity": int(f.quantity),
                        "Fill Price": f"${f.fill_price:,.2f}",
                        "Fee": f"${f.fee:.2f}",
                        "Cash After": f"${f.cash_after:,.2f}",
                        "Position After": int(f.position_after),
                    }
                    for f in fills
                ]
                st.dataframe(pd.DataFrame(fills_data), use_container_width=True, height=250)

                # Export CSV button
                export_df = pd.DataFrame(
                    [
                        {
                            "Run_ID": selected_run.id,
                            "Symbol": selected_run.symbol,
                            "Timestamp": f.timestamp_utc.isoformat(),
                            "Side": f.side,
                            "Quantity": f.quantity,
                            "Fill_Price": f.fill_price,
                            "Fee": f.fee,
                            "Cash_After": f.cash_after,
                            "Position_After": f.position_after,
                        }
                        for f in fills
                    ]
                )
                csv_export = export_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"📥 Download Fills CSV ({selected_run.symbol})",
                    data=csv_export,
                    file_name=f"tradelab_{selected_run.symbol}_{selected_run.id[:8]}_fills.csv",
                    mime="text/csv",
                )
            else:
                st.info("No trades were triggered during this backtest run.")

            # Run Management
            with st.expander("🗑️ Delete Stored Run"):
                st.caption(
                    "Permanently delete this backtest record and associated fill ledger entries."
                )
                if st.button("Confirm Delete Run", type="secondary"):
                    repo.delete_run(selected_run_id)
                    st.success("Run deleted.")
                    st.rerun()

with tab_paper:
    render_empty_state(
        title="Paper Trading Audit Trail",
        message=(
            "Simulated paper broker orders, client idempotency tokens, and Alpaca response logs "
            "will be automatically recorded here in Phase 5."
        ),
        icon="💼",
    )

render_disclaimer()
