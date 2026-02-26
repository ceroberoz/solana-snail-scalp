# Forex Mean Reversion Bot - Phase 1

**Branch:** `forex/base`  
**Focus:** USD/SGD scalping strategy  
**Status:** Backtest complete, ready for live testing

---

## 📊 Phase 1 Results (2-Year Backtest)

| Metric | Value |
|--------|-------|
| **Total Trades** | 76 |
| **Win Rate** | 42.1% |
| **Total Pips** | **+235.3** |
| **P&L ($1k account)** | **+$168.85 (+16.9%)** |
| **Max Drawdown** | 15.5% |
| **Avg Win** | 39.2 pips |
| **Avg Loss** | 23.1 pips |
| **Reward/Risk** | 1.7:1 |

---

## 🏗️ Architecture

```
src/forex_bot/
├── config/
│   └── pairs.py          # USD/SGD, USD/MYR configurations
├── data/
│   ├── provider.py       # Abstract base class
│   ├── yahoo_provider.py # Backtesting data with caching
│   └── oanda_provider.py # Live trading data
└── strategy/
    ├── indicators.py     # BB, RSI, ATR, ADX
    ├── backtest.py       # Event-driven backtest engine
    └── position_sizing.py # Risk-based position sizing
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
uv pip install pandas yfinance diskcache pyarrow matplotlib requests
```

### 2. Download Historical Data

```bash
uv run python -X utf8 scripts/forex_download_history.py --pair USD_SGD --period 2y
```

### 3. Run Backtest

```bash
uv run python -X utf8 scripts/forex_run_backtest.py --capital 1000
```

### 4. Test OANDA Connection (for live trading)

```bash
# Set environment variables
export OANDA_API_KEY="your_api_key"
export OANDA_ACCOUNT_ID="your_account_id"
export OANDA_ENVIRONMENT="practice"

# Test connection
uv run python -X utf8 scripts/forex_test_oanda.py
```

---

## 📈 Strategy Details

### Entry Criteria
1. **ADX < 25** - Only trade ranging markets
2. **RSI 20-40** - Oversold condition
3. **Price at Lower BB** - Mean reversion setup
4. **BB Width > 10 pips** - Sufficient volatility

### Exit Strategy
1. **Partial Profits** - 25, 50, 80 pips
2. **Breakeven Stop** - After TP1 hit
3. **Time Exit** - Max 48 hours
4. **Stop Loss** - 25 pips (ATR-based)

### Position Sizing
```python
Risk = 2% of account
Position = Risk Amount / (Stop Pips × Pip Value)

Example ($1k account, 25 pip stop):
- Risk = $20
- Pip Value = $0.074 (USD/SGD micro lot)
- Position = $20 / (25 × $0.074) = 10.8 micro lots ≈ 0.11 lots
```

---

## 📁 Key Files

| File | Description |
|------|-------------|
| `data/historical/usd_sgd_1h_2y.parquet` | 2 years of 1h data |
| `data/backtest_results.png` | Equity curve visualization |
| `scripts/forex_download_history.py` | Data downloader |
| `scripts/forex_run_backtest.py` | Backtest runner |
| `scripts/forex_test_oanda.py` | OANDA connection test |
| `scripts/forex_fetch_live_price.py` | Live price fetcher |

---

## 🎯 Next Steps

### Phase 1 Complete ✅
- [x] USD/SGD data infrastructure
- [x] Yahoo Finance caching
- [x] Backtest engine
- [x] Position sizing
- [x] Profitable backtest

### Phase 1 Remaining
- [ ] OANDA live data integration
- [ ] Paper trading (optional - skipped for now)

### Phase 2 (Future)
- Add USD/MYR pair
- Multi-pair correlation management
- Interactive Brokers integration

---

## 🔑 Environment Variables

```bash
# OANDA API (get from https://www.oanda.com/demo-account/)
export OANDA_API_KEY="xxx-xxx-xxx"
export OANDA_ACCOUNT_ID="xxx-xxx-xxx-xxx"
export OANDA_ENVIRONMENT="practice"  # or "live"
```

---

## 📚 Documentation

- Original crypto bot: [solana-snail-scalp](https://github.com/ceroberoz/solana-snail-scalp)
- Forex roadmap: `roadmap.md`

---

**Branch:** `forex/base`  
**Last Updated:** 2026-02-26
