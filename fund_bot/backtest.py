"""Backtest engine + integrity checks (prompt sections 5-6).

Convention: a signal computed from bar t's close is executed at bar t+1's open.
Costs: (fee + slippage) per side on every change in position. Funding: longs pay
`funding` (per bar) when positive, shorts receive.
"""
import numpy as np
import pandas as pd
from statistics import NormalDist

MIN_OOS_TRADES = 50

def run_backtest(df, signal_fn, fee=0.0010, slip=0.0005, funding_col="funding"):
    """df needs open/close; optional `funding` column. signal_fn(df)->Series in {-1,0,1}."""
    sig = signal_fn(df).reindex(df.index).fillna(0).clip(-1, 1)
    pos = sig.shift(1).fillna(0)                      # act on next bar
    bar_ret = df["close"] / df["open"] - 1            # held from open to close of the bar
    # approximate holding over open->open so overnight gap is included
    ret_oo = df["open"].shift(-1) / df["open"] - 1
    ret_oo.iloc[-1] = bar_ret.iloc[-1]
    gross = pos * ret_oo
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * (fee + slip)
    fund = pos * (df[funding_col] if funding_col in df else 0.0)
    net = gross - cost - fund
    trades = int((turnover > 0).sum())
    return dict(net=net, gross=gross, cost=cost, funding=fund, pos=pos, trades=trades)

def sharpe(r, periods=365):
    r = pd.Series(r).dropna()
    return 0.0 if r.std() == 0 else float(r.mean() / r.std() * np.sqrt(periods))

def max_drawdown(r):
    eq = (1 + pd.Series(r).fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1).min())

def deflated_sharpe(sr_per_period, n_obs, n_trials, skew=0.0, kurt=3.0, sr_var=None):
    """Probability that the true Sharpe > 0 after n_trials attempts (Bailey & Lopez de Prado)."""
    nd = NormalDist()
    sr_var = (1.0 / n_obs) if sr_var is None else sr_var
    emax = 0.0
    if n_trials > 1:
        g = 0.5772156649
        emax = np.sqrt(sr_var) * ((1 - g) * nd.inv_cdf(1 - 1 / n_trials)
                                  + g * nd.inv_cdf(1 - 1 / (n_trials * np.e)))
    denom = np.sqrt(1 - skew * sr_per_period + (kurt - 1) / 4 * sr_per_period ** 2)
    return nd.cdf((sr_per_period - emax) * np.sqrt(n_obs - 1) / denom)

def lookahead_check(signal_fn, df, probes=20, seed=0):
    """Signal at t must not change when future bars are removed. Returns list of leaking bars."""
    full = signal_fn(df)
    rng = np.random.default_rng(seed)
    idx = rng.choice(np.arange(30, len(df) - 1), size=min(probes, len(df) - 31), replace=False)
    leaks = []
    for i in sorted(idx):
        part = signal_fn(df.iloc[: i + 1])
        if part.iloc[-1] != full.iloc[i]:
            leaks.append(int(i))
    return leaks

def buy_and_hold(df):
    return df["close"].pct_change().fillna(0)

def random_entry_baseline(df, like_pos, n=200, seed=0, **kw):
    """Random signals with the same time-in-market and a similar flip rate as the strategy."""
    rng = np.random.default_rng(seed)
    p_in = float((like_pos != 0).mean())
    flips = max(float((like_pos.diff().abs() > 0).mean()), 1e-3)
    out = []
    for _ in range(n):
        state, s = 0, []
        for _ in range(len(df)):
            if rng.random() < flips:
                state = int(rng.random() < p_in) * (1 if rng.random() < 0.5 else -1)
            s.append(state)
        sg = pd.Series(s, index=df.index)
        out.append(run_backtest(df, lambda d, sg=sg: sg.reindex(d.index), **kw)["net"].sum())
    return np.array(out)

def walk_forward(df, signal_factory, param_grid, tune=360, test=90, **kw):
    """Tune on `tune` bars, evaluate the chosen params on the next `test` bars, roll forward.
    Reports only the concatenated out-of-sample returns."""
    oos, picks, start = [], [], 0
    while start + tune + test <= len(df):
        tr, te = df.iloc[start:start + tune], df.iloc[start + tune: start + tune + test]
        best = max(param_grid, key=lambda p: sharpe(run_backtest(tr, signal_factory(p), **kw)["net"]))
        # warm-up: give the test window the history it needs, but score only the test bars
        ctx = df.iloc[start: start + tune + test]
        res = run_backtest(ctx, signal_factory(best), **kw)
        oos.append(res["net"].iloc[tune:])
        picks.append(best)
        start += test
    if not oos:
        raise ValueError("not enough data for one walk-forward window")
    r = pd.concat(oos)
    return dict(oos_net=r, picks=picks, sharpe=sharpe(r), max_dd=max_drawdown(r))

def verdict(trades_oos, dsr, beats_bh, beats_random, dd, dd_limit=0.15):
    if trades_oos < MIN_OOS_TRADES:
        return "ANECDOTE (too few OOS trades)"
    if not (beats_bh and beats_random):
        return "FAIL (baseline)"
    if dd < -dd_limit:
        return "FAIL (drawdown over limit)"
    return "PASS" if dsr > 0.95 else "INCONCLUSIVE (deflated Sharpe)"
