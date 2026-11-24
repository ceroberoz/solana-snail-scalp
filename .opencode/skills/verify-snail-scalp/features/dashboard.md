# Monitoring dashboard

The dashboard summarizes saved portfolio state, trade attribution, and the last backtest from files in the current directory. It reports empty sections honestly when no state exists.

## Sub-features

- `dashboard-empty` reports missing portfolio and attribution state.
- `dashboard-backtest` shows the last backtest after a real backtest run.
- `dashboard-degraded` survives unreadable or absent files with a message.

## How to get to it (user POV)

- Run `uv run python -m snail_scalp --dashboard` before any trading run.
- Run `uv run python -m snail_scalp --dashboard` after `--backtest`.
- Run it after a trading run that produced portfolio state or trade attribution.

## Driving it with verify_cli.py

Preconditions:

- A fresh seeded workdir for the empty-state drive, or a workdir that just completed a backtest for the populated drive.
- Doctor passed.

- **Empty state.** In a fresh workdir execute `verify_cli.py ... --label dashboard-empty --timeout 30 -- --dashboard`. Stdout contains `MONITORING DASHBOARD`, `No portfolio state file found.`, and `No trade attribution log yet (run a simulation first).`
- **Populated state.** After the backtest recipe in [backtest.md](./backtest.md), execute `verify_cli.py ... --label dashboard-backtest --timeout 30 -- --dashboard` in the same workdir. Stdout contains `Last Backtest: return` with the trade count and return from `data/backtest_report.json`.
- **Confirm the second view.** Read `$INIT_DIR/data/backtest_report.json` and confirm the numbers printed by the dashboard match its `performance` block.
- **Proof.** Keep `dashboard-empty.stdout.txt` and `dashboard-backtest.stdout.txt` with the report JSON copy; the pair proves both honest empty state and correct consumption of saved state.

## Gotchas

- Portfolio and attribution sections stay empty in this journey. That is correct: neither the seeded simulation nor the backtest writes `data/simulation_portfolio.json` or `data/trade_attribution.csv`. Do not seed those files by hand to force a populated display.
- The dashboard reads files relative to the current directory. A different workdir will show empty state even if a backtest ran elsewhere.
- `Last Backtest:` only appears after a report exists. Running the dashboard first and the backtest second does not populate the earlier output; rerun the dashboard.
- Do not assert exact return or drawdown values. Compare the dashboard line with the report file from the same run.
