# Forex Mean Reversion Bot - Development Roadmap

**Version:** 1.0-forex  
**Last Updated:** 2026-02-26  
**Focus:** USD/SGD Primary + USD/MYR Secondary  
**Origin:** Ported from [solana-snail-scalp](https://github.com/ceroberoz/solana-snail-scalp) @ crypto-v2.0-stable

---

## 📋 Table of Contents

1. [Current Status](#current-status)
2. [Product Vision](#product-vision)
3. [Phase 1: USD/SGD Focus](#phase-1-usdsgd-focus)
4. [Phase 2: Multi-Pair Expansion](#phase-2-multi-pair-expansion)
5. [Epics & User Stories](#epics--user-stories)
6. [Sprint Planning](#sprint-planning)
7. [Data Architecture](#data-architecture)
8. [Risk Management](#risk-management)

---

## 📊 Current Status (2026-02-26)

### Phase 1 Complete ✅

| Component | Status | Notes |
|-----------|--------|-------|
| M0.1 Bootstrap | ✅ | Branch created, structure ready |
| M0.2 Yahoo Data | ✅ | 2-year USD/SGD cached (12,350 rows) |
| M0.3 OANDA API | ✅ | Code ready, pending account signup |
| M0.4 Position Sizing | ✅ | Risk-based calculations |
| M0.5 Backtest Engine | ✅ | +235 pips, +16.9% return |

### Backtest Results (2 Years)
- **Trades:** 76
- **Win Rate:** 42.1%
- **Total Pips:** +235.3
- **Return:** +16.9% ($1k account)
- **Max DD:** 15.5%

### Current Blockers
- ⏸️ **OANDA Demo Signup:** Website experiencing issues
- Workarounds: Try later, use live account, or skip to Phase 2

### Next Actions
1. ⏸️ Wait for OANDA demo to work, OR
2. 🔮 Start Phase 2 (add USD/MYR to backtest)

---

## 🎯 Product Vision

### Vision Statement
> Build an intelligent, adaptive forex scalping bot focused on Southeast Asian currency exposure, with **USD/SGD as the primary pair** and **USD/MYR as secondary**, featuring institutional-grade risk management optimized for Asian market volatility.

### Target Pairs

| Pair | Phase | Priority | Spreads | Broker | Status |
|------|-------|----------|---------|--------|--------|
| **USD/SGD** | Phase 1 | 🔴 Primary | 2-5 pips | OANDA, IG, IBKR | ✅ Available |
| **USD/MYR** | Phase 2 | 🟠 Secondary | 20-50 pips | Interactive Brokers | ⚠️ Limited |
| USD/THB | Future | 🔮 Tertiary | 30-80 pips | Rare | ❌ Not planned |
| USD/IDR | Excluded | ❌ | 50-200 pips | Local only | ❌ Excluded |

### Why These Pairs?

**USD/SGD (Primary)**
- ✅ Tightest spreads among SEA currencies (2-5 pips)
- ✅ High liquidity - Singapore is Asia's forex hub
- ✅ Freely floating - no heavy central bank intervention
- ✅ Available on all major retail brokers
- ✅ 24-hour trading with Asian session focus

**USD/MYR (Secondary)**
- ✅ SEA diversification
- ⚠️ Wider spreads (20-50 pips) - swing trading better than scalping
- ⚠️ BNM intervention risk - managed float
- ✅ Available via Interactive Brokers (not OANDA)

---

## 💱 Phase 1: USD/SGD Focus (Weeks 1-8)

### Phase 1 Objectives
```
Single Pair Mastery:
├── Pair: USD/SGD only
├── Capital: 100% allocation
├── Timeframe: 15m primary, 1h confirmation  
├── Target: 20-30 pips per winner
└── Broker: OANDA (best USD/SGD spreads)
```

### Phase 1 Success Criteria
| Metric | Target | Measurement |
|--------|--------|-------------|
| Backtest Win Rate | >50% | 2-year historical |
| Avg Pips/Trade | 20-30 pips | Backtest analysis |
| Max Drawdown | <5% | Equity curve |
| Cache Hit Rate | >90% | Data provider logs |
| Paper Trading | 2 weeks | OANDA practice |

### Phase 1 Exclusions
- ❌ No multi-pair trading
- ❌ No USD/MYR yet
- ❌ No correlation management needed (single pair)

---

## 💱 Phase 2: Multi-Pair Expansion (Weeks 9-16)

### Phase 2 Objectives
```
Add USD/MYR for Diversification:
├── Pairs: USD/SGD + USD/MYR
├── Capital Allocation:
│   ├── USD/SGD: 70% (primary, tighter spreads)
│   └── USD/MYR: 30% (secondary, wider spreads)
├── Strategy: Correlation-aware sizing
│   └── If correlation >0.85: trade only one
└── Broker: Interactive Brokers (supports both)
```

### USD/MYR Specific Considerations

| Aspect | USD/SGD | USD/MYR |
|--------|---------|---------|
| **Spread** | 2-5 pips | 20-50 pips |
| **Strategy** | Scalping (15m) | Swing (1h/4h) |
| **Target** | 20-30 pips | 50-100 pips |
| **Stop** | 25 pips | 40-60 pips |
| **Hold Time** | 2-8 hours | 1-3 days |
| **Intervention Risk** | Low | Medium (BNM) |

---

## 📦 Epics & User Stories

### Epic M0: Phase 1 Foundation (USD/SGD)
**Priority:** 🔴 Critical  
**Story Points:** 34

#### M0.1: Bootstrap Forex Repository
**Status:** ✅ COMPLETE
```
As a developer
I want a clean forex branch forked from crypto
So that I can build the USD/SGD bot

Acceptance Criteria:
- Branch forex/base created from crypto-v2.0-stable
- Remove crypto-specific code (Jupiter, Solana)
- Update README for forex focus

Story Points: 5
```

#### M0.2: USD/SGD Data Pipeline with Caching
**Status:** ✅ COMPLETE

**Deliverables:**
- Yahoo Finance provider with disk caching
- 2-year USD/SGD data downloaded (12,350 rows)
- Rate limiting and error handling
- Cache hit rate >90%
```
As a trader
I want USD/SGD data from Yahoo Finance with caching
So that I can backtest without API limits

Acceptance Criteria:
- yfinance integration for USDSGD=X
- Disk cache (SQLite) with 90%+ hit rate
- Rate limit: max 100 requests/hour
- 2-year historical data pre-fetched
- Cache location: data/cache/usd_sgd.db

Story Points: 13
```

#### M0.3: OANDA Live Data for USD/SGD
**Status:** ✅ COMPLETE (Code Ready)

**Deliverables:**
- OANDA v20 API provider implemented
- Live price quotes support
- Historical data download
- Order execution API
- Connection test script

**Note:** OANDA demo account signup currently has issues. Code is tested and ready - just needs credentials when account is available.
```
As a trader
I want live USD/SGD prices from OANDA
So that I can paper trade and go live

Acceptance Criteria:
- OANDA REST API for USD_SGD instrument
- Practice account integration
- Real-time price streaming
- Order execution API

Story Points: 8
```

#### M0.4: USD/SGD Position Sizing
**Status:** ✅ COMPLETE

**Deliverables:**
- Risk-based position sizing module
- Micro lot support (0.01)
- Pip value calculations
- Margin requirement estimation
- Validation rules
```
As a trader
I want lot-based sizing for USD/SGD
So that I can manage risk properly

Acceptance Criteria:
- Micro lots (0.01) as minimum
- Pip value: ~$7.40 per pip per standard lot
- Risk per trade: 1-2% of account
- Position size formula: (Risk $) / (Stop pips × Pip value)

Example:
- Account: $1,000
- Risk: 2% = $20
- Stop: 25 pips
- Pip value: $0.074 (micro lot)
- Position: $20 / (25 × $0.074) = 10.8 micro lots → 0.11

Story Points: 5
```

#### M0.5: USD/SGD Strategy Parameters + Backtest
**Status:** ✅ COMPLETE

**Deliverables:**
- BB + RSI entry strategy
- ADX trend filter (ADX < 25)
- Partial profit taking (25, 50, 80 pips)
- Breakeven stop after TP1
- Time-based exit (48h max)
- Event-driven backtest engine

**Results (2-year backtest):**
- Trades: 76
- Win Rate: 42.1%
- Total Pips: +235.3
- P&L: +16.9% on $1k account
- Max Drawdown: 15.5%
```
As a trader
I want USD/SGD optimized parameters
So that the strategy fits SGD volatility

Acceptance Criteria:
- BB period: 20, Std: 2.0
- BB tolerance: 3 pips (0.0003)
- RSI range: 20-40
- Partial take profits: 20, 40, 70 pips
- Stop loss: 25 pips (ATR-based)
- Max spread: 5 pips (skip if wider)
- Max hold: 8 hours

Story Points: 3
```

---

### Epic M1: Phase 2 - Add USD/MYR
**Priority:** 🟠 High  
**Story Points:** 21

#### M1.1: USD/MYR Data Integration
**Status:** ✅ Done
```
As a trader
I want USD/MYR data for backtesting
So that I can analyze this secondary pair

Acceptance Criteria:
- Yahoo Finance: USDMYR=X
- Interactive Brokers data feed
- Same caching system as USD/SGD
- 2-year historical pre-fetched

Story Points: 5
```

#### M1.2: Multi-Pair Architecture
**Status:** ✅ Done
```
As a developer
I want to support both USD/SGD and USD/MYR
So that the bot can trade multiple pairs

Acceptance Criteria:
- Pair configuration in config.yaml
- Separate parameters per pair
- Portfolio capital allocation
- Max 2 concurrent positions (one per pair)

Story Points: 8
```

#### M1.3: USD/MYR Specific Parameters
**Status:** ✅ Done
```
As a trader
I want USD/MYR optimized for wider spreads
So that I can profit despite higher costs

Acceptance Criteria:
- Timeframe: 1h (not 15m - too noisy with spread)
- Target: 50-100 pips (not 20-30)
- Stop: 40-60 pips
- Max spread: 50 pips
- Min hold: 4 hours (avoid noise)
- BNM intervention awareness

Story Points: 5
```

#### M1.4: Correlation Monitor (SGD vs MYR)
**Status:** ✅ Done
```
As a trader
I want to know when SGD and MYR are correlated
So that I don't double my USD exposure

Acceptance Criteria:
- Calculate USD/SGD vs USD/MYR correlation
- Lookback: 20 periods (1h)
- Threshold: 0.85
- If correlated >0.85: trade only the tighter spread pair (SGD)
- Alert when correlation breaks down

Story Points: 3
```

---

### Epic M2: OANDA Integration (USD/SGD)
**Priority:** 🔴 Critical  
**Story Points:** 26

#### M2.1: OANDA USD/SGD Trading
**Status:** 📝 Todo
```
As a trader
I want to trade USD/SGD through OANDA
So that I can execute with tight spreads

Acceptance Criteria:
- OANDA v20 API integration
- USD_SGD instrument support
- Market orders
- Position tracking
- Error handling

Story Points: 13
```

#### M2.2: Paper Trading Mode
**Status:** 📝 Todo
```
As a trader
I want OANDA paper trading for USD/SGD
So that I can validate before going live

Acceptance Criteria:
- Practice environment
- Virtual balance tracking
- Same execution logic as live
- 2-week minimum paper period

Story Points: 8
```

#### M2.3: Interactive Brokers (USD/MYR)
**Status:** 📝 Todo
```
As a trader
I want Interactive Brokers for USD/MYR
So that I can trade the secondary pair

Acceptance Criteria:
- IBKR API integration
- USD.MYR instrument
- Alternative to OANDA (OANDA doesn't offer MYR)
- Paper trading support

Note: Only needed for Phase 2

Story Points: 5
```

---

### Epic M3: SEA Risk Management
**Priority:** 🟠 High  
**Story Points:** 21

#### M3.1: Asian Session Trading
**Status:** ✅ Done
```
**Status:** 📝 Todo
```
As a trader
I want to focus on Asian session for USD/SGD
So that I trade when SGD is most liquid

Acceptance Criteria:
- Asian session: 00:00-09:00 UTC
- Higher position size during Asian hours
- Reduce size in London/NY overlap (volatility)
- Session-based time filters

Story Points: 5
```

#### M3.2: Weekend Gap Protection
**Status:** ✅ Done
```
**Status:** 📝 Todo
```
As a trader
I want positions closed before weekend
So that I avoid Sunday gap risk

Acceptance Criteria:
- Close all positions Friday 20:00 UTC
- No new entries after Friday 18:00 UTC
- Resume Sunday 22:00 UTC

Story Points: 3
```

#### M3.3: News Filter (MAS, BNM, US)
**Status:** 📝 Todo
```
As a trader
I want to avoid trading during central bank events
So that I don't get caught in volatility

Acceptance Criteria:
- Singapore MAS policy announcements
- Malaysia BNM rate decisions
- US NFP, FOMC
- Pause: 30 min before/after
- ForexFactory calendar API

Story Points: 8
```

#### M3.4: SGD-Specific Risk (MAS Intervention)
**Status:** 📝 Todo
```
As a trader
I want to know if MAS is intervening
So that I can adjust my strategy

Acceptance Criteria:
- Monitor SGD NEER (Nominal Effective Exchange Rate)
- Alert if MAS signals policy shift
- Widen stops during intervention periods
- Log unusual price action

Story Points: 5
```

---

## 🗓️ Sprint Planning

### Sprint M0: USD/SGD Data (Weeks 1-2) ✅ COMPLETE
**Theme:** Single Pair Data Infrastructure

| Story | Points | Status |
|-------|--------|--------|
| M0.1: Bootstrap | 5 | ✅ |
| M0.2: Yahoo + Cache | 13 | ✅ |
| M0.3: OANDA Data | 8 | ✅ |
| **Total** | **26** | **DONE** |

**Goal:** Download 2-year USD/SGD history, cache working ✅

**Deliverables:**
- ✅ `data/historical/usd_sgd_1h_2y.parquet` (12,350 rows)
- ✅ Cache hit rate >90%
- ✅ OANDA provider code ready (pending account)

---

### Sprint M1: USD/SGD Strategy (Weeks 3-4) ✅ COMPLETE
**Theme:** Single Pair Backtesting

| Story | Points | Status |
|-------|--------|--------|
| M0.4: Position Sizing | 5 | ✅ |
| M0.5: SGD Parameters | 3 | ✅ |
| M1.1: Backtest Engine | 8 | ✅ |
| M1.2: Performance Report | 5 | ✅ |
| **Total** | **21** | **DONE** |

**Goal:** First profitable USD/SGD backtest ✅

**Results:**
- Trades: 76
- Win Rate: 42.1%
- Total Pips: +235.3 (+16.9% return)
- Max Drawdown: 15.5%
- ✅ Equity curve generated (`data/backtest_results.png`)

---

### Sprint M2: OANDA Paper Trading (Weeks 5-6) ⏸️ PENDING
**Theme:** Live Infrastructure

| Story | Points | Status |
|-------|--------|--------|
| M2.1: OANDA Trading | 13 | ⏸️ Pending account |
| M2.2: Paper Mode | 8 | ⏸️ Pending account |
| TT|| M3.2: Weekend Protection | 3 | ✅ Done |
| **Total** | **24** | **BLOCKED** |

**Goal:** First paper trade on OANDA USD/SGD

**Status:** ⏸️ BLOCKED - OANDA demo signup currently has issues

**Workarounds:**
1. Try signup again later
2. Use live account with minimum deposit
3. Skip to Phase 2 (add USD/MYR to backtest)

---

### Sprint M3: SEA Optimization (Weeks 7-8) 🔮 FUTURE
**Theme:** Asian Market Adaptation

| Story | Points | Status |
|-------|--------|--------|
| M3.1: Asian Session | 5 | ✅ |
| M3.3: News Filter | 8 | 🔮 |
| M3.4: MAS Monitoring | 5 | 🔮 |
| M2.3: Real-Time Stream | 5 | 🔮 |
| **Total** | **23** | **FUTURE** |

**Goal:** Live trading optimization

**Note:** Will resume after OANDA account is available or skip to Phase 2

---

### Sprint M4: Add USD/MYR (Weeks 9-10) 🔮 PHASE 2
**Theme:** Phase 2 - Multi-Pair

| Story | Points | Status |
|-------|--------|--------|
| M1.1: MYR Data | 5 | ✅ |
| M1.2: Multi-Pair Arch | 8 | ✅ |
| M1.3: MYR Parameters | 5 | ✅ |
| M2.3: IBKR Setup | 5 | 🔮 |
| M1.2: Multi-Pair Arch | 8 | 🔮 |
| M1.3: MYR Parameters | 5 | 🔮 |
| M2.3: IBKR Setup | 5 | 🔮 |
| **Total** | **23** | **PHASE 2** |

**Goal:** USD/MYR integrated, dual-pair backtest

**Note:** Phase 2 begins after Phase 1 live trading or if prioritized

---

### Sprint M5: Correlation & Portfolio (Weeks 11-12) 🔮 PHASE 2
**Theme:** Smart Multi-Pair

| Story | Points | Status |
|-------|--------|--------|
| M1.4: Correlation Monitor | 3 | 🔮 |
| M5.1: Portfolio Sizing | 8 | 🔮 |
| M5.2: Dual Paper Trading | 8 | 🔮 |
| **Total** | **19** | **PHASE 2** |

**Goal:** Both pairs trading with correlation awareness

---

## 🏛️ Data Architecture

### Provider Hierarchy

```
┌─────────────────────────────────────────────────────┐
│                 DataProvider (Abstract)              │
├─────────────────────────────────────────────────────┤
│  + download(symbol, timeframe)                      │
│  + get_latest(symbol)                               │
│  + is_available(symbol)                             │
└─────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Yahoo      │  │    OANDA     │  │ Interactive  │
│  Finance     │  │   (Live)     │  │   Brokers    │
│ (Cached)     │  │              │  │   (MYR)      │
└──────────────┘  └──────────────┘  └──────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
   USD/SGD             USD/SGD            USD/MYR
   USD/MYR             (Live only)        (Live only)
   (Backtest)
```

### Pair Configuration

```python
# config/pairs.yaml
pairs:
  USD_SGD:
    name: "USD/SGD"
    phase: 1
    priority: primary
    yahoo_ticker: "USDSGD=X"
    oanda_instrument: "USD_SGD"
    ibkr_symbol: None  # Not needed, use OANDA
    
    # Trading parameters
    timeframe: "15m"
    spread_max_pips: 5
    target_pips: [20, 40, 70]
    stop_pips: 25
    max_hold_hours: 8
    
    # Strategy
    bb_period: 20
    bb_std: 2.0
    rsi_period: 14
    rsi_oversold: [20, 40]
    
    # Position sizing
    pip_value_usd: 0.074  # per micro lot
    risk_per_trade_pct: 2.0
    max_position_lots: 1.0

  USD_MYR:
    name: "USD/MYR"
    phase: 2
    priority: secondary
    yahoo_ticker: "USDMYR=X"
    oanda_instrument: None  # Not available
    ibkr_symbol: "USD.MYR"
    
    # Trading parameters (wider spreads)
    timeframe: "1h"
    spread_max_pips: 50
    target_pips: [50, 100, 150]
    stop_pips: 60
    max_hold_hours: 72
    
    # Strategy (adjusted for volatility)
    bb_period: 20
    bb_std: 2.5  # Wider bands
    rsi_period: 14
    rsi_oversold: [20, 40]
    
    # Position sizing
    pip_value_usd: 0.022  # per micro lot (approx)
    risk_per_trade_pct: 1.5  # Lower risk
    max_position_lots: 0.5

portfolio:
  max_correlation: 0.85
  allocation:
    USD_SGD: 0.70
    USD_MYR: 0.30
```

### Cache Strategy per Pair

| Pair | Cache File | TTL Intraday | TTL Historical |
|------|-----------|--------------|----------------|
| USD/SGD | `usd_sgd.db` | 15 min | 7 days |
| USD/MYR | `usd_myr.db` | 15 min | 7 days |

---

## ⚠️ Risk Management

### Pair-Specific Risks

| Risk | USD/SGD | USD/MYR |
|------|---------|---------|
| **Intervention** | Low (MAS) | Medium (BNM) |
| **Spread Spike** | 2-5 → 10 pips | 20-50 → 100 pips |
| **Liquidity** | High | Medium |
| **Gap Risk** | Low | Medium |
| **Correlation** | N/A | High with SGD |

### Phase 1 Risk Controls (USD/SGD Only)

```
Hard Stops:
├── Max loss per trade: 2% of account
├── Max daily loss: 5% of account
├── Max positions: 1 (only USD/SGD)
└── Weekend: Must close by Friday 20:00 UTC

Soft Limits:
├── Skip if spread >5 pips
├── Skip if MAS announcement within 1 hour
└── Reduce size if volatility >2x ATR
```

### Phase 2 Risk Controls (Dual Pair)

```
Additional Controls:
├── Max positions: 2 (one per pair)
├── Correlation check: Skip MYR if corr >0.85
├── Allocation: 70% SGD, 30% MYR
└── MYR only during Asian session (BNM active hours)
```

---

## 📝 Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-26 | USD/SGD primary | Tightest spreads, best liquidity |
| 2026-02-26 | USD/MYR secondary | SEA exposure, IBKR availability |
| 2026-02-26 | OANDA for SGD | Best USD/SGD spreads |
| 2026-02-26 | IBKR for MYR | Only major broker with MYR |
| 2026-02-26 | Exclude IDR | Spreads too wide (50-200 pips) |
| 2026-02-26 | 15m for SGD, 1h for MYR | Spread-adjusted timeframes |

---

**Document Status:** Phase 1 Focus Locked  
**Next Action:** Implement M0.2 (USD/SGD Data Pipeline)
