# Stage 3 — Strategy and Risk-Based Signal Sizing

Stage 3 reads Stage 2 processed CSV files and produces a latest-signal report. It is **read-only**: no Binance API calls, no API keys, no leverage changes, and no orders.

## Agreed initial profile

- Starting capital reference: IDR 200,000 (convert the actual available futures balance to USDT before running).
- Active style, but only one setup per symbol snapshot; no forced entries.
- BTCUSDT and ETHUSDT.
- Entry timeframe: 15m; trend confirmation: 1h.
- Long and Short.
- Maximum leverage parameter: 10x.
- Risk budget: 1% of supplied USDT balance per trade.
- Minimum planned reward/risk: 2:1.
- Stop distance: 1.2 × ATR(14).

## Signal rules

1. 1h trend: EMA20 > EMA50 and close > EMA20 for Long; inverse for Short.
2. 15m Long: RSI(14) > 50, MACD histogram positive and rising, volume ratio >= 1.1.
3. 15m Short: RSI(14) < 50, MACD histogram negative and falling, volume ratio >= 1.1.
4. Entry is the last closed candle close; SL uses 1.2 ATR and TP is 2R.
5. Neutral/incomplete data produces no signal.

This first strategy iteration intentionally keeps the rule set transparent. Support/resistance are retained in the Stage 2 dataset for subsequent filter/backtest refinement; they are not yet hard entry gates.

## Run (PowerShell)

Run Stage 2 first, then:

```powershell
python stage3.py --balance-usdt 12.50
```

Replace 12.50 with the actual available futures wallet balance expressed in USDT. Do not treat the IDR-to-USDT example as a live exchange rate.

Optional parameters:

```powershell
python stage3.py --balance-usdt 12.50 --risk 0.01 --leverage 10
```

Output: `data/signals/latest_signals.csv`.

## Important sizing limitations

The default quantity step, minimum quantity and minimum notional are placeholders, not verified Binance contract filters. Before any testnet execution, fetch and validate each symbol's current `exchangeInfo` filters (LOT_SIZE / MARKET_LOT_SIZE and MIN_NOTIONAL / NOTIONAL), contract precision, fee tier, and margin availability. Stage 3 must skip trades if the real exchange constraints cannot be met. Fees and slippage use conservative estimates in the sizing function; adjust to actual account fee tier and measured slippage.

## Validation

```powershell
python -m unittest discover -s tests -v
```

No live trading is implemented in Stage 3.
