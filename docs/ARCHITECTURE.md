# TradeLab Architecture & Data Flow

TradeLab is an interactive Python algorithmic trading workbench and paper trading application built using **Streamlit**.

## 1. System Topology

```text
Streamlit Multipage UI
  ├── App Landing Hub (app.py)
  ├── 1. Market Dashboard (pages/1_Market_Dashboard.py)
  ├── 2. Backtest Lab (pages/2_Backtest_Lab.py)
  ├── 3. Paper Trading Control (pages/3_Paper_Trading.py)
  ├── 4. Trade History & Reports (pages/4_Trade_History.py)
  └── 5. Settings & About (pages/5_Settings_About.py)
         │
         ▼
Application Services (`tradelab/services/`)
  ├── MarketDataService     ──> Fetches, caches, and validates OHLCV bars
  ├── StrategyService       ──> Evaluates indicator signals and crossover events
  ├── BacktestService       ──> Executes simulation engine and persists run results
  ├── PaperTradingService   ──> Manages paper account balance, positions, orders
  └── BotController         ──> Safe scheduler, risk gates, idempotency guards
         │
         ├───────────────────────────────┬───────────────────────────────┐
         ▼                               ▼                               ▼
Domain & Adapters                Broker Adapters                  Persistence
(`tradelab/data/`,               (`tradelab/brokers/`)            (`tradelab/storage/`)
 `tradelab/strategies/`,         ├── AlpacaPaperBroker            └── SQLite / SQLAlchemy
 `tradelab/backtesting/`)        └── MockBroker (Offline)             ├── Backtest runs & fills
 ├── YahooMarketDataProvider                                         ├── Paper orders
 └── SyntheticFixtureProvider                                         └── Audit events
```

## 2. Separation of Concerns

1. **UI Layer (`app.py`, `pages/`, `tradelab/ui/`):**
   - Pure presentation and user interaction.
   - Never directly executes trades, computes moving averages, or manages raw SQL connections.
   - Never exposes secret environment variables.
2. **Service Layer (`tradelab/services/`):**
   - Coordinates workflows and input validation.
   - Enforces business rules and UI-level caching (`st.cache_data`).
3. **Domain Layer (`tradelab/data/`, `tradelab/strategies/`, `tradelab/backtesting/`):**
   - Standalone, deterministic, pure-Python logic.
   - Completely testable in unit test suites without network or Streamlit dependencies.
4. **Broker Layer (`tradelab/brokers/`):**
   - Strictly isolated paper broker interactions using official `alpaca-py`.
   - Rejects live production endpoints.
5. **Storage Layer (`tradelab/storage/`):**
   - Embedded SQLite persistence using SQLAlchemy ORM.

## 3. Execution Invariant: Zero Lookahead Bias

In financial backtesting, lookahead bias occurs when simulated trades execute at the close of bar $t$ using signals derived from that same close.

In TradeLab:
- Indicators and crossover signals for bar $t$ are calculated using the bar's completed `Close` price.
- The order fill is simulated at the **Open price of bar $t+1$**.
- Slippage and fees are applied to the $t+1$ Open price.
- Unfilled signals on the final available bar are recorded as `PENDING`.
