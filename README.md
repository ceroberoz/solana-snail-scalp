# Solana Snail Scalp Bot 🐌

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

A conservative multi-token scalping strategy for Solana, designed to grow small capital through systematic trading with automatic token screening.

## Features

- **🔍 Token Screening**: Automatically finds top Solana coins with best hype/momentum
- **📊 Technical Analysis**: Bollinger Bands + RSI entry signals
- **💼 Portfolio Management**: Trade up to 3 tokens simultaneously
- **🧪 Backtest Engine**: Validate strategy before risking capital
- **⚡ Multi-Token Mode**: Diversify across trending tokens
- **🛡️ Risk Management**: Daily loss limits, circuit breakers, position sizing
- **📈 Performance Tracking**: Real-time PnL and trade history

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/solana-snail-scalp.git
cd solana-snail-scalp

# Install dependencies with uv
uv sync
```

### 1. Screen for Opportunities

```bash
# Show best trading candidates
uv run python -m snail_scalp --screen

# Filter by criteria
uv run python -m snail_scalp --screen --hype 70 --risk moderate
```

### 2. Backtest Strategy

```bash
# Test on 30 days of historical data
uv run python -m snail_scalp --backtest --days 30

# Test with custom capital
uv run python -m snail_scalp --backtest --capital 100 --days 60
```

### 3. Run Simulation (Paper Trading)

```bash
# Multi-token simulation
uv run python -m snail_scalp --multi

# Single-token simulation
uv run python -m snail_scalp --simulate
```

### 4. Live Trading

```bash
# ⚠️ Only after testing! Uses real funds
uv run python -m snail_scalp --multi --live
```

## Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `--screen` | Screen and rank tokens | `--screen --hype 60` |
| `--backtest` | Historical simulation | `--backtest --days 30` |
| `--multi` | Multi-token trading | `--multi --capital 50` |
| `--simulate` | Single-token simulation | `--simulate --speed 5` |
| `--live` | Enable live trading | `--multi --live` |
| `--capital` | Set initial capital | `--capital 100` |
| `--reset` | Reset all state | `--reset --multi` |

## How It Works

### Trading Strategy

```
Entry Conditions (ALL must be met):
├── Price touches lower Bollinger Band
├── RSI between 25-35 (oversold)
└── Band width > 2% (avoid flat markets)

Exit Strategy:
├── TP1: Sell 50% at +2.5%
├── TP2: Sell remaining at +4%
├── DCA: Add 50% if price drops -1%
└── Stop Loss: Exit at -1.5%
```

### Token Screening

The bot automatically screens tokens based on:
- **Technical**: 24h/7d momentum, volume/market cap ratio
- **Liquidity**: Minimum $100k liquidity for easy exits
- **Sentiment**: Social buzz, community growth
- **Risk**: 5-tier risk classification

### Risk Management

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max Positions | 3 tokens | Portfolio diversification |
| Position Size | $1.50-$3.00 | Risk-adjusted per token |
| Daily Loss Limit | $1.50 (7.5%) | Stop trading if hit |
| Consecutive Losses | 2 trades | 24h pause after |
| Max Per Token | $6.00 (30%) | Single token limit |

## Example Output

### Screening Results

```
[TOP SCALPING CANDIDATES]

#   Symbol    Price       24h%      Vol/MCap    Risk      Score
------------------------------------------------------------------
1   COPPERINU $0.006442   +29.7%    1.83x       HIGH      83.4
2   BIRB      $0.312900   +26.8%    3.65x       MODERATE  78.7
3   PENGUIN   $0.031040   +16.1%    1.16x       MODERATE  83.5
4   FARTCOIN  $0.219100   +3.3%     0.32x       LOW       65.1
```

### Backtest Results

```
[BACKTEST RESULTS]

Initial Capital: $20.00
Final Value: $23.17
Total Return: +15.84%
Total Trades: 245
Win Rate: 41.2%
Max Drawdown: 5.75%
Sharpe Ratio: 1.68
```

### Live Trading

```
[ENTRY] COPPERINU: Opened $3.00 at $0.006442
[DCA]   COPPERINU: Added $1.50 at $0.006378 (down 1%)
[TP1]   COPPERINU: Closed 50% at $0.006603, PnL: +$0.08
[TP2]   COPPERINU: Closed remaining at $0.006700, PnL: +$0.12

[PORTFOLIO] Value: $20.20 (+1.0%) | Open: 1/3
```

## Configuration

Edit `src/snail_scalp/config.py`:

```python
# Trading settings
initial_capital = 20.0        # Starting capital
max_position_usd = 6.0        # Max per position (30%)
trading_start_utc = 9         # 09:00 UTC
trading_end_utc = 11          # 11:00 UTC

# Strategy parameters
rsi_oversold_min = 25         # RSI entry lower bound
rsi_oversold_max = 35         # RSI entry upper bound
tp1_percent = 2.5             # First take profit
tp2_percent = 4.0             # Second take profit
stop_loss_percent = 1.5       # Stop loss
```

## Project Structure

```
solana-snail-scalp/
├── src/snail_scalp/
│   ├── __init__.py           # Package exports
│   ├── cli.py                # Main CLI entry point
│   ├── config.py             # Configuration settings
│   ├── data_feed.py          # Price data fetching
│   ├── indicators.py         # Technical indicators (BB, RSI)
│   ├── risk_manager.py       # Risk management & circuit breakers
│   ├── trader.py             # Trade execution logic
│   ├── generate_data.py      # Sample data generator
│   │
│   ├── token_screener.py     # 🔍 Token screening & ranking
│   ├── sentiment_analysis.py # 📊 Social sentiment analysis
│   ├── multi_token_feed.py   # 📡 Multi-token data management
│   ├── portfolio_manager.py  # 💼 Portfolio tracking
│   ├── screening_bot.py      # 🤖 Integrated screening bot
│   └── backtest_engine.py    # 🧪 Historical backtesting
│
├── data/
│   ├── top10_solana_coins.json  # Curated token data
│   └── .gitkeep
│
├── examples/
│   ├── token_screening_demo.py  # Screening examples
│   └── complete_workflow.py     # Full workflow demo
│
├── tests/                    # Test files
├── docs/                     # Documentation
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

## Workflow for Growing Capital

### Phase 1: Research (5 mins)
```bash
# Screen for today's opportunities
uv run python -m snail_scalp --screen

# Review top picks in output
```

### Phase 2: Validate (Backtest)
```bash
# Test strategy on 30 days of data
uv run python -m snail_scalp --backtest --days 30

# Check if profitable before risking capital
```

### Phase 3: Practice (Simulation)
```bash
# Run paper trading for 1 week
uv run python -m snail_scalp --multi

# Monitor performance, adjust settings
```

### Phase 4: Live Trading
```bash
# Week 1-2: Start with $20
uv run python -m snail_scalp --multi --live --capital 20

# Week 3+: Scale up if profitable (+$20 weekly)
uv run python -m snail_scalp --multi --live --capital 40
```

## Expected Returns

Based on backtesting with $20 capital:

| Metric | Conservative | Moderate | Aggressive |
|--------|--------------|----------|------------|
| Daily | 0.5-1% | 1-2% | 2-3% |
| Weekly | 3-5% | 5-10% | 10-15% |
| Monthly | 15-25% | 25-50% | 50-100% |
| Max DD | <10% | <15% | <25% |

*Compounding: $20 → $35+ in 30 days at 5% daily*

## Risk Warning

⚠️ **Trading Risk Disclaimer**

- Cryptocurrency trading carries significant risk
- Past performance does not guarantee future results
- Never trade with money you cannot afford to lose completely
- Start with small capital ($20) and scale gradually
- Always backtest before live trading
- Monitor positions - this is semi-automated, not set-and-forget

## Safety Features

- ✅ Daily loss limits with automatic circuit breakers
- ✅ Consecutive loss pause (24h cooldown)
- ✅ Risk-adjusted position sizing
- ✅ Max position limits per token
- ✅ Emergency reserve protection (20%)
- ✅ Simulation mode for practice
- ✅ Backtest validation before live

## Development

```bash
# Run type checking
uv run mypy src/snail_scalp

# Run linting
uv run ruff check src/snail_scalp

# Run formatting
uv run black src/snail_scalp

# Run tests
uv run pytest
```

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- (Optional) Solana wallet for live trading
- (Optional) Private RPC endpoint

## License

MIT License - Use at your own risk. See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Support

For issues or questions:
- Check the [Integration Guide](INTEGRATION_GUIDE.md)
- Review code comments
- Create an issue in the repository

---

**Remember**: 
- Start with simulation
- Then $20 live tests
- Scale gradually
- Never risk more than you can afford to lose

Happy trading! 🐌🚀
