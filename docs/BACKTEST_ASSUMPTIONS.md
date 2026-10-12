# TradeLab Backtesting Engine Assumptions & Methodology

This document outlines the core quantitative and execution assumptions used by TradeLab's event-driven backtesting simulator.

---

## 1. Zero Lookahead Bias (Strict Next-Bar Open Execution)

In historical simulation, a common pitfall is executing a trade at the closing price of day $t$ using an indicator calculated from that same day $t$'s close. In real-world trading, market participants do not know the exact closing price until the trading session has ended.

### Execution Policy
- **Indicator & Signal Evaluation:** Indicators (e.g., Simple Moving Averages) and crossover logic are evaluated using the completed bar's `Close` price at time $t$.
- **Fill Execution:** If a crossover occurs at bar $t$, the order is placed into a pending state and simulated at the **opening price of the subsequent bar $t+1$** (`Open_{t+1}`).
- **Final Bar Signals:** Any signal triggered on the final observation in the dataset remains strictly marked as `PENDING_UNEXECUTED` and is never backfilled.

---

## 2. Adverse Slippage & Transaction Costs

Fills are subject to simulated market friction:
1. **Adverse Slippage:** Configurable in basis points (default $5\text{ bps} = 0.05\%$ per trade side).
   - **Buy Execution Price:**
     $$\text{Fill Price}_{\text{BUY}} = \text{Open}_{t+1} \times (1 + \text{slippage\_factor})$$
   - **Sell Execution Price:**
     $$\text{Fill Price}_{\text{SELL}} = \text{Open}_{t+1} \times (1 - \text{slippage\_factor})$$
2. **Transaction Fees:** Flat dollar fee per trade order (default $\$0.00$, fully configurable). Deducted from cash on both buy entries and sell exits.

---

## 3. Position Sizing & Cash Invariants

- **Long-Only:** TradeLab MVP supports long-only strategies (no short selling, no borrowing, no leverage).
- **Whole Shares Default:** By default, position sizing rounds down to integer whole shares:
  $$\text{Shares} = \left\lfloor \frac{\text{Cash} - \text{Fee}}{\text{Fill Price}_{\text{BUY}}} \right\rfloor$$
- **Capital Solvency:** Cash cannot fall below $\$0.00$. If available capital cannot afford at least one share plus fees, the order is rejected with an auditable warning.
- **Single Active Position:** The strategy only enters if flat, and only exits if holding a position. Duplicate orders are prohibited.

---

## 4. Mark-to-Market Accounting & End-of-Data Invariants

- **Daily Mark-to-Market:** At the close of each day $t$, portfolio equity is calculated as:
  $$\text{Equity}_t = \text{Cash}_t + (\text{Quantity}_t \times \text{Close}_t)$$
- **Accounting Invariant:** $\text{Equity}_t \equiv \text{Cash}_t + \text{Market Value}_t$ holds exactly on every single bar.
- **No Forced Exit:** If an open position exists at the conclusion of the backtest period, the simulator does **not** simulate an artificial sale. It marks the holdings to market on the final close and reports unrealized P&L separately.

---

## 5. Performance Metrics & Benchmark Comparison

### Buy-and-Hold Benchmark
The benchmark allocates the identical initial cash at the first available open bar with matching slippage and fee assumptions, and marks to market across the identical time horizon.

### Metrics Formulas
1. **Total Return:**
   $$\text{Total Return} = \frac{\text{Final Equity}}{\text{Initial Cash}} - 1$$
2. **Alpha:**
   $$\text{Alpha} = \text{Total Return}_{\text{Strategy}} - \text{Total Return}_{\text{Benchmark}}$$
3. **Drawdown Series:**
   $$\text{Drawdown}_t = \frac{\text{Equity}_t}{\max_{0 \le s \le t}(\text{Equity}_s)} - 1$$
   $$\text{Max Drawdown} = \min_{t}(\text{Drawdown}_t)$$
4. **Annualized Volatility:**
   $$\sigma_{\text{ann}} = \sigma(\text{Daily Returns}) \times \sqrt{252}$$
5. **Sharpe Ratio (Risk-Free Rate = 0%):**
   $$\text{Sharpe} = \sqrt{252} \times \frac{\mu(\text{Daily Returns})}{\sigma(\text{Daily Returns})}$$
   *Returns `N/A` if volatility is zero or observations are fewer than 2.*
6. **Win Rate:**
   $$\text{Win Rate} = \frac{\text{Profitable Closed Round Trips}}{\text{Total Closed Round Trips}}$$
   *Returns `N/A` if zero closed trades occurred (never fabricated as 0%).*
