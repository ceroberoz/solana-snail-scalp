# Solana Snail Scalp Bot 🐌

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A conservative multi-token scalping strategy for Solana with automatic token screening and real market data support.

## Quick Start

```bash
# Install
git clone https://github.com/ceroberoz/solana-snail-scalp.git
cd solana-snail-scalp
uv sync

# Screen tokens
uv run python -m snail_scalp --screen

# Simulate with real data
uv run python -m snail_scalp --real-data --capital 20

# Backtest
uv run python -m snail_scalp --backtest --days 30
```

## CLI Commands

| Command | Description | Example Output |
|---------|-------------|----------------|
| `--screen` | Find best trading opportunities | Top 5 tokens with hype scores |
| `--real-data` | Simulate with real market data | Fetches CoinGecko data, shows PnL |
| `--backtest` | Test strategy historically | Win rate, max drawdown, Sharpe ratio |
| `--multi` | Multi-token trading mode | Portfolio tracking across 3 positions |
| `--simulate` | Single-token simulation | Price feed + indicator values |

## Common Usage Examples

### 1. Screen for Opportunities
```bash
uv run python -m snail_scalp --screen
```

**Expected Output:**
```
[ROCKET] SOLANA SCALPING DASHBOARD

[TARGET] TOP SCALPING CANDIDATES:
#   Symbol    Price       24h%      Vol/MCap    Risk      Score
1   COPPERINU $0.006442   +29.7%    1.83x       HIGH      83.4
2   BIRB      $0.312900   +26.8%    3.65x       MODERATE  78.7
3   PENGUIN   $0.031040   +16.1%    1.16x       MODERATE  83.5

Watchlist exported to: data/screening_watchlist.json
```

### 2. Simulate with Real Data
```bash
uv run python -m snail_scalp --real-data --token solana --days 7 --capital 20
```

**Expected Output:**
```
======================================================================
REAL DATA SIMULATION MODE
======================================================================
Token: SOLANA
Days: 7
Capital: $20.00
======================================================================

[FETCH] Getting 7 days of solana data from CoinGecko...
[OK] Downloaded 168 price points

[MARKET DATA]
  Price Range: $76.56 - $89.98
  Change: +7.39%

======================================================================
SIMULATION RESULTS (REAL DATA)
======================================================================
Initial Capital:    $20.00
Total PnL:          $+0.45
Return:             +2.25%
Total Trades:       3
Win Rate:           66.7%
======================================================================
```

### 3. Backtest Strategy
```bash
uv run python -m snail_scalp --backtest --days 30 --capital 20
```

**Expected Output:**
```
======================================================================
BACKTEST RESULTS
======================================================================

Initial Capital: $20.00
Final Value: $23.17
Total Return: +15.84%
Total Trades: 245
Win Rate: 41.2%
Max Drawdown: 5.75%
Sharpe Ratio: 1.68

Report saved to: data/backtest_report.json
```

## Configuration

Edit `src/snail_scalp/config.py`:

```python
initial_capital = 20.0        # Starting capital
trading_start_utc = 9         # 09:00 UTC
trading_end_utc = 11          # 11:00 UTC
rsi_oversold_min = 25         # RSI entry lower bound
rsi_oversold_max = 35         # RSI entry upper bound
tp1_percent = 2.5             # First take profit
tp2_percent = 4.0             # Second take profit
stop_loss_percent = 1.5       # Stop loss
```

## Risk Management

| Limit | Value | Action |
|-------|-------|--------|
| Daily Loss | $1.50 (7.5%) | Stop trading |
| Consecutive Losses | 2 | 24h pause |
| Max Position | $6 (30%) | Per trade |
| Max Positions | 3 | Concurrent |

## Documentation

| Document | Description |
|----------|-------------|
| [Installation](docs/INSTALLATION.md) | Setup instructions |
| [CLI Reference](docs/CLI_REFERENCE.md) | All commands and flags |
| [Strategy](docs/STRATEGY.md) | How the trading strategy works |
| [Real Data](docs/REAL_DATA.md) | Using real market data |
| [Integration](docs/INTEGRATION.md) | Advanced usage and API |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and fixes |

## Project Structure

```
solana-snail-scalp/
├── src/snail_scalp/          # Source code
│   ├── cli.py                # CLI entry point
│   ├── token_screener.py     # Token ranking
│   ├── portfolio_manager.py  # Position tracking
│   ├── backtest_engine.py    # Historical testing
│   └── ...
├── data/                     # Data files
├── docs/                     # Documentation
├── examples/                 # Example scripts
└── README.md                 # This file
```

## Safety Disclaimer

⚠️ **Trading Risk**: Cryptocurrency trading carries significant risk. Never trade with money you cannot afford to lose completely. Past performance does not guarantee future results.

- Start with small capital ($20)
- Always backtest before live trading
- Monitor positions - this is semi-automated
- Use simulation mode first

## License

MIT License - Use at your own risk.
