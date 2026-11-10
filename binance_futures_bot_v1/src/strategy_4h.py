from __future__ import annotations
import pandas as pd
from .indicators import calculate_indicators

def calculate_4h_indicators(candles: pd.DataFrame) -> pd.DataFrame:
    """4H SMA(50/200) and Wilder RSI(14), matching TradingView's default method."""
    df = calculate_indicators(candles)
    close = pd.to_numeric(df["close"], errors="coerce")
    df["sma_50"] = close.rolling(50, min_periods=50).mean()
    df["sma_200"] = close.rolling(200, min_periods=200).mean()
    df["bull_regime"] = df["sma_50"] > df["sma_200"]
    df["bear_regime"] = df["sma_50"] < df["sma_200"]
    df["rsi_cross_up_50"] = (df["rsi_14"] > 50) & (df["rsi_14"].shift(1) <= 50)
    df["rsi_cross_down_50"] = (df["rsi_14"] < 50) & (df["rsi_14"].shift(1) >= 50)
    return df

def signal_at_close(row: pd.Series) -> str | None:
    required = ["sma_50", "sma_200", "rsi_14", "atr_14"]
    if any(pd.isna(row.get(key)) for key in required):
        return None
    if bool(row["bull_regime"]) and bool(row["rsi_cross_up_50"]):
        return "LONG"
    if bool(row["bear_regime"]) and bool(row["rsi_cross_down_50"]):
        return "SHORT"
    return None
