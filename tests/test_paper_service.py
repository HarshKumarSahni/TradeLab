"""Unit tests for PaperTradingService, order preview, and idempotency."""

import uuid

import pytest

from tradelab.brokers.mock_broker import MockPaperBroker
from tradelab.exceptions import RiskLimitViolationError
from tradelab.models import OrderSide, OrderStatus
from tradelab.services.paper_service import PaperTradingService
from tradelab.storage.repository import BacktestRepository


@pytest.fixture
def memory_db_url() -> str:
    return f"sqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


@pytest.fixture
def paper_service(memory_db_url: str) -> PaperTradingService:
    BacktestRepository(database_url=memory_db_url)
    broker = MockPaperBroker(initial_cash=50000.0)
    return PaperTradingService(broker=broker, database_url=memory_db_url)


def test_get_account_and_clock(paper_service: PaperTradingService) -> None:
    """Verify account telemetry and paper mode enforcement."""
    account = paper_service.get_account()
    assert account.is_paper is True
    assert account.cash == 50000.0
    assert account.equity == 50000.0
    assert account.status == "ACTIVE"

    clock = paper_service.get_clock()
    assert clock.is_open is True


def test_order_preview_safe(paper_service: PaperTradingService) -> None:
    """Verify pre-trade analysis for an affordable buy order."""
    preview = paper_service.preview_order(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=10.0,
        current_price=150.0,
    )
    assert preview.is_safe is True
    assert preview.estimated_cost == 1500.0
    assert len(preview.warnings) == 0
    assert preview.proposed_client_order_id.startswith("TL-AAPL-")


def test_order_preview_insufficient_buying_power(paper_service: PaperTradingService) -> None:
    """Verify pre-trade check fails when cost exceeds buying power."""
    # 500 shares @ $150 = $75,000 > $50,000 cash
    preview = paper_service.preview_order(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=500.0,
        current_price=150.0,
    )
    assert preview.is_safe is False
    assert any("Insufficient buying power" in w for w in preview.warnings)


def test_order_submission_requires_confirmation(paper_service: PaperTradingService) -> None:
    """Unconfirmed order submissions must raise RiskLimitViolationError."""
    with pytest.raises(RiskLimitViolationError, match="confirmation"):
        paper_service.submit_paper_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=10.0,
            current_price=150.0,
            confirmed=False,
        )


def test_order_execution_and_positions(paper_service: PaperTradingService) -> None:
    """Verify confirmed order updates cash and positions."""
    order = paper_service.submit_paper_order(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=10.0,
        current_price=150.0,
        confirmed=True,
    )
    assert order.status == OrderStatus.FILLED
    assert order.quantity == 10.0

    account_after = paper_service.get_account()
    assert account_after.cash == 50000.0 - 1500.0

    positions = paper_service.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].quantity == 10.0


def test_idempotency_prevents_duplicate_submission(paper_service: PaperTradingService) -> None:
    """Submitting the same order twice on the same day must be rejected by risk gates."""
    # First submission succeeds
    paper_service.submit_paper_order(
        symbol="MSFT",
        side=OrderSide.BUY,
        quantity=5.0,
        current_price=200.0,
        confirmed=True,
    )

    # Second submission with the same deterministic date key must be blocked
    with pytest.raises(RiskLimitViolationError, match="already submitted"):
        paper_service.submit_paper_order(
            symbol="MSFT",
            side=OrderSide.BUY,
            quantity=5.0,
            current_price=200.0,
            confirmed=True,
        )
