from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from src.strategy import generate_signal
from src.risk import calculate_position_size

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "data" / "signals"
MARKETS = ["BTCUSDT", "ETHUSDT"]


def load_frame(symbol: str, timeframe: str) -> pd.DataFrame:
    path = PROCESSED / f"{symbol}_{timeframe}_indicators.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run Stage 2 first.")
    df = pd.read_csv(path)
    for col in ("open_time", "close_time"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 3 signal generator (no orders).")
    parser.add_argument("--balance-usdt", type=float, required=True,
                        help="Available futures wallet balance converted to USDT.")
    parser.add_argument("--risk", type=float, default=0.01,
                        help="Risk fraction per trade; default 0.01 = 1%%.")
    parser.add_argument("--leverage", type=float, default=10.0)
    parser.add_argument("--quantity-step", type=float, default=0.001,
                        help="Placeholder only; replace with live exchangeInfo filters before testnet.")
    parser.add_argument("--min-quantity", type=float, default=0.001)
    parser.add_argument("--min-notional", type=float, default=5.0,
                        help="Placeholder only; verify per-symbol exchange rules.")
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = []
    print("=" * 68)
    print("BINANCE FUTURES BOT - STAGE 3: SIGNAL GENERATION")
    print("READ-ONLY: no API calls, no leverage changes, no orders")
    print("=" * 68)

    for symbol in MARKETS:
        df15 = load_frame(symbol, "15m")
        df1h = load_frame(symbol, "1h")
        signal = generate_signal(df15, df1h, symbol)
        if signal is None:
            print(f"[NO SIGNAL] {symbol}: conditions not fully aligned.")
            results.append({"symbol": symbol, "side": "NONE", "reason": "No valid setup"})
            continue

        sizing = calculate_position_size(
            balance_usdt=args.balance_usdt,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            risk_fraction=args.risk,
            leverage=args.leverage,
            quantity_step=args.quantity_step,
            min_quantity=args.min_quantity,
            min_notional=args.min_notional,
        )
        row = signal.to_dict()
        row.update({
            "quantity": sizing.quantity,
            "notional": sizing.notional,
            "margin_required": sizing.margin_required,
            "estimated_loss": sizing.estimated_loss,
            "risk_budget": sizing.risk_budget,
            "sizing_accepted": sizing.accepted,
            "sizing_reason": sizing.reason,
        })
        results.append(row)
        status = "READY (simulation only)" if sizing.accepted else "SKIP"
        print(f"[{status}] {symbol} {signal.side} entry={signal.entry:.6f} "
              f"SL={signal.stop_loss:.6f} TP={signal.take_profit:.6f}")
        print(f"             qty={sizing.quantity} notional={sizing.notional:.4f} "
              f"margin={sizing.margin_required:.4f} est_loss={sizing.estimated_loss:.4f}")
        print(f"             {sizing.reason}")

    out = OUTPUT / "latest_signals.csv"
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\nSaved: {out}")
    print("Stage 3 completed. No orders were submitted.")


if __name__ == "__main__":
    main()
