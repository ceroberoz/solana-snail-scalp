# Forex Mean Reversion Bot - Development Roadmap

**Version:** 1.0-forex  
**Last Updated:** 2026-02-26  
**Methodology:** Scrum/Agile  
**Sprint Duration:** 2 weeks  
**Origin:** Ported from [solana-snail-scalp](https://github.com/ceroberoz/solana-snail-scalp) @ crypto-v2.0-stable

---

## 📋 Table of Contents

1. [Product Vision](#product-vision)
2. [Migration Overview](#migration-overview)
3. [Epics & User Stories](#epics--user-stories)
4. [Sprint Planning](#sprint-planning)
5. [Product Backlog](#product-backlog)
6. [Definition of Done](#definition-of-done)
7. [Success Metrics](#success-metrics)
8. [Risk Management](#risk-management)

---

## 🎯 Product Vision

### Vision Statement
> Build an intelligent, adaptive forex scalping bot that maximizes small account growth through systematic mean-reversion trading on major currency pairs, with institutional-grade risk management adapted for forex volatility.

### Target Users
- Retail forex traders with $500-$5,000 capital
- Scalpers seeking consistent 10-20 pip gains
- Algorithmic trading enthusiasts transitioning from crypto

### Success Criteria
- Win rate > 50%
- Monthly return 10-20%
- Max drawdown < 5%
- Average trade: 15-30 pips profit
- Fully automated execution via OANDA/IG

---

## 🔄 Migration Overview

### From Crypto to Forex - Key Changes

| Aspect | Crypto (Original) | Forex (This Branch) |
|--------|------------------|---------------------|
| **Market** | Solana tokens | Major forex pairs |
| **Data Source** | DexScreener, Birdeye | OANDA REST API, Yahoo Finance |
| **Volatility** | 2-10% daily | 0.5-1.5% daily |
| **Profit Target** | 1.5%, 2.5%, 4.0% | 0.3%, 0.6%, 1.0% |
| **Stop Loss** | 1.5-3% | 15-30 pips |
| **Timeframes** | 5m / 15m | 15m / 1h |
| **Position Size** | USD amount | Lot size (micro 0.01) |
| **Leverage** | None (spot) | 30:1 (ESMA), 50:1 (US) |
| **Trading Hours** | 24/7 | 24/5 (Sun-Fri) |
| **New Risks** | - | Weekend gaps, rollover, news events |

### Migration Epics

| Epic | Description | Story Points |
|------|-------------|--------------|
| **M0** | Infrastructure Migration | 34 |
| **M1** | Data & Broker Integration | 34 |
| **M2** | Parameter Adaptation | 21 |
| **M3** | Forex Risk Management | 21 |

---

## 📦 Epics & User Stories

### Epic M0: Infrastructure Migration
**Priority:** 🔴 Critical  
**Business Value:** Foundation  
**Story Points:** 34

#### M0.1: Bootstrap Forex Repository
**Status:** ✅ Done (Branch Created)
```
As a developer
I want a clean forex branch forked from crypto-v2.0-stable
So that I can adapt the codebase for forex trading

Acceptance Criteria:
- Branch forex/base created from main
- Tag crypto-v2.0-stable preserved
- Remove crypto-specific files (Jupiter, Solana wallet)
- Update README for forex focus

Story Points: 5
```

#### M0.2: Replace Data Architecture
**Status:** 📝 Todo
```
As a trader
I want to fetch EUR/USD data from OANDA instead of DexScreener
So that I get institutional-grade price feeds

Acceptance Criteria:
- Remove DexScreener/CoinGecko integration
- Implement OANDA REST API client
- Support historical data fetching
- Handle rate limits (20 req/sec)
- Fallback to Yahoo Finance for backtesting

Story Points: 13
```

#### M0.3: Convert Position Sizing to Lots
**Status:** 📝 Todo
```
As a trader
I want position size in lots (0.01) not USD amounts
So that I can use standard forex risk management

Acceptance Criteria:
- Replace USD sizing with lot sizing
- Support micro lots (0.01), mini (0.1), standard (1.0)
- Calculate pip value per pair
- Account for leverage in margin calculation
- Configurable risk per trade (% of account)

Story Points: 8
```

#### M0.4: Adapt Timeframes
**Status:** 📝 Todo
```
As a trader
I want 15m/1h timeframes instead of 5m/15m
So that I reduce noise in forex markets

Acceptance Criteria:
- Change default interval from 300s (5m) to 900s (15m)
- Change confirmation TF from 15m to 1h
- Update multi-timeframe aggregation logic
- Adjust indicator periods accordingly

Story Points: 5
```

#### M0.5: Create Forex Configuration
**Status:** 📝 Todo
```
As a trader
I want forex-specific default parameters
So that the strategy fits forex volatility

Acceptance Criteria:
- BB tolerance: 0.05% (was 0.5%)
- Min band width: 0.3% (was 2%)
- Partial scale: 0.3%, 0.6%, 1.0% (was 1.5%, 2.5%, 4.0%)
- Trailing stop: 0.3% (was 1%)
- Max hold: 8 hours (was 2 hours)
- Correlation threshold: 0.85 (was 0.7)

Story Points: 3
```

---

### Epic M1: Data & Broker Integration
**Priority:** 🔴 Critical  
**Business Value:** Execution  
**Story Points:** 34

#### M1.1: OANDA API Integration
**Status:** 📝 Todo
```
As a trader
I want to execute trades through OANDA API
So that I can trade with real money

Acceptance Criteria:
- OANDA REST API v20 integration
- Practice account support
- Market order execution
- Order status tracking
- Error handling and retries

Story Points: 13
```

#### M1.2: Paper Trading Mode
**Status:** 📝 Todo
```
As a trader
I want a paper trading mode with OANDA practice account
So that I can validate the strategy risk-free

Acceptance Criteria:
- Use OANDA practice environment
- Track virtual PnL
- Same logic as live mode
- 2-week minimum paper trading period
- Performance report generation

Story Points: 8
```

#### M1.3: Multi-Broker Support Framework
**Status:** 📝 Todo
```
As a developer
I want an abstract broker interface
So that I can support IG, FXCM later

Acceptance Criteria:
- Broker base class
- OANDA implementation
- Mock broker for testing
- Configuration-driven broker selection

Story Points: 5
```

#### M1.4: Real-Time Price Streaming
**Status:** 📝 Todo
```
As a trader
I want WebSocket price feeds
So that I get sub-second price updates

Acceptance Criteria:
- OANDA streaming API
- Reconnect on disconnect
- Heartbeat monitoring
- Fallback to polling

Story Points: 8
```

---

### Epic M2: Parameter Adaptation
**Priority:** 🟠 High  
**Business Value:** Performance  
**Story Points:** 21

#### M2.1: Pip-Based Calculations
**Status:** 📝 Todo
```
As a trader
I want all calculations in pips not percentages
So that I can think in standard forex terms

Acceptance Criteria:
- Replace % with pips throughout codebase
- PnL displayed in pips and USD
- Stop loss in pips (e.g., 20 pips)
- Take profit in pips (e.g., 30 pips)
- Pip value calculation per pair

Story Points: 8
```

#### M2.2: Spread Consideration
**Status:** 📝 Todo
```
As a trader
I want the bot to account for spread in entries/exits
So that I don't enter when spread is too wide

Acceptance Criteria:
- Fetch current spread from broker
- Max spread filter (e.g., 2 pips for EUR/USD)
- Entry only if spread < threshold
- Log spread at entry/exit

Story Points: 5
```

#### M2.3: Session-Aware Trading
**Status:** 📝 Todo
```
As a trader
I want the bot to know forex trading sessions
So that it trades during liquid hours

Acceptance Criteria:
- London session (08:00-17:00 UTC)
- New York session (13:00-22:00 UTC)
- Avoid Asian session (lower volatility)
- Session overlap detection (most liquid)
- Configurable trading windows per session

Story Points: 5
```

#### M2.4: Weekend Gap Protection
**Status:** 📝 Todo
```
As a trader
I want positions closed before weekend
So that I avoid gap risk

Acceptance Criteria:
- Detect Friday 20:00 UTC (market close)
- Close all positions 1 hour before close
- Prevent new entries after Friday 18:00 UTC
- Resume trading Sunday 22:00 UTC

Story Points: 3
```

---

### Epic M3: Forex Risk Management
**Priority:** 🟠 High  
**Business Value:** Capital Protection  
**Story Points:** 21

#### M3.1: Rollover/Swap Tracking
**Status:** 📝 Todo
```
As a trader
I want to track overnight swap costs
So that I know the true cost of holding

Acceptance Criteria:
- Fetch swap rates from broker
- Calculate daily rollover cost
- Log cumulative swap costs
- Alert if swap exceeds expected profit

Story Points: 5
```

#### M3.2: High-Impact News Filter
**Status:** 📝 Todo
```
As a trader
I want the bot to pause during major news
So that I avoid whipsaws

Acceptance Criteria:
- Economic calendar integration (ForexFactory API)
- High impact events: NFP, FOMC, CPI, ECB
- Pause 15 min before, resume 30 min after
- Configurable event list

Story Points: 8
```

#### M3.3: Margin Monitoring
**Status:** 📝 Todo
```
As a trader
I want margin level monitoring
So that I avoid margin calls

Acceptance Criteria:
- Track used margin vs available
- Calculate margin level percentage
- Alert if margin level < 200%
- Reduce position size if margin low

Story Points: 5
```

#### M3.4: Correlation Management (Forex)
**Status:** 📝 Todo
```
As a trader
I want stricter correlation limits for forex
So that I don't overexpose to USD moves

Acceptance Criteria:
- Max 1 correlated position (was 2)
- Threshold 0.85 (was 0.7)
- Track EUR/USD vs GBP/USD correlation
- Track USD/JPY inverse correlation

Story Points: 3
```

---

### Epic M4: Strategy Validation (Future)
**Priority:** 🟡 Medium  
**Business Value:** Confidence  
**Story Points:** 34

#### M4.1: Walk-Forward Optimization
**Status:** 📝 Todo
```
As a trader
I want walk-forward optimization
So that I validate parameters on unseen data

Acceptance Criteria:
- 2-year backtest data
- Walk-forward analysis
- Parameter stability check
- Out-of-sample testing

Story Points: 13
```

#### M4.2: Multi-Pair Backtesting
**Status:** 📝 Todo
```
As a trader
I want to backtest on EUR/USD, GBP/USD, USD/JPY
So that I know which pairs work best

Acceptance Criteria:
- Support 3 major pairs
- Individual pair reports
- Portfolio combined report
- Pair-specific parameter optimization

Story Points: 13
```

#### M4.3: Performance Analytics
**Status:** 📝 Todo
```
As a trader
I want detailed performance analytics
So that I can optimize the strategy

Acceptance Criteria:
- Win rate by pair
- Win rate by session
- Average pips per trade
- Maximum consecutive losses
- Recovery factor

Story Points: 8
```

---

## 🗓️ Sprint Planning

### Sprint M0: Migration Foundation (Weeks 1-2)
**Theme:** Infrastructure Setup

| User Story | Points | Owner |
|------------|--------|-------|
| M0.1: Bootstrap Repository | 5 | Done |
| M0.2: Replace Data Architecture | 13 | TBD |
| M0.3: Convert Position Sizing | 8 | TBD |
| **Total** | **26** | |

**Sprint Goal:** Forex codebase functional with OANDA data

---

### Sprint M1: Broker Integration (Weeks 3-4)
**Theme:** Live Trading Infrastructure

| User Story | Points | Owner |
|------------|--------|-------|
| M0.4: Adapt Timeframes | 5 | TBD |
| M0.5: Forex Configuration | 3 | TBD |
| M1.1: OANDA API | 13 | TBD |
| M1.2: Paper Trading | 8 | TBD |
| **Total** | **29** | |

**Sprint Goal:** Execute first paper trade on EUR/USD

---

### Sprint M2: Parameter Tuning (Weeks 5-6)
**Theme:** Adapt to Forex Volatility

| User Story | Points | Owner |
|------------|--------|-------|
| M2.1: Pip-Based Calculations | 8 | TBD |
| M2.2: Spread Consideration | 5 | TBD |
| M2.3: Session-Aware Trading | 5 | TBD |
| M2.4: Weekend Gap Protection | 3 | TBD |
| **Total** | **21** | |

**Sprint Goal:** Profitable backtest on 6 months EUR/USD data

---

### Sprint M3: Risk Management (Weeks 7-8)
**Theme:** Forex-Specific Protection

| User Story | Points | Owner |
|------------|--------|-------|
| M3.1: Rollover Tracking | 5 | TBD |
| M3.2: News Filter | 8 | TBD |
| M3.3: Margin Monitoring | 5 | TBD |
| M3.4: Correlation Mgmt | 3 | TBD |
| **Total** | **21** | |

**Sprint Goal:** 2-week paper trading with no major incidents

---

## 📊 Product Backlog

### Migration Backlog (Prioritized)

| Rank | ID | Story | Epic | Points | Priority |
|------|-----|-------|------|--------|----------|
| 1 | M0.1 | Bootstrap Repository | M0 | 5 | ✅ Done |
| 2 | M0.2 | Replace Data Architecture | M0 | 13 | 🔴 |
| 3 | M0.3 | Convert Position Sizing | M0 | 8 | 🔴 |
| 4 | M1.1 | OANDA API Integration | M1 | 13 | 🔴 |
| 5 | M0.4 | Adapt Timeframes | M2 | 5 | 🔴 |
| 6 | M0.5 | Forex Configuration | M2 | 3 | 🔴 |
| 7 | M1.2 | Paper Trading Mode | M1 | 8 | 🟠 |
| 8 | M2.1 | Pip-Based Calculations | M2 | 8 | 🟠 |
| 9 | M2.2 | Spread Consideration | M2 | 5 | 🟠 |
| 10 | M3.2 | News Filter | M3 | 8 | 🟠 |
| 11 | M2.3 | Session-Aware Trading | M2 | 5 | 🟡 |
| 12 | M2.4 | Weekend Gap Protection | M2 | 3 | 🟡 |
| 13 | M3.1 | Rollover Tracking | M3 | 5 | 🟡 |
| 14 | M3.3 | Margin Monitoring | M3 | 5 | 🟡 |
| 15 | M1.3 | Multi-Broker Framework | M1 | 5 | 🟢 |
| 16 | M1.4 | Real-Time Streaming | M1 | 8 | 🟢 |
| 17 | M3.4 | Correlation Mgmt | M3 | 3 | 🟢 |

---

## ✅ Definition of Done

### For Migration Stories
- [ ] Crypto code successfully adapted
- [ ] Forex-specific tests pass
- [ ] Backtest runs on EUR/USD data
- [ ] No hard-coded crypto references
- [ ] Documentation updated for forex
- [ ] Configuration validated

### For Broker Integration
- [ ] API connection established
- [ ] Order execution tested (practice)
- [ ] Error handling verified
- [ ] Rate limit compliance
- [ ] Logging comprehensive

---

## 📈 Success Metrics

### Migration Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Code Coverage | >75% | pytest coverage |
| Backtest Profitable | Yes | 6 months EUR/USD |
| Paper Trading | 2 weeks | No errors |
| Max Drawdown | <5% | Backtest |

### Forex Performance Targets
| Metric | Baseline | Target v1.0 |
|--------|----------|-------------|
| Win Rate | - | >50% |
| Avg Pips/Win | - | 20-30 pips |
| Avg Pips/Loss | - | <15 pips |
| Monthly Return | - | 10-20% |
| Max Drawdown | - | <5% |
| Profit Factor | - | >1.5 |

---

## ⚠️ Risk Management

### Migration Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Parameters don't translate | High | Critical | Extensive backtesting, WFO |
| API changes | Medium | Medium | Abstract broker layer |
| Broker reliability | Medium | High | Multi-broker support |

### Forex-Specific Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Weekend gaps | High | Medium | Mandatory Friday close |
| News whipsaws | Medium | High | News filter, wider stops |
| Low liquidity (Asian) | Medium | Medium | Session filters |
| Rollover costs | High | Low | Track and optimize hold time |

---

## 🔄 Status Legend

| Emoji | Status | Description |
|-------|--------|-------------|
| 📝 | Todo | Not started |
| 🚧 | In Progress | Working on it |
| ✅ | Done | Completed |
| ⏸️ | Blocked | Waiting on dependency |

---

## 📝 Decision Log

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2026-02-26 | Create forex/base branch | Isolate forex development | Approved |
| 2026-02-26 | Use OANDA as primary broker | Best API, practice accounts | Proposed |
| 2026-02-26 | Target EUR/USD first | Most liquid, tightest spread | Proposed |
| 2026-02-26 | 30:1 leverage max | ESMA compliance, risk management | Proposed |

---

**Document Owner:** Lead Developer  
**Next Review:** After Sprint M0  
**Status:** Draft - Migration In Progress

---

## 🔗 References

- [Original Crypto Roadmap](../main/roadmap.md) (crypto-v2.0-stable)
- [Forex Strategy Guide](docs/FOREX_STRATEGY.md) (to be created)
- [OANDA API Docs](https://developer.oanda.com/)
- [Original Strategy](docs/STRATEGY.md) (adapted from crypto)
