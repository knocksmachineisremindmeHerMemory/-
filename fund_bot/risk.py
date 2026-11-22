"""Risk rules from the setup prompt (sections 8, 10, 14). Pure functions, no I/O."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN

@dataclass(frozen=True)
class Limits:
    risk_per_trade: Decimal = Decimal("0.01")
    daily_loss: Decimal = Decimal("0.03")
    kill_switch: Decimal = Decimal("0.15")
    max_leverage: Decimal = Decimal("2")
    max_position_frac: Decimal = Decimal("2")   # notional / equity cap
    event_window_min: int = 30

@dataclass(frozen=True)
class MarketRules:
    tick: Decimal
    step: Decimal
    min_qty: Decimal
    min_notional: Decimal

class Reject(Exception):
    pass

def round_down(x: Decimal, step: Decimal) -> Decimal:
    return (x / step).to_integral_value(rounding=ROUND_DOWN) * step

def size_from_stop(equity, entry, stop, lim: Limits, rules: MarketRules) -> Decimal:
    equity, entry, stop = Decimal(equity), Decimal(entry), Decimal(stop)
    if stop is None or stop <= 0:
        raise Reject("no stop, no trade")
    dist = abs(entry - stop)
    if dist == 0:
        raise Reject("stop equals entry")
    qty = equity * lim.risk_per_trade / dist
    cap = equity * min(lim.max_leverage, lim.max_position_frac) / entry
    qty = round_down(min(qty, cap), rules.step)
    if qty < rules.min_qty:
        raise Reject("below min qty")
    if qty * entry < rules.min_notional:
        raise Reject("below min notional")
    return qty

def check_entry_allowed(equity, day_start_equity, high_water, lim: Limits):
    equity, day_start_equity, high_water = map(Decimal, (equity, day_start_equity, high_water))
    if equity <= high_water * (1 - lim.kill_switch):
        return "KILL"
    if equity <= day_start_equity * (1 - lim.daily_loss):
        return "DAILY_LIMIT"
    return "OK"

def in_event_window(now: datetime, events, lim: Limits) -> bool:
    w = timedelta(minutes=lim.event_window_min)
    return any(e - w <= now <= e + w for e in events)
