# Solana Snail Scalp Bot - Integration Guide v1.2

## Overview

The bot has been upgraded with multi-token screening, portfolio management, and backtesting capabilities to help grow your initial capital through systematic scalping.

---

## New Features in v1.2

### 1. Token Screening (`--screen`)
Automatically screen and rank Solana tokens by hype, liquidity, and risk.

```bash
# Show best trading candidates
uv run python -m snail_scalp --screen

# Filter by hype score
uv run python -m snail_scalp --screen --hype 70

# Filter by risk level
uv run python -m snail_scalp --screen --risk moderate
```

**Output:**
- Top scalping candidates (liquidity + momentum)
- Risk category breakdown
- 2-hour trading watchlist
- Exported watchlist JSON

### 2. Backtest Engine (`--backtest`)
Test strategy performance on historical data before risking real capital.

```bash
# Run 30-day backtest (default)
uv run python -m snail_scalp --backtest

# Test with different capital
uv run python -m snail_scalp --backtest --capital 100 --days 60
```

**Metrics Provided:**
- Total Return %
- Win Rate
- Max Drawdown
- Sharpe Ratio
- Equity Curve

### 3. Multi-Token Trading (`--multi`)
Trade multiple tokens simultaneously with portfolio management.

```bash
# Simulation mode
uv run python -m snail_scalp --multi

# Live trading (use with caution!)
uv run python -m snail_scalp --multi --live
```

**Features:**
- Auto-screening before trading
- Up to 3 concurrent positions
- Risk-adjusted position sizing
- Individual token tracking

---

## Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `--screen` | Screen tokens and show rankings | `uv run python -m snail_scalp --screen` |
| `--backtest` | Run historical simulation | `uv run python -m snail_scalp --backtest --days 30` |
| `--multi` | Multi-token trading mode | `uv run python -m snail_scalp --multi` |
| `--simulate` | Single-token simulation | `uv run python -m snail_scalp --simulate` |
| `--reset` | Reset all state files | `uv run python -m snail_scalp --reset --screen` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SCREENING BOT                            │
├─────────────────────────────────────────────────────────────┤
│  Token Feed → Screener → Ranked Tokens → Trading Loop      │
│       ↓                                                      │
│  Portfolio Manager (3 max positions)                         │
│       ↓                                                      │
│  Risk Manager → Position Sizing → Entry/Exit                 │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **TokenScreener** - Technical + sentiment analysis scoring
2. **PortfolioManager** - Multi-position tracking and allocation
3. **RiskManager** - Circuit breakers and daily limits
4. **BacktestEngine** - Historical performance testing
5. **ScreeningTradingBot** - Main orchestrator

---

## Trading Strategy Integration

### Entry Criteria (Same as v1.0)
- Price touches lower Bollinger Band
- RSI between 25-35 (oversold)
- BB width > 2% (avoid flat markets)

### Risk Adjustments by Token

| Risk Level | Position Size | Stop Loss | Take Profit |
|------------|---------------|-----------|-------------|
| EXTREME | $1.50 (50%) | 1.0% | 2% / 3% |
| HIGH | $2.25 (75%) | 1.5% | 2.5% / 4% |
| MODERATE | $3.00 (100%) | 1.5% | 2.5% / 4% |
| LOW | $3.00 (100%) | 1.5% | 2.5% / 4% |

### Portfolio Limits
- Max 3 concurrent positions
- Max $6 per token (30% of $20)
- Daily loss limit: $1.50 (7.5%)
- Consecutive loss pause: 2 trades

---

## Workflow for Growing Capital

### Phase 1: Research & Backtest
```bash
# 1. Screen for opportunities
uv run python -m snail_scalp --screen

# 2. Backtest strategy
uv run python -m snail_scalp --backtest --days 30

# 3. Review results
cat data/backtest_report.json
```

### Phase 2: Paper Trading
```bash
# Run multi-token simulation
uv run python -m snail_scalp --multi

# Monitor for 1 week
# Check portfolio status in real-time
```

### Phase 3: Live Trading (Gradual)
```bash
# Week 1-2: $20 capital
uv run python -m snail_scalp --multi --live

# Week 3+: Scale up if profitable
uv run python -m snail_scalp --multi --live --capital 50
```

---

## Performance Tracking

### Portfolio State
Saved to `data/portfolio_state.json` (live) or `data/simulation_portfolio.json` (sim):
```json
{
  "initial_capital": 20.0,
  "available_capital": 15.5,
  "total_realized_pnl": 2.3,
  "total_unrealized_pnl": 0.8,
  "positions": { ... },
  "closed_positions": [ ... ]
}
```

### Backtest Report
Saved to `data/backtest_report.json`:
```json
{
  "performance": {
    "total_return_pct": 15.5,
    "win_rate": 58.3,
    "max_drawdown_pct": 8.2,
    "sharpe_ratio": 1.4
  },
  "equity_curve": [ ... ]
}
```

---

## Risk Management

### Token Selection Filters
- Min liquidity: $100k
- Min volume: $50k
- Min market cap: $500k
- Max risk: Configurable (default HIGH)

### Position Management
- Stop loss: 1.5% (adjustable by risk)
- Take profit: 2.5% (50%) + 4% (50%)
- DCA: -1% trigger, 50% additional
- Time stop: Close EOD if not hitting targets

### Circuit Breakers
- Daily loss > $1.50: Stop trading
- 2 consecutive losses: 24h pause
- Max 3 positions open

---

## Example Session

```bash
# 1. Check what's hot today
$ uv run python -m snail_scalp --screen
Top picks: COPPERINU, BIRB, PENGUIN

# 2. Backtest these picks
$ uv run python -m snail_scalp --backtest --days 14
Return: +12.5%, Win rate: 55%, Max DD: 6%

# 3. Run simulation to practice
$ uv run python -m snail_scalp --multi
[ENTRY] COPPERINU: Opened $3.00 at $0.006442
[TP1] COPPERINU: Closed 50% at $0.006603, PnL: +$0.08
[TP2] COPPERINU: Closed remaining at $0.006700, PnL: +$0.12

# 4. Review performance
Portfolio: $20.20 (+1.0%)
Open positions: 1/3

# 5. Go live when ready
$ uv run python -m snail_scalp --multi --live
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `data/top10_solana_coins.json` | Curated token data |
| `data/screening_watchlist.json` | Auto-generated watchlist |
| `data/backtest_report.json` | Backtest results |
| `data/portfolio_state.json` | Live portfolio state |
| `data/simulation_portfolio.json` | Sim portfolio state |

---

## Tips for Growing Capital

1. **Start Small**: Use $20 until consistent profitability
2. **Backtest First**: Validate on 30+ days of data
3. **Diversify**: Trade 2-3 tokens to spread risk
4. **Monitor Drawdown**: Keep max DD under 10%
5. **Scale Gradually**: Add $10-20 per week if profitable
6. **Review Weekly**: Check win rate and adjust filters

---

## Troubleshooting

### Issue: No tokens pass screening
**Solution**: Lower hype threshold or increase risk tolerance
```bash
uv run python -m snail_scalp --screen --hype 50 --risk high
```

### Issue: Backtest shows negative returns
**Solution**: Check market conditions, adjust strategy parameters in `config.py`

### Issue: Portfolio not updating
**Solution**: Check state files, reset if corrupted
```bash
uv run python -m snail_scalp --reset --multi
```

---

*Happy trading! Remember: Consistency > Home runs. Small daily gains compound.*
