# Trading Strategy Guide

## Overview

The Solana Snail Scalp Bot uses an **adaptive Bollinger Bands + RSI** mean reversion strategy designed for small capital ($20-$100). The strategy has evolved through multiple sprints to include advanced risk management, intelligent position sizing, and dynamic exit strategies.

---

## Entry Strategy (Sprint 1-2)

### Entry Criteria - Enhanced

All conditions must be met for entry:

| # | Condition | Value | Rationale |
|---|-----------|-------|-----------|
| 1 | Price at Lower BB | `<= lower * 1.005` | 0.5% tolerance captures fast moves |
| 2 | RSI Range | 20-40 | Wider range captures more valid entries |
| 3 | Volume Confirmation | `> 1.3x` avg | Avoid low-liquidity fakeouts |
| 4 | BB Width | `> 2%` | Avoid flat markets |
| 5 | Price vs Recent Low | `> 99%` | Avoid falling knives |
| 6 | 15m RSI | `< 50` | Higher timeframe confirmation |

### RSI Range Evolution

**Original:** 25-35 (narrow, missed 40% of entries)  
**Enhanced:** 20-40 (wider, captures +15% more trades)

```python
# Configuration
rsi_oversold_min = 20  # Was 25
rsi_oversold_max = 40  # Was 35
```

### Volume Confirmation (US-1.2)

Entry requires current volume to be above the 20-period average:

```python
def _check_volume_confirmation(threshold=1.3):
    avg_volume = mean(volumes[:-1])
    return current_volume >= avg_volume * threshold
```

**Why:** High volume indicates genuine interest, low volume often precedes fakeouts.

### Multi-Timeframe Confirmation (US-1.4)

The 15-minute timeframe must confirm the 5-minute signal:

```
5m Signal: RSI 20-40, Price at Lower BB
    ↓
15m Check: RSI < 50 (not overbought)
    ↓
Entry Allowed
```

**Configurable:** Can be disabled via `enable_multi_timeframe = False`

---

## Exit Strategy (Sprint 1-2, 3-4)

### ATR-Based Dynamic Stops (US-2.1)

Instead of fixed 1.5% stops, the bot uses ATR (Average True Range) for dynamic stops:

```python
atr = calculate_atr(period=14)
stop_price = entry - (atr * 1.5)
max_stop = entry * (1 - 3%)  # Cap at 3%
final_stop = max(atr_stop, max_stop)
```

| Market Condition | ATR | Stop Distance |
|------------------|-----|---------------|
| Low volatility | 0.5% | ~0.75% |
| Normal | 1.5% | ~2.25% |
| High volatility | 3.0% | 3.0% (capped) |

**Benefit:** Stops adapt to market volatility - tighter in calm markets, wider in volatile markets.

### Breakeven Stop (US-2.2)

After TP1 hits, the stop is moved to breakeven plus a small buffer:

```
Entry: $100.00
TP1 Hit: $102.50 (+2.5%)
    ↓
Stop Moved: $100.10 (+0.1% buffer)
    ↓
Remaining Position: Protected
```

**Why:** Eliminates risk on remaining position after first profit.

### Trailing Stop (US-2.3)

After TP1, a trailing stop locks in profits:

```python
# Update every 5 minutes
if time_since_update >= 300:
    trailing_stop = highest_price * (1 - 1%)
    # Don't trail below breakeven
    effective_stop = max(trailing_stop, breakeven_price)
```

**Example:**
```
Price Action: $100 → $105 → $110 → $108
Trailing Stop:   --    --     --   $108.90 (1% below $110)
```

### Time-Based Exit (US-2.5)

Maximum hold time prevents tying up capital:

```python
max_hold_time_minutes = 120  # 2 hours

if hold_time >= max_hold:
    close_position(reason="TIME_EXIT")
```

**Why:** Positions held too long often consolidate; better to redeploy capital.

---

## Partial Profit Scaling (US-2.6)

Instead of just TP1 (50%) and TP2 (50%), the bot now scales out in 4 levels:

| Level | Portion | Profit Target | Action |
|-------|---------|---------------|--------|
| Scale 1 | 25% | +1.5% | Take profit |
| Scale 2 | 25% | +2.5% | Take profit |
| Scale 3 | 25% | +4.0% | Take profit |
| Final | 25% | Trailing | Let winners run |

**Benefits:**
- Captures profits at multiple levels
- Reduces risk as position gets profitable
- Final 25% rides trends with trailing protection

### Configuration

```python
partial_scale_levels = (
    (0.25, 1.5),   # 25% at +1.5%
    (0.25, 2.5),   # 25% at +2.5%
    (0.25, 4.0),   # 25% at +4.0%
)
final_trailing_after_scale = True
```

---

## Risk Management

### Improved DCA (US-3.1)

**Original:** DCA = 100% of original position (doubles risk)  
**Improved:** DCA = 50% of original position

```
Original Position: $3.00
Price drops 1%
    ↓
DCA Added: $1.50 (50% of $3.00)
    ↓
New Position: $4.50 total
New Average: Weighted average price
```

**Risk Comparison:**
- Old: $6.00 at risk after DCA (100% increase)
- New: $4.50 at risk after DCA (50% increase)

### Dynamic Position Sizing (US-3.2)

Position size is calculated based on entry confidence:

```python
confidence = calculate_confidence_score()  # 0-100
size_multiplier = 0.5 + (confidence / 100)  # 0.5x to 1.5x
position_size = base_size * size_multiplier
```

**Confidence Factors:**
| Factor | Weight | Calculation |
|--------|--------|-------------|
| RSI Depth | 40% | Lower RSI = higher confidence |
| Volume | 30% | >1.5x avg = +15 points |
| BB Width | 30% | Wider bands = higher confidence |

**Size Range:** 50% to 150% of base allocation ($1.50 to $4.50 for $3 base)

### Correlation Risk Management (US-3.3)

Prevents taking multiple positions in correlated tokens:

```python
correlation_threshold = 0.7  # 70% correlation limit
max_correlated_positions = 2  # Max 2 correlated

def check_correlation_risk(new_token, active_positions):
    for active in active_positions:
        corr = calculate_correlation(new_token, active)
        if abs(corr) > threshold:
            return False  # Skip trade
```

**Example:**
```
Active: SOL, JUP (correlated 0.85)
New Signal: RAY (correlated 0.80 with SOL)
    ↓
Action: SKIP (would be 3rd correlated position)
```

---

## Market Intelligence (Sprint 5-6)

### Market Regime Detection (US-1.5)

Uses ADX (Average Directional Index) to detect market conditions:

| Regime | ADX | Characteristics | Position Size |
|--------|-----|-----------------|---------------|
| TRENDING_UP | >25 | +DI > -DI | 1.2x (increase) |
| TRENDING_DOWN | >25 | -DI > +DI | 0.7x (decrease) |
| RANGING | <25 | Sideways | 1.0x (normal) |
| CHOPPY | <25 + Narrow BB | Noise | Skip trade |

```python
adx, plus_di, minus_di = calculate_adx()

if adx > 25:
    regime = "TRENDING_UP" if plus_di > minus_di else "TRENDING_DOWN"
else:
    regime = "CHOPPY" if bb_width < 1.5 else "RANGING"

if regime == "CHOPPY" and skip_choppy_markets:
    return False  # Skip trade
```

**Why:** Trade with the trend, avoid noise in choppy markets.

### Regime-Based Position Sizing

```python
regime_multipliers = {
    "TRENDING_UP": 1.2,    # Increase size
    "TRENDING_DOWN": 0.7,  # Reduce size
    "RANGING": 1.0,        # Normal
    "CHOPPY": 0.6,         # Should skip
}

final_size = confidence_based_size * regime_multiplier
```

---

## Configuration Reference

### Sprint 1-2 Features
```python
# Entry Enhancement
rsi_oversold_min = 20              # Widen from 25
rsi_oversold_max = 40              # Widen from 35

# Volume Confirmation
use_volume_confirmation = True     # Enable 1.3x check

# BB Tolerance
bb_tolerance = 1.005               # 0.5% vs 0.1%

# ATR Stops
use_atr_stop = True
stop_loss_atr_multiplier = 1.5
stop_loss_max_percent = 3.0
```

### Sprint 3-4 Features
```python
# Breakeven Stop
use_breakeven_stop = True
breakeven_buffer_percent = 0.1

# Trailing Stop
use_trailing_stop = True
trailing_stop_percent = 1.0
trailing_update_interval = 300     # 5 minutes

# Time Exit
use_time_exit = True
max_hold_time_minutes = 120

# Multi-Timeframe
enable_multi_timeframe = True
```

### Sprint 5-6 Features
```python
# Partial Scaling
use_partial_scaling = True
partial_scale_levels = ((0.25, 1.5), (0.25, 2.5), (0.25, 4.0))

# Dynamic Sizing
use_dynamic_sizing = True
min_position_ratio = 0.5
max_position_ratio = 1.5

# Correlation
use_correlation_check = True
max_correlated_positions = 2
correlation_threshold = 0.7

# Regime Detection
use_regime_detection = True
skip_choppy_markets = True
regime_adx_threshold = 25.0
```

---

## Trade Example Walkthrough

### Scenario: Winning Trade with All Features

```
1. MARKET ANALYSIS
   Regime: TRENDING_UP
   ADX: 32
   Confidence: 75/100

2. ENTRY CALCULATION
   Base Size: $3.00
   Confidence Multiplier: 0.5 + 0.75 = 1.25x
   Regime Multiplier: 1.2x (trending up)
   Final Size: $3.00 * 1.25 * 1.2 = $4.50

3. ENTRY EXECUTION
   Price: $100.00
   RSI: 28
   Volume: 1.6x average
   15m RSI: 45 (confirms)
   Position: $4.50

4. SCALE 1 HIT (+1.5%)
   Price: $101.50
   Action: Sell 25% ($1.125)
   PnL: +$0.017
   Remaining: $3.375

5. SCALE 2 HIT (+2.5%)
   Price: $102.50
   Action: Sell 25% ($1.125)
   PnL: +$0.028
   Remaining: $2.25
   Stop moved to breakeven: $100.10

6. SCALE 3 HIT (+4%)
   Price: $104.00
   Action: Sell 25% ($1.125)
   PnL: +$0.045
   Remaining: $1.125

7. TRAILING PHASE
   Price peaks: $106.00
   Trailing stop: $104.94 (1% below)
   Price drops to: $104.50
   Action: Trailing stop triggered
   Final PnL: +$0.051

TOTAL TRADE PnL: +$0.141 (+3.1%)
REALIZED: $0.090 (first 75%)
TRAILING: $0.051 (final 25%)
```

### Scenario: Losing Trade with Risk Management

```
1. ENTRY
   Price: $100.00
   Confidence: 55/100 (moderate)
   Size: $3.00 * 0.55 = $3.30

2. PRICE DROPS (-1%)
   Price: $99.00
   Action: DCA - Add 50% = $1.65
   New average: $99.67
   Total: $4.95

3. PRICE DROPS MORE
   Current: $98.00
   ATR Stop: $97.50 (based on volatility)
   
4. STOP TRIGGERED
   Price: $97.50
   Loss: -$0.11 (-2.2%)

5. RISK LIMITED
   Reduced size due to moderate confidence
   50% DCA instead of 100%
   ATR stop adapted to volatility
```

---

## Expected Performance

Based on backtests with $20 capital and all features enabled:

| Metric | Before | After (v2.0) | Improvement |
|--------|--------|--------------|-------------|
| Win Rate | 41% | 50%+ | +9% |
| Avg Win | +2.5% | +3.5% | +40% |
| Avg Loss | -1.5% | -1.2% | -20% |
| Trade Frequency | 8/month | 12-15/month | +50% |
| Max Drawdown | 9% | <7% | -22% |
| Monthly Return | 15% | 25-35% | +67% |
| Sharpe Ratio | 1.68 | >2.0 | +19% |

---

## When Strategy Works Best

✅ **Optimal Conditions:**
- TRENDING_UP or RANGING regime
- BB width 2-5%
- Volume >1.3x average
- 15m RSI confirming (not overbought)
- Low correlation with existing positions

❌ **Avoid Conditions:**
- CHOPPY regime (noise)
- TRENDING_DOWN (reduce size or skip)
- Volume <1.0x average
- 15m RSI >50 (overbought on higher TF)
- Correlated with 2+ active positions
- Extreme volatility (>10% BB width)

---

## Risk Management Summary

| Layer | Feature | Protection |
|-------|---------|------------|
| Entry | Regime Detection | Skip choppy markets |
| Entry | Correlation Check | Max 2 correlated |
| Entry | Confidence Sizing | 50-150% adaptive |
| Position | 50% DCA | Limits risk on losers |
| Exit | ATR Stops | Volatility-adaptive |
| Exit | Breakeven Stop | Zero risk after TP1 |
| Exit | Trailing Stop | Capture extended moves |
| Exit | Time Exit | Max 2 hour hold |
| Exit | Partial Scaling | Smooth profit taking |

---

## Further Reading

- [John Bollinger's BB Rules](https://www.bollingerbands.com)
- [ADX Indicator Guide](https://www.investopedia.com/terms/a/adx.asp)
- [Correlation in Trading](https://www.investopedia.com/terms/c/correlation.asp)
- [Roadmap](../roadmap.md) - Development roadmap and user stories
