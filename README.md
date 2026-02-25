# Solana Snail Scalp Bot 🐌

A conservative scalping strategy for small-capital trading on Solana. Designed for $20 starting capital with strict risk management.

## Features

- **Simulation Mode**: Paper trade with historical/log data before risking real money
- **Bollinger Band Strategy**: Enter on lower band touch with RSI confirmation
- **Risk Management**: Daily loss limits, consecutive loss circuit breakers
- **Time-Boxed Trading**: Only trades during 09:00-11:00 UTC window
- **DCA Support**: Second entry if price drops 1% from initial entry
- **Partial Exits**: TP1 at 2.5% (50%), TP2 at 4% (remaining 50%)

## Requirements

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) - Modern Python package manager

## Quick Start

### 1. Installation

```bash
# Clone or download the project
git clone https://github.com/ceroberoz/solana-snail-scalp.git
cd solana-snail-scalp

# Install dependencies with uv
uv sync
```

### 2. Generate Sample Data (for simulation)

```bash
# Generate default sample data
uv run python -m snail_scalp.generate_data

# Generate with custom parameters
uv run python -m snail_scalp.generate_data --days 3 --interval 5

# Generate specific market scenarios
uv run python -m snail_scalp.generate_data --scenario trending_up
uv run python -m snail_scalp.generate_data --scenario trending_down
uv run python -m snail_scalp.generate_data --scenario sideways
uv run python -m snail_scalp.generate_data --scenario volatile
```

### 3. Run Simulation (Paper Trading)

```bash
# Basic simulation
uv run python -m snail_scalp --simulate

# Custom log file
uv run python -m snail_scalp --simulate --log data/my_data.csv

# 10x speed simulation
uv run python -m snail_scalp --simulate --speed 10

# Custom capital and window
uv run python -m snail_scalp --simulate --capital 50 --window-start 10 --window-end 12
```

### 4. Live Trading (⚠️ Use with caution)

```bash
# Edit config.py with your RPC and wallet first!
uv run python -m snail_scalp
```

## Command Line Options

| Flag | Description | Default |
|------|-------------|---------|
| `--simulate, -s` | Run in simulation mode | False |
| `--log, -l` | Path to price log file | `data/sample_price_data.csv` |
| `--speed, -x` | Simulation speed multiplier | 1.0 (real-time) |
| `--capital, -c` | Initial capital in USD | 20.0 |
| `--window-start` | Trading window start (UTC hour) | 9 |
| `--window-end` | Trading window end (UTC hour) | 11 |
| `--reset` | Reset all state files | False |
| `--results` | Path to save results | `data/simulation_results.json` |

## Development Commands

```bash
# Run type checking
uv run mypy src/snail_scalp

# Run linting
uv run ruff check src/snail_scalp

# Run formatting
uv run black src/snail_scalp

# Run tests (when added)
uv run pytest
```

## Strategy Configuration

Edit `src/snail_scalp/config.py` to adjust:

```python
# Entry conditions
rsi_oversold_min = 25        # RSI must be >= 25
rsi_oversold_max = 35        # RSI must be <= 35
min_band_width_percent = 2.0 # Avoid flat markets

# Position sizing
primary_allocation = 3.0     # $3 first entry
dca_allocation = 3.0         # $3 DCA entry

# Exit targets
tp1_percent = 2.5            # Sell 50% at +2.5%
tp2_percent = 4.0            # Sell 50% at +4%
stop_loss_percent = 1.5      # Stop at -1.5%
```

## Risk Limits

| Limit | Value | Action |
|-------|-------|--------|
| Daily Loss | $1.50 (7.5%) | Stop trading for the day |
| Consecutive Losses | 2 | Pause 24 hours |
| Max Position | $6 (30%) | Per trade limit |
| Emergency Reserve | $4 (20%) | Never trade this |
| Vault Reserve | $10 (50%) | Untouchable capital |

## Project Structure

```
solana-snail-scalp/
├── pyproject.toml          # Project configuration for uv
├── README.md              # This file
├── .gitignore             # Git ignore rules
├── src/
│   └── snail_scalp/       # Main package
│       ├── __init__.py    # Package exports
│       ├── cli.py         # Main entry point & CLI
│       ├── config.py      # Configuration settings
│       ├── data_feed.py   # Price data fetching (live + simulation)
│       ├── indicators.py  # Technical indicators (BB, RSI)
│       ├── risk_manager.py # Risk management & circuit breakers
│       ├── trader.py      # Trade execution logic
│       └── generate_data.py # Sample data generator
├── data/                  # Data files (CSV, JSON states)
│   ├── .gitkeep
│   └── sample_price_data.csv
├── tests/                 # Test files (to be added)
│   └── __init__.py
└── docs/                  # Documentation (to be added)
    └── .gitkeep
```

## Simulation Mode

The simulation mode allows you to test the strategy without risking real money:

```bash
# Generate different market scenarios
uv run python -m snail_scalp.generate_data --scenario trending_up
uv run python -m snail_scalp.generate_data --scenario trending_down
uv run python -m snail_scalp.generate_data --scenario sideways
uv run python -m snail_scalp.generate_data --scenario volatile

# Test with each scenario
uv run python -m snail_scalp --simulate --log data/scenario_trending_up.csv --speed 5
```

### Simulation Output

Results are saved to `data/simulation_trades.json`:

```json
{
  "total_pnl": 2.45,
  "total_trades": 5,
  "trades": [
    {
      "entry_price": 150.25,
      "exit_price": 154.75,
      "pnl_usd": 1.50,
      "close_reason": "tp2"
    }
  ]
}
```

## Live Trading Setup

⚠️ **WARNING**: Live trading requires:

1. **Solana Wallet**: Create a dedicated wallet with ONLY your trading capital
2. **RPC Endpoint**: Get a private RPC (Helius, QuickNode, etc.)
3. **Jupiter API**: Integration for swap execution
4. **Manual Oversight**: This is NOT set-and-forget

### Configuration

```python
# src/snail_scalp/config.py
API_ENDPOINTS = {
    'rpc': 'https://your-private-rpc.com',  # REPLACE THIS
}

PAIR_ADDRESS = "your-token-pair-address"     # VERIFY CURRENT
```

### Jupiter Integration (TODO)

The current implementation has placeholder comments where Jupiter API calls should go:

```python
# In trader.py, replace simulation blocks with:
# 1. Get quote from Jupiter
# 2. Check slippage < 0.8%
# 3. Execute swap
# 4. Store transaction signature
```

## Safety Checklist

Before live trading:

- [ ] Tested extensively in simulation mode
- [ ] Verified pair address is current
- [ ] Set up dedicated wallet with only $20
- [ ] Have emergency funds for priority fees
- [ ] Can monitor trades during 09:00-11:00 UTC
- [ ] Understand the bot may fail - have manual exit plan

## Important Disclaimers

1. **No Automatic Stop-Loss**: Due to Solana network limitations, stop-losses are checked on 5-minute intervals, not continuously.

2. **Manual Oversight Required**: This is a semi-automated tool. You must be available to intervene if the bot fails or RPC lags.

3. **Transaction Fees**: With $20 capital, a single failed transaction during congestion can cost $0.50 (2.5% of capital).

4. **Not Financial Advice**: This is educational code. Trading cryptocurrencies carries significant risk.

## Troubleshooting

### Simulation won't start
```bash
# Generate sample data first
uv run python -m snail_scalp.generate_data
```

### Module not found
```bash
# Reinstall dependencies
uv sync
```

### State file corruption
```bash
# Reset all state
uv run python -m snail_scalp --simulate --reset
```

## UV Tips

```bash
# Add a new dependency
uv add package_name

# Add a development dependency
uv add --dev package_name

# Update all dependencies
uv sync --upgrade

# Run a specific Python file
uv run python script.py

# Activate the virtual environment
source .venv/bin/activate
```

## License

MIT License - Use at your own risk.

## Support

For issues or questions, check the code comments or create an issue in the repository.

---

**Remember**: Start with simulation, then $5 live tests, then gradually increase. Never risk more than you can afford to lose completely.
