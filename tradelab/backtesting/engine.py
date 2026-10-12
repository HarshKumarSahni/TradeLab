"""Deterministic event-driven daily-bar backtest simulation engine."""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

import pandas as pd

from tradelab.data.validation import validate_ohlcv_dataframe
from tradelab.exceptions import BacktestError, StrategyError
from tradelab.models import OrderSide, OrderStatus
from tradelab.strategies.base import SignalType, Strategy


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration parameters for execution simulation."""

    initial_cash: float = 10000.0
    fee: float = 0.0  # Flat per-order execution fee in dollars
    slippage_bps: float = 5.0  # Slippage per side in basis points (5 bps = 0.05%)
    allow_fractional: bool = False  # Default: floor to integer shares

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise BacktestError(
                f"Initial cash must be strictly positive, got ${self.initial_cash}."
            )
        if self.fee < 0:
            raise BacktestError(f"Fee cannot be negative, got ${self.fee}.")
        if self.slippage_bps < 0:
            raise BacktestError(
                f"Slippage basis points cannot be negative, got {self.slippage_bps}."
            )


@dataclass(frozen=True)
class Order:
    """Scheduled order generated after bar close."""

    side: OrderSide
    signal_date: date
    status: OrderStatus = OrderStatus.PENDING


@dataclass(frozen=True)
class Fill:
    """Immutable record of an executed trade fill."""

    timestamp: pd.Timestamp
    side: OrderSide
    quantity: float
    fill_price: float
    fee: float
    cash_after: float
    position_after: float


@dataclass
class BacktestResult:
    """Complete results, ledger, fills, and metrics of a backtest run."""

    symbol: str
    config: BacktestConfig
    start_date: date
    end_date: date
    equity_curve: pd.DataFrame
    fills: List[Fill]
    signals_df: pd.DataFrame
    initial_cash: float
    final_cash: float
    final_quantity: float
    final_equity: float
    unrealized_pnl: float
    pending_signal: Optional[OrderSide] = None
    warnings: List[str] = field(default_factory=list)


class BacktestEngine:
    """Simulates trading strategies on daily OHLCV bars with next-bar open execution."""

    @classmethod
    def run(
        cls,
        candles: pd.DataFrame,
        strategy: Strategy,
        config: Optional[BacktestConfig] = None,
        symbol: str = "ASSET",
    ) -> BacktestResult:
        """Run deterministic event-driven simulation.

        Execution Order:
        1. At bar open (t): Fill any order scheduled after previous bar close (t-1).
           Apply slippage: Buy = Open * (1 + slip), Sell = Open * (1 - slip).
        2. At bar close (t): Mark open position to market using Close price;
           record equity snapshot.
        3. From completed bar (t): Evaluate strategy crossover; schedule order
           for execution at next bar's open (t+1).
        4. End of data: Open positions remain open (marked to market);
           unexecuted final signals are marked as pending.
        """
        # Validate data integrity
        candles = validate_ohlcv_dataframe(candles, min_bars=5)

        # Generate strategy signals
        signals_df = strategy.generate_signals(candles)
        if "Signal" not in signals_df.columns:
            raise StrategyError("Strategy signals DataFrame must contain a 'Signal' column.")

        cfg = config or BacktestConfig()
        signals = signals_df["Signal"]
        slippage_factor = cfg.slippage_bps / 10000.0

        cash = float(cfg.initial_cash)
        quantity = 0.0
        pending_order: Optional[Order] = None
        fills: List[Fill] = []
        equity_records = []
        warnings: List[str] = []

        cost_basis = 0.0

        for current_dt, row in candles.iterrows():
            # -------------------------------------------------------------
            # 1. AT BAR OPEN: Execute pending order from previous bar
            # -------------------------------------------------------------
            if pending_order is not None:
                open_price = float(row["Open"])

                if pending_order.side == OrderSide.BUY:
                    fill_price = open_price * (1.0 + slippage_factor)
                    available_cash = cash - cfg.fee

                    if available_cash <= 0:
                        warnings.append(
                            f"Insufficient cash to execute BUY order on {current_dt.date()}: "
                            f"cash ${cash:.2f} <= fee ${cfg.fee:.2f}."
                        )
                    else:
                        if cfg.allow_fractional:
                            shares = available_cash / fill_price
                        else:
                            shares = float(int(available_cash // fill_price))

                        if shares <= 0:
                            warnings.append(
                                f"Insufficient cash for whole share BUY on {current_dt.date()}: "
                                f"execution price ${fill_price:.2f}, available ${available_cash:.2f}."
                            )
                        else:
                            cost = (shares * fill_price) + cfg.fee
                            cash -= cost
                            quantity += shares
                            cost_basis = fill_price

                            fill = Fill(
                                timestamp=current_dt,
                                side=OrderSide.BUY,
                                quantity=shares,
                                fill_price=fill_price,
                                fee=cfg.fee,
                                cash_after=cash,
                                position_after=quantity,
                            )
                            fills.append(fill)

                elif pending_order.side == OrderSide.SELL:
                    fill_price = open_price * (1.0 - slippage_factor)

                    if quantity <= 0:
                        warnings.append(
                            f"Ignored SELL order on {current_dt.date()}: position already flat."
                        )
                    else:
                        proceeds = (quantity * fill_price) - cfg.fee
                        cash += proceeds
                        sold_qty = quantity
                        quantity = 0.0
                        cost_basis = 0.0

                        fill = Fill(
                            timestamp=current_dt,
                            side=OrderSide.SELL,
                            quantity=sold_qty,
                            fill_price=fill_price,
                            fee=cfg.fee,
                            cash_after=cash,
                            position_after=quantity,
                        )
                        fills.append(fill)

                # Pending order consumed
                pending_order = None

            # -------------------------------------------------------------
            # 2. AT BAR CLOSE: Mark to market and enforce state invariants
            # -------------------------------------------------------------
            close_price = float(row["Close"])
            market_val = quantity * close_price
            equity = cash + market_val

            # Accounting invariants check
            if cash < -1e-5:
                raise BacktestError(
                    f"Cash invariant violated: cash is negative (${cash:.4f}) on {current_dt.date()}."
                )
            if quantity < 0:
                raise BacktestError(
                    f"Quantity invariant violated: quantity is negative ({quantity}) on {current_dt.date()}."
                )

            equity_records.append(
                {
                    "Cash": cash,
                    "Quantity": quantity,
                    "Close": close_price,
                    "MarketValue": market_val,
                    "Equity": equity,
                }
            )

            # -------------------------------------------------------------
            # 3. FROM COMPLETED BAR: Evaluate signal for next bar's open
            # -------------------------------------------------------------
            bar_signal = int(signals.loc[current_dt])

            if bar_signal == int(SignalType.BUY):
                if quantity == 0.0:
                    pending_order = Order(
                        side=OrderSide.BUY,
                        signal_date=current_dt.date(),
                        status=OrderStatus.PENDING,
                    )
            elif bar_signal == int(SignalType.SELL):
                if quantity > 0.0:
                    pending_order = Order(
                        side=OrderSide.SELL,
                        signal_date=current_dt.date(),
                        status=OrderStatus.PENDING,
                    )

        equity_df = pd.DataFrame(equity_records, index=candles.index)

        # Final unrealized PnL calculation
        final_close = float(candles["Close"].iloc[-1])
        unrealized_pnl = (quantity * (final_close - cost_basis)) if quantity > 0 else 0.0

        final_equity = float(equity_df["Equity"].iloc[-1])
        pending_signal_side = pending_order.side if pending_order is not None else None

        return BacktestResult(
            symbol=symbol.upper(),
            config=cfg,
            start_date=candles.index[0].date(),
            end_date=candles.index[-1].date(),
            equity_curve=equity_df,
            fills=fills,
            signals_df=signals_df,
            initial_cash=cfg.initial_cash,
            final_cash=cash,
            final_quantity=quantity,
            final_equity=final_equity,
            unrealized_pnl=unrealized_pnl,
            pending_signal=pending_signal_side,
            warnings=warnings,
        )
