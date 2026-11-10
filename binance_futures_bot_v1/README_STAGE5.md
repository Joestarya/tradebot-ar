# Stage 5 — BTCUSDT 4H SMA 50/200 crossover + RSI 14

This experiment focuses on **BTCUSDT only**. Stage 3/4 remain unchanged.

## Strategy
- One timeframe only: 4h for indicators, signals, entries and exits.
- Symbol: BTCUSDT perpetual futures.
- SMA 50 and SMA 200 (simple moving averages).
- RSI 14 uses Wilder RMA, TradingView's default RSI smoothing method.
- LONG: golden cross (SMA50 crosses above SMA200) AND RSI14 > 50 on the closed 4H candle.
- SHORT: death cross (SMA50 crosses below SMA200) AND RSI14 < 50 on the closed 4H candle.
- Entry at next 4H open with adverse slippage.
- Stop: 2 x ATR(14) from actual fill. Target: 2R from actual fill.
- Exit at next 4H open after opposite SMA regime is confirmed.
- Entry candle checked for SL/TP; if both touched, assume SL first.

## Defaults and flexible sizing
- Starting balance: 500 USDT.
- Risk budget: 1% per trade (max accepted input 2%).
- Leverage: 3x, used for margin feasibility only; it does not multiply the risk budget.
- Fee: 0.05% per side (example taker fee; change to actual fee tier).
- Slippage: 0.02% per side (scenario assumption).
- Quantity step/minimum quantity: 0.001 and min notional 5 USDT are placeholders; verify current Binance BTCUSDT exchangeInfo before relying on sizing.
- Trades failing configured quantity/notional or margin constraints are skipped.

## Run
Default settings:
python stage5.py

Custom settings:
python stage5.py --days 730 --balance-usdt 300 --risk 0.01 --leverage 3 --fee 0.0005 --slippage 0.0002 --atr-multiplier 2 --reward-risk 2

Change quantity filters only after checking BTCUSDT exchangeInfo:
python stage5.py --quantity-step 0.001 --min-quantity 0.001 --min-notional 5

## Outputs
- data/backtest_4h/summary.json
- data/backtest_4h/all_trades.csv
- data/backtest_4h/BTCUSDT_trades.csv

## Limitations
- Public historical BTCUSDT candles only; no API keys and no live orders.
- Funding, liquidation, partial fills, spread variation and maintenance-margin tiers are not modeled.
- Quantity step/minimum quantity/minimum notional are placeholders; verify current Binance exchangeInfo.
- This is an experiment, not evidence of a profitable edge. Validate out-of-sample before considering testnet/live.
