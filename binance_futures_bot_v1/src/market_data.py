
from __future__ import annotations

import socket
from contextlib import contextmanager
from threading import Lock
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import pandas as pd
import requests

from .config import BASE_URL, KLINE_LIMIT, REQUEST_TIMEOUT, DATA_DIR


KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_asset_volume", "number_of_trades",
    "taker_buy_base_volume", "taker_buy_quote_volume", "ignore",
]

NUMERIC_COLUMNS = [
    "open", "high", "low", "close", "volume", "quote_asset_volume",
    "taker_buy_base_volume", "taker_buy_quote_volume",
]

DOH_URL = "https://cloudflare-dns.com/dns-query"

# Socket resolver bersifat global. Lock mencegah dua request bot
# mengubah resolver secara bersamaan.
DNS_LOCK = Lock()


class BinanceMarketDataError(RuntimeError):
    pass


def resolve_doh(hostname: str) -> list[str]:
    """Resolve hostname using Cloudflare DNS-over-HTTPS."""

    try:
        response = requests.get(
            DOH_URL,
            params={"name": hostname, "type": "A"},
            headers={"accept": "application/dns-json"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

    except (requests.RequestException, ValueError) as exc:
        raise BinanceMarketDataError(
            f"Cloudflare DoH resolution failed for {hostname}: {exc}"
        ) from exc

    if payload.get("Status") != 0:
        raise BinanceMarketDataError(
            f"DoH returned DNS status {payload.get('Status')} for {hostname}"
        )

    # Type 1 = IPv4 A record.
    # Abaikan CNAME dan ambil alamat IPv4 akhirnya.
    ips = list(dict.fromkeys(
        answer["data"]
        for answer in payload.get("Answer", [])
        if answer.get("type") == 1
    ))

    if not ips:
        raise BinanceMarketDataError(
            f"No IPv4 address found for {hostname} through DoH"
        )

    return ips


@contextmanager
def temporary_dns_override(hostname: str, ip: str):
    """Connect to a selected IP while preserving the original hostname.

    HTTPS URL, Host header, SNI and certificate verification continue
    to use the original hostname.
    """

    original_getaddrinfo = socket.getaddrinfo

    def custom_getaddrinfo(host, port, *args, **kwargs):
        if isinstance(host, str) and host.lower().rstrip(".") == hostname.lower():
            return original_getaddrinfo(
                ip, port, *args, **kwargs
            )

        return original_getaddrinfo(host, port, *args, **kwargs)

    with DNS_LOCK:
        try:
            socket.getaddrinfo = custom_getaddrinfo
            yield
        finally:
            socket.getaddrinfo = original_getaddrinfo


def get_binance_response(url: str, params: dict) -> requests.Response:
    """Request Binance using DoH-resolved IPs with SSL verification."""

    hostname = urlparse(url).hostname

    if not hostname:
        raise BinanceMarketDataError(f"Invalid Binance URL: {url}")

    ips = resolve_doh(hostname)
    last_error = None

    for ip in ips:
        try:
            print(f"[DNS] {hostname} -> {ip}")

            with temporary_dns_override(hostname, ip):
                response = requests.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )

            # HTTP errors are not DNS failures. Let the caller handle them.
            return response

        except requests.RequestException as exc:
            last_error = exc
            print(f"[WARN] Connection to {ip} failed: {exc}")

    raise BinanceMarketDataError(
        f"Could not connect to {hostname} using DoH IPs {ips}: {last_error}"
    )


def fetch_klines(
    symbol: str,
    interval: str,
    limit: int = KLINE_LIMIT,
    *,
    drop_open_candle: bool = True,
) -> pd.DataFrame:
    """Fetch USDⓈ-M Futures klines using public market data."""

    symbol = symbol.upper()
    url = f"{BASE_URL}/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    try:
        response = get_binance_response(url, params)
        response.raise_for_status()
        payload = response.json()

    except requests.RequestException as exc:
        raise BinanceMarketDataError(
            f"HTTP error fetching {symbol} {interval}: {exc}"
        ) from exc

    except ValueError as exc:
        raise BinanceMarketDataError(
            f"Invalid JSON from Binance for {symbol} {interval}"
        ) from exc

    if not isinstance(payload, list) or not payload:
        raise BinanceMarketDataError(
            f"Unexpected/empty kline response for {symbol} {interval}: {payload}"
        )

    df = pd.DataFrame(payload, columns=KLINE_COLUMNS)

    df["open_time"] = pd.to_datetime(
        df["open_time"], unit="ms", utc=True
    )
    df["close_time"] = pd.to_datetime(
        df["close_time"], unit="ms", utc=True
    )

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["number_of_trades"] = pd.to_numeric(
        df["number_of_trades"], errors="coerce"
    ).astype("Int64")

    df = (
        df.drop(columns=["ignore"])
        .sort_values("open_time")
        .reset_index(drop=True)
    )

    if df[["open", "high", "low", "close", "volume"]].isna().any().any():
        raise BinanceMarketDataError(
            f"Missing numeric OHLCV values in {symbol} {interval}"
        )

    if drop_open_candle:
        now = pd.Timestamp.now(tz="UTC")
        df = df[df["close_time"] < now].copy().reset_index(drop=True)

    if df.empty:
        raise BinanceMarketDataError(
            f"No closed candles available for {symbol} {interval}"
        )

    df.insert(0, "symbol", symbol)
    df.insert(1, "timeframe", interval)

    return df


def save_klines_csv(df: pd.DataFrame, output_dir: Path = DATA_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    symbol = str(df["symbol"].iloc[0])
    timeframe = str(df["timeframe"].iloc[0])

    path = output_dir / f"{symbol}_{timeframe}.csv"
    df.to_csv(path, index=False)

    return path


def fetch_market_snapshot(
    symbols: Iterable[str],
    timeframes: Iterable[str],
    limit: int = KLINE_LIMIT,
) -> list[Path]:

    saved_paths: list[Path] = []

    for symbol in symbols:
        for timeframe in timeframes:
            df = fetch_klines(symbol, timeframe, limit)

            path = save_klines_csv(df)
            saved_paths.append(path)

            last = df.iloc[-1]

            print(
                f"[OK] {symbol:8} {timeframe:>3} | "
                f"candles={len(df):3} | "
                f"last_closed={last['open_time']} | "
                f"close={last['close']}"
            )

    return saved_paths
