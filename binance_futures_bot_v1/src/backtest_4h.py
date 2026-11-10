from __future__ import annotations
import pandas as pd
from .risk import calculate_position_size
from .strategy_4h import signal_at_close

def _record(symbol, pos, exit_price, exit_time, gross, exit_fee, net, reason, balance):
    return {"symbol":symbol,"side":pos["side"],"signal_time":str(pos["signal_time"]),
        "entry_time":str(pos["entry_time"]),"exit_time":str(exit_time),
        "entry":pos["entry"],"exit":exit_price,"stop_loss":pos["sl"],
        "take_profit":pos["tp"],"quantity":pos["qty"],"gross_pnl":gross,
        "fees":pos["entry_fee"]+exit_fee,"net_pnl":net,"exit_reason":reason,
        "balance_after":balance}

def backtest_4h(df: pd.DataFrame, symbol: str, initial_balance: float,
    risk_fraction: float=0.01, leverage: float=10.0, fee_rate: float=0.0005,
    slippage_rate: float=0.0002, atr_multiplier: float=2.0,
    reward_risk: float=2.0, min_notional: float=5.0,
    quantity_step: float=0.001, min_quantity: float=0.001) -> tuple[pd.DataFrame,dict]:
    """Single-symbol 4H backtest; next-open fills; actual-fill SL/TP; stop-first ambiguity."""
    balance=float(initial_balance); pos=None; pending_entry=None; pending_exit=False; trades=[]
    for i in range(1,len(df)):
        bar=df.iloc[i]; ts=bar["close_time"]
        if pos is not None and pending_exit:
            raw=float(bar["open"]); side=pos["side"]
            exit_price=raw*(1-slippage_rate if side=="LONG" else 1+slippage_rate)
            gross=((exit_price-pos["entry"]) if side=="LONG" else (pos["entry"]-exit_price))*pos["qty"]
            fee=exit_price*pos["qty"]*fee_rate; net=gross-pos["entry_fee"]-fee; balance+=net
            trades.append(_record(symbol,pos,exit_price,ts,gross,fee,net,"MA_REGIME_EXIT",balance))
            pos=None; pending_exit=False
        if pos is None and pending_entry is not None:
            side=pending_entry["side"]; raw=float(bar["open"])
            entry=raw*(1+slippage_rate if side=="LONG" else 1-slippage_rate)
            dist=atr_multiplier*pending_entry["atr"]
            sl=entry-dist if side=="LONG" else entry+dist
            tp=entry+reward_risk*dist if side=="LONG" else entry-reward_risk*dist
            size=calculate_position_size(balance,entry,sl,risk_fraction,leverage,fee_rate,
                slippage_rate,quantity_step,min_quantity,min_notional)
            if size.accepted:
                pos={"side":side,"entry":entry,"entry_time":bar["open_time"],
                    "signal_time":pending_entry["signal_time"],"sl":sl,"tp":tp,
                    "qty":size.quantity,"entry_fee":entry*size.quantity*fee_rate}
            pending_entry=None
        # Check entry candle too; if both SL and TP are touched, assume SL first.
        if pos is not None:
            side=pos["side"]
            hit_sl=float(bar["low"])<=pos["sl"] if side=="LONG" else float(bar["high"])>=pos["sl"]
            hit_tp=float(bar["high"])>=pos["tp"] if side=="LONG" else float(bar["low"])<=pos["tp"]
            reason="STOP_LOSS" if hit_sl else "TAKE_PROFIT" if hit_tp else None
            if reason:
                raw=pos["sl"] if hit_sl else pos["tp"]
                exit_price=raw*(1-slippage_rate if side=="LONG" else 1+slippage_rate)
                gross=((exit_price-pos["entry"]) if side=="LONG" else (pos["entry"]-exit_price))*pos["qty"]
                fee=exit_price*pos["qty"]*fee_rate; net=gross-pos["entry_fee"]-fee; balance+=net
                trades.append(_record(symbol,pos,exit_price,ts,gross,fee,net,reason,balance))
                pos=None; pending_exit=False
        # Decisions are made at this candle close and executed at the next candle open.
        if pos is not None:
            pending_exit=((pos["side"]=="LONG" and bool(bar["bear_regime"])) or
                          (pos["side"]=="SHORT" and bool(bar["bull_regime"])))
        elif pending_entry is None:
            side=signal_at_close(bar)
            if side and i+1<len(df):
                pending_entry={"side":side,"atr":float(bar["atr_14"]),"signal_time":ts}
    if pos is not None:
        bar=df.iloc[-1]; side=pos["side"]; raw=float(bar["close"])
        exit_price=raw*(1-slippage_rate if side=="LONG" else 1+slippage_rate)
        gross=((exit_price-pos["entry"]) if side=="LONG" else (pos["entry"]-exit_price))*pos["qty"]
        fee=exit_price*pos["qty"]*fee_rate; net=gross-pos["entry_fee"]-fee; balance+=net
        trades.append(_record(symbol,pos,exit_price,bar["close_time"],gross,fee,net,"END_OF_DATA",balance))
    result=pd.DataFrame(trades)
    wins=int((result.net_pnl>0).sum()) if not result.empty else 0
    gp=float(result.loc[result.net_pnl>0,"net_pnl"].sum()) if not result.empty else 0.0
    gl=float(-result.loc[result.net_pnl<=0,"net_pnl"].sum()) if not result.empty else 0.0
    summary={"symbol":symbol,"timeframe":"4h","initial_balance":initial_balance,"final_balance":balance,
        "net_pnl":balance-initial_balance,"return_pct":(balance/initial_balance-1)*100,
        "trades":len(result),"wins":wins,"losses":len(result)-wins,
        "win_rate_pct":wins/len(result)*100 if len(result) else 0.0,
        "profit_factor":gp/gl if gl else (float("inf") if gp else 0.0),
        "gross_pnl":float(result.gross_pnl.sum()) if not result.empty else 0.0,
        "total_fees":float(result.fees.sum()) if not result.empty else 0.0,
        "expectancy_usdt":float(result.net_pnl.mean()) if not result.empty else 0.0}
    return result,summary
