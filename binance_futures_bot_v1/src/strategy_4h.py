from __future__ import annotations
import pandas as pd
from .indicators import calculate_indicators

def calculate_4h_indicators(candles: pd.DataFrame) -> pd.DataFrame:
    """4H SMA(50/200) crossover and Wilder RSI(14)."""
    df = calculate_indicators(candles)
    close = pd.to_numeric(df["close"], errors="coerce")
    df["sma_50"] = close.rolling(50, min_periods=50).mean()
    df["sma_200"] = close.rolling(200, min_periods=200).mean()
    df["bull_regime"] = df["sma_50"] > df["sma_200"]
    df["bear_regime"] = df["sma_50"] < df["sma_200"]
    df["golden_cross"] = (df["sma_50"] > df["sma_200"]) & (df["sma_50"].shift(1) <= df["sma_200"].shift(1))
    df["death_cross"] = (df["sma_50"] < df["sma_200"]) & (df["sma_50"].shift(1) >= df["sma_200"].shift(1))
    return df

def signal_at_close(row: pd.Series) -> str | None:
    required = ["sma_50", "sma_200", "rsi_14", "atr_14"]
    if any(pd.isna(row.get(key)) for key in required):
        return None
    # MA crossover is the trigger; RSI(14) >/< 50 confirms direction.
    if bool(row["golden_cross"]) and float(row["rsi_14"]) > 50:
        return "LONG"
    if bool(row["death_cross"]) and float(row["rsi_14"]) < 50:
        return "SHORT"
    return None
