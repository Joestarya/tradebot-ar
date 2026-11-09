# Stage 4 — Historical Backtesting

Stage 4 downloads public USD-M futures candles, calculates the same Stage 2 indicators, and simulates the Stage 3 trend-following rules. It does not use API keys, change leverage, or submit orders.

## Run (PowerShell)

From the project root with the virtual environment activated:

```powershell
python stage4.py --days 180 --balance-usdt 12.50
```

Use the actual futures wallet balance converted to USDT. The 12.50 value is only an example. Start with at least 90–180 days; longer history is preferable. Binance public kline history is paginated automatically.

Optional settings:

```powershell
python stage4.py --days 180 --balance-usdt 12.50 --risk 0.01 --leverage 10 --fee 0.0005 --slippage 0.0005
```

Outputs:
- `data/backtest/trades.csv`
- `data/backtest/summary.json`

## Simulation assumptions

- Signal evaluated only after a closed 15m candle.
- The 1h trend uses only hourly candles whose close time is no later than the signal time.
- Entry is at the next 15m candle open, not the signal candle close.
- One portfolio position at a time; if both symbols signal together, BTCUSDT has priority.
- Stop loss is checked before take profit if both are touched in the same candle (conservative assumption).
- 1% risk budget, 10x leverage, quantity step 0.001 and minimum notional USD 5 are initial simulation assumptions; verify current exchange filters before any testnet work.
- Fees and slippage are charged on entry and exit using configurable assumptions.
- A 2% realized daily loss cap blocks new entries for the rest of that UTC day.
- Open position at the end of the data is closed at the last candle close.

## Important limitations

This is an initial research backtester, not proof of profitability. It does not yet model funding payments, liquidation, changing maintenance margin tiers, partial fills, spread variation, exchange outages, or market impact. The quantity step/minimum notional are placeholders. Results can be distorted by limited history and parameter selection. Use out-of-sample / walk-forward testing before considering testnet execution. The historical fetcher uses the configured `BASE_URL`; for full public production history, set `BINANCE_BASE_URL=https://fapi.binance.com` in your local `.env` if your current configuration points to demo futures.

Run unit tests:

```powershell
python -m unittest discover -s tests -v
```

No live or testnet order execution is included.
