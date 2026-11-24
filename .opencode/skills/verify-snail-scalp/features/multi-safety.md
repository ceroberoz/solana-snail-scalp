# Multi-token safety gate

Multi-token mode ranks and simulates several tokens with a position cap. Its live variant is deliberately refused before any wallet or network use, which is the safety gate to verify.

## Sub-features

- `multi-sim-start` enters multi-token simulation with the expected limits.
- `multi-sim-bounded` runs the intentional loop until interrupted.
- `multi-live-refusal` refuses `--multi --live` with a clear message.

## How to get to it (user POV)

- Run `uv run python -m snail_scalp --multi --capital 20` for simulation.
- Run `uv run python -m snail_scalp --multi --live` to attempt live multi-token trading.
- Stop the simulation with Ctrl-C in the terminal.

## Driving it with verify_cli.py

Preconditions:

- A fresh seeded workdir.
- No wallet credentials in the driving shell.
- Doctor passed.

- **Enter multi simulation.** Execute `verify_cli.py ... --label multi-sim --timeout 8 --interrupt -- --multi --capital 20`. Stdout contains `MULTI-TOKEN TRADING MODE`, `Mode: SIMULATION`, `Initial Capital: $20.00`, `Max Positions: 3`, and `[STARTING TRADING LOOP]`.
- **Stop it cleanly.** The helper sends SIGINT at the timeout. Stdout contains `Stopped by user.` and contains no `[LIVE]` line. The recorded exit is `0`.
- **Check the live refusal.** In the same workdir run `verify_cli.py ... --label multi-live-guard --timeout 20 -- --multi --live`. Stdout contains `[NOT SUPPORTED] Multi-token live trading is not implemented.` and `Real live execution currently supports the single-token SOL/USDC path only.`
- **Confirm no execution side effects.** Confirm `$INIT_DIR` contains no `pending_swap.json` and no `portfolio_state.json` after both drives.
- **Proof.** Keep `multi-sim.stdout.txt` and `multi-live-guard.stdout.txt` together; the first shows bounded simulation, the second shows the refusal.

## Gotchas

- The multi-token loop never exits by itself. Without `--interrupt`, the helper kills it after the timeout and the shutdown line is missing.
- `--multi --live` currently exits `0` despite the refusal because `main()`'s return value is discarded. Assert the refusal text, never the exit code.
- Outside 09:00–11:00 UTC the loop prints `Outside trading window` and does not trade. That is expected; do not wait for an `[ENTRY]` line.
- Never add a wallet key to make this drive "more realistic". The gate must be proven with no wallet present.
