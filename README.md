# TradeLab 📈

> **Algorithmic Trading & Paper Trading Workbench**  
> An interactive Python algorithmic trading workbench built with Streamlit, Pandas, Plotly, SQLAlchemy, and Alpaca Paper Trading. Engineered with strict zero lookahead bias, adverse execution modeling, and non-bypassable safety controls. Inspired by [Berk-Unsal/Python-Algorithmic-Trading-Bot](https://github.com/Berk-Unsal/Python-Algorithmic-Trading-Bot).

[![CI](https://github.com/HarshKumarSahni/TradeLab/actions/workflows/ci.yml/badge.svg)](https://github.com/HarshKumarSahni/TradeLab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## 🚀 Overview

TradeLab is a modular, transparent algorithmic trading and simulation platform designed for quantitative researchers, software engineers, and learners. It provides an institutional-grade, zero-credential-capable environment that allows you to:

1. **Explore Historical Market Data:** Visualize interactive daily candlestick charts and volume trends for US equities and ETFs with automatic synthetic Geometric Brownian Motion (GBM) fallback when offline.
2. **Backtest Strategies Without Lookahead Bias:** Test Simple Moving Average (SMA) crossover strategies where signals generated at bar $t$ close are strictly executed at bar $t+1$ Open with adverse slippage and transaction costs.
3. **Analyze Quantitative Performance:** Review equity curves, underwater drawdown charts, Sharpe ratio, CAGR, win rate, and round-trip trade logs benchmarked against Buy-and-Hold.
4. **Audit Runs with SQLite Persistence:** Persist runs and execution fills to local SQLite tables with schema-enforced foreign key cascade deletion and CSV export.
5. **Practice Safe Paper Trading:** Connect to Alpaca's paper trading sandbox or the offline `MockPaperBroker` with hardcoded safety rails to ensure live real-money execution is impossible.
6. **Automate with Safe Bot Controls:** Run single-cycle bot iterations with pre-trade buying power validation, allocation limits, rerun idempotency, and a 1-click emergency liquidation kill switch.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.11+ (tested on 3.12) | Core runtime |
| **User Interface** | Streamlit | Python-native reactive multipage dashboard |
| **Data & Computing** | Pandas, NumPy | Canonical OHLCV schema, indicator calculations, ledger simulation |
| **Visualization** | Plotly | Dual-pane candlesticks, volume subplots, benchmark equity curves |
| **Market Data** | yfinance & Offline Fixtures | Live Yahoo Finance historical adapter + deterministic GBM fixture fallback |
| **Broker Integration** | alpaca-py & MockPaperBroker | Official Alpaca paper trading SDK (sandbox only) + 100% offline mock broker |
| **Persistence** | SQLite & SQLAlchemy | Local auditable storage for runs, fills, and bot audit logs |
| **Configuration** | pydantic-settings | Typed environment variables and secret masking |
| **Testing & Linting** | pytest, pytest-mock, ruff | Deterministic unit tests (62 tests), CI workflow, and code formatting |

---

## 🏛️ Application Architecture

```text
Streamlit Multipage UI
  ├── App Home (app.py)
  ├── 1. Market Dashboard (pages/1_Market_Dashboard.py)
  ├── 2. Backtest Lab (pages/2_Backtest_Lab.py)
  ├── 3. Paper Trading (pages/3_Paper_Trading.py)
  ├── 4. Trade History (pages/4_Trade_History.py)
  └── 5. Settings & About (pages/5_Settings_About.py)
         │
         ▼
Application Services (tradelab/services/)
  ├── MarketDataService   ──> Yahoo / Offline Fixtures (tradelab/data/)
  ├── BacktestService     ──> Event-Driven Engine (tradelab/backtesting/)
  ├── PaperTradingService ──> Alpaca Paper / Mock Broker (tradelab/brokers/)
  ├── BotController       ──> Idempotent Single-Cycle Runner (tradelab/services/)
  └── BacktestRepository  ──> SQLite Storage & Cascade Fills (tradelab/storage/)
```

---

## ⚡ Quickstart & Installation

### Windows (PowerShell)
```powershell
# 1. Clone repository
git clone https://github.com/HarshKumarSahni/TradeLab.git
cd TradeLab

# 2. Create virtual environment (Python 3.11 or 3.12)
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies in editable mode
python -m pip install -e ".[dev]"

# 4. Copy environment configuration template
Copy-Item .env.example .env

# 5. Launch TradeLab
streamlit run app.py
```

### macOS / Linux (Bash / Zsh)
```bash
# 1. Clone repository
git clone https://github.com/HarshKumarSahni/TradeLab.git
cd TradeLab

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Copy environment configuration template
cp .env.example .env

# 5. Launch TradeLab
streamlit run app.py
```

---

## 🧪 Verification & Smoke Testing

### Offline Subsystem Smoke Test
TradeLab includes a zero-dependency offline smoke test that verifies all 8 core subsystems (Configuration, Market Pipeline, Simulator, Invariants, Benchmark, SQLite, Mock Broker, and Streamlit shells) in ~1 second:

```bash
python scripts/smoke_test.py
```

### Running the Pytest Suite
```bash
# Run all 62 unit & integration tests
pytest -v

# Run code linter & formatting check
ruff check .
ruff format --check .
```

---

## 🎙️ Interview Walkthrough Demo Script

For technical interviews, portfolio demonstrations, or video walkthroughs, consult the complete 2-3 minute guided script:
📄 **[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)**

### Key Highlights to Demonstrate
1. **Zero Lookahead Bias:** Clear separation between signal calculation at bar $t$ close and execution at bar $t+1$ Open.
2. **Adverse Execution Modeling:** BUY fills at $\text{Open} \times (1 + \text{slippage})$; SELL fills at $\text{Open} \times (1 - \text{slippage})$.
3. **Accounting Invariants:** Strictly tracks $\text{Cash} + \text{Position Value} \equiv \text{Equity}$ with zero fractional shorting or uncollateralized leverage.
4. **Alpaca Sandbox & Mock Broker:** Guaranteed paper-only execution with hardcoded URL safeguards rejecting live Alpaca credentials.
5. **Idempotent Bot Cycles:** Re-evaluating the strategy within the same bar window produces `IDEMPOTENT_SKIP` with zero duplicate orders.
6. **Emergency Kill Switch:** 1-click panic button that cancels all open orders and liquidates open positions.

---

## ⚙️ Configuration (`.env`)

TradeLab is preconfigured to run immediately in **Offline / Demo Mode** without requiring any API keys.

To enable optional Alpaca paper trading:
1. Register for a free paper trading account at [Alpaca Markets](https://alpaca.markets).
2. Generate API Keys from your Paper Trading Dashboard.
3. Configure your local `.env` file:
```dotenv
APP_MODE=demo
MARKET_DATA_PROVIDER=yahoo
ALPACA_API_KEY=your_alpaca_paper_key
ALPACA_SECRET_KEY=your_alpaca_paper_secret
ALPACA_PAPER=true
DATABASE_URL=sqlite:///tradelab.db
LOG_LEVEL=INFO
```

> ⚠️ **Safety Enforcement:** `ALPACA_PAPER` is strictly required to be `true`. TradeLab code prevents connection to live trading endpoints (`api.alpaca.markets`) to eliminate any risk of real-money loss.

---

## 📖 Key Backtesting Assumptions

For complete algorithmic formulation and mathematical proofs, see **[docs/BACKTEST_ASSUMPTIONS.md](docs/BACKTEST_ASSUMPTIONS.md)**:

1. **No Lookahead Bias:** Indicators calculated on bar $t$'s close execute strictly at the open of bar $t+1$.
2. **Transaction Costs:** Configurable per-trade fees and adverse execution slippage (default 5 bps = 0.05% per trade side).
3. **Cash Invariance:** Capital must remain $\ge 0$ at all times; no margin or shorting in the MVP.
4. **Mark-to-Market:** Open positions at the end of the backtest period are marked to market on the final close and clearly labeled.

---

## ⚖️ Legal & Regulatory Disclosures

TradeLab is built solely for educational, research, and portfolio demonstration purposes. It does not provide investment advice or financial recommendations. Past hypothetical or paper performance does not guarantee future results.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Attribution & Acknowledgements

Inspired by the conceptual architecture of [Berk-Unsal/Python-Algorithmic-Trading-Bot](https://github.com/Berk-Unsal/Python-Algorithmic-Trading-Bot), rebuilt from the ground up with Streamlit, Plotly, deterministic backtesting invariants, and modern `alpaca-py` paper integration.
