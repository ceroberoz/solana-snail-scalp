# Solana Snail Scalp Bot - Development Roadmap

**Version:** 2.3  
**Last Updated:** 2026-11-23  
**Methodology:** Scrum/Agile  
**Sprint Duration:** 2 weeks  

---

## 🎯 Target Architecture & User Want

> **Core Objective:**  
> 1. **Dynamic Memecoin Discovery:** Continuously scan Solana memecoins live to select the top 3–5 high-momentum, liquid tokens.  
> 2. **Base Currency:** Execute trades on Solana using **USDT** (`Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB`).  
> 3. **Loss Prevention:** Execute live multi-position trades on Jupiter while strictly avoiding losses using the built-in risk engine (Wilder ATR stops, trailing stops, breakeven stops, regime gating, and daily circuit breakers).

---

## 🆕 Recent Improvements (v2.2 - v2.3)

- **Strategy & Indicators (Sprints 1–6 Complete):**
  - Config key alignment; CLI modes (`--simulate`, `--backtest`, `--real-data`, `--multi`) runnable.
  - Risk/strategy profiles: `default`, `balanced`, `aggressive` (`--profile`).
  - Wilder-smoothed ATR/ADX calculation; ATR stops with true high/low when OHLC available.
  - Regime-aware entry modes: momentum in bull trends, mean reversion in ranges, short/skip in bear.
  - Trailing stops, breakeven stop after TP1, time-based exit, and partial profit scale-outs.
  - Portfolio correlation tracker and daily loss circuit breakers.
- **Live Trading Baseline:**
  - Integrated Jupiter Swap API v2 for single-pair SOL/USDC live swaps with `solders` keypair signing.
  - Guarded `--multi --live` in CLI to prevent unintended execution until multi-token live engine is ready.

---

## 📋 Table of Contents

1. [Product Vision & Target Architecture](#-target-architecture--user-want)
2. [Current State Assessment & Gap Analysis](#-current-state-assessment)
3. [Strategic Objectives](#-strategic-objectives)
4. [Epics & User Stories](#-epics--user-stories)
5. [Sprint Planning](#️-sprint-planning)
6. [Product Backlog](#-product-backlog)
7. [Definition of Done](#-definition-of-done)
8. [Success Metrics](#-success-metrics)
9. [Risk Management](#️-risk-management)
10. [Team Structure](#-team-structure)
11. [Timeline](#-timeline)

---

## 🔍 Current State Assessment

### What Works (Production-Ready Strategy & Single-Pair Foundation)
| Feature | Status | Notes |
|---------|--------|-------|
| BB + RSI Strategy (Wider Range + Near Touch) | ✅ Done | Tested & operational (US-1.1, US-1.3) |
| Volume Confirmation (1.3x filter) | ✅ Done | Tested & operational (US-1.2) |
| ATR-Based Dynamic Stops (Wilder Smoothing) | ✅ Done | Tested & operational (US-2.1) |
| Breakeven Stop After TP1 | ✅ Done | Tested & operational (US-2.2) |
| Trailing Stop Engine | ✅ Done | Tested & operational (US-2.3) |
| Dynamic Profit Targets & Partial Scaling | ✅ Done | Tested & operational (US-2.4, US-2.6) |
| Time-Based Exit (Max 120m hold) | ✅ Done | Tested & operational (US-2.5) |
| Market Regime Detection (ADX + Trends) | ✅ Done | Tested & operational (US-1.5) |
| Dynamic Sizing & Correlation Management | ✅ Done | Tested & operational (US-3.2, US-3.3) |
| Single-Pair Live Execution (Jupiter v2) | ✅ Done | Tested on SOL/USDC live swaps |

### Architectural Gaps Against Target Design
| Gap | Severity | Current Codebase State | Target Requirement |
|-----|----------|------------------------|--------------------|
| **1. Dynamic Memecoin Scanner** | 🔴 High | Uses static mock snapshot (`top10_solana_coins.json`) | Live DexScreener/Birdeye API scanning for top 3–5 tokens |
| **2. Base Quote Currency** | 🟡 Medium | Hardcoded to USDC (`EPjFWdd5...`) | Solana USDT (`Es9vMFrza...`) with dynamic routing |
| **3. Multi-Token Live Swaps** | 🔴 High | Multi-token bot is simulated (`_simulate_price`) | Live on-chain swaps across 3–5 concurrent positions |
| **4. Memecoin Safety Gates** | 🔴 High | None | Honeypot, revoked freeze/mint authority, min liquidity checks |

---

## 🎯 Strategic Objectives

### Phase 1: Strategy & Single-Pair Baseline (Complete)
- Build robust indicators, regime detection, dynamic stops, and single-pair Jupiter live swap.

### Phase 2: Memecoin Discovery & Safety Pipeline (Sprint 8)
- Dynamic DexScreener scanning for 3–5 trending memecoins.
- Honeypot, freeze authority revocation, and minimum liquidity checks.
- Solana USDT base configuration and dynamic multi-hop Jupiter routing.

### Phase 3: Multi-Token Live Execution & Risk Wiring (Sprint 9)
- Wire `PortfolioManager` to `JupiterClient` for real multi-token entries & exits.
- Connect existing ATR stops, trailing stops, and daily circuit breakers to live on-chain sell orders.

### Phase 4: Production Hardening (Sprint 10)
- Priority fees / compute budget optimization, MEV protection, and monitoring.

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
**Status:** ✅ Done
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
**Status:** ✅ Done
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
**Status:** ✅ Done
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
**Status:** ✅ Done
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
**Status:** 🚧 In Progress (Single-Pair SOL/USDC Complete; Multi-token in Epic 6)
```
As a trader
I want the bot to execute trades on Jupiter
So that I can trade with real money

Acceptance Criteria:
- Jupiter API integration (v2 Swap API quote + execute)
- Transaction signing (solders / local keypair)
- Slippage protection (<0.8%)
- Single-pair SOL/USDC live verification

Story Points: 13
```

**US-5.2: Wallet Management**
**Status:** 📝 Todo
```
As a trader
I want secure wallet integration
So that funds are protected

Acceptance Criteria:
- Support Phantom/Solflare keypair export
- Private key environment variable security (SOLANA_PRIVATE_KEY)
- Unsigned transaction fallback (`data/pending_swap.json`)
- Pre-flight wallet balance verification

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
- Priority fee / compute budget optimization
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
- Web UI (React/Vue or lightweight HTML/SSE)
- Real-time PnL tracking
- Trade history with filters
- Mobile responsive

Story Points: 21
```

---

### Epic 6: Multi-Token Live Memecoin Scalper (USDT Base)
**Priority:** 🔴 Critical  
**Business Value:** Maximum (Core Target Architecture)  
**Story Points:** 45

#### User Stories

**US-6.1: Live Dynamic Memecoin Screener (DexScreener/Birdeye API)**
**Status:** ✅ Done
```
As a trader
I want the bot to dynamically scan trending Solana memecoins live
So that I identify 3-5 high-potential candidate tokens without relying on static mock data

Acceptance Criteria:
- Live discovery via DexScreener API (`/latest/dex/search`, trending, or token profiles)
- Filters candidates by 24h/1h volume surges, volume-to-MCap ratio (>0.5x), and price velocity
- Selects and rotates top 3-5 candidates for scalping
- Rate-limiting backoff and error handling for external DEX APIs

Story Points: 8
```

**US-6.2: Memecoin Safety Gate (Honeypot, Freeze & Liquidity Protection)**
**Status:** ✅ Done
```
As a trader
I want every candidate token to pass safety & liquidity checks before trading
So that capital is protected from honeypots, rugs, and illiquid traps

Acceptance Criteria:
- Verify freeze authority is revoked (RPC token supply / account info)
- Verify mint authority is revoked or renounced
- Minimum pool liquidity gate ($20,000+ USD) to prevent excessive slippage
- Maximum price impact verification via Jupiter quote (<1.5%) before entry execution

Story Points: 8
```

**US-6.3: Solana USDT Base Quote & Dynamic Routing**
**Status:** ✅ Done
```
As a trader
I want the bot to use USDT on Solana as the base quote currency
So that trading capital and profits are held and tracked in USDT

Acceptance Criteria:
- Set `TOKEN_IN` to Solana USDT (`Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB`)
- Support Jupiter multi-hop routing (`USDT -> SOL -> MEME` for buys, `MEME -> SOL -> USDT` for sells)
- Dynamic SPL token decimal scaling (USDT 6 decimals, target memecoins 6 or 9 decimals)
- Accurate balance checks using Solana RPC for USDT and held memecoins

Story Points: 8
```

**US-6.4: Multi-Token Live Portfolio Execution Engine**
**Status:** 📝 Todo
```
As a trader
I want the bot to manage and trade 3-5 live memecoin positions concurrently
So that capital is diversified across high-momentum candidates

Design Specifications (Aligned via /grill-me):
- Equal slot allocation: divide capital equally across 3 active slots with 20% emergency reserve
- Technical entry gate: wait for 1m/5m pullback to lower BB + RSI 20-40 (or momentum breakout in bull trend)
- Continuous slot rotation: re-screen market immediately when a position closes to fill open slots
- Wire PortfolioManager to JupiterClient for live USDT swaps (USDT -> MEME and MEME -> USDT)
- Two-stage rollout: Stage 1 live paper-trading on real DexScreener ticks -> Stage 2 real micro-capital ($20-$50)

Acceptance Criteria:
- Manage 3 concurrent position slots with independent balance, fill, and decimal tracking
- Execute live on-chain entries via Jupiter with 1.2% - 1.5% slippage cap and price-impact check (<1.5%)
- Continuous rotation fills vacated slots automatically without restarting the bot
- Clean error handling: abort unconfirmed swaps without desyncing portfolio state

Story Points: 13
```

**US-6.5: Multi-Token Loss-Prevention Engine Integration**
**Status:** 📝 Todo
```
As a trader
I want all active memecoin positions protected by the existing risk & exit logic
So that downside is capped and winners are locked in

Design Specifications (Aligned via /grill-me):
- Fast exit polling: 3-5 second tick frequency for active positions to react to rapid memecoin volatility
- Dynamic priority fees: use Jupiter compute budget / priority fees to ensure exit swaps land within 1-2 blocks
- Multi-tier scale outs: TP1 (50% close), TP2 (final close), and trailing stop on runner

Acceptance Criteria:
- Wilder ATR stops trigger on-chain sell swap (MEME -> USDT) within 3-5 seconds of price breach
- Breakeven stop shifts stop price to entry + fee buffer after TP1 execution
- Trailing stop locks in gains as the token pushes higher highs
- Portfolio-wide daily loss limit and consecutive loss limits halt all active trading immediately

Story Points: 8
```

---

## 🗓️ Sprint Planning

### Sprint 1-2: Quick Wins (Completed ✅)
**Theme:** Immediate Strategy Improvements
- US-1.1: Widen RSI Range (3 SP) - ✅ Done
- US-1.2: Volume Confirmation (5 SP) - ✅ Done
- US-1.3: BB Near-Touch (3 SP) - ✅ Done
- US-2.1: ATR-Based Stops (8 SP) - ✅ Done
- US-3.1: Improved DCA (5 SP) - ✅ Done

---

### Sprint 3-4: Exit Optimization (Completed ✅)
**Theme:** Better Exits & Profit Retention
- US-2.2: Breakeven Stop (5 SP) - ✅ Done
- US-2.3: Trailing Stop (8 SP) - ✅ Done
- US-2.4: Dynamic Targets (5 SP) - ✅ Done
- US-2.5: Time-Based Exit (3 SP) - ✅ Done
- US-1.4: Multi-Timeframe Confirmation (8 SP) - ✅ Done

---

### Sprint 5-6: Intelligence Layer (Completed ✅)
**Theme:** Adaptive Trading & Regimes
- US-1.5: Market Regime Detection (13 SP) - ✅ Done
- US-3.2: Dynamic Position Sizing (8 SP) - ✅ Done
- US-2.6: Partial Profit Scaling (5 SP) - ✅ Done
- US-3.3: Correlation Management (8 SP) - ✅ Done

---

### Sprint 7: Live Foundation (Completed ✅)
**Theme:** Single-Pair Jupiter Integration
- US-5.1 (Phase 1): Jupiter v2 Swap Client (Quote & Execute) - ✅ Done
- Single-pair SOL/USDC live execution engine with `solders` signing - ✅ Done
- Guardrails against unverified `--multi --live` runs - ✅ Done

---

### Sprint 8: Memecoin Discovery, Safety Gates & USDT Quote (Completed ✅)
**Theme:** Real Memecoin Pipeline & Safety Filters
| User Story | Points | Priority | Status |
|------------|--------|----------|--------|
| US-6.1: Live Dynamic Memecoin Screener (DexScreener API) | 8 | 🔴 Critical | ✅ Done |
| US-6.2: Memecoin Safety Gate (Honeypot, Freeze & Liquidity) | 8 | 🔴 Critical | ✅ Done |
| US-6.3: Solana USDT Base Quote & Dynamic Routing | 8 | 🔴 Critical | ✅ Done |
| **Total** | **24** | | |

**Sprint Goal:** Automatically scan, safety-check, and rank 3–5 real Solana memecoins quote-routed to USDT.

---

### Sprint 9: Multi-Token Live Execution & Risk Wiring (Weeks 15-16) 🚀 Next
**Theme:** Live Multi-Position Scalper
| User Story | Points | Priority | Status |
|------------|--------|----------|--------|
| US-6.4: Multi-Token Live Portfolio Execution Engine | 13 | 🔴 Critical | 📝 Todo |
| US-6.5: Multi-Token Loss-Prevention Engine Integration | 8 | 🔴 Critical | 📝 Todo |
| **Total** | **21** | | |

**Sprint Goal:** Live automated trading across 3–5 memecoin positions using USDT with active ATR stops, trailing exits, and circuit breakers.

---

### Sprint 10: Production Hardening & Dashboard (Weeks 17-18)
**Theme:** Infrastructure & Observability
| User Story | Points | Priority | Status |
|------------|--------|----------|--------|
| US-5.2: Wallet Management & Balance Guard | 8 | 🟠 High | 📝 Todo |
| US-5.3: Priority Fees & MEV Protection | 13 | 🟡 Medium | 📝 Todo |
| US-5.4: Monitoring Dashboard | 21 | 🔵 Nice to Have | 📝 Todo |
| **Total** | **42** | | |

---

## 📊 Product Backlog

### Prioritized Backlog (Refined)

| Rank | ID | Story | Epic | Points | Priority | Status |
|------|-----|-------|------|--------|----------|--------|
| 1 | US-6.4 | Multi-Token Live Portfolio Execution | Memecoin Scalper | 13 | 🔴 Critical | 📝 Todo |
| 2 | US-6.5 | Multi-Token Loss-Prevention Integration | Memecoin Scalper | 8 | 🔴 Critical | 📝 Todo |
| 3 | US-5.2 | Wallet Management & Balance Guard | Live Trading | 8 | 🟠 High | 📝 Todo |
| 4 | US-5.3 | Priority Fees & MEV Protection | Live Trading | 13 | 🟡 Medium | 📝 Todo |
| 5 | US-4.1 | Order Book Imbalance Filter | Data Intelligence | 13 | 🟢 Low | 📝 Todo |
| 6 | US-5.4 | Monitoring Dashboard | Live Trading | 21 | 🔵 Nice to Have | 📝 Todo |
| - | US-6.1 | Live Dynamic Memecoin Screener | Memecoin Scalper | 8 | - | ✅ Done |
| - | US-6.2 | Memecoin Safety Gate (Honeypot/Freeze) | Memecoin Scalper | 8 | - | ✅ Done |
| - | US-6.3 | Solana USDT Base Quote & Routing | Memecoin Scalper | 8 | - | ✅ Done |
| 6 | US-5.2 | Wallet Management & Balance Guard | Live Trading | 8 | 🟠 High | 📝 Todo |
| 7 | US-5.3 | Priority Fees & MEV Protection | Live Trading | 13 | 🟡 Medium | 📝 Todo |
| 8 | US-4.1 | Order Book Imbalance Filter | Data Intelligence | 13 | 🟢 Low | 📝 Todo |
| 9 | US-5.4 | Monitoring Dashboard | Live Trading | 21 | 🔵 Nice to Have | 📝 Todo |
| - | US-1.1 | Widen RSI Range | Entry Optimization | 3 | - | ✅ Done |
| - | US-1.2 | Volume Confirmation | Entry Optimization | 5 | - | ✅ Done |
| - | US-1.3 | BB Near-Touch Entry | Entry Optimization | 3 | - | ✅ Done |
| - | US-1.4 | Multi-Timeframe Confirmation | Entry Optimization | 8 | - | ✅ Done |
| - | US-1.5 | Market Regime Detection | Entry Optimization | 13 | - | ✅ Done |
| - | US-2.1 | ATR-Based Stops | Exit Enhancement | 8 | - | ✅ Done |
| - | US-2.2 | Breakeven Stop After TP1 | Exit Enhancement | 5 | - | ✅ Done |
| - | US-2.3 | Trailing Stop After TP1 | Exit Enhancement | 8 | - | ✅ Done |
| - | US-2.4 | Dynamic Profit Targets | Exit Enhancement | 5 | - | ✅ Done |
| - | US-2.5 | Time-Based Exit | Exit Enhancement | 3 | - | ✅ Done |
| - | US-2.6 | Partial Profit Scaling | Exit Enhancement | 5 | - | ✅ Done |
| - | US-3.1 | Improved DCA Logic | Risk Management | 5 | - | ✅ Done |
| - | US-3.2 | Dynamic Position Sizing | Risk Management | 8 | - | ✅ Done |
| - | US-3.3 | Correlation Risk Management | Risk Management | 8 | - | ✅ Done |

**Legend:**
- 🔴 Critical (Sprint 8–9 Core)
- 🟠 High (Next)
- 🟡 Medium (Later)
- 🟢 Low (Future)
- 🔵 Nice to Have

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
| 2026-02-26 | RSI range 25→35 to 20→40 | Capture more valid entries | Approved |
| 2026-02-26 | Add volume filter 1.3x | Reduce false signals | Approved |
| 2026-02-26 | ATR-based stops vs fixed | Adapt to volatility | Approved |
| 2026-02-26 | 2-week sprints | Balance velocity and planning | Approved |
| 2026-11-23 | Multi-token Memecoin USDT Pivot | Shift live trading from single-pair SOL/USDC to dynamic 3–5 memecoin discovery with Solana USDT base and honeypot/freeze safety gates, wired into the existing risk engine. | Approved |

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
