# Stage 2 — Technical Indicators

Copy `src/indicators.py` into your existing project's `src` folder and copy
`stage2.py` into the project root. The patch also includes a basic unit test.

Run from the project root with the virtual environment active:

```powershell
python stage2.py
```

The script reads the four Stage 1 CSV files from `data/raw/` and writes:
- `data/processed/BTCUSDT_15m_indicators.csv`
- `data/processed/BTCUSDT_1h_indicators.csv`
- `data/processed/ETHUSDT_15m_indicators.csv`
- `data/processed/ETHUSDT_1h_indicators.csv`

Run tests:

```powershell
python -m unittest discover -s tests -v
```

Indicator conventions:
- RSI(14): Wilder RMA with SMA seed over the first 14 price changes.
- MACD(12,26,9): recursive EMA (`adjust=False`).
- ATR(14): True Range smoothed by Wilder RMA.
- Support/Resistance: unique 3-left / 3-right pivots, made available only on
  the confirmation candle to avoid look-ahead bias.
- Volume: SMA(20), volume ratio, and above-SMA boolean.

This stage is offline: it makes no API requests and places no orders.
