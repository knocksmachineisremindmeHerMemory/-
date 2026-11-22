"""Deterministic in-memory exchange for paper/dry-run tests."""
from decimal import Decimal
from itertools import count

class ExchangeError(Exception):
    pass

class MockExchange:
    def __init__(self, equity="10000", fail_next=0, fee_rate="0.0005", slip="0.0005"):
        self.equity = Decimal(equity)
        self.orders = {}
        self.position = None
        self.fail_next = fail_next       # number of upcoming place_order calls to reject
        self.fee_rate, self.slip = Decimal(fee_rate), Decimal(slip)
        self._ids = count(1)
        self.calls = []

    def place_order(self, side, qty, price, order_type="market", reduce_only=False, stop=False):
        self.calls.append(("place", order_type, side, qty, price, reduce_only, stop))
        if self.fail_next > 0:
            self.fail_next -= 1
            raise ExchangeError("rejected")
        oid = next(self._ids)
        o = dict(id=oid, side=side, qty=qty, price=price, type=order_type,
                 reduce_only=reduce_only, stop=stop, status="open")
        self.orders[oid] = o
        if order_type == "market" and not stop:
            sgn = 1 if side == "buy" else -1
            fill = price * (1 + sgn * self.slip)
            o.update(status="filled", fill_price=fill, fee=qty * fill * self.fee_rate)
            self.position = dict(side=side, qty=qty, entry=fill)
        return o

    def cancel(self, oid):
        self.calls.append(("cancel", oid))
        if oid in self.orders and self.orders[oid]["status"] == "open":
            self.orders[oid]["status"] = "cancelled"

    def open_stops(self):
        return [o for o in self.orders.values() if o["stop"] and o["status"] == "open"]

    def trigger_price(self, price):
        """Fill resting stops if price crosses them."""
        for o in self.open_stops():
            hit = price <= o["price"] if o["side"] == "sell" else price >= o["price"]
            if hit:
                # a gap through the stop fills at the worse (market) price, never better than the stop
                fill = min(o["price"], price) if o["side"] == "sell" else max(o["price"], price)
                o.update(status="filled", fill_price=fill, fee=o["qty"] * fill * self.fee_rate)
                self.position = None

    def settle(self, pnl):
        self.equity += pnl
