"""Order flow: sizing -> entry -> exchange-resident stop -> logging (prompt section 8)."""
import csv, os
from decimal import Decimal
from datetime import datetime
from . import risk
from .mock_exchange import ExchangeError

COLUMNS = ["trade_id","strategy","mode","market","side","entry_time","entry_price","size",
           "stop","target","exit_time","exit_price","fees","funding","slippage","pnl",
           "r_multiple","reason_in","reason_out","regime","backtest_expected_r","notes"]

class Bot:
    def __init__(self, ex, limits, rules, mode="PAPER", log_path="trades.csv", alerts=None, go_live=False):
        if mode == "LIVE" and not go_live:
            raise PermissionError("LIVE needs explicit go-live approval")
        self.ex, self.lim, self.rules, self.mode = ex, limits, rules, mode
        self.log_path, self.alerts = log_path, alerts if alerts is not None else []
        self.day_start = self.high = Decimal(ex.equity)
        self.halted = False
        self.events = []
        self.n = 0
        if not os.path.exists(log_path):
            with open(log_path, "w", newline="") as f:
                csv.writer(f).writerow(COLUMNS)

    def banner(self):
        return f"MODE: {self.mode}"

    def _place_retry_once(self, *a, **k):
        try:
            return self.ex.place_order(*a, **k)
        except ExchangeError:
            try:
                return self.ex.place_order(*a, **k)
            except ExchangeError as e:
                raise e

    def enter(self, strategy, market, side, entry, stop, now, reason="", regime=""):
        status = risk.check_entry_allowed(self.ex.equity, self.day_start, self.high, self.lim)
        if status != "OK":
            self.halted = True
            self.alerts.append(status)
            raise risk.Reject(status)
        if risk.in_event_window(now, self.events, self.lim):
            raise risk.Reject("event window")
        entry, stop = Decimal(entry), Decimal(stop)
        if (side == "buy" and stop >= entry) or (side == "sell" and stop <= entry):
            raise risk.Reject("stop on wrong side")
        qty = risk.size_from_stop(self.ex.equity, entry, stop, self.lim, self.rules)
        stop = risk.round_down(stop, self.rules.tick)
        try:
            o = self._place_retry_once(side, qty, entry)
        except ExchangeError:
            self._cancel_strategy_orders()
            self.alerts.append("ORDER_FAILED")
            raise
        exit_side = "sell" if side == "buy" else "buy"
        try:
            self._place_retry_once(exit_side, qty, stop, order_type="stop", reduce_only=True, stop=True)
        except ExchangeError:
            # position without a stop is forbidden: flatten at once
            self.ex.place_order(exit_side, qty, entry, reduce_only=True)
            self.ex.position = None
            self.alerts.append("STOP_FAILED_FLATTENED")
            raise
        self.n += 1
        slip = abs(o["fill_price"] - entry) / entry
        row = dict.fromkeys(COLUMNS, "")
        row.update(trade_id=self.n, strategy=strategy, mode=self.mode, market=market, side=side,
                   entry_time=now.isoformat(), entry_price=o["fill_price"], size=qty, stop=stop,
                   fees=o["fee"], slippage=slip, reason_in=reason, regime=regime)
        with open(self.log_path, "a", newline="") as f:
            csv.DictWriter(f, COLUMNS).writerow(row)
        return o

    def _cancel_strategy_orders(self):
        for o in list(self.ex.orders.values()):
            if o["status"] == "open":
                self.ex.cancel(o["id"])
