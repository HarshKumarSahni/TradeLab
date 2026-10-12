"""Unit tests for BotController, risk limits, and single-cycle executions."""

import uuid

import pandas as pd
import pytest

from tradelab.brokers.mock_broker import MockPaperBroker
from tradelab.services.bot_controller import BotConfig, BotController
from tradelab.services.paper_service import PaperTradingService
from tradelab.storage.repository import BacktestRepository


@pytest.fixture
def memory_db_url() -> str:
    return f"sqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


@pytest.fixture
def bot_controller(memory_db_url: str) -> BotController:
    BacktestRepository(database_url=memory_db_url)
    broker = MockPaperBroker(initial_cash=50000.0)
    paper_service = PaperTradingService(broker=broker, database_url=memory_db_url)
    config = BotConfig(
        symbol="AAPL",
        fast_window=2,
        slow_window=4,
        max_allocation_usd=10000.0,
        max_order_qty=50.0,
        is_enabled=True,
        kill_switch_active=False,
    )
    return BotController(paper_service=paper_service, config=config, database_url=memory_db_url)


@pytest.fixture
def bullish_crossover_candles() -> pd.DataFrame:
    """10-day candles ending with a BUY crossover on the final bar."""
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    # Flat 10.0 for 9 bars, then sharp spike on the 10th bar (index 9) to trigger crossover
    closes = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 25.0]
    opens = closes
    highs = [p + 1.0 for p in opens]
    lows = [p - 1.0 for p in opens]
    volumes = [500000] * 10

    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
        index=pd.DatetimeIndex(dates, name="Date"),
    )


def test_kill_switch_halts_cycle(
    bot_controller: BotController, bullish_crossover_candles: pd.DataFrame
) -> None:
    """Active kill switch prevents all cycle evaluations immediately."""
    bot_controller.config.kill_switch_active = True

    result = bot_controller.run_cycle(bullish_crossover_candles, dry_run=False)
    assert result.success is False
    assert result.action_taken == "HALTED"
    assert "KILL SWITCH" in result.messages[0]


def test_bot_disabled_skips_live_execution(
    bot_controller: BotController, bullish_crossover_candles: pd.DataFrame
) -> None:
    """Disabled bot skips live order submission."""
    bot_controller.config.is_enabled = False

    result = bot_controller.run_cycle(bullish_crossover_candles, dry_run=False)
    assert result.success is True
    assert result.action_taken == "SKIPPED"
    assert "disabled" in result.messages[0]


def test_dry_run_evaluates_without_submitting(
    bot_controller: BotController, bullish_crossover_candles: pd.DataFrame
) -> None:
    """Dry run produces proposed order audit without submitting to broker."""
    result = bot_controller.run_cycle(bullish_crossover_candles, dry_run=True)
    assert result.success is True
    assert "DRY_RUN_BUY" in result.action_taken
    assert "[DRY RUN]" in result.messages[0]
    assert len(bot_controller.paper_service.get_orders()) == 0


def test_live_cycle_executes_buy_order(
    bot_controller: BotController, bullish_crossover_candles: pd.DataFrame
) -> None:
    """Enabled bot executes paper buy order and respects idempotency on rerun."""
    # First execution should succeed
    res1 = bot_controller.run_cycle(bullish_crossover_candles, dry_run=False)
    assert res1.success is True
    assert res1.action_taken == "EXECUTED_BUY"
    assert res1.order is not None

    orders = bot_controller.paper_service.get_orders()
    assert len(orders) == 1

    # Immediate rerun on same completed bar must be skipped by Idempotency Guard
    res2 = bot_controller.run_cycle(bullish_crossover_candles, dry_run=False)
    assert res2.action_taken == "IDEMPOTENT_SKIP"
    assert len(bot_controller.paper_service.get_orders()) == 1
