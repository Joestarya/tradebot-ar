from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.backtest import run_backtest
from src.history import fetch_historical_klines
from src.indicators import calculate_indicators

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "backtest"
SYMBOLS = ["BTCUSDT", "ETHUSDT"]


def load_with_indicators(symbol: str, timeframe: str) -> pd.DataFrame:
    path = RAW / f"{symbol}_{timeframe}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing. Download history first.")
    candles = pd.read_csv(path, parse_dates=["open_time", "close_time"])
    return calculate_indicators(candles)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 4 historical backtest (no orders).")
    parser.add_argument("--days", type=int, default=180,
                        help="Historical lookback; minimum 30 days, default 180.")
    parser.add_argument("--balance-usdt", type=float, required=True)
    parser.add_argument("--risk", type=float, default=0.01)
    parser.add_argument("--leverage", type=float, default=10.0)
    parser.add_argument("--fee", type=float, default=0.0005,
                        help="Fee per side; verify your actual Binance fee tier.")
    parser.add_argument("--slippage", type=float, default=0.0005,
                        help="Adverse slippage per side.")
    args = parser.parse_args()

    if args.days < 30:
        parser.error("--days must be at least 30")
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    print("=" * 68)
    print("BINANCE FUTURES BOT - STAGE 4: HISTORICAL BACKTEST")
    print("PUBLIC DATA ONLY | NO API KEYS | NO ORDERS")
    print("=" * 68)

    for symbol in SYMBOLS:
        for timeframe in ("15m", "1h"):
            fetch_historical_klines(symbol, timeframe, args.days, RAW)

    frames_15m = {s: load_with_indicators(s, "15m") for s in SYMBOLS}
    frames_1h = {s: load_with_indicators(s, "1h") for s in SYMBOLS}

    trades, summary = run_backtest(
        frames_15m, frames_1h,
        initial_balance=args.balance_usdt,
        risk_fraction=args.risk,
        leverage=args.leverage,
        fee_rate=args.fee,
        slippage_rate=args.slippage,
    )
    trades_path = OUT / "trades.csv"
    summary_path = OUT / "summary.json"
    trades.to_csv(trades_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n--- BACKTEST SUMMARY ---")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"\nTrades: {trades_path}")
    print(f"Summary: {summary_path}")
    print("\nBacktest finished. Historical simulation only; no orders submitted.")


if __name__ == "__main__":
    main()
