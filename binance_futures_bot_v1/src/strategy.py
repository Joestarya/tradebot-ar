from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class Signal:
    symbol: str
    timestamp: str
    side: str
    entry: float
    stop_loss: float
    take_profit: float
    atr: float
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _ema(series: pd.Series, period: int) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").ewm(
        span=period, adjust=False, min_periods=period
    ).mean()


def _latest_trend(df_1h: pd.DataFrame) -> str:
    required = {"close"}
    if not required.issubset(df_1h.columns) or len(df_1h) < 55:
        return "NEUTRAL"
    close = pd.to_numeric(df_1h["close"], errors="coerce")
    ema20 = _ema(close, 20)
    ema50 = _ema(close, 50)
    if pd.isna(ema20.iloc[-1]) or pd.isna(ema50.iloc[-1]):
        return "NEUTRAL"
    if ema20.iloc[-1] > ema50.iloc[-1] and close.iloc[-1] > ema20.iloc[-1]:
        return "LONG"
    if ema20.iloc[-1] < ema50.iloc[-1] and close.iloc[-1] < ema20.iloc[-1]:
        return "SHORT"
    return "NEUTRAL"


def generate_signal(
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    symbol: str,
    atr_multiplier: float = 1.2,
    reward_risk: float = 2.0,
    volume_threshold: float = 1.1,
) -> Optional[Signal]:
    """Evaluate only the latest CLOSED 15m candle against the latest closed 1h trend."""
    required = {
        "close", "high", "low", "rsi_14", "macd_hist", "atr_14",
        "volume_ratio", "support", "resistance"
    }
    missing = required.difference(df_15m.columns)
    if missing:
        raise ValueError(f"15m data missing columns: {sorted(missing)}")
    if len(df_15m) < 3:
        return None

    trend = _latest_trend(df_1h)
    if trend == "NEUTRAL":
        return None

    d = df_15m.reset_index(drop=True)
    current, previous = d.iloc[-1], d.iloc[-2]
    numeric = ["close", "rsi_14", "macd_hist", "atr_14", "volume_ratio"]
    if any(pd.isna(current[c]) for c in numeric):
        return None

    close = float(current["close"])
    atr = float(current["atr_14"])
    if close <= 0 or atr <= 0:
        return None

    # Active style: RSI can already be on the trend side, provided momentum
    # is improving. This avoids requiring a fresh RSI-50 cross on every trade.
    rsi = float(current["rsi_14"])
    rsi_prev = float(previous["rsi_14"]) if pd.notna(previous["rsi_14"]) else np.nan
    hist = float(current["macd_hist"])
    hist_prev = float(previous["macd_hist"]) if pd.notna(previous["macd_hist"]) else np.nan
    volume_ratio = float(current["volume_ratio"])

    if trend == "LONG":
        momentum = rsi > 50 and hist > hist_prev
        if not momentum or hist <= 0 or volume_ratio < volume_threshold:
            return None
        side = "LONG"
        stop = close - atr_multiplier * atr
        target = close + reward_risk * (close - stop)
        reason = "1H EMA20>EMA50; 15M RSI>50, MACD histogram positive and rising, volume confirmed"
    else:
        momentum = rsi < 50 and hist < hist_prev
        if not momentum or hist >= 0 or volume_ratio < volume_threshold:
            return None
        side = "SHORT"
        stop = close + atr_multiplier * atr
        target = close - reward_risk * (stop - close)
        reason = "1H EMA20<EMA50; 15M RSI<50, MACD histogram negative and falling, volume confirmed"

    timestamp = str(current.get("close_time", current.get("open_time", "")))
    return Signal(
        symbol=symbol,
        timestamp=timestamp,
        side=side,
        entry=close,
        stop_loss=float(stop),
        take_profit=float(target),
        atr=atr,
        reason=reason,
    )
