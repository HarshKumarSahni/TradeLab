"""Plotly chart visualizers for market data, candlesticks, and volume."""

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Curated palette matching Streamlit dark theme
COLOR_INCREASING = "#00D47E"  # Emerald green
COLOR_DECREASING = "#EF5350"  # Coral red
COLOR_BG = "#0E1117"
COLOR_PLOT_BG = "#131722"
COLOR_GRID = "#2A2E39"
COLOR_TEXT = "#E6E8EB"


def create_candlestick_chart(
    df: pd.DataFrame,
    symbol: str,
    title: Optional[str] = None,
    show_volume: bool = True,
) -> go.Figure:
    """Create a high-performance interactive Plotly Candlestick and Volume chart.

    Parameters
    ----------
    df : pd.DataFrame
        Canonical OHLCV DataFrame with DatetimeIndex
    symbol : str
        Ticker symbol string
    title : Optional[str]
        Custom title for the figure
    show_volume : bool
        Whether to include a linked volume subplot

    Returns
    -------
    go.Figure
        Styled Plotly figure ready for st.plotly_chart
    """
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

        # Volume Bar Colors matching candle direction
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

    # Layout Styling
    fig.update_layout(
        title=dict(
            text=f"<b>{chart_title}</b>",
            font=dict(size=18, color=COLOR_TEXT),
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
        hovermode="x unified",
    )

    # Gridlines and Axis formatting
    fig.update_xaxes(
        gridcolor=COLOR_GRID,
        zerolinecolor=COLOR_GRID,
        showline=True,
        linecolor=COLOR_GRID,
    )
    fig.update_yaxes(
        gridcolor=COLOR_GRID,
        zerolinecolor=COLOR_GRID,
        showline=True,
        linecolor=COLOR_GRID,
    )

    if show_volume:
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
    else:
        fig.update_yaxes(title_text="Price ($)")

    return fig
