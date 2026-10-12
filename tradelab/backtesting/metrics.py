"""Portfolio analytics, risk metrics, and trade accounting."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from tradelab.backtesting.benchmark import BenchmarkResult
from tradelab.backtesting.engine import BacktestResult
from tradelab.models import OrderSide


@dataclass(frozen=True)
class ClosedTrade:
    """A completed round-trip trade (BUY entry followed by SELL exit)."""

    entry_timestamp: pd.Timestamp
    exit_timestamp: pd.Timestamp
    quantity: float
    entry_price: float
    exit_price: float
    entry_fee: float
    exit_fee: float
    total_fees: float
    net_pnl: float
    return_pct: float
    is_win: bool


@dataclass(frozen=True)
class PerformanceMetrics:
    """Comprehensive performance metrics summary."""

    total_return: float
    benchmark_return: float
    alpha: float
    max_drawdown: float
    annualized_volatility: Optional[float]
    sharpe_ratio: Optional[float]
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Optional[float]
    avg_trade_pnl: Optional[float]
    best_trade_pnl: Optional[float]
    worst_trade_pnl: Optional[float]
    total_fees: float
    exposure_pct: float
    drawdown_series: pd.Series
    closed_trades: List[ClosedTrade]

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a clean serializable dictionary."""
        return {
            "total_return": round(self.total_return, 4),
            "benchmark_return": round(self.benchmark_return, 4),
            "alpha": round(self.alpha, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "annualized_volatility": round(self.annualized_volatility, 4)
            if self.annualized_volatility is not None
            else None,
            "sharpe_ratio": round(self.sharpe_ratio, 4) if self.sharpe_ratio is not None else None,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 4) if self.win_rate is not None else None,
            "avg_trade_pnl": round(self.avg_trade_pnl, 2)
            if self.avg_trade_pnl is not None
            else None,
            "best_trade_pnl": round(self.best_trade_pnl, 2)
            if self.best_trade_pnl is not None
            else None,
            "worst_trade_pnl": round(self.worst_trade_pnl, 2)
            if self.worst_trade_pnl is not None
            else None,
            "total_fees": round(self.total_fees, 2),
            "exposure_pct": round(self.exposure_pct, 2),
        }


def calculate_metrics(
    result: BacktestResult,
    benchmark: BenchmarkResult,
    risk_free_rate: float = 0.0,
) -> PerformanceMetrics:
    """Calculate deterministic performance metrics from backtest results."""
    equity_curve = result.equity_curve["Equity"]
    total_return = (result.final_equity / result.initial_cash) - 1.0
    benchmark_return = benchmark.total_return
    alpha = total_return - benchmark_return

    # Drawdown calculations
    running_max = equity_curve.cummax()
    drawdown_series = (equity_curve / running_max) - 1.0
    max_drawdown = float(drawdown_series.min())

    # Daily returns & volatility
    daily_returns = equity_curve.pct_change().dropna()
    ann_vol: Optional[float] = None
    sharpe: Optional[float] = None

    if len(daily_returns) >= 2:
        std_dev = float(daily_returns.std())
        if std_dev > 1e-8:
            ann_vol = float(std_dev * np.sqrt(252))
            mean_ret = float(daily_returns.mean())
            excess_return = mean_ret - (risk_free_rate / 252.0)
            sharpe = float(np.sqrt(252) * excess_return / std_dev)

    # Market exposure
    holding_days = (result.equity_curve["Quantity"] > 0).sum()
    total_days = len(result.equity_curve)
    exposure_pct = (holding_days / total_days * 100.0) if total_days > 0 else 0.0

    # Total fees paid
    total_fees = sum(fill.fee for fill in result.fills)

    # Round-trip trade pairing
    closed_trades: List[ClosedTrade] = []
    buy_fill = None

    for fill in result.fills:
        if fill.side == OrderSide.BUY:
            buy_fill = fill
        elif fill.side == OrderSide.SELL and buy_fill is not None:
            sell_fill = fill
            entry_cost = (buy_fill.quantity * buy_fill.fill_price) + buy_fill.fee
            exit_proceeds = (sell_fill.quantity * sell_fill.fill_price) - sell_fill.fee
            net_pnl = exit_proceeds - entry_cost
            return_pct = (net_pnl / entry_cost) if entry_cost > 0 else 0.0
            trade_fees = buy_fill.fee + sell_fill.fee

            closed_trades.append(
                ClosedTrade(
                    entry_timestamp=buy_fill.timestamp,
                    exit_timestamp=sell_fill.timestamp,
                    quantity=buy_fill.quantity,
                    entry_price=buy_fill.fill_price,
                    exit_price=sell_fill.fill_price,
                    entry_fee=buy_fill.fee,
                    exit_fee=sell_fill.fee,
                    total_fees=trade_fees,
                    net_pnl=net_pnl,
                    return_pct=return_pct,
                    is_win=net_pnl > 0,
                )
            )
            buy_fill = None

    total_trades = len(closed_trades)
    winning_trades = sum(1 for t in closed_trades if t.is_win)
    losing_trades = total_trades - winning_trades

    win_rate: Optional[float] = None
    avg_trade_pnl: Optional[float] = None
    best_trade_pnl: Optional[float] = None
    worst_trade_pnl: Optional[float] = None

    if total_trades > 0:
        win_rate = winning_trades / total_trades
        pnls = [t.net_pnl for t in closed_trades]
        avg_trade_pnl = float(np.mean(pnls))
        best_trade_pnl = float(np.max(pnls))
        worst_trade_pnl = float(np.min(pnls))

    return PerformanceMetrics(
        total_return=total_return,
        benchmark_return=benchmark_return,
        alpha=alpha,
        max_drawdown=max_drawdown,
        annualized_volatility=ann_vol,
        sharpe_ratio=sharpe,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        avg_trade_pnl=avg_trade_pnl,
        best_trade_pnl=best_trade_pnl,
        worst_trade_pnl=worst_trade_pnl,
        total_fees=total_fees,
        exposure_pct=exposure_pct,
        drawdown_series=drawdown_series,
        closed_trades=closed_trades,
    )
