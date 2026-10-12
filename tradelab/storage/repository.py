"""Repository layer for persisting and retrieving backtest runs and fills."""

import json
import uuid
from typing import List, Optional

from tradelab.backtesting.engine import BacktestResult
from tradelab.backtesting.metrics import PerformanceMetrics
from tradelab.storage.db import get_session, init_db
from tradelab.storage.tables import BacktestFillRecord, BacktestRunRecord


class BacktestRepository:
    """Provides transactional persistence operations for backtests."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url
        init_db(self.database_url)

    def save_run(
        self,
        result: BacktestResult,
        metrics: PerformanceMetrics,
        fast_window: int = 20,
        slow_window: int = 50,
    ) -> str:
        """Atomically persist a backtest run and all its execution fills."""
        run_id = str(uuid.uuid4())
        metrics_dict = metrics.to_dict()
        config_dict = {
            "initial_cash": result.config.initial_cash,
            "fee": result.config.fee,
            "slippage_bps": result.config.slippage_bps,
            "allow_fractional": result.config.allow_fractional,
            "fast_window": fast_window,
            "slow_window": slow_window,
        }

        with get_session(self.database_url) as session:
            try:
                run_record = BacktestRunRecord(
                    id=run_id,
                    symbol=result.symbol,
                    start_date=result.start_date,
                    end_date=result.end_date,
                    fast_window=fast_window,
                    slow_window=slow_window,
                    initial_cash=result.config.initial_cash,
                    fee=result.config.fee,
                    slippage_bps=result.config.slippage_bps,
                    total_return=metrics.total_return,
                    max_drawdown=metrics.max_drawdown,
                    metrics_json=json.dumps(metrics_dict),
                    config_json=json.dumps(config_dict),
                )
                session.add(run_record)

                for fill in result.fills:
                    fill_record = BacktestFillRecord(
                        run_id=run_id,
                        timestamp_utc=fill.timestamp.to_pydatetime(),
                        side=fill.side.value,
                        quantity=fill.quantity,
                        fill_price=fill.fill_price,
                        fee=fill.fee,
                        cash_after=fill.cash_after,
                        position_after=fill.position_after,
                    )
                    session.add(fill_record)

                session.commit()
                return run_id
            except Exception:
                session.rollback()
                raise

    def get_run(self, run_id: str) -> Optional[BacktestRunRecord]:
        """Retrieve a specific run by its UUID."""
        with get_session(self.database_url) as session:
            return session.query(BacktestRunRecord).filter_by(id=run_id).first()

    def list_runs(self, symbol: Optional[str] = None, limit: int = 50) -> List[BacktestRunRecord]:
        """Retrieve historical runs ordered by creation date descending."""
        with get_session(self.database_url) as session:
            query = session.query(BacktestRunRecord)
            if symbol and symbol.upper() != "ALL":
                query = query.filter_by(symbol=symbol.upper())
            return query.order_by(BacktestRunRecord.created_at_utc.desc()).limit(limit).all()

    def get_fills_for_run(self, run_id: str) -> List[BacktestFillRecord]:
        """Retrieve all fills for a given run."""
        with get_session(self.database_url) as session:
            return (
                session.query(BacktestFillRecord)
                .filter_by(run_id=run_id)
                .order_by(BacktestFillRecord.timestamp_utc.asc())
                .all()
            )

    def delete_run(self, run_id: str) -> bool:
        """Delete a backtest run and its cascaded fills."""
        with get_session(self.database_url) as session:
            run = session.query(BacktestRunRecord).filter_by(id=run_id).first()
            if run:
                session.delete(run)
                session.commit()
                return True
            return False
