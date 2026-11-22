import os
from decimal import Decimal as D
from fund_bot import check_connection as cc

KEY, SEC = "AKIA_TESTKEY_123456", "s3cr3t_VALUE_abcdef"
SYM = "BTC/USDT:USDT"

class Fake:
    has = {"fetchAccounts": True, "fetchPositions": True}
    def __init__(self, sandbox=True, balance=10000, drift=0, accounts=("sub1",), boom=None, positions=()):
        self.isSandboxModeEnabled, self._b, self._d = sandbox, balance, drift
        self._a, self._boom, self._p = accounts, boom, positions
        self.calls = []
    def fetch_time(self): return 1_700_000_000_000 + self._d
    def fetch_balance(self):
        if self._boom: raise RuntimeError(f"auth failed key={KEY} secret={SEC}")
        return {"total": {"USDT": self._b}}
    def fetch_accounts(self): return [{"id": a, "name": a} for a in self._a]
    def load_markets(self):
        return {SYM: {"precision": {"price": 0.1, "amount": 0.001},
                      "limits": {"amount": {"min": 0.001}, "cost": {"min": 5}}}}
    def fetch_open_orders(self, s): return []
    def fetch_positions(self, s): return list(self._p)
    def create_order(self, *a, **k): self.calls.append("create"); raise AssertionError("must never trade")
    def cancel_order(self, *a, **k): self.calls.append("cancel"); raise AssertionError("must never cancel")

def run(client, tmp_path, key=KEY, secret=SEC, **kw):
    env = tmp_path / ".env.fund"; env.write_text("x"); os.chmod(env, 0o600)
    kw.setdefault("expect_balance", 10000); kw.setdefault("expect_account", "sub1")
    return cc.run_checks(client, key, secret, str(env), SYM, now_ms=1_700_000_000_000, **kw)

def status(res, name): return {n: s for n, s, _ in res}[name]
def text(res): return " ".join(d for _, _, d in res)

def test_all_good(tmp_path):
    res = run(Fake(), tmp_path)
    assert all(s != cc.FAIL for _, s, _ in res)
    assert "MODE: PAPER (testnet)" in text(res)
    assert cc.report(res) == 0

def test_refuses_non_sandbox(tmp_path):
    res = run(Fake(sandbox=False), tmp_path)
    assert status(res, "testnet endpoint") == cc.FAIL and len(res) == 1   # stops before touching anything

def test_placeholder_keys_fail(tmp_path):
    assert status(run(Fake(), tmp_path, key="your_key"), "keys loaded") == cc.FAIL

def test_clock_drift_fails(tmp_path):
    assert status(run(Fake(drift=5000), tmp_path), "server clock") == cc.FAIL

def test_balance_mismatch_fails_and_within_tol_passes(tmp_path):
    assert status(run(Fake(balance=9000), tmp_path), "balance") == cc.FAIL
    assert status(run(Fake(balance=10050), tmp_path), "balance") == cc.PASS

def test_balance_without_expectation_only_warns(tmp_path):
    assert status(run(Fake(), tmp_path, expect_balance=None), "balance") == cc.WARN

def test_wrong_subaccount_fails(tmp_path):
    assert status(run(Fake(accounts=("main",)), tmp_path), "account name") == cc.FAIL

def test_secrets_never_in_output(tmp_path, capsys):
    res = run(Fake(boom=True), tmp_path)
    cc.report(res)
    out = capsys.readouterr().out + text(res)
    assert KEY not in out and SEC not in out and "***" in out
    assert status(res, "balance") == cc.FAIL and cc.report(res) == 1

def test_never_places_or_cancels_orders(tmp_path):
    c = Fake(); run(c, tmp_path); assert c.calls == []

def test_loose_env_permissions_warn(tmp_path):
    env = tmp_path / ".env.fund"; env.write_text("x"); os.chmod(env, 0o644)
    res = cc.run_checks(Fake(), KEY, SEC, str(env), SYM, 10000, "sub1", now_ms=1_700_000_000_000)
    assert status(res, "env file permissions") == cc.WARN

def test_open_position_warns(tmp_path):
    res = run(Fake(positions=[{"contracts": 1}]), tmp_path)
    assert status(res, "open positions") == cc.WARN

def test_unlisted_symbol_fails(tmp_path):
    c = Fake(); c.load_markets = lambda: {}
    assert status(run(c, tmp_path), "market rules") == cc.FAIL

def test_load_keys_does_not_pollute_environ(tmp_path):
    env = tmp_path / "e"; env.write_text(f"EXCHANGE_API_KEY={KEY}\nEXCHANGE_API_SECRET={SEC}\n")
    assert cc.load_keys(str(env)) == (KEY, SEC) and "EXCHANGE_API_KEY" not in os.environ

def test_main_fails_closed_when_client_setup_fails(tmp_path, capsys, monkeypatch):
    def boom(ex, k, s): raise RuntimeError(f"cannot set sandbox, key={k}")
    monkeypatch.setattr(cc, "build_client", boom)
    env = tmp_path / "e"; env.write_text(f"EXCHANGE_API_KEY={KEY}\nEXCHANGE_API_SECRET={SEC}\n")
    rc = cc.main(["--exchange", "bybit", "--env-file", str(env), "--symbol", SYM])
    out = capsys.readouterr().out
    assert rc == 1 and KEY not in out and SEC not in out
