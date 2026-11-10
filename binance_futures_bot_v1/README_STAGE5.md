# Stage 5 — 4H SMA 50/200 crossover + RSI 14

A separate experiment; Stage 3/4 remain unchanged.

## Rules
- One timeframe only: 4h for indicators, signals, entries and exits.
- SMA 50 and SMA 200 (simple moving averages).
- RSI 14 uses Wilder RMA, TradingView's default RSI smoothing method.
- LONG trigger: golden cross (SMA50 crosses above SMA200) AND RSI14 > 50 on the closed 4H candle.
- SHORT trigger: death cross (SMA50 crosses below SMA200) AND RSI14 < 50 on the closed 4H candle.
- Entry at next 4H open with adverse slippage.
- Stop: 2 x ATR(14) from actual fill. Target: 2R from actual fill.
- Exit at next 4H open after the opposite SMA regime is confirmed.
- Entry candle is checked for SL/TP; if both are touched, SL is assumed first.
- Risk sizing uses actual fill and stop; trades below minimum quantity/notional are skipped.

## Run
PowerShell: python stage5.py --days 730 --balance-usdt 12.50

## Outputs
- data/backtest_4h/summary.json
- data/backtest_4h/all_trades.csv
- Per-symbol BTCUSDT_trades.csv and ETHUSDT_trades.csv

## Limitations
- Public historical candles only; no API keys and no live orders.
- Fee default is 0.05% per side as an example taker fee; set your actual fee tier.
- Slippage default is 0.02% per side; compare 0.01%, 0.02%, and 0.05%.
- Funding, liquidation, partial fills, spread variation and maintenance margin tiers are not modeled.
- Quantity step/minimum notional are placeholders (0.001 and 5 USDT); verify current exchangeInfo.
- BTC and ETH are tested independently with the same starting balance; do not add their ending balances as one portfolio.
- This is an experiment, not evidence of a profitable edge. Validate out-of-sample before considering testnet/live.
