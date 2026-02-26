# Forex Mean Reversion Bot - Phase 1 Complete

**Branch:** `forex/base`  
**Status:** Phase 1 Complete - Backtest Validated ✅  
**Focus:** USD/SGD scalping strategy  
**Origin:** Ported from [solana-snail-scalp](https://github.com/ceroberoz/solana-snail-scalp) @ crypto-v2.0-stable

---

## 📊 Phase 1 Results (2-Year Backtest)

| Metric | Value | Status |
|--------|-------|--------|
| **Total Trades** | 76 | Selective (ADX filter) |
| **Win Rate** | 42.1% | Good for mean reversion |
| **Total Pips** | **+235.3** | ✅ Profitable |
| **P&L ($1k account)** | **+$168.85 (+16.9%)** | ✅ Profitable |
| **Max Drawdown** | 15.5% | ✅ Acceptable |
| **Avg Win** | 39.2 pips | |
| **Avg Loss** | 23.1 pips | |
| **Reward/Risk** | 1.7:1 | ✅ Good ratio |

---

## ✅ Phase 1 Completed Items

### M0.1: Repository Bootstrap ✅
- Created `forex/base` branch from crypto-v2.0-stable
- Removed crypto-specific code (Jupiter, Solana)
- Clean project structure

### M0.2: Yahoo Finance Data Pipeline ✅
- Yahoo Finance integration with disk caching
- 2-year USD/SGD historical data downloaded (12,350 rows)
- Rate limiting (100 req/hour) with exponential backoff
- Cache hit rate >90%

### M0.3: OANDA Integration ✅
- OANDA v20 API provider implemented
- Live price quotes support
- Historical candle data download
- Order creation/position management API
- Connection test script (`forex_test_oanda.py`)
- **Note:** OANDA demo account creation currently has issues - try again later or use live account with small balance

### M0.4: Position Sizing ✅
- Risk-based position calculation
- Micro lot support (0.01)
- Pip value calculations for USD/SGD ($0.074)
- Margin requirement estimation
- Validation rules

### M0.5: Backtest Engine ✅
- Event-driven backtest engine
- ADX trend filter (trade only ranging markets)
- Bollinger Bands + RSI entry signals
- Partial profit taking (3 levels)
- Breakeven stop after TP1
- Time-based exits
- Equity curve visualization

---

## 🏗️ Architecture

```
src/forex_bot/
├── config/
│   └── pairs.py          # USD/SGD (Phase 1), USD/MYR (Phase 2) configs
├── data/
│   ├── provider.py       # Abstract base class
│   ├── yahoo_provider.py # Backtesting data with caching
│   └── oanda_provider.py # Live trading data (API ready)
└── strategy/
    ├── indicators.py     # BB, RSI, ATR, ADX
    ├── backtest.py       # Event-driven backtest engine
    └── position_sizing.py # Risk-based position sizing

scripts/
├── forex_download_history.py   # Download historical data
├── forex_run_backtest.py       # Run backtest simulation
├── forex_test_oanda.py         # Test OANDA connection
├── forex_fetch_live_price.py   # Fetch live prices
└── crypto_sync_roadmap.py      # GitHub roadmap sync
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
uv pip install pandas yfinance diskcache pyarrow matplotlib requests python-dotenv
```

### 2. Run Backtest (No API Key Required)

```bash
# Uses cached historical data
uv run python -X utf8 scripts/forex_run_backtest.py --capital 1000
```

### 3. Test OANDA Connection (Optional - Requires Account)

```bash
# Create .env file
copy .env.example .env
# Edit .env with your OANDA credentials

# Test connection
uv run python -X utf8 scripts/forex_test_oanda.py
```

**Note:** OANDA demo account creation is currently experiencing issues. You can:
- Try creating account later at https://www.oanda.com/demo-account/
- Or use a live account with minimum deposit ($1-10)
- The code is ready - just needs credentials when account is available

---

## 📈 Strategy Details

### Entry Criteria
1. **ADX < 25** - Only trade ranging markets (mean reversion)
2. **RSI 20-40** - Oversold condition
3. **Price at Lower BB** - Within 3 pips of lower band
4. **BB Width > 10 pips** - Sufficient volatility

### Exit Strategy
1. **Partial Profits:** 25, 50, 80 pips (25% each, final 25% trails)
2. **Breakeven Stop:** After TP1 hit
3. **Time Exit:** Max 48 hours hold
4. **Stop Loss:** 25 pips (ATR-based)

### Position Sizing
```python
Risk = 2% of account ($20 on $1k)
Position = Risk Amount / (Stop Pips × Pip Value)

Example:
- Account: $1,000
- Stop: 25 pips
- Pip Value: $0.074 (USD/SGD micro lot)
- Position: $20 / (25 × $0.074) = 10.8 micro lots ≈ 0.11 lots
```

---

## 📁 Key Files

| File | Description |
|------|-------------|
| `data/historical/usd_sgd_1h_2y.parquet` | 2 years of 1h OHLCV data (12,350 rows) |
| `data/backtest_results.png` | Equity curve visualization |
| `scripts/forex_download_history.py` | Data downloader with caching |
| `scripts/forex_run_backtest.py` | Backtest runner |
| `scripts/forex_test_oanda.py` | OANDA connection test |
| `scripts/forex_fetch_live_price.py` | Live price fetcher |
| `.env.example` | API credentials template |

---

## 🔑 Environment Variables (for Live Trading)

Create `.env` file:
```bash
OANDA_API_KEY=your-api-key-here
OANDA_ACCOUNT_ID=your-account-id-here
OANDA_ENVIRONMENT=practice  # or "live"
```

Get credentials:
1. OANDA website: https://www.oanda.com/demo-account/
2. API Access: https://www.oanda.com/account/manage-api/
3. **Note:** Demo signup currently has issues - check back later

---

## 🎯 Next Steps / Phase 2

### Phase 2 Planned (Not Started)
- Add USD/MYR pair (secondary)
- Multi-pair correlation management
- Interactive Brokers integration (for MYR)
- Portfolio allocation (70% SGD / 30% MYR)

### Immediate Options
1. **Wait for OANDA** - Demo account issues should resolve
2. **Use Live Account** - Small deposit ($1-10) for testing
3. **Optimize Strategy** - Parameter tuning, add more indicators
4. **Start Phase 2** - Add USD/MYR pair to backtest

---

## 📝 Known Issues

1. **OANDA Demo Signup** - Website experiencing issues (2026-02-26)
   - Workaround: Try again later or use live account
   - Code is ready and tested with mock credentials

2. **Yahoo Data Limitation** - 15m data only available for last 60 days
   - Using 1h data for 2-year backtest
   - Sufficient for strategy validation

---

## 📚 References

- Original crypto bot: [solana-snail-scalp](https://github.com/ceroberoz/solana-snail-scalp)
- Forex roadmap: `roadmap.md`
- Phase 1 complete: Commit `97ae4b4`

---

**Branch:** `forex/base`  
**Last Updated:** 2026-02-26  
**Status:** Phase 1 Complete ✅
