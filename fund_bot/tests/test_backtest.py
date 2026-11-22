import numpy as np, pandas as pd, pytest
from fund_bot import backtest as bt

def make_df(n=1500, seed=1, drift=0.0, vol=0.02, funding=0.0):
    rng = np.random.default_rng(seed)
    r = rng.normal(drift, vol, n)
    close = 100 * np.exp(np.cumsum(r))
    open_ = np.r_[100, close[:-1]]
    idx = pd.date_range("2022-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame(dict(open=open_, close=close, funding=funding), index=idx)

def momentum(n):
    return lambda d: np.sign(d["close"].pct_change(n)).fillna(0)

def cheater(d):  # uses tomorrow's close: lookahead
    return np.sign(d["close"].shift(-1) / d["close"] - 1).fillna(0)

def full_long(d):
    return pd.Series(1, index=d.index)

# --- lookahead ---
def test_honest_signal_passes_lookahead():
    assert bt.lookahead_check(momentum(10), make_df()) == []
def test_cheating_signal_detected():
    assert len(bt.lookahead_check(cheater, make_df())) > 0
def test_centered_rolling_leak_detected():
    df = make_df()
    leaky = lambda d: np.sign(d["close"].rolling(5, center=True).mean() - d["close"]).fillna(0)
    assert len(bt.lookahead_check(leaky, df)) > 0

# --- costs / funding ---
def test_costs_reduce_return():
    df = make_df()
    free = bt.run_backtest(df, momentum(5), fee=0, slip=0)["net"].sum()
    paid = bt.run_backtest(df, momentum(5), fee=0.001, slip=0.0005)["net"].sum()
    assert paid < free
def test_cost_equals_turnover_times_rate():
    df = make_df()
    r = bt.run_backtest(df, momentum(5), fee=0.001, slip=0.0005)
    assert r["cost"].sum() == pytest.approx(r["pos"].diff().abs().fillna(r["pos"].abs()).sum() * 0.0015)
def test_funding_long_pays_short_receives():
    df = make_df(funding=0.001)
    long_r = bt.run_backtest(df, full_long, fee=0, slip=0)
    short_r = bt.run_backtest(df, lambda d: -full_long(d), fee=0, slip=0)
    assert long_r["funding"].sum() > 0 and short_r["funding"].sum() < 0
    assert long_r["net"].sum() == pytest.approx(long_r["gross"].sum() - long_r["funding"].sum())
def test_first_bar_has_no_position():
    r = bt.run_backtest(make_df(), full_long)
    assert r["pos"].iloc[0] == 0 and r["pos"].iloc[1] == 1

# --- stats ---
def test_deflated_sharpe_falls_with_more_trials():
    a = bt.deflated_sharpe(0.1, 500, 1)
    b = bt.deflated_sharpe(0.1, 500, 200)
    assert b < a
def test_max_drawdown_known():
    assert bt.max_drawdown([0.1, -0.5, 0.0]) == pytest.approx(-0.5)
def test_sharpe_zero_std():
    assert bt.sharpe([0.0] * 10) == 0.0

# --- baselines & walk-forward ---
def test_random_data_strategy_does_not_beat_random_baseline_reliably():
    df = make_df(seed=7, drift=0.0)
    mine = bt.run_backtest(df, momentum(10))
    base = bt.random_entry_baseline(df, mine["pos"], n=60)
    pct = (base < mine["net"].sum()).mean()
    assert pct < 0.97          # on pure noise, no edge should be flagged
def test_walk_forward_reports_only_oos_and_rolls():
    df = make_df(n=900)
    wf = bt.walk_forward(df, lambda n: momentum(n), [3, 10, 30], tune=360, test=90)
    assert len(wf["oos_net"]) == 540 and len(wf["picks"]) == 6
    assert wf["oos_net"].index[0] == df.index[360]
def test_walk_forward_needs_data():
    with pytest.raises(ValueError):
        bt.walk_forward(make_df(n=100), lambda n: momentum(n), [3], tune=360, test=90)

# --- verdict ---
def test_verdict_rules():
    assert bt.verdict(30, 0.99, True, True, -0.05).startswith("ANECDOTE")
    assert bt.verdict(80, 0.99, False, True, -0.05).startswith("FAIL")
    assert bt.verdict(80, 0.99, True, True, -0.20).startswith("FAIL")
    assert bt.verdict(80, 0.50, True, True, -0.05).startswith("INCONCLUSIVE")
    assert bt.verdict(80, 0.99, True, True, -0.05) == "PASS"
