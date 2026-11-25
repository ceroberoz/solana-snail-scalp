# CLI Reference

Complete reference for all command-line options.

## Global Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--capital` | `-c` | 20.0 | Initial capital in USD |
| `--window-start` | | 9 | Trading window start (UTC hour) |
| `--window-end` | | 11 | Trading window end (UTC hour) |
| `--reset` | | | Reset all state files |
| `--results` | | data/simulation_results.json | Results file path |
| `--profile` | | default | Risk/strategy profile: default, balanced, aggressive |
| `--aggressive` | | | Shorthand for `--profile aggressive` |
| `--fast` | | | Skip per-candle delays in simulation |
| `--dashboard` | | | Show monitoring dashboard |

## Commands

### `--screen` - Token Screening

Find and rank real-time Solana memecoins dynamically using the DexScreener API with built-in rug/liquidity safety filtering.

```bash
# Live screening (default)
uv run python -m snail_scalp --screen

# Custom liquidity and hype gates
uv run python -m snail_scalp --screen --min-liquidity 30000 --hype 70

# Offline mode using cached snapshot
uv run python -m snail_scalp --screen --offline
```

**Options:**
- `--hype` (float): Minimum hype score (default: 60)
- `--risk` (str): Max risk level - minimal/low/moderate/high/extreme (default: extreme for memecoins)
- `--min-liquidity` (float): Minimum pool liquidity in USD (default: $20,000)
- `--offline` (flag): Use local/cached data instead of live DEX query

**Output:**
- Real-time Solana memecoin market metrics (price, 24h/1h momentum, liquidity, volume)
- Top 3–5 potential candidates for scalping with USDT on Solana (with real contract addresses and Jupiter swap routes)
- Risk category breakdown
- 2-hour trading watchlist
- Exported watchlist to `data/screening_watchlist.json`

---

### `--real-data` - Real Market Simulation

Fetch real historical data and run simulation.

```bash
# Default SOL data
uv run python -m snail_scalp --real-data

# Different token
uv run python -m snail_scalp --real-data --token bonk

# More days
uv run python -m snail_scalp --real-data --days 14 --capital 50
```

**Options:**
- `--token` (str): Token ID - solana/bonk/dogwifcoin
- `--days` (int): Days of history (default: 7)
- `--speed` (float): Simulation speed multiplier

**Output:**
```
[FETCH] Getting 7 days of solana data from CoinGecko...
[OK] Downloaded 168 price points

[MARKET DATA]
  Price Range: $76.56 - $89.98
  Change: +7.39%

[SIMULATION RESULTS]
Initial Capital:    $20.00
Total PnL:          $+0.45
Return:             +2.25%
Total Trades:       3
Win Rate:           66.7%
```

---

### `--backtest` - Historical Testing

Test strategy on historical token data.

```bash
uv run python -m snail_scalp --backtest
uv run python -m snail_scalp --backtest --days 60 --capital 100
```

**Options:**
- `--days` (int): Backtest period (default: 30)

**Output:**
```
Initial Capital: $20.00
Final Value: $23.17
Total Return: +15.84%
Total Trades: 245
Win Rate: 41.2%
Max Drawdown: 5.75%
Sharpe Ratio: 1.68
```

---

### `--multi` - Multi-Token Trading

Trade multiple tokens simultaneously in simulation mode.

```bash
# Simulation
uv run python -m snail_scalp --multi
```

> **Note:** Multi-token live execution is not supported. Real live trading currently executes on the single-token USDT/SOL pair only (`uv run python -m snail_scalp --capital 20`). Passing `--multi --live` exits with code `1` after an informative error.

**Output:**
```
[ENTRY] COPPERINU: Opened $3.00 at $0.006442
[TP1]   COPPERINU: Closed 50% at $0.006603, PnL: +$0.08
[TP2]   COPPERINU: Closed remaining at $0.006700, PnL: +$0.12

[PORTFOLIO] Value: $20.20 (+1.0%) | Open: 1/3
```

---

### `--simulate` - Single-Token Simulation

Simulate trading on sample or custom data.

```bash
# With sample data
uv run python -m snail_scalp --simulate

# With custom data
uv run python -m snail_scalp --simulate --log data/my_data.csv

# Faster simulation
uv run python -m snail_scalp --simulate --speed 10
```

**Options:**
- `--log` (str): Path to price log file
- `--speed` (float): Speed multiplier (default: 1.0)

**Output:**
```
[09:35:00] [SIM] Price: $149.2561 | Vol24h: $173,091,299
   RSI: 27.6 | BB Width: 6.46% | Data Points: 20

[ENTRY] ENTRY SIGNAL at $149.2561
[OK] Position opened: $3.00 @ $149.2561

[TP1] TP1 HIT at $152.9876 (+2.5%)
```

## Complete Command Examples

### Beginner Workflow

```bash
# 1. See what's hot today
uv run python -m snail_scalp --screen

# 2. Test with real data (small)
uv run python -m snail_scalp --real-data --days 3 --capital 20

# 3. Backtest longer period
uv run python -m snail_scalp --backtest --days 30
```

### Advanced Workflow

```bash
# 1. Screen with custom filters
uv run python -m snail_scalp --screen --hype 75 --risk moderate

# 2. Multi-token simulation
uv run python -m snail_scalp --multi --capital 50

# 3. Test specific token with real data
uv run python -m snail_scalp --real-data --token bonk --days 14

# 4. Full backtest with report
uv run python -m snail_scalp --backtest --days 90 --capital 100
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (check output) |

## File Outputs

| Command | Output File |
|---------|-------------|
| `--screen` | `data/screening_watchlist.json` |
| `--real-data` | `data/real_{token}_{days}d.csv` |
| `--backtest` | `data/backtest_report.json` |
| `--multi` | `data/simulation_portfolio.json` |
| `--simulate` | `data/simulation_results.json` |


---

### `--dashboard` - Monitoring Dashboard

Summarize portfolio state, trade attribution, and last backtest.

```bash
uv run python -m snail_scalp --dashboard
```

### `--profile` - Risk/Strategy Profile

```bash
uv run python -m snail_scalp --backtest --days 7 --profile aggressive
uv run python -m snail_scalp --simulate --profile balanced --fast
```

Profiles: `default` (conservative), `balanced`, `aggressive` (enables short entries).

