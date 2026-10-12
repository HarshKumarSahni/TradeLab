"""Page 3: Paper Trading Control & Simulated Execution."""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from tradelab.config import get_settings
from tradelab.exceptions import BrokerError, RiskLimitViolationError
from tradelab.models import OrderSide
from tradelab.services.bot_controller import BotConfig, BotController
from tradelab.services.market_service import MarketDataService
from tradelab.services.paper_service import PaperTradingService
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
    subtitle="Simulated execution, pre-trade risk gates, and Alpaca paper account monitoring.",
    icon="💼",
)

# Mandatory Safety Notice
st.warning(
    "🛡️ **SIMULATED PAPER TRADING ONLY** — TradeLab operates exclusively in sandbox mode. "
    "Live production trading and real capital execution are hardcoded to be rejected.",
    icon="⚠️",
)

# Initialize Service
paper_service = PaperTradingService()
broker = paper_service.broker

try:
    account = paper_service.get_account()
    clock = paper_service.get_clock()
except Exception as e:
    st.error(f"❌ Failed to connect to paper broker: {e}")
    st.stop()

# Account Telemetry KPI Row
with st.container(border=True):
    st.markdown("#### 👤 **Paper Account Overview**")
    acc_col1, acc_col2, acc_col3, acc_col4, acc_col5 = st.columns(5)

    with acc_col1:
        broker_badge = "🟢 Alpaca Paper" if broker.name == "alpaca_paper" else "🟡 Mock Sandbox"
        st.metric("Broker Connection", broker_badge)
    with acc_col2:
        st.metric("Portfolio Equity", f"${account.equity:,.2f}")
    with acc_col3:
        st.metric("Cash Balance", f"${account.cash:,.2f}")
    with acc_col4:
        st.metric("Buying Power", f"${account.buying_power:,.2f}")
    with acc_col5:
        clock_status = "OPEN 🟢" if clock.is_open else "CLOSED 🔴"
        st.metric("Market Status", clock_status)

st.write("")

# Main Control Panels
tab_manual, tab_bot, tab_positions, tab_orders = st.tabs(
    [
        "📝 Manual Order Preview & Execution",
        "🤖 Safe Bot Controller (One-Cycle)",
        "📊 Open Positions",
        "📜 Broker Order History",
    ]
)

# -------------------------------------------------------------
# TAB 1: MANUAL ORDER PREVIEW & SUBMISSION
# -------------------------------------------------------------
with tab_manual:
    st.markdown("#### 🔒 **Two-Step Pre-Trade Risk Verification**")
    st.caption(
        "Orders must be previewed and explicitly authorized before submission to the broker."
    )

    with st.container(border=True):
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            order_symbol = (
                st.text_input(
                    "Symbol",
                    value=st.session_state.get("selected_symbol", "AAPL"),
                    max_chars=10,
                )
                .strip()
                .upper()
            )
        with m_col2:
            order_side_str = st.selectbox("Action", options=["BUY", "SELL"])
            order_side = OrderSide.BUY if order_side_str == "BUY" else OrderSide.SELL
        with m_col3:
            order_qty = st.number_input("Shares Quantity", min_value=1.0, value=10.0, step=1.0)
        with m_col4:
            est_price = st.number_input(
                "Estimated Price ($)", min_value=0.01, value=150.0, step=1.0
            )

        preview_clicked = st.button(
            "🔎 Preview Proposed Order", type="primary", use_container_width=True
        )

    if preview_clicked or "manual_preview" in st.session_state:
        if preview_clicked:
            preview = paper_service.preview_order(
                symbol=order_symbol,
                side=order_side,
                quantity=order_qty,
                current_price=est_price,
            )
            st.session_state["manual_preview"] = preview

        preview = st.session_state["manual_preview"]

        with st.container(border=True):
            st.markdown("#### 📋 **Pre-Trade Risk Audit**")
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                st.write(
                    f"**Action:** `{preview.side.value}` {preview.quantity:,.0f} shares of `{preview.symbol}`"
                )
                st.write(f"**Estimated Value:** `${preview.estimated_cost:,.2f}`")
            with p_col2:
                st.write(f"**Safety Check:** {'✅ PASSED' if preview.is_safe else '❌ FAILED'}")
                st.write(f"**Idempotency Token:** `{preview.proposed_client_order_id}`")
            with p_col3:
                if preview.warnings:
                    for w in preview.warnings:
                        st.warning(w)
                else:
                    st.success("All pre-trade risk controls satisfied.")

            if preview.is_safe:
                confirm_check = st.checkbox(
                    "I authorize submitting this simulated paper order.", value=False
                )
                if st.button(
                    "🚀 Confirm & Submit Paper Order", type="primary", disabled=not confirm_check
                ):
                    try:
                        submitted = paper_service.submit_paper_order(
                            symbol=preview.symbol,
                            side=preview.side,
                            quantity=preview.quantity,
                            current_price=preview.estimated_price,
                            confirmed=True,
                        )
                        st.success(
                            f"✅ Paper order accepted! Broker ID: `{submitted.broker_order_id}` "
                            f"(Status: `{submitted.status.value}`)"
                        )
                        del st.session_state["manual_preview"]
                        st.rerun()
                    except (RiskLimitViolationError, BrokerError) as e:
                        st.error(f"❌ Order failed: {e}")

# -------------------------------------------------------------
# TAB 2: SAFE BOT CONTROLLER
# -------------------------------------------------------------
with tab_bot:
    st.markdown("#### 🤖 **Automated Paper Bot (Discrete Single-Cycle Runner)**")
    st.caption(
        "TradeLab never runs uncontrolled infinite loops in the dashboard. "
        "Each cycle evaluates completed market bars with full idempotency and risk limits."
    )

    with st.container(border=True):
        b_col1, b_col2, b_col3, b_col4 = st.columns(4)
        with b_col1:
            bot_symbol = st.text_input("Bot Target Symbol", value="AAPL").strip().upper()
        with b_col2:
            bot_fast = st.number_input("Fast SMA", min_value=2, value=20, step=1)
        with b_col3:
            bot_slow = st.number_input("Slow SMA", min_value=3, value=50, step=1)
        with b_col4:
            bot_alloc = st.number_input(
                "Max Allocation ($)", min_value=100.0, value=10000.0, step=500.0
            )

        c_col1, c_col2 = st.columns(2)
        with c_col1:
            bot_enabled = st.toggle("Enable Live Execution for Bot", value=False)
        with c_col2:
            kill_switch = st.toggle("🛑 Emergency Stop / Kill Switch", value=False)

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            run_dry_btn = st.button("▶️ Run One Cycle (Dry Run)", use_container_width=True)
        with btn_col2:
            run_live_btn = st.button(
                "🚀 Execute One Cycle (Paper Broker)",
                type="primary",
                use_container_width=True,
                disabled=not bot_enabled or kill_switch,
            )

    if run_dry_btn or run_live_btn:
        try:
            with st.spinner(f"Evaluating completed bars for {bot_symbol}..."):
                # Fetch recent market data
                market_service = MarketDataService()
                candles, _ = market_service.fetch_history(
                    symbol=bot_symbol,
                    start_date=datetime.now(timezone.utc).date() - pd.Timedelta(days=200),
                    end_date=datetime.now(timezone.utc).date(),
                    allow_fallback=True,
                )

                bot_cfg = BotConfig(
                    symbol=bot_symbol,
                    fast_window=int(bot_fast),
                    slow_window=int(bot_slow),
                    max_allocation_usd=float(bot_alloc),
                    max_order_qty=100.0,
                    is_enabled=bot_enabled,
                    kill_switch_active=kill_switch,
                )
                controller = BotController(paper_service=paper_service, config=bot_cfg)
                cycle_res = controller.run_cycle(candles, dry_run=run_dry_btn)

                if cycle_res.success:
                    st.success(
                        f"**Cycle Result:** {cycle_res.action_taken} (Signal: `{cycle_res.signal_detected}`)"
                    )
                else:
                    st.warning(f"**Cycle Warning:** {cycle_res.action_taken}")

                for msg in cycle_res.messages:
                    st.write(f"- {msg}")

                if cycle_res.order:
                    st.info(f"Broker Order Submitted: `{cycle_res.order.broker_order_id}`")

        except Exception as e:
            st.error(f"❌ Bot cycle error: {e}")

# -------------------------------------------------------------
# TAB 3: POSITIONS
# -------------------------------------------------------------
with tab_positions:
    st.markdown("#### 📊 **Current Paper Broker Holdings**")
    positions = paper_service.get_positions()

    if positions:
        pos_data = [
            {
                "Symbol": p.symbol,
                "Shares": f"{p.quantity:,.0f}",
                "Cost Basis": f"${p.cost_basis:,.2f}",
                "Current Price": f"${p.current_price:,.2f}",
                "Market Value": f"${p.market_value:,.2f}",
                "Unrealized P&L": f"${p.unrealized_pl:+,.2f} ({p.unrealized_plpc * 100:+.2f}%)",
            }
            for p in positions
        ]
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True)
    else:
        render_empty_state(
            title="Portfolio Flat",
            message="No active positions held in your paper trading account.",
            icon="📊",
        )

# -------------------------------------------------------------
# TAB 4: ORDERS HISTORY
# -------------------------------------------------------------
with tab_orders:
    st.markdown("#### 📜 **Recent Paper Broker Orders**")
    orders = paper_service.get_orders(limit=25)

    if orders:
        ord_data = [
            {
                "Broker Order ID": o.broker_order_id,
                "Client Order ID": o.client_order_id,
                "Submitted (UTC)": o.submitted_at.strftime("%Y-%m-%d %H:%M"),
                "Symbol": o.symbol,
                "Side": o.side.value,
                "Quantity": f"{o.quantity:,.0f}",
                "Status": o.status.value,
                "Fill Price": f"${o.filled_avg_price:,.2f}" if o.filled_avg_price else "—",
            }
            for p in orders
            for o in [p]
        ]
        st.dataframe(pd.DataFrame(ord_data), use_container_width=True)
    else:
        render_empty_state(
            title="No Recent Orders",
            message="No paper orders submitted to the broker yet.",
            icon="📜",
        )

render_disclaimer()
