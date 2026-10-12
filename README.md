# TradeLab 📈

> **Algorithmic Trading & Paper Trading Dashboard**  
> An interactive Python algorithmic trading workbench built with Streamlit, Pandas, Plotly, and Alpaca Paper Trading. Inspired by [Berk-Unsal/Python-Algorithmic-Trading-Bot](https://github.com/Berk-Unsal/Python-Algorithmic-Trading-Bot).

---

## 🚀 Overview

TradeLab is a modular, transparent algorithmic trading and simulation platform designed for learners, developers, and researchers. It allows users to:
1. **Explore Historical Market Data:** Visualize interactive daily candlestick charts and volume trends for US equities and ETFs.
2. **Backtest Strategies Without Lookahead Bias:** Test Simple Moving Average (SMA) crossover strategies where trades are strictly filled on the next bar's open, with configurable slippage and fees.
3. **Analyze Performance:** Review equity curves, drawdown series, Sharpe ratio, win rate, and benchmark comparisons.
4. **Practice Safe Paper Trading:** Connect to Alpaca's paper trading sandbox for real-time portfolio tracking and order preview with strict safety gates (no live capital risk).

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.11+ (tested on 3.12) | Core runtime |
| **User Interface** | Streamlit | Python-native reactive multipage dashboard |
| **Data & Computing** | Pandas, NumPy | OHLCV processing, indicator calculations, ledger simulation |
| **Visualization** | Plotly | Interactive candlesticks, volume subplots, equity curves |
| **Market Data** | yfinance & Offline Fixtures | Zero-credential default historical price feeds |
| **Broker Integration** | alpaca-py | Official Alpaca paper trading SDK (sandbox only) |
| **Persistence** | SQLite & SQLAlchemy | Local auditable storage for runs, trades, and logs |
| **Configuration** | pydantic-settings | Typed environment variables and secret masking |
| **Testing & Linting** | pytest, pytest-mock, ruff | Deterministic unit tests and code formatting |

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
         │
         ├── MarketDataService ──> Yahoo / Offline Fixtures (tradelab/data/)
         ├── StrategyService   ──> SMA Crossover (tradelab/strategies/)
         ├── BacktestEngine    ──> Next-bar open simulator (tradelab/backtesting/)
         ├── PaperTradingService ──> Alpaca Paper Broker (tradelab/brokers/)
         └── Storage           ──> SQLite (tradelab/storage/)
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

> ⚠️ **Safety Enforcement:** `ALPACA_PAPER` is strictly required to be `true`. TradeLab code prevents connection to live trading endpoints to eliminate any risk of real-money loss.

---

## 🧪 Running Tests & Quality Checks

Run the automated test suite and linter:
```bash
# Run unit tests
pytest -v

# Run linter
ruff check .

# Check formatting
ruff format --check .
```

---

## 📖 Key Backtesting Assumptions

1. **No Lookahead Bias:** Indicators calculated on bar $t$'s close execute at the open of bar $t+1$.
2. **Transaction Costs:** Configurable per-trade fees and adverse execution slippage (default 5 bps = 0.05% per trade side).
3. **Cash Invariance:** Capital must remain $\ge 0$ at all times; no margin or shorting in the MVP.
4. **Mark-to-Market:** Open positions at the end of the data are marked to market on the final close and clearly labeled.

---

## ⚖️ Legal & Regulatory Disclosures

TradeLab is built solely for educational, research, and portfolio demonstration purposes. It does not provide investment advice or financial recommendations. Past hypothetical or paper performance does not guarantee future results.

## 🤝 Attribution & Acknowledgements

Inspired by the conceptual architecture of [Berk-Unsal/Python-Algorithmic-Trading-Bot](https://github.com/Berk-Unsal/Python-Algorithmic-Trading-Bot), rebuilt from the ground up with Streamlit, Plotly, deterministic backtesting invariants, and modern `alpaca-py` paper integration.
