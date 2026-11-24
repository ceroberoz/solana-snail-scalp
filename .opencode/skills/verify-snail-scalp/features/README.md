# Snail-scalp verification map

This directory is the maintained source for verifying the user-facing behavior of the snail-scalp CLI. Read the index before driving, then use the matching feature file as the recipe.

## Baseline preconditions

- Run every command from the disposable workdir created by `scripts/verify_init.sh`, never from the repository root.
- The workdir's `data/` contains `sample_price_data.csv`, `top10_solana_coins.json`, and `live_screened_tokens.json`.
- `scripts/verify_cli.py` has `PYTHONPATH` set to the repository's `src` plus the available site-packages stand-in.
- No `SOLANA_PRIVATE_KEY` or `SOLANA_KEYPAIR_PATH` in the driving shell.
- Doctor passes: help banner and seeded files are present.
- Never drive an instance that was not started by this verification run.

## Driving conventions

- Start every journey from a fresh workdir unless its preconditions say otherwise.
- Treat every flag and expected string as literal. Keep quoted values unchanged.
- Use `--offline` for screening. Do not query DexScreener or CoinGecko during verification.
- Do not run the bare CLI (live mode) or pass a wallet.
- Bound long-lived modes with `--interrupt --timeout 8`.
- Assert output strings, side-effect files, and the exit code named in the feature file.

## Proof and skip reporting

- Capture the user action and the resulting state, not only a final success line.
- CLI proof includes the command, stdout, stderr, and exit code, all written by the helper.
- Mutation proof includes a read-only second view of the stored value, such as `--dashboard` after `--backtest`.
- Record the feature ID and entry point beside every artifact set.
- Report an unreachable path with the attempted command and the unmet precondition.
- Never report a skipped entry point as verified through a different path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing user-visible behavior. It uses exactly four H2 sections in this order:

1. `Sub-features` lists short IDs with one line per behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with verify_cli.py` starts with `Preconditions:` and pairs each user action with an exact command and observable result.
4. `Gotchas` lists traps that can waste or invalidate a run.

Keep implementation details out of the map. Name only user paths, stable flags, required state, and observable proof.

## Features

- [Screen memecoins offline](./screen.md) covers the offline screening banner, USDT base display, and watchlist export.
- [Paper trade a price log](./simulate.md) covers single-token simulation to completion, the summary, and the results file.
- [Backtest and monitor](./backtest.md) covers a bounded backtest, its report, and the dashboard reading that report.
- [Multi-token safety gate](./multi-safety.md) covers bounded multi-token simulation and the `--multi --live` refusal.
- [Monitoring dashboard](./dashboard.md) covers empty state and populated state from a prior backtest.
