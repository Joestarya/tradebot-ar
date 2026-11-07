# Binance Futures Bot v1.0 — Stage 1

Stage 1 only collects public USDⓈ-M Futures candlestick data for BTCUSDT and ETHUSDT on 15m and 1h timeframes.

**Safety:** this version is read-only. It does not contain order placement, API-key handling, leverage configuration, or live trading functionality.

## Requirements

- Windows 10/11
- Python 3.10–3.12 recommended
- Internet connection

## Setup (PowerShell)

```powershell
cd path\to\binance_futures_bot_v1

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
python main.py
```

If `py -3.11` is unavailable, use an installed Python version between 3.10 and 3.12.

## What it does

- Calls `GET /fapi/v1/klines`.
- Downloads up to 500 candles per symbol/timeframe.
- Removes the currently-forming candle.
- Converts timestamps to UTC and OHLCV fields to numeric values.
- Saves CSV files in `data/raw/`.

Expected files:

- `data/raw/BTCUSDT_15m.csv`
- `data/raw/BTCUSDT_1h.csv`
- `data/raw/ETHUSDT_15m.csv`
- `data/raw/ETHUSDT_1h.csv`

## Endpoint configuration

Default is Binance Futures Demo/Testnet market-data endpoint:

`https://demo-fapi.binance.com`

To use public production market data instead, edit `.env`:

```env
BINANCE_BASE_URL=https://fapi.binance.com
```

No API key is needed for this stage's public market-data endpoint.

## Validation checklist

1. All four CSV files are created.
2. Each CSV contains `symbol`, `timeframe`, `open_time`, `open`, `high`, `low`, `close`, `volume`, and `close_time`.
3. Timestamps are UTC.
4. The last candle is closed, not still forming.
5. The close prices are plausible compared with the Binance Futures chart.

## Next stage

Stage 2 will calculate RSI(14), MACD(12,26,9), ATR(14), and initial swing-based support/resistance levels. We will compare indicator values with TradingView before connecting any order execution.
