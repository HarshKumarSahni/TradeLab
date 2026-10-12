"""Domain-specific exceptions for TradeLab."""


class TradeLabException(Exception):
    """Base exception for all TradeLab domain errors."""

    pass


class ConfigError(TradeLabException):
    """Raised when configuration values or environment variables are invalid."""

    pass


class MarketDataError(TradeLabException):
    """Raised when fetching market data fails from an external provider."""

    pass


class DataValidationError(TradeLabException):
    """Raised when OHLCV data fails schema, date, or structural validation checks."""

    pass


class StrategyError(TradeLabException):
    """Raised when strategy parameters or calculation constraints are violated."""

    pass


class BacktestError(TradeLabException):
    """Raised when a backtest simulation fails or invariants are broken."""

    pass


class BrokerError(TradeLabException):
    """Raised when broker communication fails or is rejected."""

    pass


class RiskLimitViolationError(TradeLabException):
    """Raised when an operation violates risk controls or safety rules."""

    pass
