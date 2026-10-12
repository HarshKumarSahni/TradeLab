"""Typed application configuration and credential management."""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from tradelab.exceptions import ConfigError


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_mode: Literal["demo", "paper"] = Field(
        default="demo",
        description="Application operational mode (demo or paper).",
    )
    market_data_provider: Literal["yahoo", "fixture", "alpha_vantage"] = Field(
        default="yahoo",
        description="Market data provider adapter.",
    )

    alpaca_api_key: Optional[str] = Field(
        default=None,
        description="Alpaca Paper Trading API key.",
    )
    alpaca_secret_key: Optional[str] = Field(
        default=None,
        description="Alpaca Paper Trading secret key.",
    )
    alpaca_paper: bool = Field(
        default=True,
        description="Enforces paper trading endpoint. Live trading is strictly prohibited.",
    )

    database_url: str = Field(
        default="sqlite:///tradelab.db",
        description="SQLAlchemy database connection URL.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level.",
    )

    @field_validator("alpaca_paper")
    @classmethod
    def validate_alpaca_paper(cls, v: bool) -> bool:
        if not v:
            raise ConfigError(
                "TradeLab strictly enforces simulated paper trading. "
                "ALPACA_PAPER must remain True to prevent accidental live execution."
            )
        return v

    @property
    def has_alpaca_credentials(self) -> bool:
        """Check if Alpaca paper trading credentials are provided without exposing them."""
        return bool(
            self.alpaca_api_key
            and self.alpaca_secret_key
            and self.alpaca_api_key.strip()
            and self.alpaca_secret_key.strip()
        )

    @property
    def masked_alpaca_key(self) -> str:
        """Return a safely masked representation of the API key for UI indicators."""
        if not self.alpaca_api_key:
            return "Not Set"
        key = self.alpaca_api_key.strip()
        if len(key) <= 6:
            return "***"
        return f"{key[:3]}...{key[-3:]}"

    @property
    def status_label(self) -> str:
        """Human-readable badge label for global UI header and sidebar."""
        if self.app_mode == "demo":
            return "Demo Mode (Offline / Sandbox)"
        if self.has_alpaca_credentials and self.alpaca_paper:
            return "Connected Paper Account (Alpaca Sandbox)"
        return "Disconnected (No Paper Keys)"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
