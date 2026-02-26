# Solana Snail Scalp Bot - Development Roadmap

**Version:** 2.0  
**Last Updated:** 2026-02-26  
**Methodology:** Scrum/Agile  
**Sprint Duration:** 2 weeks  

---

## 📋 Table of Contents

1. [Product Vision](#product-vision)
2. [Current State Assessment](#current-state-assessment)
3. [Strategic Objectives](#strategic-objectives)
4. [Epics & User Stories](#epics--user-stories)
5. [Sprint Planning](#sprint-planning)
6. [Product Backlog](#product-backlog)
7. [Definition of Done](#definition-of-done)
8. [Success Metrics](#success-metrics)
9. [Risk Management](#risk-management)
10. [Team Structure](#team-structure)
11. [Timeline](#timeline)

---

## 🎯 Product Vision

### Vision Statement
> Build an intelligent, adaptive scalping bot for Solana that maximizes small capital growth through systematic mean-reversion trading with institutional-grade risk management.

### Target Users
- Retail traders with $20-$1,000 capital
- Risk-averse scalpers seeking consistent returns
- Algorithmic trading enthusiasts

### Success Criteria
- Win rate > 45%
- Monthly return 20-35%
- Max drawdown < 10%
- Fully automated execution

---

## 🔍 Current State Assessment

### What Works (MVP Complete)
| Feature | Status | Notes |
|---------|--------|-------|
| BB + RSI Strategy | ✅ | Basic implementation working |
| Risk Management | ✅ | Circuit breakers, position limits |
| Multi-token Support | ✅ | 3 concurrent positions |
| Backtesting | ✅ | Historical simulation |
| Real Data Integration | ✅ | CoinGecko/Birdeye APIs |
| CLI Interface | ✅ | All major commands working |
| Portfolio Tracking | ✅ | PnL, win rate, history |

### Technical Debt
| Issue | Priority | Effort |
|-------|----------|--------|
| Hard-coded parameters | High | 2 SP |
| No ATR calculation | High | 3 SP |
| Missing volume filter | High | 2 SP |
| No trailing stops | Medium | 5 SP |
| Single timeframe only | Medium | 8 SP |
| No market regime detection | Medium | 13 SP |

### Performance Gaps
- RSI 25-35 too narrow (missing 40% of entries)
- Fixed stops don't adapt to volatility
- No volume confirmation
- DCA doubles risk without limit
- Missing market regime awareness

---

## 🎯 Strategic Objectives

### Q1 2026: Foundation Enhancement
**Goal:** Optimize entry/exit logic, reduce false signals

**Key Results:**
- Increase trade frequency by 30%
- Improve win rate from 41% to 50%
- Reduce max drawdown by 20%

### Q2 2026: Intelligence Layer
**Goal:** Add adaptive parameters and market regime detection

**Key Results:**
- Implement dynamic position sizing
- Add multi-timeframe confirmation
- Achieve 25% monthly returns consistently

### Q3 2026: Production Readiness
**Goal:** Live trading with full automation

**Key Results:**
- Jupiter DEX integration
- Real-time execution with <1s latency
- 99.9% uptime

---

## 📦 Epics & User Stories

### Epic 1: Entry Strategy Optimization
**Priority:** 🔴 Critical  
**Business Value:** High  
**Story Points:** 21

#### User Stories

**US-1.1: Widen RSI Entry Range**
**Status:** ✅ Done
```
As a trader
I want the bot to enter when RSI is 20-40 (not 25-35)
So that I don't miss valid pullback opportunities

Acceptance Criteria:
- RSI lower bound: 20 (was 25)
- RSI upper bound: 40 (was 35)
- Backtest shows >15% more trades
- Win rate doesn't drop below 40%

Story Points: 3
```

**US-1.2: Add Volume Confirmation**
**Status:** ✅ Done
```
As a trader
I want entries only when volume is >1.3x average
So that I avoid low-liquidity fakeouts

Acceptance Criteria:
- Calculate 20-period volume average
- Entry requires current_volume > avg * 1.3
- Configurable threshold (1.0 - 2.0x)
- Backtest shows improved win rate

Story Points: 5
```

**US-1.3: BB Near-Touch Entry**
**Status:** ✅ Done
```
As a trader
I want to enter when price is within 0.5% of lower BB
So that I catch more opportunities in fast markets

Acceptance Criteria:
- Entry zone: price <= lower_bb * 1.005
- Maintains existing RSI filter
- Tests show >10% more entries

Story Points: 3
```

**US-1.4: Multi-Timeframe Confirmation**
**Status:** ✅ Done
```
As a trader
I want 15-min timeframe to confirm 5-min signals
So that I avoid counter-trend trades

Acceptance Criteria:
- Track separate indicators for 15m
- 15m RSI must be < 50 (not overbought)
- 15m trend aligns with trade direction
- Optional: can disable via config

Story Points: 8
```

**US-1.5: Market Regime Detection**
**Status:** 📝 Todo
```
As a trader
I want the bot to detect trending vs ranging markets
So that position sizes adapt to conditions

Acceptance Criteria:
- Detect: TRENDING_UP, TRENDING_DOWN, RANGING, CHOPPY
- Adjust position size by regime
- Skip trades in CHOPPY markets
- Log regime changes

Story Points: 13
```

---

### Epic 2: Exit Strategy Enhancement
**Priority:** 🔴 Critical  
**Business Value:** High  
**Story Points:** 34

#### User Stories

**US-2.1: Implement ATR-Based Stops**
**Status:** ✅ Done
```
As a trader
I want dynamic stop-loss based on ATR
So that stops adapt to market volatility

Acceptance Criteria:
- Calculate 14-period ATR
- Stop = Entry - (ATR * 1.5)
- Max stop capped at 3%
- Backtest shows lower drawdown

Story Points: 8
```

**US-2.2: Breakeven Stop After TP1**
**Status:** ✅ Done
```
As a trader
I want stop moved to breakeven after TP1 hits
So that I protect my capital on remaining position

Acceptance Criteria:
- Trigger: TP1 execution
- New stop: Entry price + fees
- Apply only to remaining 50% position
- Log breakeven adjustment

Story Points: 5
```

**US-2.3: Trailing Stop After TP1**
**Status:** ✅ Done
```
As a trader
I want trailing stop to lock in profits
So that I capture extended moves

Acceptance Criteria:
- Activate after TP1
- Trail at 1% below recent high
- Update every 5 minutes
- Don't trail below breakeven

Story Points: 8
```

**US-2.4: Dynamic Profit Targets**
**Status:** ✅ Done
```
As a trader
I want profit targets based on ATR not fixed %
So that targets adapt to volatility

Acceptance Criteria:
- TP1 = Entry + (ATR * 1.0)
- TP2 = Entry + (ATR * 2.0)
- Minimum 2%, maximum 8%
- Configurable ATR multiplier

Story Points: 5
```

**US-2.5: Time-Based Exit**
**Status:** ✅ Done
```
As a trader
I want positions closed after 2 hours max
So that I don't hold through consolidation

Acceptance Criteria:
- Max hold time: 2 hours
- Close at market if no TP2
- Configurable duration
- Log time-based exits separately

Story Points: 3
```

**US-2.6: Partial Profit Scaling**
**Status:** 📝 Todo
```
As a trader
I want to take profits at 25%, 50%, 75% intervals
So that I scale out of positions smoothly

Acceptance Criteria:
- TP1: 25% of position at +1.5%
- TP2: 25% at +2.5%
- TP3: 25% at +4%
- Final 25% with trailing stop
- Configurable levels

Story Points: 5
```

---

### Epic 3: Risk Management 2.0
**Priority:** 🟠 High  
**Business Value:** High  
**Story Points:** 21

#### User Stories

**US-3.1: Improved DCA Logic**
**Status:** ✅ Done
```
As a trader
I want DCA size to be 50% of original (not 100%)
So that I don't double risk on losers

Acceptance Criteria:
- DCA size = 0.5 * original position
- Max 1 DCA per trade
- Cancel DCA if approaching stop
- Log DCA events

Story Points: 5
```

**US-3.2: Dynamic Position Sizing**
**Status:** 📝 Todo
```
As a trader
I want position size based on confidence score
So that high-probability setups get larger allocation

Acceptance Criteria:
- Confidence from: RSI depth, volume, BB width
- Size = Base * (0.5 + confidence/100)
- Range: 50% to 150% of base
- Never exceed max position limit

Story Points: 8
```

**US-3.3: Correlation Risk Management**
**Status:** 📝 Todo
```
As a trader
I want the bot to avoid correlated positions
So that I don't have 3 similar trades at once

Acceptance Criteria:
- Calculate correlation between tokens
- Max 2 correlated positions
- Correlation threshold: 0.7
- Alert if correlation detected

Story Points: 8
```

---

### Epic 4: Data & Intelligence
**Priority:** 🟡 Medium  
**Business Value:** Medium  
**Story Points:** 34

#### User Stories

**US-4.1: Order Book Imbalance**
**Status:** 📝 Todo
```
As a trader
I want to see bid/ask imbalance before entry
So that I avoid entries into selling pressure

Acceptance Criteria:
- Fetch L2 order book
- Calculate bid/ask ratio
- Entry requires ratio > 1.2
- Update in real-time

Story Points: 13
```

**US-4.2: Funding Rate Arbitrage**
**Status:** 📝 Todo
```
As a trader
I want to know funding rates for perps
So that I avoid expensive holds

Acceptance Criteria:
- Fetch funding rates
- Alert if funding > 0.1% / 8h
- Consider in hold time decisions
- Log funding costs

Story Points: 8
```

**US-4.3: Whale Wallet Tracking**
**Status:** 📝 Todo
```
As a trader
I want to see whale wallet movements
So that I anticipate large moves

Acceptance Criteria:
- Track top 100 wallets
- Alert on >$100k moves
- Correlate with entry signals
- Store in database

Story Points: 13
```

---

### Epic 5: Live Trading Infrastructure
**Priority:** 🟡 Medium  
**Business Value:** Very High  
**Story Points:** 55

#### User Stories

**US-5.1: Jupiter DEX Integration**
**Status:** 📝 Todo
```
As a trader
I want the bot to execute trades on Jupiter
So that I can trade with real money

Acceptance Criteria:
- Jupiter API integration
- Quote fetching
- Transaction signing
- Slippage protection (<0.8%)

Story Points: 13
```

**US-5.2: Wallet Management**
**Status:** 📝 Todo
```
As a trader
I want secure wallet integration
So that funds are protected

Acceptance Criteria:
- Support Phantom/Solflare
- Private key encryption
- Multi-wallet support
- Withdrawal limits

Story Points: 8
```

**US-5.3: Real-Time Execution**
**Status:** 📝 Todo
```
As a trader
I want <1 second execution latency
So that I get filled at intended prices

Acceptance Criteria:
- WebSocket price feeds
- Async transaction processing
- Priority fee optimization
- MEV protection

Story Points: 13
```

**US-5.4: Monitoring Dashboard**
**Status:** 📝 Todo
```
As a trader
I want a web dashboard to monitor trades
So that I can see performance in real-time

Acceptance Criteria:
- Web UI (React/Vue)
- Real-time PnL tracking
- Trade history with filters
- Mobile responsive

Story Points: 21
```

---

## 🗓️ Sprint Planning

### Sprint 1-2: Quick Wins (Weeks 1-4)
**Theme:** Immediate Improvements

| User Story | Points | Owner |
|------------|--------|-------|
| US-1.1: Widen RSI Range | 3 | TBD |
| US-1.2: Volume Confirmation | 5 | TBD |
| US-1.3: BB Near-Touch | 3 | TBD |
| US-2.1: ATR-Based Stops | 8 | TBD |
| US-3.1: Improved DCA | 5 | TBD |
| **Total** | **24** | |

**Sprint Goal:** Increase trade frequency by 25% while maintaining win rate

**Definition of Done:**
- All stories merged to main
- Backtests show improvement
- Documentation updated

---

### Sprint 3-4: Exit Optimization (Weeks 5-8)
**Theme:** Better Exits = Better Profits

| User Story | Points | Owner |
|------------|--------|-------|
| US-2.2: Breakeven Stop | 5 | TBD |
| US-2.3: Trailing Stop | 8 | TBD |
| US-2.4: Dynamic Targets | 5 | TBD |
| US-2.5: Time-Based Exit | 3 | TBD |
| US-1.4: Multi-Timeframe | 8 | TBD |
| **Total** | **29** | |

**Sprint Goal:** Reduce drawdown by 20%, improve avg win size

---

### Sprint 5-6: Intelligence Layer (Weeks 9-12)
**Theme:** Adaptive Trading

| User Story | Points | Owner |
|------------|--------|-------|
| US-1.5: Market Regime | 13 | TBD |
| US-3.2: Dynamic Sizing | 8 | TBD |
| US-2.6: Partial Scaling | 5 | TBD |
| US-3.3: Correlation Mgmt | 8 | TBD |
| **Total** | **34** | |

**Sprint Goal:** Achieve consistent 25%+ monthly returns

---

### Sprint 7-10: Live Trading (Weeks 13-20)
**Theme:** Production Deployment

| User Story | Points | Owner |
|------------|--------|-------|
| US-5.1: Jupiter Integration | 13 | TBD |
| US-5.2: Wallet Management | 8 | TBD |
| US-5.3: Real-Time Execution | 13 | TBD |
| US-5.4: Monitoring Dashboard | 21 | TBD |
| **Total** | **55** | |

**Sprint Goal:** Full live trading with dashboard

---

## 📊 Product Backlog

### Prioritized Backlog (Refined)

| Rank | ID | Story | Epic | Points | Priority |
|------|-----|-------|------|--------|----------|
| 1 | US-1.1 | Widen RSI Range | Entry Optimization | 3 | 🔴 |
| 2 | US-1.2 | Volume Confirmation | Entry Optimization | 5 | 🔴 |
| 3 | US-2.1 | ATR-Based Stops | Exit Enhancement | 8 | 🔴 |
| 4 | US-3.1 | Improved DCA | Risk Management | 5 | 🔴 |
| 5 | US-2.2 | Breakeven Stop | Exit Enhancement | 5 | 🟠 |
| 6 | US-2.3 | Trailing Stop | Exit Enhancement | 8 | 🟠 |
| 7 | US-1.4 | Multi-Timeframe | Entry Optimization | 8 | 🟠 |
| 8 | US-2.4 | Dynamic Targets | Exit Enhancement | 5 | 🟠 |
| 9 | US-1.5 | Market Regime | Entry Optimization | 13 | 🟡 |
| 10 | US-3.2 | Dynamic Sizing | Risk Management | 8 | 🟡 |
| 11 | US-5.1 | Jupiter Integration | Live Trading | 13 | 🟡 |
| 12 | US-5.2 | Wallet Management | Live Trading | 8 | 🟢 |
| 13 | US-5.3 | Real-Time Execution | Live Trading | 13 | 🟢 |
| 14 | US-4.1 | Order Book Imbalance | Data Intelligence | 13 | 🟢 |
| 15 | US-5.4 | Monitoring Dashboard | Live Trading | 21 | 🔵 |

**Legend:**
- 🔴 Critical (Do First)
- 🟠 High (Next)
- 🟡 Medium (Later)
- 🟢 Low (Future)
- 🔵 Nice to Have

---

## ✅ Definition of Done

### For User Stories
- [ ] Code implemented and tested
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass
- [ ] Backtest shows improvement vs baseline
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] No critical bugs in QA
- [ ] Merged to main branch

### For Epics
- [ ] All user stories completed
- [ ] Epic-level integration tests pass
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] Demo to stakeholders

### For Releases
- [ ] All epics for version complete
- [ ] Full regression test pass
- [ ] Security audit (if applicable)
- [ ] User acceptance testing
- [ ] Deployment plan documented
- [ ] Rollback plan ready

---

## 📈 Success Metrics

### Sprint Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Velocity | 25-35 SP/sprint | JIRA/GitHub Projects |
| Burndown | <20% carryover | Sprint reports |
| Defect Rate | <2 bugs/SP | Bug tracker |
| Code Coverage | >80% | pytest coverage |

### Product Metrics
| Metric | Baseline | Target v2.0 |
|--------|----------|-------------|
| Win Rate | 41% | >50% |
| Monthly Return | 15% | 25-35% |
| Max Drawdown | 9% | <7% |
| Sharpe Ratio | 1.68 | >2.0 |
| Trade Frequency | 8/month | 12-15/month |
| Avg Win / Avg Loss | 1.5 | >2.0 |

### Business Metrics
| Metric | Target |
|--------|--------|
| User Adoption | 100+ active users |
| User Retention | >60% after 3 months |
| Support Tickets | <5/week |
| NPS Score | >50 |

---

## ⚠️ Risk Management

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Backtests don't translate to live | High | Critical | Walk-forward testing, paper trading |
| API rate limits | Medium | Medium | Caching, multiple data sources |
| Smart contract bugs | Low | Critical | Security audit, testnet first |
| Latency issues | Medium | High | WebSocket feeds, priority fees |

### Market Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Strategy decay | Medium | High | Continuous monitoring, re-optimization |
| Black swan events | Low | Critical | Circuit breakers, max loss limits |
| Liquidity drying up | Medium | High | Volume filters, slippage protection |

### Project Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep | High | Medium | Strict sprint boundaries |
| Team availability | Medium | Medium | Knowledge sharing, documentation |
| Technical debt | Medium | Medium | Refactoring sprints |

---

## 👥 Team Structure

### Roles (Recommended)

| Role | Responsibility | FTE |
|------|----------------|-----|
| Product Owner | Prioritize backlog, stakeholder mgmt | 0.5 |
| Scrum Master | Facilitate ceremonies, remove blockers | 0.25 |
| Lead Developer | Architecture, code review | 1.0 |
| Backend Developer | Strategy implementation | 1.0 |
| Data Engineer | Market data, analytics | 0.5 |
| QA Engineer | Testing, backtesting validation | 0.5 |

### Ceremonies

| Ceremony | Frequency | Duration | Participants |
|----------|-----------|----------|--------------|
| Sprint Planning | Bi-weekly | 2 hours | Full team |
| Daily Standup | Daily | 15 min | Developers |
| Sprint Review | Bi-weekly | 1 hour | Full team + stakeholders |
| Retrospective | Bi-weekly | 1 hour | Full team |
| Backlog Refinement | Weekly | 1 hour | PO + Lead Dev |

---

## 📅 Timeline

### Phase 1: Foundation (Q1 2026)
**Months:** Feb - Apr  
**Focus:** Entry/exit optimization  
**Deliverables:**
- v1.5: Quick wins implemented
- v1.6: Exit strategy enhanced
- Backtests showing 20%+ returns

### Phase 2: Intelligence (Q2 2026)
**Months:** May - Jul  
**Focus:** Adaptive parameters  
**Deliverables:**
- v1.8: Multi-timeframe + regime detection
- v2.0-beta: Complete feature set
- Paper trading validation

### Phase 3: Production (Q3 2026)
**Months:** Aug - Oct  
**Focus:** Live trading  
**Deliverables:**
- v2.0: Jupiter integration
- Dashboard launch
- First live users

### Phase 4: Scale (Q4 2026)
**Months:** Nov - Dec  
**Focus:** Advanced features  
**Deliverables:**
- v2.1: Advanced intelligence (whales, order book)
- Mobile app
- Institutional features

---

## 🔄 Continuous Improvement

### Monthly Activities
- **Strategy Review:** Analyze live performance vs backtest
- **Parameter Optimization:** Walk-forward optimization
- **User Feedback:** Collect and prioritize
- **Tech Debt:** Address highest priority items

### Quarterly Activities
- **Major Release:** New version with epics
- **Strategy Refresh:** Re-optimize based on 3 months data
- **Security Audit:** If handling real funds
- **Team Retrospective:** Process improvements

---

## 🔄 Status Legend

Update the status emoji in each user story to sync with GitHub:

| Emoji | Status | Description |
|-------|--------|-------------|
| 📝 | Todo | Not started yet |
| 🚧 | In Progress | Currently working on it |
| ✅ | Done | Completed and merged |
| ⏸️ | Blocked | Waiting on dependency |

**To sync with GitHub:**
```bash
python scripts/sync_roadmap_to_github.py
```

---

## 📝 Decision Log

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2026-02-26 | RSI range 25→35 to 20→40 | Capture more valid entries | Proposed |
| 2026-02-26 | Add volume filter 1.3x | Reduce false signals | Proposed |
| 2026-02-26 | ATR-based stops vs fixed | Adapt to volatility | Proposed |
| 2026-02-26 | 2-week sprints | Balance velocity and planning | Approved |

---

## 🚀 Getting Started

### For Product Owner
1. Review and prioritize backlog
2. Set up JIRA/GitHub Projects
3. Schedule Sprint 1 Planning
4. Define acceptance criteria for US-1.1

### For Developers
1. Set up development environment
2. Review existing codebase
3. Create feature branch for US-1.1
4. Write tests first (TDD)

### For QA
1. Set up testing framework
2. Create baseline backtests
3. Define test scenarios
4. Prepare staging environment

---

## 📚 References

- [Strategy Documentation](docs/STRATEGY.md)
- [CLI Reference](docs/CLI_REFERENCE.md)
- [Integration Guide](docs/INTEGRATION.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

---

**Document Owner:** Product Owner  
**Next Review:** After Sprint 1  
**Status:** Draft - Ready for team review
