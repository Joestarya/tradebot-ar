from pathlib import Path
import pandas as pd

from src.indicators import calculate_indicators

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
FILES = ["BTCUSDT_15m.csv", "BTCUSDT_1h.csv",
         "ETHUSDT_15m.csv", "ETHUSDT_1h.csv"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 68)
    print("BINANCE FUTURES BOT - STAGE 2: TECHNICAL INDICATORS")
    print("Offline CSV calculation; no API calls and no orders")
    print("=" * 68)

    for name in FILES:
        source = RAW / name
        if not source.exists():
            raise FileNotFoundError(
                f"Missing {source}. Run Stage 1 (`python main.py`) first."
            )
        candles = pd.read_csv(source, parse_dates=["open_time", "close_time"])
        df = calculate_indicators(candles)
        target = OUT / name.replace(".csv", "_indicators.csv")
        df.to_csv(target, index=False)
        last = df.iloc[-1]
        print(
            f"[OK] {name:22} | rows={len(df):3} | "
            f"close={last['close']} | RSI={last['rsi_14']:.2f} | "
            f"MACD hist={last['macd_hist']:.6f} | ATR={last['atr_14']:.6f}"
        )
        print(f"     Saved: {target}")
    print("\nStage 2 completed.")


if __name__ == "__main__":
    main()
