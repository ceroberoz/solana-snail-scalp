# Trading Strategy Guide

## Overview

The Solana Snail Scalp Bot uses a **Bollinger Bands + RSI** mean reversion strategy designed for small capital ($20-$100).

## Entry Criteria

All conditions must be met:

```
1. Price touches or crosses below Lower Bollinger Band
2. RSI is between 25-35 (oversold, not extreme)
3. BB width > 2% (avoid flat markets)
4. Price above recent low (avoid falling knives)
```

### Visual Example

```
Price
  │    ╭──╮ Upper BB
  │   ╱    ╲
  │  ╱      ╲  ← Exit TP2 here (+4%)
  │ ╱   ╭──╮ ╲
  │╱   ╱    ╲ ╲
  │   ╱      ╲  ╲
  │  ╱   ●──────  Middle BB (TP1 target)
  │ ╱  ╱
  │╱  ╱  ← Entry here (Lower BB touch + RSI 25-35)
  └──╱──────────────────
      Lower BB
```

## Exit Strategy

### Take Profit Levels

| Level | Trigger | Action | Target |
|-------|---------|--------|--------|
| TP1 | +2.5% | Sell 50% | Middle BB |
| TP2 | +4.0% | Sell 50% | Upper BB |

### Stop Loss

- **Trigger**: -1.5% from entry
- **Action**: Close entire position
- **Risk**: ~$0.05 on $3 position

### DCA (Dollar Cost Average)

- **Trigger**: Price drops -1% from entry
- **Action**: Add 50% more ($1.50)
- **New Position**: Averaged entry price

## Risk Management

### Position Sizing

| Capital | Position Size | % of Capital |
|---------|--------------|--------------|
| $20 | $3.00 | 15% |
| $50 | $3.00 | 6% |
| $100 | $6.00 | 6% |

Risk-adjusted by token volatility:
- Extreme risk: 50% of normal size ($1.50)
- High risk: 75% of normal size ($2.25)
- Moderate/Low: 100% ($3.00)

### Daily Limits

| Limit | Value | Action |
|-------|-------|--------|
| Daily Loss | $1.50 | Stop trading for day |
| Consecutive Losses | 2 | 24-hour pause |
| Max Concurrent | 3 positions | Portfolio limit |

### Capital Allocation

```
$20 Capital:
├── Trading: $6 (30% - 2x $3 positions)
├── Emergency Reserve: $4 (20%)
├── Vault (untouchable): $10 (50%)
```

## Time Window

**Trading Hours:** 09:00 - 11:00 UTC

Why this window?
- Overlaps with US market open
- High volatility period
- Good liquidity on Solana
- 2-hour window prevents overtrading

## Indicators Explained

### Bollinger Bands (BB)

```python
Upper = SMA(20) + (STD(20) * 2)
Lower = SMA(20) - (STD(20) * 2)
Width = ((Upper - Lower) / SMA) * 100
```

**Interpretation:**
- Price at Lower BB = Potentially oversold
- Width > 2% = Good volatility for scalping
- Width < 2% = Avoid (flat market)

### RSI (Relative Strength Index)

```python
RSI = 100 - (100 / (1 + RS))
```

**Levels:**
- RSI < 25: Extreme oversold (risky)
- RSI 25-35: Oversold (entry zone)
- RSI 35-50: Neutral
- RSI > 70: Overbought (avoid)

## Trade Example Walkthrough

### Scenario: Winning Trade

```
1. ENTRY
   Price: $150.00
   RSI: 28 (oversold)
   Position: $3.00

2. PRICE MOVES UP (+2.5%)
   Price: $153.75
   Action: TP1 - Sell 50% ($1.50)
   Realized PnL: +$0.04

3. PRICE CONTINUES (+4%)
   Price: $156.00
   Action: TP2 - Sell remaining ($1.50)
   Realized PnL: +$0.06

TOTAL TRADE PnL: +$0.10 (+3.3% on $3 position)
PORTFOLIO RETURN: +0.5% on $20 capital
```

### Scenario: Losing Trade

```
1. ENTRY
   Price: $150.00
   RSI: 30
   Position: $3.00

2. PRICE DROPS (-1%)
   Price: $148.50
   Action: DCA - Add $1.50
   New average: $149.25
   Total position: $4.50

3. PRICE DROPS MORE (-1.5% from original)
   Price: $147.75
   Action: STOP LOSS - Close all
   Loss: -$0.07 on $4.50 position

TOTAL TRADE PnL: -$0.07 (-1.5%)
PORTFOLIO RETURN: -0.35% on $20 capital
```

## Expected Performance

Based on backtests with $20 capital:

| Metric | Conservative | Moderate | Aggressive |
|--------|--------------|----------|------------|
| Win Rate | 40-50% | 40-50% | 40-50% |
| Avg Win | +2.5% | +3.0% | +4.0% |
| Avg Loss | -1.5% | -1.5% | -1.5% |
| Daily Return | 0.5-1% | 1-2% | 2-3% |
| Max Drawdown | <10% | <15% | <25% |

**Compounding Example:**
```
Start: $20
Day 7: $20.70 (+3.5% weekly)
Day 30: $24.50 (+22% monthly)
Day 90: $35.80 (+79% quarterly)
```

## When Strategy Works Best

✅ **Good Conditions:**
- Sideways to slightly trending markets
- Normal volatility (BB width 2-5%)
- Regular pullbacks to lower BB

❌ **Avoid Conditions:**
- Strong trending markets (no pullbacks)
- Very low volatility (<2% BB width)
- Extreme volatility (>10% BB width)
- News events causing gaps

## When to Stop Trading

1. Daily loss limit hit ($1.50)
2. 2 consecutive losses
3. Outside trading window
4. Market conditions don't match strategy
5. Emotional/stressed

## Further Reading

- [John Bollinger's BB Rules](https://www.bollingerbands.com)
- [RSI Strategy Guide](docs/RSI_GUIDE.md)
- [Risk Management](docs/RISK.md)
