# TradeLab: 2-3 Minute Interview Walkthrough & Demo Script

This script provides an interviewer-ready walkthrough of **TradeLab**—an algorithmic trading backtester and paper trading workbench engineered with zero lookahead bias, adverse execution modeling, and non-bypassable safety controls.

---

## Pitch & Overview (30 Seconds)

> *"Welcome to TradeLab. As quant traders and engineers know, the #1 failure in retail backtesting is lookahead bias and unrealistic execution assumptions—such as filling market orders at the exact bar close where the signal was generated, or assuming zero slippage.*
>
> *TradeLab solves this with an event-driven engine where signals generated at bar $t$ close are strictly scheduled for execution at bar $t+1$ Open with adverse slippage and transaction costs. The entire workbench is built on Streamlit, uses SQLite for auditable trade history, and integrates with Alpaca's paper trading sandbox and an offline mock broker with hardcoded safety rails to ensure live real-money execution is impossible."*

---

## Act 1: Market Explorer & Data Hygiene (30 Seconds)

1. **Navigate to `Market Dashboard`** (Page 1):
   - Select ticker `AAPL` (or type any valid US equity ticker like `MSFT` or `SPY`).
   - Pick date range (e.g. 1 Year).
   - Click **Fetch Market Data**.
2. **Talking Points:**
   - *"The data ingestion layer enforces a strict canonical schema: open, high, low, close, volume with positive price validation and monotonic chronological indexing."*
   - *"If the user has no internet access or Yahoo Finance rate-limits the client, TradeLab seamlessly falls back to a deterministic 252-bar Geometric Brownian Motion (GBM) fixture without crashing."*
   - *"The chart displays a dual-pane Plotly interactive candlestick and volume series with configurable Fast/Slow SMA overlays."*

---

## Act 2: Backtest Lab & Zero Lookahead Simulator (45 Seconds)

1. **Navigate to `Backtest Lab`** (Page 2):
   - Set Strategy Parameters: Fast SMA `10`, Slow SMA `30`.
   - Initial Capital: `$10,000`. Slippage: `5 bps` (0.05%). Commission: `$1.00/trade`.
   - Click **Run Backtest**.
2. **Talking Points:**
   - *"Notice the execution model: at bar $t$, the SMA crossover is evaluated solely using closed bars. If a golden cross occurs, an order is staged and executes at the next bar's Open price ($t+1$)."*
   - *"Slippage is modeled adversely: BUY orders fill at $\text{Open} \times (1 + \text{slippage})$, while SELL orders fill at $\text{Open} \times (1 - \text{slippage})$, plus fixed commission."*
   - *"Portfolio invariants are tracked on every bar: $\text{Cash} + \text{Position Value} \equiv \text{Equity}$. No margin borrowing or fractional share shorting is permitted."*
3. **Review Results & Analytics:**
   - Point out KPI Cards: **Total Return**, **CAGR**, **Sharpe Ratio**, **Max Drawdown**, **Win Rate**, and **Profit Factor**.
   - Review the **Equity Curve vs Buy-and-Hold Benchmark** chart and the **Underwater Drawdown** chart.
   - Expand the **Trade Log (Round-Trips)** table showing entry/exit dates, prices, holding duration, and realized P&L.
   - Click **Save Run to Database** to persist the execution run and fills into SQLite.
   - Click **Download Trades (CSV)** to show data export readiness.

---

## Act 3: Persistent Trade History & Auditing (20 Seconds)

1. **Navigate to `Trade History`** (Page 4):
   - Show the interactive table listing all historical backtests with their timestamps, symbols, Sharpe ratios, and total returns.
   - Select a saved run from the dropdown.
   - View its complete parameter snapshot and full ledger of executed fills (`BUY`/`SELL`, execution timestamp, price, fee, slippage).
   - Demonstrate the **Delete Run** button, showing foreign-key cascade deletion in action.

---

## Act 4: Paper Trading Sandbox & Execution Bot (45 Seconds)

1. **Navigate to `Paper Trading`** (Page 3):
2. **Highlight Safety Rails:**
   - Point to the header badge: `"Paper Trading Sandbox Only"`.
   - *"Our broker interface contains hardcoded assertions that reject any URL pointing to `api.alpaca.markets`. Only `paper-api.alpaca.markets` or our offline `MockPaperBroker` can ever be instantiated."*
3. **Manual Order Execution with Pre-Trade Risk Checks:**
   - Switch to `Mock Broker (Offline Demo)` or `Alpaca Paper Sandbox`.
   - Try placing a BUY order for 10 shares of `AAPL`.
   - Explain the risk filters:
     - Minimum cash check (order value + cushion must not exceed buying power).
     - Maximum notional order cap ($50,000 per order).
     - Allowed symbols whitelist / valid order sizes.
4. **Single-Cycle Bot Execution & Idempotency:**
   - Set Fast SMA `5`, Slow SMA `15`.
   - Click **Run Single Bot Cycle**.
   - Point out the execution log: the bot fetches recent market bars, computes the signal on the latest completed bar, formats a deterministic `client_order_id`, and executes if necessary.
   - Click **Run Single Bot Cycle** a second time immediately.
   - Show the result: `IDEMPOTENT_SKIP`—*"The bot recognizes that an order was already dispatched for this bar, preventing duplicate fills or race conditions."*
5. **Emergency Kill Switch:**
   - Point out the red **Kill Switch / Panic Liquidate** button.
   - Click the button to cancel all working orders, liquidate existing positions, and latch the bot into a paused state.

---

## Act 5: System Health & Diagnostics (15 Seconds)

1. **Navigate to `System Settings`** (Page 5):
   - View runtime configuration, Alpaca credential status, database connection path, and table row counts.
   - Click **Test Database Connection** and **Vacuum Database** to demonstrate system maintenance utilities.

---

## Offline Smoke Test Verification (Bonus Terminal Demo)

Run in terminal:
```bash
python scripts/smoke_test.py
```
Outputs 8 clean offline subsystem checks:
```text
[1/8] Verifying Settings & Paper Safety Guards... ✅ OK
[2/8] Verifying Market Data Pipeline & Fixtures... ✅ OK
[3/8] Verifying Strategy & Backtest Simulator... ✅ OK
[4/8] Verifying Benchmark & Metric Calculations... ✅ OK
[5/8] Verifying SQLite Persistence & Foreign Keys... ✅ OK
[6/8] Verifying Mock Paper Broker & Risk Checks... ✅ OK
[7/8] Verifying Bot Controller & Idempotency Guard... ✅ OK
[8/8] Verifying Streamlit Multi-Page Scripts... ✅ OK
🎉 ALL 8 TRADELAB SUBSYSTEMS PASSED OFFLINE SMOKE TEST!
```
