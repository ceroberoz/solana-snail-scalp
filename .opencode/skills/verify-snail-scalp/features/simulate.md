# Paper trade a price log

Single-token simulation replays a price log through the strategy and prints a trading summary without touching a wallet or the network.

## Sub-features

- `simulate-start` loads the seeded log and enters SIMULATION mode.
- `simulate-run` consumes every candle and exits cleanly at end of data.
- `simulate-summary` prints trades, wins, losses, PnL, and return.
- `simulate-results` writes the results file.

## How to get to it (user POV)

- Run `uv run python -m snail_scalp --simulate --fast` with the bundled sample log.
- Run `uv run python -m snail_scalp --simulate --log data/my_data.csv` with a custom log.
- Run `uv run python -m snail_scalp --simulate --speed 10 --profile balanced` to change pacing and profile.

## Driving it with verify_cli.py

Preconditions:

- A fresh seeded workdir whose `data/sample_price_data.csv` has 576 rows.
- Default trading window (09:00–11:00 UTC). Do not widen it.
- Doctor passed.

- **Enter simulation.** Execute `verify_cli.py ... --label simulate-fast --timeout 90 -- --simulate --fast --results data/simulation_results.json`. Stdout contains `Solana Snail Scalp Bot - SIMULATION` and `[DATA] Loaded 576 data points for simulation`.
- **Consume the log.** Read the same stdout for `[END] Simulation data exhausted` and `Simulation complete - no more data`. These prove the run reached the end rather than being killed.
- **Read the summary.** Stdout contains the block `TRADING SUMMARY` with lines `Total Trades:`, `Win Rate:`, `Total PnL:`, and `Return:`.
- **Confirm the side effect.** Stdout contains `Results saved to: data/simulation_results.json`. Read `$INIT_DIR/data/simulation_results.json` and confirm it is valid JSON.
- **Proof.** Keep `simulate-fast.command.txt`, `simulate-fast.stdout.txt`, and the results file copy together.

## Gotchas

- `--fast` only skips delays outside the 09:00–11:00 UTC window. With `--window-start 0 --window-end 24`, all 576 candles sleep up to 0.5s each and the run takes minutes. Keep the default window.
- The bundled log may produce zero trades; the summary then reports `Total Trades: 0`. That is a valid outcome, not a failure. Do not assert a trade occurred.
- `--simulate` without a log file prompts interactively to generate one. The helper cannot answer that prompt, so always verify with the seeded file present.
- `--results` accepts a custom path. Keep it under `data/` so the join with the workdir stays predictable.
