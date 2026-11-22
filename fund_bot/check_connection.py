"""Read-only testnet connection check (prompt section 8, step 1-3).

Run on YOUR machine/server with testnet keys (trade-only, withdraw OFF, IP-locked):
    python -m fund_bot.check_connection --exchange bybit --env-file .env.fund \
        --symbol BTC/USDT:USDT --expect-balance 10000 --expect-account my-subaccount

Never places or cancels orders. Never prints keys. Refuses to run against a live endpoint.
Exit code 0 only when nothing FAILED.
"""
import argparse, os, stat, sys, time
from decimal import Decimal

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
PLACEHOLDERS = ("", "your_key", "your_secret", "changeme", "xxx")

def redact(text, secrets):
    text = str(text)
    for s in secrets:
        if s:
            text = text.replace(s, "***")
    return text

def load_keys(env_file):
    from dotenv import dotenv_values          # read the file only; do not touch os.environ
    vals = dotenv_values(env_file)
    return vals.get("EXCHANGE_API_KEY", ""), vals.get("EXCHANGE_API_SECRET", "")

def build_client(exchange, key, secret):
    import ccxt                                # pip install ccxt
    client = getattr(ccxt, exchange)({"apiKey": key, "secret": secret, "enableRateLimit": True})
    client.set_sandbox_mode(True)              # raises NotSupported -> we fail closed
    return client

def run_checks(client, key, secret, env_file, symbol, expect_balance=None, expect_account=None,
               tolerance=Decimal("0.01"), max_drift_ms=1000, quote="USDT", now_ms=None):
    out, secrets = [], (key, secret)
    add = lambda n, s, d: out.append((n, s, d))

    # 1. testnet only
    if getattr(client, "isSandboxModeEnabled", False) is True:
        add("testnet endpoint", PASS, "MODE: PAPER (testnet)")
    else:
        add("testnet endpoint", FAIL, "sandbox mode not confirmed; refusing to continue")
        return out

    # 2. keys / env file
    if key.strip().lower() in PLACEHOLDERS or secret.strip().lower() in PLACEHOLDERS:
        add("keys loaded", FAIL, "missing or placeholder key/secret in env file")
        return out
    add("keys loaded", PASS, f"key length {len(key)}, secret length {len(secret)} (values never shown)")
    try:
        mode = os.stat(env_file).st_mode
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            add("env file permissions", WARN, f"{env_file} readable by others; run chmod 600")
        else:
            add("env file permissions", PASS, "owner-only")
    except OSError:
        pass

    def guarded(name, fn):
        try:
            return fn()
        except Exception as e:                       # report, never leak secrets
            add(name, FAIL, redact(f"{type(e).__name__}: {e}", secrets))
            return None

    # 3. clock
    t = guarded("server clock", client.fetch_time)
    if t is not None:
        local = now_ms if now_ms is not None else int(time.time() * 1000)
        drift = abs(local - int(t))
        add("server clock", PASS if drift <= max_drift_ms else FAIL, f"drift {drift} ms (limit {max_drift_ms})")

    # 4. balance
    bal = guarded("balance", client.fetch_balance)
    if bal is not None:
        total = Decimal(str((bal.get("total") or {}).get(quote, 0) or 0))
        if expect_balance is None:
            add("balance", WARN, f"{total} {quote}; no --expect-balance given, cannot verify")
        else:
            exp = Decimal(str(expect_balance))
            ok = abs(total - exp) <= abs(exp) * tolerance
            add("balance", PASS if ok else FAIL, f"{total} {quote} vs expected {exp} (tol {tolerance:.0%})")

    # 5. account / sub-account
    if expect_account is not None:
        if getattr(client, "has", {}).get("fetchAccounts"):
            accts = guarded("account name", client.fetch_accounts)
            if accts is not None:
                names = {str(a.get("id")) for a in accts} | {str(a.get("name")) for a in accts}
                add("account name", PASS if expect_account in names else FAIL,
                    "matches expected sub-account" if expect_account in names else "expected account not found")
        else:
            add("account name", WARN, "exchange API cannot list accounts; verify the sub-account in the UI")
    else:
        add("account name", WARN, "no --expect-account given, cannot verify")

    # 6. market rules
    mk = guarded("market rules", client.load_markets)
    if mk is not None:
        m = mk.get(symbol)
        if not m:
            add("market rules", FAIL, f"{symbol} not listed on testnet")
        else:
            tick, step = (m.get("precision") or {}).get("price"), (m.get("precision") or {}).get("amount")
            lim = m.get("limits") or {}
            min_qty, min_cost = (lim.get("amount") or {}).get("min"), (lim.get("cost") or {}).get("min")
            missing = [n for n, v in (("tick", tick), ("step", step), ("min_qty", min_qty), ("min_notional", min_cost)) if v is None]
            add("market rules", WARN if missing else PASS,
                f"tick={tick} step={step} min_qty={min_qty} min_notional={min_cost}"
                + (f" (missing: {', '.join(missing)})" if missing else ""))

    # 7. existing orders / positions (read-only)
    oo = guarded("open orders", lambda: client.fetch_open_orders(symbol))
    if oo is not None:
        add("open orders", PASS if not oo else WARN, f"{len(oo)} open order(s) on {symbol}")
    if getattr(client, "has", {}).get("fetchPositions"):
        pos = guarded("open positions", lambda: client.fetch_positions([symbol]))
        if pos is not None:
            live = [p for p in pos if abs(float(p.get("contracts") or 0)) > 0]
            add("open positions", PASS if not live else WARN,
                f"{len(live)} open position(s); each must have a resting stop")

    add("permissions", WARN, "cannot be verified via API: confirm in the exchange UI that withdrawals are OFF and the key is IP-locked")
    return out

def report(results):
    width = max(len(n) for n, _, _ in results)
    for n, s, d in results:
        print(f"[{s}] {n.ljust(width)}  {d}")
    fails = sum(s == FAIL for _, s, _ in results)
    warns = sum(s == WARN for _, s, _ in results)
    print(f"\n{fails} failed, {warns} warning(s). " + ("NOT ready for paper trading." if fails else "Paper trading may proceed; resolve warnings first."))
    return 1 if fails else 0

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exchange", required=True)
    ap.add_argument("--env-file", default=".env.fund")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--expect-balance")
    ap.add_argument("--expect-account")
    ap.add_argument("--tolerance", default="0.01")
    ap.add_argument("--max-drift-ms", type=int, default=1000)
    ap.add_argument("--quote", default="USDT")
    a = ap.parse_args(argv)
    key, secret = load_keys(a.env_file)
    try:
        client = build_client(a.exchange, key, secret)
    except Exception as e:
        print(f"[FAIL] client setup  {redact(f'{type(e).__name__}: {e}', (key, secret))}")
        return 1
    return report(run_checks(client, key, secret, a.env_file, a.symbol, a.expect_balance,
                             a.expect_account, Decimal(a.tolerance), a.max_drift_ms, a.quote))

if __name__ == "__main__":
    sys.exit(main())
