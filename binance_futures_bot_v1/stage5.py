from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
from src.history import fetch_historical_klines
from src.strategy_4h import calculate_4h_indicators
from src.backtest_4h import backtest_4h

ROOT=Path(__file__).resolve().parent
RAW=ROOT/"data"/"raw"
OUT=ROOT/"data"/"backtest_4h"
SYMBOLS=["BTCUSDT"]

def main():
    p=argparse.ArgumentParser(description="Stage 5: 4H SMA50/200 + RSI14 experiment")
    p.add_argument("--days",type=int,default=730)
    p.add_argument("--balance-usdt",type=float,default=500.0,
                   help="Starting balance for BTCUSDT backtest; default 500 USDT")
    p.add_argument("--risk",type=float,default=0.01,
                   help="Risk budget per trade as fraction of balance; default 0.01 (1%%), max 2%%")
    p.add_argument("--leverage",type=float,default=3.0,
                   help="Leverage used for margin calculation; default 3x")
    p.add_argument("--fee",type=float,default=0.0005,help="Fee per side; default example taker fee")
    p.add_argument("--slippage",type=float,default=0.0002,help="Adverse slippage per side; default 0.02%%")
    p.add_argument("--atr-multiplier",type=float,default=2.0)
    p.add_argument("--reward-risk",type=float,default=2.0)
    p.add_argument("--quantity-step",type=float,default=0.001,
                   help="Placeholder; verify Binance exchangeInfo for each symbol")
    p.add_argument("--min-quantity",type=float,default=0.001,
                   help="Placeholder; verify Binance exchangeInfo for each symbol")
    p.add_argument("--min-notional",type=float,default=5.0,
                   help="Placeholder minimum notional in USDT; verify exchange rules")
    a=p.parse_args()
    if a.balance_usdt<=0: p.error("--balance-usdt must be positive")
    if not 0<a.risk<=0.02: p.error("--risk must be >0 and <=0.02")
    if a.leverage<1: p.error("--leverage must be >=1")
    RAW.mkdir(parents=True,exist_ok=True)
    OUT.mkdir(parents=True,exist_ok=True)
    summaries=[]
    all_trades=[]
    print(f"Settings: balance={a.balance_usdt} USDT | symbol=BTCUSDT | risk={a.risk:.2%} | leverage={a.leverage}x")
    for symbol in SYMBOLS:
        path=fetch_historical_klines(symbol,"4h",a.days,RAW)
        candles=pd.read_csv(path,parse_dates=["open_time","close_time"])
        frame=calculate_4h_indicators(candles)
        trades,summary=backtest_4h(
            frame,symbol,a.balance_usdt,a.risk,a.leverage,a.fee,a.slippage,
            a.atr_multiplier,a.reward_risk,a.min_notional,a.quantity_step,a.min_quantity)
        trades.to_csv(OUT/f"{symbol}_trades.csv",index=False)
        summaries.append(summary)
        all_trades.append(trades)
        print("\\n---",symbol,"---")
        for k,v in summary.items(): print(f"{k}: {v}")
    (OUT/"summary.json").write_text(json.dumps(summaries,indent=2),encoding="utf-8")
    pd.concat(all_trades,ignore_index=True).to_csv(OUT/"all_trades.csv",index=False)
    print(f"\\nOutputs: {OUT}\\nHistorical simulation only; no orders submitted.")

if __name__=="__main__":
    main()
