"""Safe trading bot controller and execution risk gates."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd

from tradelab.brokers.base import BrokerOrder
from tradelab.exceptions import RiskLimitViolationError
from tradelab.models import OrderSide
from tradelab.services.paper_service import PaperTradingService
from tradelab.storage.db import get_session
from tradelab.storage.tables import BotEventRecord, PaperOrderRecord
from tradelab.strategies.base import SignalType
from tradelab.strategies.sma_crossover import SMACrossoverConfig, SMACrossoverStrategy


@dataclass
class BotConfig:
    """Safety and risk configuration for paper bot cycles."""

    symbol: str = "AAPL"
    fast_window: int = 20
    slow_window: int = 50
    max_allocation_usd: float = 10000.0
    max_order_qty: float = 100.0
    max_orders_per_day: int = 5
    is_enabled: bool = False
    kill_switch_active: bool = False


@dataclass
class BotCycleResult:
    """Audit log of a completed bot cycle."""

    timestamp: datetime
    symbol: str
    action_taken: str
    signal_detected: str
    order: Optional[BrokerOrder] = None
    messages: List[str] = field(default_factory=list)
    success: bool = True


class BotController:
    """Controls strategy evaluation, risk limits, and single-cycle execution."""

    def __init__(
        self,
        paper_service: Optional[PaperTradingService] = None,
        config: Optional[BotConfig] = None,
        database_url: Optional[str] = None,
    ):
        self.paper_service = paper_service or PaperTradingService(database_url=database_url)
        self.config = config or BotConfig()
        self.database_url = database_url

    def log_bot_event(self, event_type: str, details: dict) -> None:
        """Persist bot audit event into SQLite."""
        with get_session(self.database_url) as session:
            try:
                record = BotEventRecord(
                    timestamp_utc=datetime.now(timezone.utc),
                    symbol=self.config.symbol,
                    event_type=event_type,
                    details_json=json.dumps(details),
                )
                session.add(record)
                session.commit()
            except Exception:
                session.rollback()

    def run_cycle(
        self,
        candles: pd.DataFrame,
        dry_run: bool = False,
    ) -> BotCycleResult:
        """Execute one discrete, idempotent bot decision cycle on completed market bars."""
        now = datetime.now(timezone.utc)

        # 1. Kill Switch Check
        if self.config.kill_switch_active:
            msg = "🛑 EMERGENCY KILL SWITCH IS ACTIVE. Bot execution halted."
            self.log_bot_event("KILL_SWITCH_ACTIVE", {"message": msg})
            return BotCycleResult(
                timestamp=now,
                symbol=self.config.symbol,
                action_taken="HALTED",
                signal_detected="NONE",
                messages=[msg],
                success=False,
            )

        # 2. Enabled Check
        if not self.config.is_enabled and not dry_run:
            msg = "Bot is currently disabled. Enable bot or run with dry_run=True."
            return BotCycleResult(
                timestamp=now,
                symbol=self.config.symbol,
                action_taken="SKIPPED",
                signal_detected="NONE",
                messages=[msg],
                success=True,
            )

        # 3. Strategy Signal from Completed Bars
        strategy = SMACrossoverStrategy(
            SMACrossoverConfig(
                fast_window=self.config.fast_window,
                slow_window=self.config.slow_window,
            )
        )
        signals_df = strategy.generate_signals(candles)
        last_signal = int(signals_df["Signal"].iloc[-1])
        last_date_str = candles.index[-1].strftime("%Y%m%d")
        current_price = float(candles["Close"].iloc[-1])

        signal_name = "HOLD"
        side: Optional[OrderSide] = None
        if last_signal == int(SignalType.BUY):
            signal_name = "BUY"
            side = OrderSide.BUY
        elif last_signal == int(SignalType.SELL):
            signal_name = "SELL"
            side = OrderSide.SELL

        if side is None:
            msg = f"No actionable crossover signal on bar {last_date_str} (Signal: HOLD)."
            self.log_bot_event("NO_SIGNAL", {"last_date": last_date_str})
            return BotCycleResult(
                timestamp=now,
                symbol=self.config.symbol,
                action_taken="HOLD",
                signal_detected=signal_name,
                messages=[msg],
                success=True,
            )

        # 4. Idempotency Check for this signal bar
        client_order_id = f"BOT-{self.config.symbol}-{last_date_str}-{side.value}"
        with get_session(self.database_url) as session:
            existing_order = (
                session.query(PaperOrderRecord).filter_by(client_order_id=client_order_id).first()
            )
            if existing_order:
                msg = f"Idempotency Guard: Order '{client_order_id}' was already executed. Skipping duplicate."
                self.log_bot_event("IDEMPOTENCY_SKIP", {"client_order_id": client_order_id})
                return BotCycleResult(
                    timestamp=now,
                    symbol=self.config.symbol,
                    action_taken="IDEMPOTENT_SKIP",
                    signal_detected=signal_name,
                    messages=[msg],
                    success=True,
                )

        # 5. Check Current Position
        positions = {p.symbol: p for p in self.paper_service.get_positions()}
        holding = positions.get(self.config.symbol)
        held_qty = holding.quantity if holding else 0.0

        if side == OrderSide.BUY and held_qty > 0:
            msg = f"BUY signal generated, but already holding {held_qty} shares of {self.config.symbol}. Ignoring."
            return BotCycleResult(
                timestamp=now,
                symbol=self.config.symbol,
                action_taken="SKIPPED",
                signal_detected=signal_name,
                messages=[msg],
                success=True,
            )

        if side == OrderSide.SELL and held_qty <= 0:
            msg = f"SELL signal generated, but position is already flat for {self.config.symbol}. Ignoring."
            return BotCycleResult(
                timestamp=now,
                symbol=self.config.symbol,
                action_taken="SKIPPED",
                signal_detected=signal_name,
                messages=[msg],
                success=True,
            )

        # 6. Position Sizing & Risk Controls
        if side == OrderSide.BUY:
            account = self.paper_service.get_account()
            target_capital = min(self.config.max_allocation_usd, account.buying_power)
            calculated_qty = int(target_capital // current_price)
            order_qty = min(calculated_qty, self.config.max_order_qty)
        else:
            order_qty = held_qty

        if order_qty <= 0:
            msg = f"Order quantity calculated to 0 (insufficient capital for 1 share @ ${current_price:,.2f})."
            return BotCycleResult(
                timestamp=now,
                symbol=self.config.symbol,
                action_taken="SKIPPED",
                signal_detected=signal_name,
                messages=[msg],
                success=False,
            )

        # 7. Dry-Run or Execution
        if dry_run:
            msg = (
                f"[DRY RUN] Would submit {side.value} order for {order_qty} shares of "
                f"{self.config.symbol} @ ~${current_price:,.2f}."
            )
            self.log_bot_event("DRY_RUN_EVALUATED", {"qty": order_qty, "side": side.value})
            return BotCycleResult(
                timestamp=now,
                symbol=self.config.symbol,
                action_taken=f"DRY_RUN_{side.value}",
                signal_detected=signal_name,
                messages=[msg],
                success=True,
            )

        # Submit paper order
        try:
            submitted_order = self.paper_service.submit_paper_order(
                symbol=self.config.symbol,
                side=side,
                quantity=float(order_qty),
                current_price=current_price,
                confirmed=True,
                client_order_id=client_order_id,
            )
            msg = f"Successfully submitted {side.value} paper order ({submitted_order.broker_order_id}) for {order_qty} shares."
            self.log_bot_event(
                "ORDER_SUBMITTED",
                {
                    "broker_order_id": submitted_order.broker_order_id,
                    "qty": order_qty,
                    "side": side.value,
                },
            )
            return BotCycleResult(
                timestamp=now,
                symbol=self.config.symbol,
                action_taken=f"EXECUTED_{side.value}",
                signal_detected=signal_name,
                order=submitted_order,
                messages=[msg],
                success=True,
            )
        except (RiskLimitViolationError, Exception) as e:
            err_msg = f"Order execution failed: {e}"
            self.log_bot_event("ORDER_FAILED", {"error": str(e)})
            return BotCycleResult(
                timestamp=now,
                symbol=self.config.symbol,
                action_taken="FAILED",
                signal_detected=signal_name,
                messages=[err_msg],
                success=False,
            )
