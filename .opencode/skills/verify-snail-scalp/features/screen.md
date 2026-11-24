# Screen memecoins offline

Screening ranks Solana memecoins and presents USDT-quoted candidates with liquidity and risk gates. Offline mode uses the bundled snapshot so the same result is reproducible without network access.

## Sub-features

- `screen-banner` announces the screening mode and its data source.
- `screen-usdt` shows USDT as the base quote currency and the liquidity gate.
- `screen-watchlist` exports ranked tokens to a watchlist file.
- `screen-live` queries DexScreener for live discovery (not covered offline).

## How to get to it (user POV)

- Run `uv run python -m snail_scalp --screen --offline` in a terminal.
- Run `uv run python -m snail_scalp --screen --min-liquidity 30000 --hype 70 --offline` with custom gates.
- Run `uv run python -m snail_scalp --screen` for live DEX discovery (network required).

## Driving it with verify_cli.py

Preconditions:

- A fresh seeded workdir from `verify_init.sh`.
- Doctor passed and no wallet credentials in the shell.

- **Enter screening.** Run the offline command. Execute `verify_cli.py ... --label screen-offline --timeout 30 -- --screen --offline`. Stdout contains `TOKEN SCREENING MODE - SOLANA MEMECOINS` and `Discovery Mode: OFFLINE MOCK DATA`.
- **Confirm quote and gate.** Read the same stdout. It contains `Base Currency:  USDT (Solana SPL)` and `Min Liquidity:  $20,000 USD (Rug/Liquidity Gate)`.
- **Confirm export.** Read the same stdout for `Watchlist exported to: data/screening_watchlist.json`, then read `$INIT_DIR/data/screening_watchlist.json` and confirm it parses as JSON with a `watchlist` list.
- **Custom gates.** Run a second drive with `--label screen-gates -- --screen --offline --min-liquidity 30000 --hype 70`. Stdout contains `Min Liquidity:  $30,000 USD` and `Min Hype Score: 70.0`.
- **Proof.** Keep `screen-offline.command.txt`, `screen-offline.stdout.txt`, and a copy of the exported watchlist JSON under the artifacts directory.

## Gotchas

- Plain `--screen` calls DexScreener. It is a live, non-deterministic path and is intentionally not verified here; report it as not covered rather than claiming it passed.
- A `--min-liquidity` value above every token's liquidity yields an empty watchlist. That is a valid result; assert the file and banner, not a minimum token count.
- `generated_at` in the watchlist changes each run. Never assert its value.
- A completed offline screen exits `0`. Assert the banner strings and the exported file.
