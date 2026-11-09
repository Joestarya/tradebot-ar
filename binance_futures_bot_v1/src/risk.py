from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class PositionSize:
    quantity: float
    notional: float
    margin_required: float
    estimated_loss: float
    risk_budget: float
    accepted: bool
    reason: str


def calculate_position_size(
    balance_usdt: float,
    entry: float,
    stop_loss: float,
    risk_fraction: float = 0.01,
    leverage: float = 10.0,
    fee_rate: float = 0.0005,
    slippage_rate: float = 0.0005,
    quantity_step: float = 0.001,
    min_quantity: float = 0.001,
    min_notional: float = 5.0,
) -> PositionSize:
    """Risk-based quantity sizing; fee/slippage estimates cover entry and exit."""
    values = [balance_usdt, entry, stop_loss, risk_fraction, leverage,
              fee_rate, slippage_rate, quantity_step, min_quantity, min_notional]
    if any(not math.isfinite(v) for v in values):
        raise ValueError("All sizing inputs must be finite")
    if balance_usdt <= 0 or entry <= 0 or stop_loss <= 0:
        raise ValueError("Balance, entry and stop_loss must be positive")
    if not 0 < risk_fraction <= 0.02:
        raise ValueError("risk_fraction must be > 0 and <= 2%")
    if leverage < 1 or quantity_step <= 0 or min_quantity < 0 or min_notional < 0:
        raise ValueError("Invalid leverage or exchange quantity constraints")
    if fee_rate < 0 or slippage_rate < 0:
        raise ValueError("Fee and slippage cannot be negative")

    risk_budget = balance_usdt * risk_fraction
    price_risk = abs(entry - stop_loss)
    round_trip_cost_per_unit = entry * 2 * (fee_rate + slippage_rate)
    loss_per_unit = price_risk + round_trip_cost_per_unit
    raw_qty = risk_budget / loss_per_unit
    quantity = math.floor(raw_qty / quantity_step) * quantity_step
    notional = quantity * entry
    margin = notional / leverage
    estimated_loss = quantity * loss_per_unit

    if quantity < min_quantity or notional < min_notional:
        return PositionSize(
            quantity=quantity, notional=notional, margin_required=margin,
            estimated_loss=estimated_loss, risk_budget=risk_budget,
            accepted=False,
            reason="Below exchange minimum quantity/notional; skip trade.",
        )
    if margin > balance_usdt:
        return PositionSize(
            quantity=quantity, notional=notional, margin_required=margin,
            estimated_loss=estimated_loss, risk_budget=risk_budget,
            accepted=False, reason="Required margin exceeds available balance.",
        )
    return PositionSize(
        quantity=quantity, notional=notional, margin_required=margin,
        estimated_loss=estimated_loss, risk_budget=risk_budget,
        accepted=True, reason="Sizing passed configured constraints.",
    )
