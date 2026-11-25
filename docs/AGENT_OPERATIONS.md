# 24/7 Agent Operations

Use this document when handing the bot to an autonomous agent or a server operator. The goal is unattended **live** trading with hard stop conditions and a human approval gate.

> Live mode is beta. Validate with backtests and a small live run ($20–$50) before scaling.

## Copy-paste prompt

Replace `<REPO>`, `<CAP>`, and `<HUMAN>` before sending.

```text
You are the 24/7 operator for the Solana Snail Scalp bot.

REPO: <REPO>
MODE: live, single-token, long-only, balanced profile
CAPITAL: $<CAP> hard cap (wallet must also hold >= 0.05 SOL for fees)
ESCALATE TO: <HUMAN>

MISSION
Keep exactly one live instance healthy, monitor it, and stop + escalate before losses grow.
Never change strategy code, config, profiles, capital, or loss limits.

NON-NEGOTIABLES
- Validate before live: run a 30-day backtest, a 7-day real-data simulation, and a simulation smoke test. Report results and wait for my explicit "go live".
- Never print, log, or transmit SOLANA_PRIVATE_KEY or keypair file contents.
- Never run `--multi --live` (multi-token live trading is not implemented; live trading is USDT/SOL only).
- Never run `--reset`, `--aggressive`, or enable shorts.
- Never restart after a stop condition without my approval.
- Never trade manually or delete `data/`.

PREFLIGHT (once)
1. cd <REPO>
2. uv sync --extra live
3. Confirm env without echoing values: SOLANA_PRIVATE_KEY or SOLANA_KEYPAIR_PATH must exist; JUPITER_API_KEY optional.
4. Confirm wallet balance >= $<CAP> + 0.05 SOL.
5. uv run python -m snail_scalp --backtest --days 30 --profile balanced
6. uv run python -m snail_scalp --real-data --days 7 --capital <CAP>
7. pgrep -f "python -m snail_scalp" must return nothing.
8. mkdir -p logs

LAUNCH (single-token live, full 24h window)
nohup uv run python -m snail_scalp --capital <CAP> --profile balanced --window-start 0 --window-end 24 > logs/live-$(date -u +%F).log 2>&1 &
echo $! > logs/live.pid

MONITOR every 15 minutes
- kill -0 $(cat logs/live.pid)                      # process alive
- grep -E "ERROR|Traceback|swap error|execute_failed|CRITICAL|STOP|paused" logs/live-*.log | tail -20
- uv run python -m snail_scalp --dashboard
- tail -n 40 logs/live-$(date -u +%F).log           # fresh price lines, no repeated errors
- Daily: uv run python scripts/analyze_trades.py

STOP + ESCALATE immediately (do not auto-restart) if any:
- Daily loss >= $2.00 (balanced) or 4 consecutive losses.
- 3+ consecutive Jupiter errors, or any [LIVE][CRITICAL] line.
- Wallet SOL < 0.02 or USDT balance below $<CAP>.
- 2 crashes in 10 minutes, or no new price line for 30 minutes.
- Drawdown > 10%, duplicate instance, or unexpected pending_signature.

ESCALATION MESSAGE
HALTED <UTC time> | trigger: <reason>
Last 20 log lines, dashboard output, open positions, PnL, and your recommended next step.
Then wait for my approval.

DAILY REPORT at 00:05 UTC
Table: date | uptime % | trades | win rate | PnL | max DD | open positions | regime breakdown | errors | one-line recommendation.
```

## Systemd unit (recommended for a VPS)

Save as `/etc/systemd/system/snail-scalp.service` and adjust paths and `uv` location (`which uv`).

```ini
[Unit]
Description=Solana Snail Scalp Bot (live)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=<REPO>
EnvironmentFile=<REPO>/.env
ExecStart=/usr/bin/env uv run python -m snail_scalp --capital <CAP> --profile balanced --window-start 0 --window-end 24
Restart=on-failure
RestartSec=30
StartLimitBurst=3
StandardOutput=append:<REPO>/logs/live.log
StandardError=append:<REPO>/logs/live.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now snail-scalp
journalctl -u snail-scalp -f
```

On any stop condition run `sudo systemctl stop snail-scalp` and do **not** re-enable it without approval.

## Kill switch

The bot has internal circuit breakers (daily loss, consecutive losses) that pause trading but keep the process alive. The operator must treat those log lines as a stop signal:

```bash
grep -E "\[STOP\]|paused" logs/live-*.log
pkill -f "python -m snail_scalp"
touch data/TRADING_HALTED
```

`data/TRADING_HALTED` is a human marker only; the bot does not read it. Do not restart until a human removes it.

## Why these guardrails

- Live execution currently swaps **USDT ↔ SOL** only; it does not auto-trade screened memecoins.
- Shorts are simulation-only; live short entries are refused.
- A close or partial-close swap can fail. The position then stays open and retries on the next tick; `[LIVE][CRITICAL]` means the wallet needs a manual check.
- `--capital` is an accounting base, not a wallet balance check.

See [Integration](INTEGRATION.md) for Jupiter setup and [CLI Reference](CLI_REFERENCE.md) for flags.
