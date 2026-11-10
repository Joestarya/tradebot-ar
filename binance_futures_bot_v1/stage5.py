from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
from src.history import fetch_historical_klines
from src.strategy_4h import calculate_4h_indicators
from src.backtest_4h import backtest_4h
ROOT=Path(__file__).resolve().parent
RAW=ROOT/"data"/"raw"; OUT=ROOT/"data"/"backtest_4h"
SYMBOLS=["BTCUSDT","ETHUSDT"]
def main():
    p=argparse.ArgumentParser(description="Stage 5: 4H SMA50/200 + RSI14 experiment")
    p.add_argument("--days",type=int,default=730)
    p.add_argument("--balance-usdt",type=float,required=True)
    p.add_argument("--risk",type=float,default=0.01)
    p.add_argument("--leverage",type=float,default=10.0)
    p.add_argument("--fee",type=float,default=0.0005,help="Fee per side; default example taker fee")
    p.add_argument("--slippage",type=float,default=0.0002,help="Adverse slippage per side; default 0.02%")
    p.add_argument("--atr-multiplier",type=float,default=2.0)
    p.add_argument("--reward-risk",type=float,default=2.0)
    a=p.parse_args(); RAW.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    summaries=[]; all_trades=[]
    for symbol in SYMBOLS:
        path=fetch_historical_klines(symbol,"4h",a.days,RAW)
        candles=pd.read_csv(path,parse_dates=["open_time","close_time"])
        frame=calculate_4h_indicators(candles)
        trades,summary=backtest_4h(frame,symbol,a.balance_usdt,a.risk,a.leverage,a.fee,
            a.slippage,a.atr_multiplier,a.reward_risk)
        trades.to_csv(OUT/f"{symbol}_trades.csv",index=False)
        summaries.append(summary); all_trades.append(trades)
        print("\n---",symbol,"---")
        for k,v in summary.items(): print(f"{k}: {v}")
    (OUT/"summary.json").write_text(json.dumps(summaries,indent=2),encoding="utf-8")
    pd.concat(all_trades,ignore_index=True).to_csv(OUT/"all_trades.csv",index=False)
    print(f"\nOutputs: {OUT}\nHistorical simulation only; no orders submitted.")
if __name__=="__main__": main()
