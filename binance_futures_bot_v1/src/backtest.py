from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .indicators import calculate_indicators
from .risk import calculate_position_size
from .strategy import _ema


@dataclass
class Trade:
    symbol: str
    side: str
    signal_time: str
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    stop_loss: float
    take_profit: float
    quantity: float
    gross_pnl: float
    fees: float
    net_pnl: float
    exit_reason: str
    balance_after: float

    def to_dict(self) -> dict:
        return asdict(self)


def _load_indicators(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["open_time", "close_time"])
    if df["open_time"].dt.tz is None:
        df["open_time"] = df["open_time"].dt.tz_localize("UTC")
        df["close_time"] = df["close_time"].dt.tz_localize("UTC")
    return calculate_indicators(df)


def _trend_at(df1h: pd.DataFrame, timestamp: pd.Timestamp) -> str:
    # Only use fully closed hourly candles available at the 15m signal close.
    eligible = df1h[df1h["close_time"] <= timestamp]
    if len(eligible) < 55:
        return "NEUTRAL"
    close = eligible["close"].astype(float)
    e20 = _ema(close, 20).iloc[-1]
    e50 = _ema(close, 50).iloc[-1]
    last = float(close.iloc[-1])
    if pd.isna(e20) or pd.isna(e50):
        return "NEUTRAL"
    if e20 > e50 and last > e20:
        return "LONG"
    if e20 < e50 and last < e20:
        return "SHORT"
    return "NEUTRAL"


def _signal(row: pd.Series, previous: pd.Series, trend: str,
            volume_threshold: float) -> Optional[str]:
    values = ["close", "rsi_14", "macd_hist", "atr_14", "volume_ratio"]
    if any(pd.isna(row.get(c)) for c in values):
        return None
    if trend == "LONG":
        if (row["rsi_14"] > 50 and row["macd_hist"] > 0
                and row["macd_hist"] > previous["macd_hist"]
                and row["volume_ratio"] >= volume_threshold):
            return "LONG"
    if trend == "SHORT":
        if (row["rsi_14"] < 50 and row["macd_hist"] < 0
                and row["macd_hist"] < previous["macd_hist"]
                and row["volume_ratio"] >= volume_threshold):
            return "SHORT"
    return None


def run_backtest(
    frames_15m: dict[str, pd.DataFrame],
    frames_1h: dict[str, pd.DataFrame],
    initial_balance: float,
    risk_fraction: float = 0.01,
    leverage: float = 10.0,
    fee_rate: float = 0.0005,
    slippage_rate: float = 0.0005,
    atr_multiplier: float = 1.2,
    reward_risk: float = 2.0,
    volume_threshold: float = 1.1,
    min_notional: float = 5.0,
) -> tuple[pd.DataFrame, dict]:
    """Single-position portfolio simulation; next-open entries; stop-first on ambiguous bars."""
    if initial_balance <= 0:
        raise ValueError("initial_balance must be positive")
    symbols = sorted(frames_15m)
    data: dict[str, pd.DataFrame] = {}
    hourly = frames_1h
    for symbol in symbols:
        df = frames_15m[symbol].copy().sort_values("open_time").reset_index(drop=True)
        data[symbol] = df
    timeline = sorted(set(t for df in data.values() for t in df["close_time"]))
    index_by_time = {
        symbol: {row.close_time: i for i, row in df.iterrows()}
        for symbol, df in data.items()
    }

    balance = float(initial_balance)
    peak = balance
    max_drawdown = 0.0
    position = None
    pending = None
    trades: list[dict] = []
    day_start_balance = balance
    current_day = None
    daily_locked = False
    equity_curve = []

    for timestamp in timeline:
        day = timestamp.date()
        if day != current_day:
            current_day = day
            day_start_balance = balance
            daily_locked = False

        # Manage an open trade using this candle's OHLC.
        if position is not None:
            symbol = position["symbol"]
            idx = index_by_time[symbol].get(timestamp)
            if idx is not None and timestamp > position["entry_time"]:
                bar = data[symbol].iloc[idx]
                side = position["side"]
                hit_sl = (bar["low"] <= position["sl"] if side == "LONG"
                          else bar["high"] >= position["sl"])
                hit_tp = (bar["high"] >= position["tp"] if side == "LONG"
                          else bar["low"] <= position["tp"])
                exit_reason = None
                raw_exit = None
                if hit_sl:
                    exit_reason, raw_exit = "STOP_LOSS", position["sl"]
                elif hit_tp:
                    exit_reason, raw_exit = "TAKE_PROFIT", position["tp"]
                if exit_reason:
                    exit_price = raw_exit * (1 - slippage_rate if side == "LONG"
                                              else 1 + slippage_rate)
                    gross = ((exit_price - position["entry"]) if side == "LONG"
                             else (position["entry"] - exit_price)) * position["qty"]
                    exit_fee = exit_price * position["qty"] * fee_rate
                    net = gross - position["entry_fee"] - exit_fee
                    balance += net
                    trade = {
                        "symbol": symbol, "side": side,
                        "signal_time": str(position["signal_time"]),
                        "entry_time": str(position["entry_time"]),
                        "exit_time": str(timestamp),
                        "entry": position["entry"], "exit": exit_price,
                        "stop_loss": position["sl"], "take_profit": position["tp"],
                        "quantity": position["qty"], "gross_pnl": gross,
                        "fees": position["entry_fee"] + exit_fee,
                        "net_pnl": net, "exit_reason": exit_reason,
                        "balance_after": balance,
                    }
                    trades.append(trade)
                    if balance <= day_start_balance * 0.98:
                        daily_locked = True
                    position = None

        # Pending signal is filled at the next 15m candle open.
        if position is None and pending is not None:
            symbol = pending["symbol"]
            idx = index_by_time[symbol].get(timestamp)
            if idx is not None and idx > 0 and not daily_locked:
                bar = data[symbol].iloc[idx]
                raw_entry = float(bar["open"])
                side = pending["side"]
                entry = raw_entry * (1 + slippage_rate if side == "LONG"
                                     else 1 - slippage_rate)
                sl, tp = pending["sl"], pending["tp"]
                size = calculate_position_size(
                    balance_usdt=balance, entry=entry, stop_loss=sl,
                    risk_fraction=risk_fraction, leverage=leverage,
                    fee_rate=fee_rate, slippage_rate=slippage_rate,
                    quantity_step=0.001, min_quantity=0.001,
                    min_notional=min_notional,
                )
                if size.accepted:
                    entry_fee = entry * size.quantity * fee_rate
                    position = {
                        "symbol": symbol, "side": side, "entry": entry,
                        "entry_time": timestamp, "signal_time": pending["signal_time"],
                        "sl": sl, "tp": tp, "qty": size.quantity,
                        "entry_fee": entry_fee,
                    }
            pending = None

        # Signal at candle close; choose BTC first if both symbols signal together.
        if position is None and pending is None and not daily_locked:
            candidates = []
            for symbol in symbols:
                idx = index_by_time[symbol].get(timestamp)
                if idx is None or idx < 1 or idx + 1 >= len(data[symbol]):
                    continue
                df = data[symbol]
                row, prev = df.iloc[idx], df.iloc[idx - 1]
                trend = _trend_at(hourly[symbol], timestamp)
                side = _signal(row, prev, trend, volume_threshold)
                if side:
                    close, atr = float(row["close"]), float(row["atr_14"])
                    distance = atr_multiplier * atr
                    sl = close - distance if side == "LONG" else close + distance
                    tp = close + reward_risk * distance if side == "LONG" else close - reward_risk * distance
                    candidates.append({
                        "symbol": symbol, "side": side, "sl": sl, "tp": tp,
                        "signal_time": timestamp,
                    })
            if candidates:
                pending = candidates[0]

        peak = max(peak, balance)
        drawdown = (peak - balance) / peak if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append({"time": timestamp, "balance": balance})

    # Any open position at end of dataset is closed at final available close.
    if position is not None:
        df = data[position["symbol"]]
        bar = df.iloc[-1]
        raw_exit = float(bar["close"])
        side = position["side"]
        exit_price = raw_exit * (1 - slippage_rate if side == "LONG" else 1 + slippage_rate)
        gross = ((exit_price - position["entry"]) if side == "LONG"
                 else (position["entry"] - exit_price)) * position["qty"]
        exit_fee = exit_price * position["qty"] * fee_rate
        net = gross - position["entry_fee"] - exit_fee
        balance += net
        trades.append({
            "symbol": position["symbol"], "side": side,
            "signal_time": str(position["signal_time"]),
            "entry_time": str(position["entry_time"]),
            "exit_time": str(bar["close_time"]), "entry": position["entry"],
            "exit": exit_price, "stop_loss": position["sl"],
            "take_profit": position["tp"], "quantity": position["qty"],
            "gross_pnl": gross, "fees": position["entry_fee"] + exit_fee,
            "net_pnl": net, "exit_reason": "END_OF_DATA",
            "balance_after": balance,
        })

    trade_df = pd.DataFrame(trades)
    wins = int((trade_df["net_pnl"] > 0).sum()) if not trade_df.empty else 0
    losses = int((trade_df["net_pnl"] <= 0).sum()) if not trade_df.empty else 0
    gross_profit = float(trade_df.loc[trade_df["net_pnl"] > 0, "net_pnl"].sum()) if not trade_df.empty else 0.0
    gross_loss = float(-trade_df.loc[trade_df["net_pnl"] <= 0, "net_pnl"].sum()) if not trade_df.empty else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
    summary = {
        "initial_balance": initial_balance,
        "final_balance": balance,
        "net_pnl": balance - initial_balance,
        "return_pct": (balance / initial_balance - 1) * 100,
        "trades": len(trade_df), "wins": wins, "losses": losses,
        "win_rate_pct": wins / len(trade_df) * 100 if len(trade_df) else 0.0,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_drawdown * 100,
    }
    return trade_df, summary
