from src.config import SYMBOLS, TIMEFRAMES, KLINE_LIMIT, BASE_URL
from src.market_data import fetch_market_snapshot, BinanceMarketDataError


def main() -> None:
    print("=" * 68)
    print("BINANCE FUTURES BOT - STAGE 1: MARKET DATA")
    print(f"Endpoint : {BASE_URL}")
    print(f"Symbols  : {', '.join(SYMBOLS)}")
    print(f"Frames   : {', '.join(TIMEFRAMES)}")
    print(f"Limit    : {KLINE_LIMIT} candles per market/timeframe")
    print("Mode     : READ-ONLY market data; no orders are submitted")
    print("=" * 68)

    try:
        paths = fetch_market_snapshot(SYMBOLS, TIMEFRAMES, KLINE_LIMIT)
    except BinanceMarketDataError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

    print("\nCompleted. CSV files:")
    for path in paths:
        print(f" - {path}")


if __name__ == "__main__":
    main()
