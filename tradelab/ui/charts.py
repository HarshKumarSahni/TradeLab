"""Plotly chart visualizers for market data, strategy signals, equity curves, and drawdowns."""

from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from tradelab.backtesting.engine import Fill
from tradelab.models import OrderSide

# Curated palette matching Streamlit dark theme
COLOR_INCREASING = "#00D47E"  # Emerald green
COLOR_DECREASING = "#EF5350"  # Coral red
COLOR_BG = "#0E1117"
COLOR_PLOT_BG = "#131722"
COLOR_GRID = "#2A2E39"
COLOR_TEXT = "#E6E8EB"
COLOR_SMA_FAST = "#FFB020"  # Amber gold
COLOR_SMA_SLOW = "#9D4EDD"  # Royal violet
COLOR_BENCHMARK = "#78909C"  # Slate grey


def create_candlestick_chart(
    df: pd.DataFrame,
    symbol: str,
    title: Optional[str] = None,
    show_volume: bool = True,
) -> go.Figure:
    """Create an interactive Plotly Candlestick and Volume chart."""
    chart_title = title or f"{symbol.upper()} Daily Price & Volume Action"

    if show_volume:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.75, 0.25],
        )
    else:
        fig = go.Figure()

    # Candlestick Trace
    candlestick = go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price",
        increasing_line_color=COLOR_INCREASING,
        decreasing_line_color=COLOR_DECREASING,
        increasing_fillcolor=COLOR_INCREASING,
        decreasing_fillcolor=COLOR_DECREASING,
        hoverlabel=dict(bgcolor="#1E222D", font_color=COLOR_TEXT),
    )

    if show_volume:
        fig.add_trace(candlestick, row=1, col=1)

        vol_colors = [
            COLOR_INCREASING if c >= o else COLOR_DECREASING
            for c, o in zip(df["Close"], df["Open"], strict=False)
        ]

        volume_bar = go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volume",
            marker_color=vol_colors,
            opacity=0.65,
            hoverlabel=dict(bgcolor="#1E222D", font_color=COLOR_TEXT),
        )
        fig.add_trace(volume_bar, row=2, col=1)
    else:
        fig.add_trace(candlestick)

    fig.update_layout(
        title=dict(text=f"<b>{chart_title}</b>", font=dict(size=18, color=COLOR_TEXT), x=0.01),
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_PLOT_BG,
        font=dict(family="sans-serif", color=COLOR_TEXT, size=12),
        margin=dict(l=40, r=40, t=50, b=30),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=COLOR_TEXT),
        ),
        hovermode="x unified",
    )

    fig.update_xaxes(
        gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID, showline=True, linecolor=COLOR_GRID
    )
    fig.update_yaxes(
        gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID, showline=True, linecolor=COLOR_GRID
    )

    if show_volume:
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
    else:
        fig.update_yaxes(title_text="Price ($)")

    return fig


def create_backtest_chart(
    candles: pd.DataFrame,
    signals_df: pd.DataFrame,
    fills: List[Fill],
    symbol: str,
    fast_window: int,
    slow_window: int,
) -> go.Figure:
    """Create chart with Candlesticks, Fast/Slow SMA overlays, and execution fill markers."""
    fig = go.Figure()

    # Base Candlestick
    fig.add_trace(
        go.Candlestick(
            x=candles.index,
            open=candles["Open"],
            high=candles["High"],
            low=candles["Low"],
            close=candles["Close"],
            name="Candles",
            increasing_line_color=COLOR_INCREASING,
            decreasing_line_color=COLOR_DECREASING,
            increasing_fillcolor=COLOR_INCREASING,
            decreasing_fillcolor=COLOR_DECREASING,
            opacity=0.6,
        )
    )

    # Fast SMA
    if "SMA_fast" in signals_df.columns:
        fig.add_trace(
            go.Scatter(
                x=signals_df.index,
                y=signals_df["SMA_fast"],
                name=f"Fast SMA ({fast_window})",
                line=dict(color=COLOR_SMA_FAST, width=2),
            )
        )

    # Slow SMA
    if "SMA_slow" in signals_df.columns:
        fig.add_trace(
            go.Scatter(
                x=signals_df.index,
                y=signals_df["SMA_slow"],
                name=f"Slow SMA ({slow_window})",
                line=dict(color=COLOR_SMA_SLOW, width=2),
            )
        )

    # Execution Fill Markers at exact execution timestamp and price
    buy_fills = [f for f in fills if f.side == OrderSide.BUY]
    sell_fills = [f for f in fills if f.side == OrderSide.SELL]

    if buy_fills:
        fig.add_trace(
            go.Scatter(
                x=[f.timestamp for f in buy_fills],
                y=[f.fill_price for f in buy_fills],
                mode="markers",
                name="BUY Fill (Next Open)",
                marker=dict(
                    symbol="triangle-up",
                    size=13,
                    color="#00E676",
                    line=dict(color="#FFFFFF", width=1.5),
                ),
                text=[
                    f"BUY: {f.quantity:,.0f} shs @ ${f.fill_price:,.2f}<br>Fee: ${f.fee:.2f}"
                    for f in buy_fills
                ],
                hoverinfo="x+text",
            )
        )

    if sell_fills:
        fig.add_trace(
            go.Scatter(
                x=[f.timestamp for f in sell_fills],
                y=[f.fill_price for f in sell_fills],
                mode="markers",
                name="SELL Fill (Next Open)",
                marker=dict(
                    symbol="triangle-down",
                    size=13,
                    color="#FF1744",
                    line=dict(color="#FFFFFF", width=1.5),
                ),
                text=[
                    f"SELL: {f.quantity:,.0f} shs @ ${f.fill_price:,.2f}<br>Fee: ${f.fee:.2f}"
                    for f in sell_fills
                ],
                hoverinfo="x+text",
            )
        )

    fig.update_layout(
        title=dict(
            text=f"<b>{symbol.upper()} — Strategy Signals & Fills (Next-Open Execution)</b>",
            font=dict(size=17, color=COLOR_TEXT),
            x=0.01,
        ),
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_PLOT_BG,
        font=dict(family="sans-serif", color=COLOR_TEXT, size=12),
        margin=dict(l=40, r=40, t=50, b=30),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=COLOR_TEXT),
        ),
    )
    fig.update_xaxes(
        gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID, showline=True, linecolor=COLOR_GRID
    )
    fig.update_yaxes(
        title_text="Price ($)",
        gridcolor=COLOR_GRID,
        zerolinecolor=COLOR_GRID,
        showline=True,
        linecolor=COLOR_GRID,
    )

    return fig


def create_equity_curve_chart(
    equity_df: pd.DataFrame,
    benchmark_series: pd.Series,
    symbol: str,
) -> go.Figure:
    """Plot Strategy Equity Curve vs Buy & Hold Benchmark."""
    fig = go.Figure()

    # Strategy Equity
    fig.add_trace(
        go.Scatter(
            x=equity_df.index,
            y=equity_df["Equity"],
            name="Strategy Equity",
            line=dict(color=COLOR_INCREASING, width=2.5),
        )
    )

    # Benchmark Equity
    fig.add_trace(
        go.Scatter(
            x=benchmark_series.index,
            y=benchmark_series,
            name=f"Buy & Hold ({symbol.upper()})",
            line=dict(color=COLOR_BENCHMARK, width=1.8, dash="dot"),
        )
    )

    # Initial Capital Reference
    if not equity_df.empty:
        initial_val = float(equity_df["Equity"].iloc[0])
        fig.add_hline(
            y=initial_val,
            line_dash="dash",
            line_color="#455A64",
            annotation_text=f"Initial: ${initial_val:,.0f}",
            annotation_position="bottom right",
            annotation_font_color="#90A4AE",
        )

    fig.update_layout(
        title=dict(
            text="<b>Portfolio Equity Curve vs Benchmark</b>",
            font=dict(size=17, color=COLOR_TEXT),
            x=0.01,
        ),
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_PLOT_BG,
        font=dict(family="sans-serif", color=COLOR_TEXT, size=12),
        margin=dict(l=40, r=40, t=50, b=30),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=COLOR_TEXT),
        ),
    )
    fig.update_xaxes(
        gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID, showline=True, linecolor=COLOR_GRID
    )
    fig.update_yaxes(
        title_text="Portfolio Value ($)",
        gridcolor=COLOR_GRID,
        zerolinecolor=COLOR_GRID,
        showline=True,
        linecolor=COLOR_GRID,
    )

    return fig


def create_drawdown_chart(drawdown_series: pd.Series) -> go.Figure:
    """Plot underwater drawdown curve."""
    fig = go.Figure()

    pct_drawdown = drawdown_series * 100.0

    fig.add_trace(
        go.Scatter(
            x=pct_drawdown.index,
            y=pct_drawdown,
            name="Drawdown",
            line=dict(color=COLOR_DECREASING, width=1.8),
            fill="tozeroy",
            fillcolor="rgba(239, 83, 80, 0.2)",
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Historical Portfolio Drawdown (%)</b>",
            font=dict(size=17, color=COLOR_TEXT),
            x=0.01,
        ),
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_PLOT_BG,
        font=dict(family="sans-serif", color=COLOR_TEXT, size=12),
        margin=dict(l=40, r=40, t=50, b=30),
        hovermode="x unified",
    )
    fig.update_xaxes(
        gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID, showline=True, linecolor=COLOR_GRID
    )
    fig.update_yaxes(
        title_text="Drawdown (%)",
        gridcolor=COLOR_GRID,
        zerolinecolor=COLOR_GRID,
        showline=True,
        linecolor=COLOR_GRID,
    )

    return fig
