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
        self.open = {}   # trade_id -> state of the open trade
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
            stop_o = self._place_retry_once(exit_side, qty, stop, order_type="stop", reduce_only=True, stop=True)
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
        self.open[self.n] = dict(side=side, qty=qty, entry=o["fill_price"], stop=stop,
                                 entry_fee=o["fee"], stop_id=stop_o["id"], funding=Decimal(0))
        return o

    # ---- exits and P&L ----
    def add_funding(self, trade_id, amount):
        """Funding paid (+) or received (-) on an open position, in quote currency."""
        self.open[trade_id]["funding"] += Decimal(amount)

    def sync(self, now, reason_out="stop"):
        """Record trades whose resting stop was filled by the exchange (works after a bot restart too)."""
        closed = []
        for tid, t in list(self.open.items()):
            so = self.ex.orders[t["stop_id"]]
            if so["status"] == "filled":
                self._close(tid, so["fill_price"], so["fee"], now, reason_out)
                closed.append(tid)
        return closed

    def close(self, trade_id, price, now, reason_out="manual"):
        t = self.open[trade_id]
        self.ex.cancel(t["stop_id"])
        exit_side = "sell" if t["side"] == "buy" else "buy"
        o = self._place_retry_once(exit_side, t["qty"], Decimal(price), reduce_only=True)
        self._close(trade_id, o["fill_price"], o["fee"], now, reason_out)

    def _close(self, tid, exit_price, exit_fee, now, reason_out):
        t = self.open.pop(tid)
        direction = 1 if t["side"] == "buy" else -1
        fees = t["entry_fee"] + exit_fee
        gross = (exit_price - t["entry"]) * t["qty"] * direction
        pnl = gross - fees - t["funding"]
        risk_amt = abs(t["entry"] - t["stop"]) * t["qty"]
        r_mult = pnl / risk_amt if risk_amt else None
        self._update_row(tid, exit_time=now.isoformat(), exit_price=exit_price, fees=fees,
                         funding=t["funding"], pnl=pnl,
                         r_multiple="" if r_mult is None else r_mult, reason_out=reason_out)
        self.ex.settle(pnl)
        eq = Decimal(self.ex.equity)
        self.high = max(self.high, eq)
        return pnl

    def _update_row(self, tid, **vals):
        with open(self.log_path, newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["trade_id"] == str(tid):
                r.update({k: str(v) for k, v in vals.items()})
        with open(self.log_path, "w", newline="") as f:
            w = csv.DictWriter(f, COLUMNS)
            w.writeheader()
            w.writerows(rows)

    def new_day(self):
        self.day_start = Decimal(self.ex.equity)
        self.halted = False

    def _cancel_strategy_orders(self):
        for o in list(self.ex.orders.values()):
            if o["status"] == "open":
                self.ex.cancel(o["id"])
