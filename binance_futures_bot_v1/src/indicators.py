from __future__ import annotations

import numpy as np
import pandas as pd


def wilder_rma(values: pd.Series, period: int) -> pd.Series:
    """Wilder RMA seeded with the SMA of the first period valid values."""
    if period < 1:
        raise ValueError("period must be >= 1")
    x = pd.to_numeric(values, errors="coerce").astype(float).to_numpy()
    out = np.full(len(x), np.nan)
    starts = [i for i in range(len(x) - period + 1)
              if np.isfinite(x[i:i + period]).all()]
    if not starts:
        return pd.Series(out, index=values.index, name=values.name)
    start = starts[0]
    seed = start + period - 1
    out[seed] = x[start:seed + 1].mean()
    for i in range(seed + 1, len(x)):
        if np.isfinite(x[i]) and np.isfinite(out[i - 1]):
            out[i] = (out[i - 1] * (period - 1) + x[i]) / period
    return pd.Series(out, index=values.index, name=values.name)


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    close = pd.to_numeric(close, errors="coerce").astype(float)
    delta = close.diff()
    gain = wilder_rma(delta.clip(lower=0), period)
    loss = wilder_rma(-delta.clip(upper=0), period)
    rsi = pd.Series(np.nan, index=close.index, dtype=float, name=f"rsi_{period}")
    normal = (gain > 0) & (loss > 0)
    rsi.loc[normal] = 100 - 100 / (1 + gain.loc[normal] / loss.loc[normal])
    rsi.loc[(gain > 0) & (loss == 0)] = 100.0
    rsi.loc[(gain == 0) & (loss > 0)] = 0.0
    rsi.loc[(gain == 0) & (loss == 0)] = 50.0
    return rsi


def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26,
                   signal: int = 9) -> pd.DataFrame:
    if fast >= slow:
        raise ValueError("MACD fast period must be smaller than slow period")
    close = pd.to_numeric(close, errors="coerce").astype(float)
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    line = ema_fast - ema_slow
    signal_line = line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({
        "macd": line,
        "macd_signal": signal_line,
        "macd_hist": line - signal_line,
    }, index=close.index)


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series,
                  period: int = 14) -> pd.Series:
    high = pd.to_numeric(high, errors="coerce").astype(float)
    low = pd.to_numeric(low, errors="coerce").astype(float)
    close = pd.to_numeric(close, errors="coerce").astype(float)
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(),
                    (low - prev).abs()], axis=1).max(axis=1)
    return wilder_rma(tr, period).rename(f"atr_{period}")


def calculate_pivots(high: pd.Series, low: pd.Series, left: int = 3,
                     right: int = 3) -> pd.DataFrame:
    """Publish a pivot only at its confirmation bar (right bars later)."""
    if left < 1 or right < 1:
        raise ValueError("left and right must be >= 1")
    h = pd.to_numeric(high, errors="coerce").to_numpy(dtype=float)
    l = pd.to_numeric(low, errors="coerce").to_numpy(dtype=float)
    ph = np.full(len(h), np.nan)
    pl = np.full(len(l), np.nan)
    for confirm in range(left + right, len(h)):
        center = confirm - right
        hw = h[center-left:center+right+1]
        lw = l[center-left:center+right+1]
        if (np.isfinite(hw).all() and h[center] == hw.max()
                and np.count_nonzero(hw == h[center]) == 1):
            ph[confirm] = h[center]
        if (np.isfinite(lw).all() and l[center] == lw.min()
                and np.count_nonzero(lw == l[center]) == 1):
            pl[confirm] = l[center]
    return pd.DataFrame({
        "pivot_high_confirmed": ph,
        "pivot_low_confirmed": pl,
        "resistance": pd.Series(ph, index=high.index).ffill(),
        "support": pd.Series(pl, index=low.index).ffill(),
    }, index=high.index)


def calculate_indicators(candles: pd.DataFrame) -> pd.DataFrame:
    required = {"open", "high", "low", "close", "volume"}
    missing = required.difference(candles.columns)
    if missing:
        raise ValueError(f"Missing candle columns: {sorted(missing)}")

    df = candles.copy()
    if "open_time" in df.columns:
        df = df.sort_values("open_time").reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    df["rsi_14"] = calculate_rsi(df["close"], 14)
    macd = calculate_macd(df["close"], 12, 26, 9)
    df[["macd", "macd_signal", "macd_hist"]] = macd
    df["atr_14"] = calculate_atr(df["high"], df["low"], df["close"], 14)
    df["atr_pct"] = df["atr_14"] / df["close"] * 100

    pivots = calculate_pivots(df["high"], df["low"], 3, 3)
    df[["pivot_high_confirmed", "pivot_low_confirmed",
        "resistance", "support"]] = pivots

    df["volume_sma_20"] = df["volume"].rolling(20, min_periods=20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_sma_20"]
    df["volume_above_sma20"] = df["volume"] > df["volume_sma_20"]
    return df
