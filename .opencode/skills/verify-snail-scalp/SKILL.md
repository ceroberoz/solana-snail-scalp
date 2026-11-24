---
name: verify-snail-scalp
description: Drive the solana-snail-scalp CLI in a disposable workdir to prove screen, simulate, backtest, multi-token safety, and dashboard behavior. Use when verifying changes to the CLI, its risk gates, or its saved reports.
---

# Verify solana-snail-scalp

The user-facing surface is a Python CLI: `python -m snail_scalp` (installed entry point `snail-scalp`). There is no web UI, server, or mobile app. Modes are selected by flags: `--screen`, `--simulate`, `--backtest`, `--multi`, `--dashboard`, and live trading with no mode flag. This skill drives the CLI only; it never drives the library internals or a test-only endpoint.

Live trading places real Jupiter swaps. Never run the CLI without a simulation/screening flag. The one safe live-adjacent check is `--multi --live`, which refuses before any wallet or network use.

Set these once per run:

```bash
REPO=$(cd "$(dirname "$SKILL_PATH")/../../.." && pwd)   # dir containing .opencode/
SKILL="$REPO/.opencode/skills/verify-snail-scalp"
SNAIL_VERIFY_SITE_PACKAGES="/Users/psanjaya/Library/Mobile Documents/com~apple~CloudDocs/Documents/Fun/Pinescript/.venv/lib/python3.9/site-packages"
```

`SNAIL_VERIFY_SITE_PACKAGES` is a local stand-in for `uv sync`; see Environment gaps.

## Launch

There is no long-lived server. Launch means creating a clean, isolated workdir seeded with the repository's fixtures, then starting one CLI process per drive.

```bash
WORKDIR_BASE=$(mktemp -d /private/var/folders/t8/5pkw24j10k5_fjpz2t2y4hf00000gn/T/opencode/snail-work-XXXXXX)
ARTIFACTS=$(mktemp -d /private/var/folders/t8/5pkw24j10k5_fjpz2t2y4hf00000gn/T/opencode/snail-proof-XXXXXX)
INIT_DIR="$WORKDIR_BASE/run"
bash "$SKILL/scripts/verify_init.sh" "$REPO" "$INIT_DIR"   # creates data/ with 3 seed files
```

`verify_init.sh` refuses an existing path. Give it the final workdir path, not a parent that already exists.

Ready means the seeded `data/` contains `sample_price_data.csv`, `top10_solana_coins.json`, and `live_screened_tokens.json`, and the CLI prints its usage banner. Confirm with the Doctor step. The canonical user command is `uv run python -m snail_scalp ...` from the repo root; never use it for verification because all outputs are relative `data/...` paths and would overwrite tracked files. Always run from `INIT_DIR` via the helper.

Teardown is in Cleanup.

## Doctor

Run this before driving anything. It answers: correct repo, correct runtime, seeded workdir, and no wallet credentials in the driving shell.

```bash
env | grep -E '^SOLANA_(PRIVATE_KEY|KEYPAIR_PATH)=' && echo "ABORT: wallet credentials present" || echo "no wallet credentials"
"$SKILL/scripts/verify_cli.py" --repo "$REPO" --workdir "$INIT_DIR" --artifacts "$ARTIFACTS" --label doctor-help --site-packages "$SNAIL_VERIFY_SITE_PACKAGES" --timeout 20 -- --help
grep -q "usage:" "$ARTIFACTS/doctor-help.stdout.txt"
grep -q "Solana Snail Scalp Bot" "$ARTIFACTS/doctor-help.stdout.txt"
ls "$INIT_DIR/data"
```

If the wallet check prints ABORT, stop: unset those variables in the driving shell before continuing. If help output or seeds are missing, fix that before driving; a skill run against a broken base teaches wrong steps.

## Drive

Use the helper for every drive. It sets `cwd=INIT_DIR`, sets `PYTHONPATH` to `$REPO/src` plus the stand-in site-packages, captures the command/stdout/stderr/exit code under `ARTIFACTS`, and kills only the process group it started.

```bash
"$SKILL/scripts/verify_cli.py" \
  --repo "$REPO" --workdir "$INIT_DIR" --artifacts "$ARTIFACTS" \
  --label <feature-id> --site-packages "$SNAIL_VERIFY_SITE_PACKAGES" \
  --timeout <seconds> [--interrupt] -- <snail_scalp flags...>
```

Stable handles are literal stdout strings, not line numbers. Every feature file names the exact flags and the strings to assert. Rules:

- Start each journey from a fresh workdir. Two commands that share state (backtest then dashboard) belong to one journey and share one workdir.
- Use `--screen --offline` only. Plain `--screen` queries DexScreener; `--real-data` queries CoinGecko. Both are live network paths and are outside this verification surface.
- Use the seeded `sample_price_data.csv` and the default 09:00–11:00 UTC window for `--simulate --fast`. See Gotchas for why widening the window makes the run take minutes.
- Bound the multi-token simulation with `--interrupt --timeout 8`. It is an intentional 24/7 loop and does not exit on its own.
- Assert observable output text, the side-effect files, and the exit code named in the feature file.

## Evidence

Proof artifacts live in `ARTIFACTS`, outside the workdir, so cleanup cannot delete them. For each drive the helper writes `<label>.command.txt`, `<label>.stdout.txt`, `<label>.stderr.txt`, and `<label>.exit.txt`.

A proof is only complete when it shows both the user action and the resulting state:

- The `.command.txt` file records the exact command. Keep it with the stdout/stderr pair.
- Assert the mode banner in stdout, then read the output file the run claims to have written. For example, after `--backtest`, read `data/backtest_report.json` from `INIT_DIR` and confirm its `performance.total_trades` matches the printed count. Do not trust the "Report saved to" line alone.
- Mutation proof needs a second user-facing read: run `--dashboard` after `--backtest` and confirm the dashboard's `Last Backtest:` line reflects the report you just read.
- `--screen --offline` is a real supported product boundary, not a mock added for tests. No other mocking is used here.
- Record the feature ID and entry point beside each artifact set. An unreachable path is reported with the attempted command and unmet precondition, never marked verified through a different path.

## Cleanup

Remove only the workdir this run created:

```bash
rm -rf "$INIT_DIR"
rmdir "$WORKDIR" 2>/dev/null || true
```

Never kill by process name and never remove `ARTIFACTS`. After cleanup, confirm the artifacts still exist. If a drive fails or times out, run this cleanup before retrying so no stranded workdir or process blocks the next attempt.

## Helpers

- `scripts/verify_init.sh <repo-root> <new-workdir>` creates an isolated `data/` and copies the three seed fixtures. Prints the workdir. Exits 1 if the path already exists.
- `scripts/verify_cli.py --repo ... --workdir ... --artifacts ... --label ... [--site-packages ...] [--timeout N] [--interrupt] -- <cli flags>` runs one bounded CLI drive and writes four proof files. `--interrupt` sends SIGINT on timeout so long-lived modes print their shutdown line.

## Feature map

Read [features/README.md](./features/README.md), then the file for the feature under test.

## Environment gaps (read before trusting a local proof)

- `uv` is not installed here. The canonical `uv run python -m snail_scalp ...` command was not executed.
- The available interpreter is `/usr/bin/python3` (3.9.6). `pyproject.toml` requires Python >=3.10. All local proof uses the stand-in site-packages path above, which supplies `numpy` and `aiohttp`. Treat results as a stand-in, not a verified production install.
- No funded wallet was used. Live swap execution, Jupiter network calls, and CoinGecko/DexScreener live fetches are not covered by this skill.
- `--multi --live` exits `1` after printing the refusal. `--help` and a completed backtest exit `0`. Assert the code named in the feature file.
- `--fast` only sets `skip_sleep` while outside the 09:00–11:00 UTC window; in-window candles each sleep up to 0.5s. Keep the default window when using the 576-row seed log.
