# Forex Mean Reversion Bot - Development Roadmap

**Version:** 1.0-forex  
**Last Updated:** 2026-02-26  
**Methodology:** Scrum/Agile  
**Sprint Duration:** 2 weeks  
**Origin:** Ported from [solana-snail-scalp](https://github.com/ceroberoz/solana-snail-scalp) @ crypto-v2.0-stable

---

## 📋 Table of Contents

1. [Product Vision](#product-vision)
2. [Currency Strategy](#currency-strategy)
3. [Epics & User Stories](#epics--user-stories)
4. [Sprint Planning](#sprint-planning)
5. [Data Architecture](#data-architecture)
6. [Definition of Done](#definition-of-done)
7. [Risk Management](#risk-management)

---

## 🎯 Product Vision

### Vision Statement
> Build an intelligent, adaptive forex scalping bot focused on SEA (Southeast Asian) currency exposure, starting with USD/SGD as the primary pair, with institutional-grade risk management adapted for Asian market volatility.

### Target Currency Pairs

| Priority | Pair | Status | Rationale |
|----------|------|--------|-----------|
| **P1** | **USD/SGD** | ✅ Primary | Tight spreads (2-5 pips), high liquidity, freely floating |
| **P2** | **USD/MYR** | ⚠️ Secondary | Available via IBKR, wider spreads (20-50 pips) |
| **P3** | **USD/THB** | 🔮 Future | Limited broker availability |
| **❌** | **USD/IDR** | ❌ Excluded | High spreads (50-200 pips), capital controls, low liquidity |

### Why USD/SGD as Primary?
- ✅ **Liquidity**: Singapore's financial hub status
- ✅ **Spreads**: 2-5 pips (comparable to EUR/USD)
- ✅ **Volatility**: Moderate, suitable for scalping
- ✅ **Availability**: All major brokers (OANDA, IG, IBKR)
- ✅ **Asian exposure**: Correlated with SEA markets

---

## 💱 Currency Strategy

### Phase 1: USD/SGD Only (Weeks 1-8)
```
Focus: Single pair mastery
Capital Allocation: 100% to USD/SGD
Strategy: Mean reversion on 15m/1h timeframes
Target: 20-30 pips per winning trade
```

### Phase 2: Multi-SEA (Weeks 9-16)
```
Focus: Portfolio diversification
Capital Allocation: 
  - USD/SGD: 60%
  - USD/MYR: 30%
  - Cash: 10%
Strategy: Correlation-aware position sizing
```

### Phase 3: Expansion (Future)
```
Consider: USD/THB, SGD/MYR crosses
Requirement: Proven profitability on Phase 1-2
```

---

## 📦 Epics & User Stories

### Epic M0: Infrastructure Migration
**Priority:** 🔴 Critical  
**Story Points:** 34

#### M0.1: Bootstrap Forex Repository
**Status:** ✅ Done
```
As a developer
I want a clean forex branch forked from crypto-v2.0-stable
So that I can adapt the codebase for forex trading

Acceptance Criteria:
- Branch forex/base created from main
- Tag crypto-v2.0-stable preserved
- Remove crypto-specific files
- Update README for forex focus

Story Points: 5
```

#### M0.2: Yahoo Finance Data Integration with Caching
**Status:** 📝 Todo
```
As a trader
I want to fetch USD/SGD data from Yahoo Finance with intelligent caching
So that I can backtest without hitting rate limits

Acceptance Criteria:
- Implement yfinance client for USD/SGD (=USDSGD=X)
- Disk-based cache with SQLite backend
- Cache TTL: 15 minutes for recent data, permanent for historical
- Rate limit handling: max 100 requests/hour with exponential backoff
- Fallback to OANDA historical API if Yahoo fails

Technical Notes:
- Yahoo Rate Limit: ~2,000 requests/hour (~48,000/day)
- yfinance built-in cache: ~/.cache/py-yfinance/
- Additional diskcache for persistence across restarts
- User-agent rotation to avoid 429 errors

Story Points: 13
```

#### M0.3: Multi-Source Data Architecture
**Status:** 📝 Todo
```
As a trader
I want a unified data interface supporting multiple sources
So that I can switch between Yahoo (backtesting) and OANDA (live)

Acceptance Criteria:
- Abstract DataProvider base class
- YahooFinanceProvider (cached, for backtesting)
- OandaProvider (live, for paper/live trading)
- MockProvider (for unit testing)
- Automatic source selection based on mode

Story Points: 8
```

#### M0.4: Convert Position Sizing to Lots
**Status:** 📝 Todo
```
As a trader
I want position size in lots not USD amounts
So that I can use standard forex risk management

Acceptance Criteria:
- Support micro lots (0.01) minimum
- Calculate pip value per pair (SGD different from MYR)
- Account for leverage in margin calculation
- Risk per trade: 1-2% of account

Story Points: 5
```

#### M0.5: USD/SGD Specific Configuration
**Status:** 📝 Todo
```
As a trader
I want USD/SGD optimized default parameters
So that the strategy fits SGD volatility

Acceptance Criteria:
- BB tolerance: 3 pips (0.0003)
- Partial scale: 20, 40, 70 pips
- Stop loss: 25 pips
- Take profit targets adjusted for SGD volatility
- Spread filter: max 5 pips

Story Points: 3
```

---

### Epic M1: Yahoo Finance Caching System
**Priority:** 🔴 Critical  
**Story Points:** 21

#### M1.1: Persistent Cache Implementation
**Status:** 📝 Todo
```
As a developer
I want a persistent disk cache for Yahoo Finance data
So that I avoid repeated API calls

Acceptance Criteria:
- SQLite-based cache with diskcache library
- Cache keys: (ticker, interval, date_range)
- TTL strategy:
  - Intraday data: 15 minutes
  - Historical data: 7 days
  - 5+ year old data: permanent
- Cache location: data/cache/yahoo.db

Implementation:
```python
from diskcache import Cache
import yfinance as yf

class CachedYahooProvider:
    def __init__(self, cache_dir='data/cache/yahoo'):
        self.cache = Cache(cache_dir)
        self.cache_limit = 100  # requests per hour
        
    def download(self, ticker, period, interval):
        cache_key = f"{ticker}_{period}_{interval}"
        
        # Check cache first
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if self._is_fresh(timestamp, interval):
                return data
        
        # Rate limit check
        self._respect_rate_limit()
        
        # Fetch from Yahoo
        data = yf.download(ticker, period=period, interval=interval)
        
        # Store in cache
        self.cache[cache_key] = (data, datetime.now())
        return data
```

Story Points: 8
```

#### M1.2: Rate Limit Protection
**Status:** 📝 Todo
```
As a trader
I want automatic rate limit protection
So that I don't get blocked by Yahoo

Acceptance Criteria:
- Track requests per hour (max 100 for safety)
- Exponential backoff on 429 errors
- User-agent rotation (5 rotating agents)
- Proxy support for emergency bypass
- Automatic retry with jitter

Story Points: 5
```

#### M1.3: Historical Data Pre-fetching
**Status:** 📝 Todo
```
As a trader
I want to pre-fetch and cache 2 years of historical data
So that backtests run instantly

Acceptance Criteria:
- One-time download script: scripts/download_history.py
- Downloads USD/SGD 2 years 15m data
- Stores in data/historical/usd_sgd_15m.parquet
- Incremental updates (append new data)
- Compression for storage efficiency

Story Points: 5
```

#### M1.4: Cache Analytics & Monitoring
**Status:** 📝 Todo
```
As a developer
I want cache hit/miss analytics
So that I can optimize caching strategy

Acceptance Criteria:
- Track cache hit rate
- Log API calls per hour
- Alert if approaching rate limit
- Cache size monitoring
- Cleanup old cache entries

Story Points: 3
```

---

### Epic M2: OANDA Live Integration
**Priority:** 🟠 High  
**Story Points:** 34

#### M2.1: OANDA REST API Client
**Status:** 📝 Todo
```
As a trader
I want to execute trades through OANDA API
So that I can trade USD/SGD with real money

Acceptance Criteria:
- OANDA v20 REST API integration
- Practice account support
- Market order execution
- Position tracking
- Error handling and retries

Story Points: 13
```

#### M2.2: Paper Trading Mode
**Status:** 📝 Todo
```
As a trader
I want a paper trading mode with OANDA practice account
So that I can validate the strategy risk-free

Acceptance Criteria:
- Use OANDA practice environment
- Virtual PnL tracking
- Same logic as live mode
- 2-week minimum paper trading
- Performance report generation

Story Points: 8
```

#### M2.3: Real-Time Price Streaming
**Status:** 📝 Todo
```
As a trader
I want WebSocket price feeds for USD/SGD
So that I get sub-second price updates

Acceptance Criteria:
- OANDA streaming API
- Reconnect on disconnect
- Heartbeat monitoring
- Fallback to polling every 5 seconds

Story Points: 8
```

#### M2.4: Multi-Broker Support Framework
**Status:** 📝 Todo
```
As a developer
I want an abstract broker interface
So that I can support IG, IBKR later

Acceptance Criteria:
- Broker base class
- OANDA implementation
- Mock broker for testing
- Configuration-driven selection

Story Points: 5
```

---

### Epic M3: SEA-Specific Risk Management
**Priority:** 🟠 High  
**Story Points:** 21

#### M3.1: Asian Session Detection
**Status:** 📝 Todo
```
As a trader
I want the bot to favor Asian session trading
So that I trade when USD/SGD is most liquid

Acceptance Criteria:
- Asian session: 00:00-09:00 UTC (Singapore active)
- London session: 08:00-17:00 UTC
- NY session: 13:00-22:00 UTC
- Higher position size during Asian session
- Configurable session preferences

Story Points: 5
```

#### M3.2: Weekend Gap Protection
**Status:** 📝 Todo
```
As a trader
I want positions closed before weekend
So that I avoid gap risk on Sunday open

Acceptance Criteria:
- Close all positions Friday 20:00 UTC
- No new entries after Friday 18:00 UTC
- Resume trading Sunday 22:00 UTC
- Special handling for Asian holidays

Story Points: 3
```

#### M3.3: High-Impact News Filter
**Status:** 📝 Todo
```
As a trader
I want to avoid trading during high-impact events
So that I don't get caught in volatility spikes

Acceptance Criteria:
- Events: US NFP, FOMC, Singapore GDP, MAS policy
- Pause 30 min before, 30 min after
- ForexFactory calendar integration
- Configurable event sensitivity

Story Points: 8
```

#### M3.4: Correlation Management (USD/SGD vs USD/MYR)
**Status:** 📝 Todo
```
As a trader
I want to manage correlation between SEA pairs
So that I don't double-risk on USD moves

Acceptance Criteria:
- Track USD/SGD vs USD/MYR correlation
- Correlation threshold: 0.85
- Max 1 position if correlated
- Correlation lookback: 20 periods

Story Points: 5
```

---

## 🗓️ Sprint Planning

### Sprint M0: Foundation (Weeks 1-2)
**Theme:** Data Infrastructure

| User Story | Points | Owner |
|------------|--------|-------|
| M0.1: Bootstrap Repository | 5 | ✅ Done |
| M0.2: Yahoo Finance + Caching | 13 | TBD |
| M0.3: Multi-Source Architecture | 8 | TBD |
| **Total** | **26** | |

**Sprint Goal:** Download and cache 2 years USD/SGD data

**Deliverables:**
- Cached historical data in `data/historical/`
- Cache hit rate > 90%
- No 429 errors during development

---

### Sprint M1: Caching & Backtesting (Weeks 3-4)
**Theme:** Reliable Data Flow

| User Story | Points | Owner |
|------------|--------|-------|
| M1.1: Persistent Cache | 8 | TBD |
| M1.2: Rate Limit Protection | 5 | TBD |
| M1.3: Historical Pre-fetch | 5 | TBD |
| M0.4: Position Sizing (Lots) | 5 | TBD |
| M0.5: USD/SGD Config | 3 | TBD |
| **Total** | **26** | |

**Sprint Goal:** Run first USD/SGD backtest with cached data

**Deliverables:**
- 2-year backtest completed
- Performance report generated
- Cache system validated

---

### Sprint M2: OANDA Integration (Weeks 5-6)
**Theme:** Live Trading Infrastructure

| User Story | Points | Owner |
|------------|--------|-------|
| M2.1: OANDA API Client | 13 | TBD |
| M2.2: Paper Trading | 8 | TBD |
| M2.4: Multi-Broker Framework | 5 | TBD |
| **Total** | **26** | |

**Sprint Goal:** Execute first paper trade on USD/SGD

**Deliverables:**
- OANDA practice account connected
- First paper trade executed
- Position tracking working

---

### Sprint M3: SEA Optimization (Weeks 7-8)
**Theme:** Asian Market Adaptation

| User Story | Points | Owner |
|------------|--------|-------|
| M3.1: Asian Session Detection | 5 | TBD |
| M3.2: Weekend Gap Protection | 3 | TBD |
| M3.3: News Filter | 8 | TBD |
| M2.3: Real-Time Streaming | 8 | TBD |
| **Total** | **24** | |

**Sprint Goal:** 2-week paper trading with no incidents

**Deliverables:**
- Session-aware trading active
- Weekend protection working
- News filter tested

---

## 🏛️ Data Architecture

### Yahoo Finance Integration with Caching

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Flow Architecture                   │
└─────────────────────────────────────────────────────────────┘

  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │   Backtest   │────▶│ YahooFinance │────▶│  Disk Cache  │
  │    Mode      │     │   Provider   │     │  (SQLite)    │
  └──────────────┘     └──────────────┘     └──────┬───────┘
         │                                         │
         │    Cache Hit ────────────────────────────┘
         │    (90%+ hit rate)
         │
         ▼    Cache Miss
  ┌──────────────┐
  │  Yahoo API   │◀── Rate Limit Control (100 req/hr)
  │  (External)  │◀── User-Agent Rotation
  └──────────────┘

  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │  Live/Paper  │────▶│   OANDA      │────▶│   OANDA      │
  │    Mode      │     │   Provider   │     │   Servers    │
  └──────────────┘     └──────────────┘     └──────────────┘
         │
         ▼
  ┌──────────────┐
  │  Live Cache  │◀── 15min TTL for recent data
  │   (SQLite)   │
  └──────────────┘
```

### Cache Configuration

```python
# config/data_config.py
DATA_CONFIG = {
    "yahoo": {
        "cache_dir": "data/cache/yahoo",
        "cache_size_limit": 1_000_000_000,  # 1GB
        "rate_limit_per_hour": 100,  # Conservative
        "ttl": {
            "1m": 900,      # 15 minutes
            "15m": 3600,    # 1 hour
            "1h": 86400,    # 1 day
            "1d": 604800,   # 7 days
        },
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            # ... 5 total rotating
        ]
    },
    "oanda": {
        "practice_url": "https://api-fxpractice.oanda.com",
        "live_url": "https://api-fxtrade.oanda.com",
        "streaming_url": "https://stream-fxpractice.oanda.com",
    },
    "pairs": {
        "USD_SGD": {
            "yahoo_ticker": "USDSGD=X",
            "oanda_instrument": "USD_SGD",
            "pip_decimal": 4,
            "spread_max": 5,  # pips
        },
        "USD_MYR": {
            "yahoo_ticker": "USDMYR=X",
            "oanda_instrument": "USD_MYR",
            "pip_decimal": 4,
            "spread_max": 50,  # pips
            "note": "Limited broker availability"
        }
    }
}
```

### Cache Implementation Details

```python
# src/data/yahoo_provider.py
from diskcache import Cache
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import random

class YahooFinanceProvider:
    """
    Yahoo Finance data provider with intelligent caching.
    
    Rate Limit Strategy:
    - Max 100 requests/hour (well below 2,000 limit)
    - Exponential backoff on 429 errors
    - User-agent rotation
    - Persistent disk cache
    """
    
    def __init__(self, cache_dir='data/cache/yahoo', max_requests_per_hour=100):
        self.cache = Cache(cache_dir)
        self.max_requests = max_requests_per_hour
        self.request_times = []
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        ]
        
    def download(self, ticker: str, period: str = "1y", interval: str = "15m") -> pd.DataFrame:
        """Download data with caching and rate limiting."""
        cache_key = f"{ticker}_{period}_{interval}"
        
        # Check cache
        cached = self._get_from_cache(cache_key, interval)
        if cached is not None:
            return cached
        
        # Rate limit check
        self._respect_rate_limit()
        
        # Download with user-agent rotation
        try:
            data = yf.download(
                ticker, 
                period=period, 
                interval=interval,
                progress=False,
                headers={'User-Agent': random.choice(self.user_agents)}
            )
            
            # Store in cache
            self._store_in_cache(cache_key, data, interval)
            self._log_request()
            
            return data
            
        except Exception as e:
            if "429" in str(e):
                # Rate limited - wait and retry
                time.sleep(60)
                return self.download(ticker, period, interval)
            raise
    
    def _get_from_cache(self, key: str, interval: str) -> pd.DataFrame:
        """Retrieve from cache if not expired."""
        if key not in self.cache:
            return None
            
        data, timestamp = self.cache[key]
        ttl = self._get_ttl(interval)
        
        if datetime.now() - timestamp < ttl:
            return data
        return None
    
    def _store_in_cache(self, key: str, data: pd.DataFrame, interval: str):
        """Store data with timestamp."""
        self.cache[key] = (data, datetime.now())
    
    def _get_ttl(self, interval: str) -> timedelta:
        """Get TTL based on data granularity."""
        ttl_map = {
            '1m': timedelta(minutes=15),
            '15m': timedelta(hours=1),
            '1h': timedelta(days=1),
            '1d': timedelta(days=7),
        }
        return ttl_map.get(interval, timedelta(hours=1))
    
    def _respect_rate_limit(self):
        """Ensure we don't exceed rate limit."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old requests
        self.request_times = [t for t in self.request_times if t > hour_ago]
        
        # Check limit
        if len(self.request_times) >= self.max_requests:
            sleep_time = 3600 - (now - self.request_times[0]).seconds
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _log_request(self):
        """Log request time for rate limiting."""
        self.request_times.append(datetime.now())
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            'size': len(self.cache),
            'volume': self.cache.volume(),
            'hit_rate': self.cache.stats(hits=True, misses=True)
        }
```

---

## 📊 Product Backlog

### Prioritized Backlog

| Rank | ID | Story | Epic | Points | Priority |
|------|-----|-------|------|--------|----------|
| 1 | M0.1 | Bootstrap Repository | M0 | 5 | ✅ Done |
| 2 | M0.2 | Yahoo Finance + Caching | M0 | 13 | 🔴 |
| 3 | M0.3 | Multi-Source Architecture | M0 | 8 | 🔴 |
| 4 | M1.1 | Persistent Cache | M1 | 8 | 🔴 |
| 5 | M2.1 | OANDA API Client | M2 | 13 | 🔴 |
| 6 | M0.4 | Position Sizing (Lots) | M0 | 5 | 🟠 |
| 7 | M0.5 | USD/SGD Config | M0 | 3 | 🟠 |
| 8 | M1.2 | Rate Limit Protection | M1 | 5 | 🟠 |
| 9 | M2.2 | Paper Trading | M2 | 8 | 🟠 |
| 10 | M1.3 | Historical Pre-fetch | M1 | 5 | 🟡 |
| 11 | M3.1 | Asian Session Detection | M3 | 5 | 🟡 |
| 12 | M3.3 | News Filter | M3 | 8 | 🟡 |
| 13 | M2.3 | Real-Time Streaming | M2 | 8 | 🟢 |
| 14 | M3.2 | Weekend Gap Protection | M3 | 3 | 🟢 |
| 15 | M2.4 | Multi-Broker Framework | M2 | 5 | 🟢 |
| 16 | M3.4 | Correlation Mgmt | M3 | 5 | 🟢 |
| 17 | M1.4 | Cache Analytics | M1 | 3 | 🔵 |

---

## ✅ Definition of Done

### For Data Stories
- [ ] Cache hit rate > 90% in normal operation
- [ ] No 429 errors in 24-hour test
- [ ] Historical data loads in < 5 seconds (from cache)
- [ ] Rate limit never exceeded (max 100/hour)
- [ ] Fallback to alternative source works

### For Broker Stories
- [ ] Practice account connected
- [ ] Order execution < 1 second
- [ ] Position tracking accurate
- [ ] Error handling tested (network down, API errors)

---

## ⚠️ Risk Management

### Data Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Yahoo blocks IP | Medium | High | Rotate user-agents, use proxy fallback |
| Yahoo API changes | Low | High | Abstract provider layer, easy to switch |
| Cache corruption | Low | Medium | Regular backups, validation checks |
| OANDA outage | Medium | High | Multi-broker support planned |

### Trading Risks (SEA Specific)
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MAS intervention (SGD) | Medium | Medium | Wider stops during policy announcements |
| BNM intervention (MYR) | Medium | High | USD/MYR position limits |
| Asian holiday low liquidity | High | Medium | Holiday calendar, reduced size |
| Weekend gap | High | Medium | Mandatory Friday close |

---

## 📝 Decision Log

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2026-02-26 | USD/SGD as primary pair | Tight spreads, high liquidity, SEA exposure | Approved |
| 2026-02-26 | Exclude IDR | High spreads (50-200 pips), capital controls | Approved |
| 2026-02-26 | Yahoo Finance for backtesting | Free, sufficient for 15m data, easy caching | Approved |
| 2026-02-26 | OANDA for live trading | Best API, practice accounts, USD/SGD available | Approved |
| 2026-02-26 | 100 req/hour Yahoo limit | Conservative (well below 2,000 limit) | Approved |

---

**Document Owner:** Lead Developer  
**Next Review:** After Sprint M0  
**Status:** Draft - USD/SGD Focus Adopted
