"""Deterministic offline mock paper broker implementation."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List

from tradelab.brokers.base import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    MarketClock,
    PaperBroker,
)
from tradelab.exceptions import BrokerError
from tradelab.models import OrderSide, OrderStatus


class MockPaperBroker(PaperBroker):
    """In-memory mock paper broker for offline testing and demonstration."""

    def __init__(self, initial_cash: float = 100000.0):
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.positions: Dict[str, BrokerPosition] = {}
        self.orders: Dict[str, BrokerOrder] = {}  # keyed by broker_order_id
        self.client_id_map: Dict[str, str] = {}  # client_order_id -> broker_order_id

    @property
    def name(self) -> str:
        return "mock_paper"

    def get_account(self) -> BrokerAccount:
        total_market_value = sum(p.market_value for p in self.positions.values())
        equity = self.cash + total_market_value
        return BrokerAccount(
            account_id="MOCK-PAPER-ACC-001",
            status="ACTIVE",
            currency="USD",
            equity=equity,
            cash=self.cash,
            buying_power=self.cash,
            is_paper=True,
        )

    def get_positions(self) -> List[BrokerPosition]:
        return list(self.positions.values())

    def get_orders(self, limit: int = 50) -> List[BrokerOrder]:
        sorted_orders = sorted(self.orders.values(), key=lambda o: o.submitted_at, reverse=True)
        return sorted_orders[:limit]

    def get_clock(self) -> MarketClock:
        now = datetime.now(timezone.utc)
        return MarketClock(
            is_open=True,
            next_open=now,
            next_close=now,
        )

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        client_order_id: str,
    ) -> BrokerOrder:
        symbol = symbol.upper()
        # Idempotency check: if client_order_id was already submitted, return the existing order
        if client_order_id in self.client_id_map:
            existing_id = self.client_id_map[client_order_id]
            return self.orders[existing_id]

        if quantity <= 0:
            raise BrokerError(f"Order quantity must be positive, got {quantity}.")

        # Simulated execution price: use existing position price or $150 default
        sim_price = 150.0
        if symbol in self.positions:
            sim_price = self.positions[symbol].current_price

        now = datetime.now(timezone.utc)
        broker_order_id = f"MOCK-{uuid.uuid4().hex[:12]}"

        if side == OrderSide.BUY:
            cost = quantity * sim_price
            if cost > self.cash:
                raise BrokerError(
                    f"Insufficient buying power: order requires ${cost:,.2f}, but cash is ${self.cash:,.2f}."
                )
            self.cash -= cost

            # Update position
            existing = self.positions.get(symbol)
            new_qty = (existing.quantity + quantity) if existing else quantity
            new_cost_basis = (
                ((existing.cost_basis * existing.quantity) + cost) / new_qty
                if existing
                else sim_price
            )
            new_mkt_val = new_qty * sim_price

            self.positions[symbol] = BrokerPosition(
                symbol=symbol,
                quantity=new_qty,
                market_value=new_mkt_val,
                cost_basis=new_cost_basis,
                current_price=sim_price,
                unrealized_pl=new_mkt_val - (new_qty * new_cost_basis),
                unrealized_plpc=0.0,
            )

        elif side == OrderSide.SELL:
            existing = self.positions.get(symbol)
            if not existing or existing.quantity < quantity:
                held = existing.quantity if existing else 0
                raise BrokerError(
                    f"Insufficient position: attempted to sell {quantity} shares of {symbol}, but only holding {held}."
                )

            proceeds = quantity * sim_price
            self.cash += proceeds
            remaining_qty = existing.quantity - quantity

            if remaining_qty <= 0:
                del self.positions[symbol]
            else:
                mkt_val = remaining_qty * sim_price
                self.positions[symbol] = BrokerPosition(
                    symbol=symbol,
                    quantity=remaining_qty,
                    market_value=mkt_val,
                    cost_basis=existing.cost_basis,
                    current_price=sim_price,
                    unrealized_pl=mkt_val - (remaining_qty * existing.cost_basis),
                    unrealized_plpc=0.0,
                )

        order = BrokerOrder(
            broker_order_id=broker_order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            status=OrderStatus.FILLED,
            filled_qty=quantity,
            filled_avg_price=sim_price,
            submitted_at=now,
            updated_at=now,
        )

        self.orders[broker_order_id] = order
        self.client_id_map[client_order_id] = broker_order_id
        return order

    def cancel_order(self, broker_order_id: str) -> bool:
        if broker_order_id in self.orders:
            old = self.orders[broker_order_id]
            self.orders[broker_order_id] = BrokerOrder(
                broker_order_id=old.broker_order_id,
                client_order_id=old.client_order_id,
                symbol=old.symbol,
                side=old.side,
                quantity=old.quantity,
                status=OrderStatus.CANCELED,
                filled_qty=old.filled_qty,
                filled_avg_price=old.filled_avg_price,
                submitted_at=old.submitted_at,
                updated_at=datetime.now(timezone.utc),
            )
            return True
        return False
