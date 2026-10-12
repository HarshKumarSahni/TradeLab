# TradeLab Architectural & Engineering Decisions

This document logs significant technical decisions, deviations from the reference project, rationale, and consequences.

## Decision Log

### ADR 001: Streamlit as Exclusive UI Framework
- **Context:** The reference implementation (Berk-Unsal/Python-Algorithmic-Trading-Bot) used Flask, raw HTML, Jinja templates, CSS, and Bootstrap.
- **Decision:** Build the entire UI using Streamlit multipage architecture (`app.py` + `pages/`).
- **Rationale:**
  - Python-native reactivity allows rapid data visualization with Plotly.
  - Native component ecosystem eliminates boilerplate REST API serialization for internal dashboard views.
  - Aligns with modern data science and algorithmic research workflows.

### ADR 002: alpaca-py Official SDK with Strict Paper-Only Guardrails
- **Context:** Legacy tutorials often rely on deprecated `alpaca-trade-api`.
- **Decision:** Use the official `alpaca-py` library with explicit validation that `paper=True` is permanently enforced.
- **Rationale:**
  - `alpaca-trade-api` is unmaintained and deprecated.
  - Strict code-level rejection of live trading endpoints prevents accidental capital risk in educational and interview demonstrations.

### ADR 003: Pure-Python Deterministic Backtest Engine
- **Context:** Many open-source bots either calculate equity naively on closing prices or pull in heavyweight external engines like Backtrader or Zipline.
- **Decision:** Implement a custom deterministic event-driven daily-bar simulator with explicit state tracking (`cash >= 0`, `quantity >= 0`).
- **Rationale:**
  - Complete control over order execution timing (strictly next-bar open).
  - Clear explanation in software engineering interviews without complex library abstractions.
  - Deterministic accounting that can be verified by simple pytest unit tests.

### ADR 004: Pydantic Settings with Masked Credential Presentation
- **Context:** Applications must handle optional API keys without risking accidental leakage in logs, screenshots, or exports.
- **Decision:** Utilize `pydantic-settings` with custom properties to verify credential availability while strictly masking key values (`AK***`).
- **Rationale:**
  - Prevents accidental token exposure during demonstrations or video recordings.
  - Centralizes configuration defaults and schema validation.
