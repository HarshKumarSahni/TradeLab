"""Alpaca paper trading SDK adapter enforcing paper-only execution."""

from datetime import datetime, timezone
from typing import List, Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide as AlpacaOrderSide
from alpaca.trading.enums import QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest

from tradelab.brokers.base import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    MarketClock,
    PaperBroker,
)
from tradelab.config import Settings, get_settings
from tradelab.exceptions import BrokerError
from tradelab.models import OrderSide, OrderStatus


class AlpacaPaperBroker(PaperBroker):
    """Adapter communicating exclusively with Alpaca Paper Trading endpoint via alpaca-py."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

        if not self.settings.has_alpaca_credentials:
            raise BrokerError(
                "Alpaca API key and Secret key are required to initialize AlpacaPaperBroker."
            )

        if not self.settings.alpaca_paper:
            raise BrokerError(
                "TradeLab strictly enforces simulated paper trading. "
                "ALPACA_PAPER must be True to prevent connection to live production endpoints."
            )

        try:
            self._client = TradingClient(
                api_key=self.settings.alpaca_api_key,
                secret_key=self.settings.alpaca_secret_key,
                paper=True,  # Hardcoded paper endpoint enforcement
            )
        except Exception as e:
            raise BrokerError(f"Failed to initialize Alpaca TradingClient: {e}") from e

    @property
    def name(self) -> str:
        return "alpaca_paper"

    def get_account(self) -> BrokerAccount:
        """Fetch account state from Alpaca paper sandbox."""
        try:
            acc = self._client.get_account()
            return BrokerAccount(
                account_id=str(acc.id),
                status=str(acc.status),
                currency=str(acc.currency),
                equity=float(acc.equity),
                cash=float(acc.cash),
                buying_power=float(acc.buying_power),
                is_paper=True,
            )
        except Exception as e:
            raise BrokerError(f"Failed to retrieve Alpaca paper account: {e}") from e

    def get_positions(self) -> List[BrokerPosition]:
        """Fetch active positions from Alpaca paper sandbox."""
        try:
            alpaca_positions = self._client.get_all_positions()
            results: List[BrokerPosition] = []
            for p in alpaca_positions:
                results.append(
                    BrokerPosition(
                        symbol=str(p.symbol),
                        quantity=float(p.qty),
                        market_value=float(p.market_value),
                        cost_basis=float(p.cost_basis),
                        current_price=float(p.current_price),
                        unrealized_pl=float(p.unrealized_pl),
                        unrealized_plpc=float(p.unrealized_plpc),
                    )
                )
            return results
        except Exception as e:
            raise BrokerError(f"Failed to retrieve Alpaca positions: {e}") from e

    def get_orders(self, limit: int = 50) -> List[BrokerOrder]:
        """Fetch recent paper orders from Alpaca."""
        try:
            req = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit)
            raw_orders = self._client.get_orders(filter=req)
            results: List[BrokerOrder] = []
            for o in raw_orders:
                # Map Alpaca status to domain OrderStatus
                raw_status = str(o.status).upper()
                if "FILLED" in raw_status:
                    status = OrderStatus.FILLED
                elif "CANCELED" in raw_status:
                    status = OrderStatus.CANCELED
                elif "REJECTED" in raw_status:
                    status = OrderStatus.REJECTED
                elif "ACCEPTED" in raw_status or "SUBMITTED" in raw_status:
                    status = OrderStatus.ACCEPTED
                else:
                    status = OrderStatus.PENDING

                side = OrderSide.BUY if str(o.side).upper() == "BUY" else OrderSide.SELL
                filled_price = float(o.filled_avg_price) if o.filled_avg_price else None

                results.append(
                    BrokerOrder(
                        broker_order_id=str(o.id),
                        client_order_id=str(o.client_order_id) if o.client_order_id else str(o.id),
                        symbol=str(o.symbol),
                        side=side,
                        quantity=float(o.qty),
                        status=status,
                        filled_qty=float(o.filled_qty) if o.filled_qty else 0.0,
                        filled_avg_price=filled_price,
                        submitted_at=o.submitted_at or datetime.now(timezone.utc),
                        updated_at=o.updated_at or datetime.now(timezone.utc),
                    )
                )
            return results
        except Exception as e:
            raise BrokerError(f"Failed to retrieve Alpaca orders: {e}") from e

    def get_clock(self) -> MarketClock:
        """Fetch market clock from Alpaca."""
        try:
            clock = self._client.get_clock()
            return MarketClock(
                is_open=bool(clock.is_open),
                next_open=clock.next_open,
                next_close=clock.next_close,
            )
        except Exception as e:
            raise BrokerError(f"Failed to retrieve Alpaca market clock: {e}") from e

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        client_order_id: str,
    ) -> BrokerOrder:
        """Submit a paper market order to Alpaca paper sandbox."""
        if quantity <= 0:
            raise BrokerError(f"Invalid order quantity: {quantity}")

        alpaca_side = AlpacaOrderSide.BUY if side == OrderSide.BUY else AlpacaOrderSide.SELL

        req = MarketOrderRequest(
            symbol=symbol.upper(),
            qty=quantity,
            side=alpaca_side,
            time_in_force=TimeInForce.DAY,
            client_order_id=client_order_id,
        )

        try:
            order_res = self._client.submit_order(order_data=req)
            return BrokerOrder(
                broker_order_id=str(order_res.id),
                client_order_id=str(order_res.client_order_id)
                if order_res.client_order_id
                else client_order_id,
                symbol=str(order_res.symbol),
                side=side,
                quantity=float(order_res.qty),
                status=OrderStatus.ACCEPTED,
                filled_qty=float(order_res.filled_qty) if order_res.filled_qty else 0.0,
                filled_avg_price=float(order_res.filled_avg_price)
                if order_res.filled_avg_price
                else None,
                submitted_at=order_res.submitted_at or datetime.now(timezone.utc),
                updated_at=order_res.updated_at or datetime.now(timezone.utc),
            )
        except Exception as e:
            raise BrokerError(f"Failed to submit paper order for {symbol} to Alpaca: {e}") from e

    def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an open paper order by ID."""
        try:
            self._client.cancel_order_by_id(broker_order_id)
            return True
        except Exception as e:
            raise BrokerError(f"Failed to cancel Alpaca order {broker_order_id}: {e}") from e
