"""SQLAlchemy ORM schema models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from tradelab.storage.db import Base


class BacktestRunRecord(Base):
    """Persistent record of a simulated backtest run."""

    __tablename__ = "backtest_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at_utc = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    symbol = Column(String(10), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    fast_window = Column(Integer, nullable=False)
    slow_window = Column(Integer, nullable=False)
    initial_cash = Column(Float, nullable=False)
    fee = Column(Float, nullable=False)
    slippage_bps = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=False)
    metrics_json = Column(Text, nullable=False)
    config_json = Column(Text, nullable=False)

    fills = relationship(
        "BacktestFillRecord",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="BacktestFillRecord.timestamp_utc",
    )


class BacktestFillRecord(Base):
    """Persistent record of an individual simulated order execution fill."""

    __tablename__ = "backtest_fills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        String(36),
        ForeignKey("backtest_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp_utc = Column(DateTime(timezone=True), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    fill_price = Column(Float, nullable=False)
    fee = Column(Float, nullable=False)
    cash_after = Column(Float, nullable=False)
    position_after = Column(Float, nullable=False)

    run = relationship("BacktestRunRecord", back_populates="fills")


class PaperOrderRecord(Base):
    """Audit log of submitted paper broker orders."""

    __tablename__ = "paper_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_order_id = Column(String(64), unique=True, nullable=False, index=True)
    broker_order_id = Column(String(64), nullable=True, index=True)
    symbol = Column(String(10), nullable=False)
    side = Column(String(10), nullable=False)
    qty = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)
    submitted_at_utc = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_updated_at_utc = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    raw_response_json = Column(Text, nullable=True)


class BotEventRecord(Base):
    """Audit log of automated paper bot operations and risk events."""

    __tablename__ = "bot_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp_utc = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    symbol = Column(String(10), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    details_json = Column(Text, nullable=True)
