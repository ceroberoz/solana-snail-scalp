# Solana Snail Scalp Bot 🐌

[![Python 3.10+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A **regime-aware scalping bot for Solana memecoins**. It screens tokens, trades Bollinger Bands + RSI setups, and adapts its entry logic to the market: momentum in bull trends, mean reversion in ranges, and optional shorts in bear trends.

## Why run it

- **Adapts instead of forcing one strategy** — momentum when the market trends up, mean reversion when it ranges, short or stay flat when it trends down.
- **Built for small capital** — starts at $20 with per-trade and daily loss caps.
- **Test before you risk money** — screen tokens, simulate, and backtest with one CLI.
- **Live-ready** — executes real swaps through Jupiter v2 when simulation is disabled.
- **Explainable** — every trade records regime + confidence for later attribution.

## At a glance

| Capability | What you get |
|---|---|
| Token screening | Ranks Solana memecoins by hype, volume and risk |
| Entries | Bollinger Bands + RSI, regime-aware |
| Exits | ATR stops, breakeven, trailing, partial scale-outs, time exit |
| Risk | Dynamic sizing, correlation check, daily loss + consecutive-loss limits |
| Modes | screen · simulate · backtest · multi-token · live |

## Quick start

```bash
git clone https://github.com/ceroberoz/solana-snail-scalp.git
cd solana-snail-scalp
uv sync

uv run python -m snail_scalp --screen                  # find candidates
uv run python -m snail_scalp --backtest --days 30      # validate the strategy
uv run python -m snail_scalp --simulate --fast         # paper trade
```

Live trading requires a funded wallet and `solders`; see [Integration](docs/INTEGRATION.md).

## Documentation

| Doc | Contents |
|---|---|
| [Installation](docs/INSTALLATION.md) | Requirements, setup, project layout |
| [CLI Reference](docs/CLI_REFERENCE.md) | Commands, flags, example output |
| [Strategy](docs/STRATEGY.md) | Entry/exit logic, regimes, profiles, risk limits |
| [Real Data](docs/REAL_DATA.md) | CoinGecko / DexScreener data modes |
| [Integration](docs/INTEGRATION.md) | Jupiter live trading, APIs, webhooks |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and fixes |

## Safety

⚠️ Crypto trading is high risk. Start with $20, backtest and paper-trade first, and never use money you cannot afford to lose. Simulation is the default; live trading is opt-in.

## License

MIT — use at your own risk.
