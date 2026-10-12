"""Paper trading service managing account telemetry, preview, and safe order execution."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from tradelab.brokers.alpaca_paper import AlpacaPaperBroker
from tradelab.brokers.base import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    MarketClock,
    PaperBroker,
)
from tradelab.brokers.mock_broker import MockPaperBroker
from tradelab.config import Settings, get_settings
from tradelab.data.validation import validate_symbol
from tradelab.exceptions import RiskLimitViolationError
from tradelab.models import OrderSide
from tradelab.storage.db import get_session
from tradelab.storage.tables import PaperOrderRecord


@dataclass(frozen=True)
class OrderPreview:
    """Pre-trade order preview details and safety checks."""

    symbol: str
    side: OrderSide
    quantity: float
    estimated_price: float
    estimated_cost: float
    is_safe: bool
    warnings: List[str]
    proposed_client_order_id: str


class PaperTradingService:
    """Service orchestrating paper broker interactions, pre-trade gates, and audit trails."""

    def __init__(
        self,
        broker: Optional[PaperBroker] = None,
        settings: Optional[Settings] = None,
        database_url: Optional[str] = None,
    ):
        self.settings = settings or get_settings()
        self.database_url = database_url

        if broker is not None:
            self._broker = broker
        elif self.settings.has_alpaca_credentials and self.settings.app_mode == "paper":
            self._broker = AlpacaPaperBroker(self.settings)
        else:
            self._broker = MockPaperBroker()

    @property
    def broker(self) -> PaperBroker:
        return self._broker

    def get_account(self) -> BrokerAccount:
        """Retrieve current broker balance and buying power."""
        return self._broker.get_account()

    def get_positions(self) -> List[BrokerPosition]:
        """Retrieve all currently held open positions."""
        return self._broker.get_positions()

    def get_orders(self, limit: int = 50) -> List[BrokerOrder]:
        """Retrieve recent paper orders."""
        return self._broker.get_orders(limit=limit)

    def get_clock(self) -> MarketClock:
        """Retrieve current market status."""
        return self._broker.get_clock()

    def generate_client_order_id(self, symbol: str, side: OrderSide, date_str: str) -> str:
        """Deterministic client order ID to prevent duplicate executions."""
        return f"TL-{symbol.upper()}-{date_str}-{side.value}"

    def preview_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        current_price: float,
        date_str: Optional[str] = None,
        client_order_id: Optional[str] = None,
    ) -> OrderPreview:
        """Perform pre-trade risk analysis and preview the proposed paper order."""
        symbol = validate_symbol(symbol)
        date_key = date_str or datetime.now(timezone.utc).strftime("%Y%m%d")
        effective_client_id = client_order_id or self.generate_client_order_id(
            symbol, side, date_key
        )

        warnings: List[str] = []
        is_safe = True

        if quantity <= 0:
            warnings.append(f"Quantity must be greater than zero, got {quantity}.")
            is_safe = False

        account = self.get_account()
        estimated_cost = quantity * current_price

        # Check existing positions
        positions = {p.symbol: p for p in self.get_positions()}
        holding = positions.get(symbol)

        if side == OrderSide.BUY:
            if estimated_cost > account.buying_power:
                warnings.append(
                    f"Insufficient buying power: requires ${estimated_cost:,.2f}, "
                    f"but buying power is ${account.buying_power:,.2f}."
                )
                is_safe = False
        elif side == OrderSide.SELL:
            held_qty = holding.quantity if holding else 0.0
            if held_qty < quantity:
                warnings.append(
                    f"Insufficient shares to sell: requested {quantity:,.0f}, but holding {held_qty:,.0f}."
                )
                is_safe = False

        # Idempotency check: check if client_order_id was already submitted locally
        with get_session(self.database_url) as session:
            existing = (
                session.query(PaperOrderRecord)
                .filter_by(client_order_id=effective_client_id)
                .first()
            )
            if existing:
                warnings.append(
                    f"Order with client_order_id '{effective_client_id}' was already submitted "
                    f"(Status: {existing.status})."
                )
                is_safe = False

        return OrderPreview(
            symbol=symbol,
            side=side,
            quantity=quantity,
            estimated_price=current_price,
            estimated_cost=estimated_cost,
            is_safe=is_safe,
            warnings=warnings,
            proposed_client_order_id=effective_client_id,
        )

    def submit_paper_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        current_price: float,
        confirmed: bool = False,
        client_order_id: Optional[str] = None,
    ) -> BrokerOrder:
        """Submit a paper order with mandatory pre-trade risk verification."""
        if not confirmed:
            raise RiskLimitViolationError(
                "Manual paper orders require explicit user confirmation before submission."
            )

        preview = self.preview_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            current_price=current_price,
            client_order_id=client_order_id,
        )
        if not preview.is_safe:
            raise RiskLimitViolationError(
                f"Order rejected by pre-trade risk gates: {'; '.join(preview.warnings)}"
            )

        client_order_id = preview.proposed_client_order_id

        # Submit to paper broker
        order = self._broker.submit_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            client_order_id=client_order_id,
        )

        # Audit order in database
        with get_session(self.database_url) as session:
            try:
                record = PaperOrderRecord(
                    client_order_id=order.client_order_id,
                    broker_order_id=order.broker_order_id,
                    symbol=order.symbol,
                    side=order.side.value,
                    qty=order.quantity,
                    status=order.status.value,
                    submitted_at_utc=order.submitted_at,
                    last_updated_at_utc=order.updated_at,
                    raw_response_json=json.dumps(
                        {
                            "filled_qty": order.filled_qty,
                            "filled_avg_price": order.filled_avg_price,
                            "broker": self._broker.name,
                        }
                    ),
                )
                session.add(record)
                session.commit()
            except Exception:
                session.rollback()
                # Order was placed with broker; don't mask broker success if local audit fails

        return order
