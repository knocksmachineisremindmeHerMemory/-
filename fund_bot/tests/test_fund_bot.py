import csv
from datetime import datetime, timezone, timedelta
from decimal import Decimal as D
import pytest
from fund_bot import risk
from fund_bot.risk import Limits, MarketRules, Reject
from fund_bot.mock_exchange import MockExchange, ExchangeError
from fund_bot.bot import Bot, COLUMNS

RULES = MarketRules(tick=D("0.1"), step=D("0.001"), min_qty=D("0.001"), min_notional=D("5"))
L = Limits()
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)

def mk(tmp_path, **kw):
    ex = MockExchange(**{k: v for k, v in kw.items() if k in ("equity", "fail_next")})
    return ex, Bot(ex, L, RULES, log_path=str(tmp_path / "trades.csv"))

# --- sizing ---
def test_size_risks_one_percent():
    q = risk.size_from_stop(10000, 100, 98, L, RULES)   # risk $100 / $2 = 50, cap = 200
    assert q == D("50.000")
def test_size_capped_by_leverage():
    q = risk.size_from_stop(10000, 100, 99.9, L, RULES)  # raw 1000, cap 2x = 200
    assert q == D("200.000")
def test_no_stop_rejected():
    with pytest.raises(Reject): risk.size_from_stop(10000, 100, 0, L, RULES)
def test_stop_equals_entry():
    with pytest.raises(Reject): risk.size_from_stop(10000, 100, 100, L, RULES)
def test_min_notional_and_qty():
    with pytest.raises(Reject): risk.size_from_stop(10, 100, 50, L, RULES)
def test_round_down_step():
    assert risk.round_down(D("1.23456"), D("0.001")) == D("1.234")

# --- limits ---
def test_daily_loss_blocks():
    assert risk.check_entry_allowed(9699, 10000, 10000, L) == "DAILY_LIMIT"
    assert risk.check_entry_allowed(9701, 10000, 10000, L) == "OK"
def test_kill_switch():
    assert risk.check_entry_allowed(8500, 10000, 10000, L) == "KILL"
    assert risk.check_entry_allowed(8501, 8501, 10000, L) == "OK"
def test_event_window():
    ev = [NOW]
    assert risk.in_event_window(NOW - timedelta(minutes=29), ev, L)
    assert risk.in_event_window(NOW + timedelta(minutes=30), ev, L)
    assert not risk.in_event_window(NOW + timedelta(minutes=31), ev, L)

# --- bot flow ---
def test_live_requires_go_live(tmp_path):
    with pytest.raises(PermissionError):
        Bot(MockExchange(), L, RULES, mode="LIVE", log_path=str(tmp_path / "t.csv"))
    assert Bot(MockExchange(), L, RULES, mode="PAPER", log_path=str(tmp_path / "t2.csv")).banner() == "MODE: PAPER"

def test_entry_places_resting_stop_and_logs(tmp_path):
    ex, b = mk(tmp_path)
    b.enter("trend", "BTC", "buy", 100, 98, NOW, reason="test")
    stops = ex.open_stops()
    assert len(stops) == 1 and stops[0]["reduce_only"] and stops[0]["side"] == "sell"
    rows = list(csv.DictReader(open(tmp_path / "trades.csv")))
    assert list(rows[0].keys()) == COLUMNS and rows[0]["pnl"] == "" and rows[0]["exit_price"] == ""

def test_stop_triggers_without_bot(tmp_path):
    ex, b = mk(tmp_path)
    b.enter("trend", "BTC", "buy", 100, 98, NOW)
    ex.trigger_price(D("97"))     # bot "dead": exchange alone closes it
    assert ex.position is None

def test_wrong_side_stop(tmp_path):
    _, b = mk(tmp_path)
    with pytest.raises(Reject): b.enter("s", "BTC", "buy", 100, 102, NOW)
    with pytest.raises(Reject): b.enter("s", "BTC", "sell", 100, 98, NOW)

def test_retry_once_then_succeeds(tmp_path):
    ex, b = mk(tmp_path, fail_next=1)
    b.enter("s", "BTC", "buy", 100, 98, NOW)
    assert ex.position is not None

def test_two_failures_alert_and_cancel(tmp_path):
    ex, b = mk(tmp_path, fail_next=2)
    with pytest.raises(ExchangeError): b.enter("s", "BTC", "buy", 100, 98, NOW)
    assert "ORDER_FAILED" in b.alerts and ex.position is None

def test_stop_failure_flattens(tmp_path):
    ex, b = mk(tmp_path)
    orig = ex.place_order
    def flaky(*a, **k):
        if k.get("stop"): raise ExchangeError("no stop")
        return orig(*a, **k)
    ex.place_order = flaky
    with pytest.raises(ExchangeError): b.enter("s", "BTC", "buy", 100, 98, NOW)
    assert ex.position is None and "STOP_FAILED_FLATTENED" in b.alerts

def test_daily_limit_blocks_entry(tmp_path):
    ex, b = mk(tmp_path)
    ex.equity = D("9600")
    with pytest.raises(Reject): b.enter("s", "BTC", "buy", 100, 98, NOW)
    assert b.halted and ex.position is None

def test_event_window_blocks_entry(tmp_path):
    ex, b = mk(tmp_path)
    b.events = [NOW + timedelta(minutes=10)]
    with pytest.raises(Reject): b.enter("s", "BTC", "buy", 100, 98, NOW)

def test_slippage_logged(tmp_path):
    ex, b = mk(tmp_path)
    b.enter("s", "BTC", "buy", 100, 98, NOW)
    r = list(csv.DictReader(open(tmp_path / "trades.csv")))[0]
    assert D(r["slippage"]) == D("0.0005") and D(r["fees"]) > 0
