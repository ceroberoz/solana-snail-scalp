"""Analyze trade attribution log produced by the bot."""
import csv
import os
from collections import defaultdict


def main():
    path = "data/trade_attribution.csv"
    if not os.path.exists(path):
        print("No trade attribution log found:", path)
        return

    rows = list(csv.DictReader(open(path)))
    if not rows:
        print("Empty log.")
        return

    print(f"Total trades: {len(rows)}")
    total_pnl = sum(float(r["pnl_usd"]) for r in rows)
    wins = sum(1 for r in rows if float(r["pnl_usd"]) > 0)
    print(f"Win rate: {wins/len(rows)*100:.1f}%  Total PnL: ${total_pnl:+.2f}\n")

    by_regime = defaultdict(lambda: [0, 0.0, 0])
    for r in rows:
        regime = r["entry_regime"] or "UNKNOWN"
        pnl = float(r["pnl_usd"])
        by_regime[regime][0] += 1
        by_regime[regime][1] += pnl
        if pnl > 0:
            by_regime[regime][2] += 1

    print("By regime:")
    print(f"{'Regime':<16}{'Trades':>8}{'WinRate':>10}{'PnL':>10}")
    for regime, (n, pnl, w) in sorted(by_regime.items()):
        print(f"{regime:<16}{n:>8}{(w/n*100 if n else 0):>9.1f}%{pnl:>10.2f}")

    # By symbol
    by_sym = defaultdict(lambda: [0, 0.0, 0])
    for r in rows:
        sym = r.get("symbol") or "UNKNOWN"
        pnl = float(r["pnl_usd"])
        by_sym[sym][0] += 1
        by_sym[sym][1] += pnl
        if pnl > 0:
            by_sym[sym][2] += 1

    print("\nBy symbol:")
    print(f"{'Symbol':<12}{'Trades':>8}{'WinRate':>10}{'PnL':>10}")
    for sym, (n, pnl, w) in sorted(by_sym.items()):
        print(f"{sym:<12}{n:>8}{(w/n*100 if n else 0):>9.1f}%{pnl:>10.2f}")

    # Confidence buckets
    buckets = defaultdict(lambda: [0, 0.0, 0])
    for r in rows:
        conf = float(r["entry_confidence"])
        bucket = f"{int(conf//10)*10}-{int(conf//10)*10+9}"
        pnl = float(r["pnl_usd"])
        buckets[bucket][0] += 1
        buckets[bucket][1] += pnl
        if pnl > 0:
            buckets[bucket][2] += 1

    print("\nBy confidence bucket:")
    print(f"{'Bucket':<10}{'Trades':>8}{'WinRate':>10}{'PnL':>10}")
    for bucket in sorted(buckets):
        n, pnl, w = buckets[bucket]
        print(f"{bucket:<10}{n:>8}{(w/n*100 if n else 0):>9.1f}%{pnl:>10.2f}")


if __name__ == "__main__":
    main()
