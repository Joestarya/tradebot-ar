from __future__ import annotations

from pathlib import Path
import time

import pandas as pd

from .config import BASE_URL, REQUEST_TIMEOUT, DATA_DIR
from .market_data import (
    BinanceMarketDataError, KLINE_COLUMNS, NUMERIC_COLUMNS, get_binance_response,
)

MAX_LIMIT = 1500


def fetch_historical_klines(
    symbol: str,
    interval: str,
    days: int = 180,
    output_dir: Path = DATA_DIR,
) -> Path:
    """Download paginated public USD-M futures klines and save closed candles."""
    if days < 30:
        raise ValueError("Use at least 30 days for a preliminary backtest.")
    symbol = symbol.upper()
    end_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
    start_ms = int((pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)).timestamp() * 1000)
    cursor = start_ms
    chunks: list[pd.DataFrame] = []
    url = f"{BASE_URL}/fapi/v1/klines"

    while cursor < end_ms:
        response = get_binance_response(url, {
            "symbol": symbol, "interval": interval,
            "startTime": cursor, "endTime": end_ms, "limit": MAX_LIMIT,
        })
        if response.status_code == 429:
            time.sleep(2)
            continue
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise BinanceMarketDataError(f"Unexpected kline payload for {symbol} {interval}")
        if not payload:
            break
        frame = pd.DataFrame(payload, columns=KLINE_COLUMNS)
        chunks.append(frame)
        last_open = int(payload[-1][0])
        next_cursor = last_open + 1
        if next_cursor <= cursor:
            raise BinanceMarketDataError("Historical pagination did not advance.")
        cursor = next_cursor
        if len(payload) < MAX_LIMIT:
            break
        time.sleep(0.15)

    if not chunks:
        raise BinanceMarketDataError(f"No historical candles returned for {symbol} {interval}")

    df = pd.concat(chunks, ignore_index=True).drop_duplicates(subset=["open_time"])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.drop(columns=["ignore"]).sort_values("open_time").reset_index(drop=True)
    df = df[df["close_time"] < pd.Timestamp.now(tz="UTC")].copy()
    df.insert(0, "symbol", symbol)
    df.insert(1, "timeframe", interval)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{symbol}_{interval}.csv"
    df.to_csv(path, index=False)
    print(f"[HISTORY] {symbol} {interval}: {len(df)} closed candles -> {path}")
    return path
