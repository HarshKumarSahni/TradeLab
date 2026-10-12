"""Abstract paper broker interface and standardized broker data contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from tradelab.models import OrderSide, OrderStatus


@dataclass(frozen=True)
class BrokerAccount:
    """Standardized broker account balance and buying power snapshot."""

    account_id: str
    status: str
    currency: str
    equity: float
    cash: float
    buying_power: float
    is_paper: bool


@dataclass(frozen=True)
class BrokerPosition:
    """Standardized broker position snapshot."""

    symbol: str
    quantity: float
    market_value: float
    cost_basis: float
    current_price: float
    unrealized_pl: float
    unrealized_plpc: float


@dataclass(frozen=True)
class BrokerOrder:
    """Standardized broker order representation."""

    broker_order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    status: OrderStatus
    filled_qty: float
    filled_avg_price: Optional[float]
    submitted_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class MarketClock:
    """Market open/close status."""

    is_open: bool
    next_open: datetime
    next_close: datetime


class PaperBroker(ABC):
    """Abstract interface for paper trading broker implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the broker adapter."""
        pass

    @abstractmethod
    def get_account(self) -> BrokerAccount:
        """Retrieve account status and buying power."""
        pass

    @abstractmethod
    def get_positions(self) -> List[BrokerPosition]:
        """Retrieve list of currently held open positions."""
        pass

    @abstractmethod
    def get_orders(self, limit: int = 50) -> List[BrokerOrder]:
        """Retrieve recent orders."""
        pass

    @abstractmethod
    def get_clock(self) -> MarketClock:
        """Retrieve current trading session status."""
        pass

    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        client_order_id: str,
    ) -> BrokerOrder:
        """Submit a simulated market order with a deterministic idempotency ID."""
        pass

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an open order by ID."""
        pass
