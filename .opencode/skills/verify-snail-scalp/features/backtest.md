# Backtest and monitor

A backtest replays historical token data, prints performance metrics, and saves a report that the dashboard later reads. The run is deterministic with seed 42.

## Sub-features

- `backtest-run` runs a bounded historical simulation.
- `backtest-metrics` prints return, trades, win rate, drawdown, and Sharpe ratio.
- `backtest-report` saves a JSON report.
- `backtest-dashboard` makes the report visible from the dashboard.

## How to get to it (user POV)

- Run `uv run python -m snail_scalp --backtest --days 7 --capital 20`.
- Run `uv run python -m snail_scalp --backtest --days 30 --capital 100` for the standard window.
- Apply a strategy profile with `--profile balanced` or `--aggressive`.

## Driving it with verify_cli.py

Preconditions:

- A fresh seeded workdir whose `data/top10_solana_coins.json` is present.
- Doctor passed.

- **Run the backtest.** Execute `verify_cli.py ... --label backtest-7d --timeout 60 -- --backtest --days 7 --capital 20`. Stdout contains `BACKTEST MODE`, `Capital: $20.00`, and `Days: 7`.
- **Read metrics.** Stdout contains `Total Trades:`, `Win Rate:`, `Max Drawdown:`, and `Sharpe Ratio:`, followed by an `INTERPRETATION` block.
- **Confirm the report side effect.** Stdout contains `Report saved to: data/backtest_report.json`. Read `$INIT_DIR/data/backtest_report.json` and confirm `performance.total_trades` equals the printed `Total Trades:` value. This is the read-only second view of the stored value.
- **Confirm dashboard visibility.** In the same workdir, run `verify_cli.py ... --label backtest-dashboard --timeout 30 -- --dashboard`. Stdout contains `Last Backtest: return` and the same trade count.
- **Proof.** Keep `backtest-7d.command.txt`, `backtest-7d.stdout.txt`, `backtest-dashboard.stdout.txt`, and the report JSON copy together.

## Gotchas

- Negative returns are a valid result. The CLI discards `main()`'s return value, so the process still exits `0`; assert metrics and the report, not the exit code.
- The engine seeds `random` with 42, so the same flags and fixture should reproduce the same trade count. Do not assert a specific PnL across code changes to the strategy.
- The hidden state file `data/.backtest_portfolio_42.json` is internal scratch. Do not use it as proof; read `backtest_report.json`.
- Keep the backtest and dashboard drives in one workdir. A fresh workdir has no report and the dashboard correctly reports no last backtest.
