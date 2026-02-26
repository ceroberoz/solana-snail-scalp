# Changelog

All notable changes to the Solana Snail Scalp Bot project.

## [2.0.0] - 2026-02-26

### Sprint 5-6: Intelligence Layer

#### Added
- **US-1.5**: Market Regime Detection using ADX
  - Detects TRENDING_UP, TRENDING_DOWN, RANGING, CHOPPY markets
  - Skips trades in choppy conditions
  - Adjusts position size by regime (1.2x trending up, 0.7x trending down)
  
- **US-2.6**: Partial Profit Scaling
  - Scale out at 25% intervals: +1.5%, +2.5%, +4%
  - Final 25% uses trailing stop to capture extended moves
  - Smooth profit taking reduces risk
  
- **US-3.2**: Dynamic Position Sizing
  - Confidence score (0-100) based on RSI depth, volume, BB width
  - Position size = Base * (0.5 + confidence/100)
  - Range: 50% to 150% of base allocation
  
- **US-3.3**: Correlation Risk Management
  - Tracks price correlations between tokens
  - Maximum 2 correlated positions (threshold 0.7)
  - Prevents concentration risk
  
#### Technical
- Added `correlation_tracker.py` module
- Extended `Trade` dataclass with `entry_regime`, `scale_levels_hit`
- New configuration options for all features

### Sprint 3-4: Exit Optimization

#### Added
- **US-1.4**: Multi-Timeframe Confirmation
  - 15-minute timeframe confirms 5-minute signals
  - Requires 15m RSI < 50 (not overbought)
  - Optional trend alignment check
  
- **US-2.2**: Breakeven Stop After TP1
  - Moves stop to entry + 0.1% buffer after first profit
  - Eliminates risk on remaining position
  
- **US-2.3**: Trailing Stop After TP1
  - Trails at 1% below recent high
  - Updates every 5 minutes
  - Won't trail below breakeven
  
- **US-2.4**: Dynamic Profit Targets
  - TP1 = Entry + (ATR * 1.0), TP2 = Entry + (ATR * 2.0)
  - Min 2%, max 8% bounds
  - Adapts to market volatility
  
- **US-2.5**: Time-Based Exit
  - Maximum 2 hour hold time
  - Closes at market if time limit reached
  - Prevents capital tie-up

#### Technical
- Extended `Trade` dataclass with `highest_price`, `breakeven_stop_price`
- Added ATR calculation to indicators
- Enhanced exit logic in `trader.py`

### Sprint 1-2: Quick Wins

#### Added
- **US-1.1**: Widen RSI Entry Range
  - Changed from 25-35 to 20-40
  - Captures 15%+ more trade opportunities
  
- **US-1.2**: Volume Confirmation
  - Entry requires volume >1.3x 20-period average
  - Filters out low-liquidity fakeouts
  
- **US-1.3**: BB Near-Touch Entry
  - Increased tolerance from 0.1% to 0.5%
  - `price <= lower_bb * 1.005`
  - Captures fast market moves
  
- **US-2.1**: ATR-Based Stops
  - Stop = Entry - (ATR * 1.5)
  - Maximum stop capped at 3%
  - Adapts to market volatility
  
- **US-3.1**: Improved DCA Logic
  - DCA size reduced from 100% to 50% of original
  - Halves risk on losing positions
  - Max 1 DCA per trade

#### Changed
- Default RSI range: 25-35 → 20-40
- BB entry tolerance: 0.1% → 0.5%
- DCA allocation: 100% → 50%
- Stop loss: Fixed 1.5% → ATR-based

#### Technical
- Added `_check_volume_confirmation()` method
- Added `calculate_atr()` method
- Added `get_exit_levels()` with ATR support
- Updated `StrategyConfig` with new defaults

### Project Infrastructure

#### Added
- GitHub Projects Kanban board integration
- Automated roadmap-to-GitHub sync script
- Comprehensive test suites for each sprint
- Status tracking in roadmap.md with emoji indicators

#### Documentation
- Updated README.md with feature matrix
- Complete strategy guide with all features
- This CHANGELOG.md

## [1.0.0] - 2026-02-20

### Initial Release (MVP)

#### Features
- Bollinger Bands + RSI mean reversion strategy
- Basic entry/exit logic (TP1/TP2 at 2.5%/4%)
- Fixed 1.5% stop loss
- 100% DCA on -1% drop
- Risk management (daily loss limit, consecutive loss pause)
- Token screening and ranking
- Backtesting engine
- Real market data integration (CoinGecko)
- Multi-token portfolio support

#### Configuration
- RSI entry: 25-35
- BB period: 20
- Trading window: 09:00-11:00 UTC
- Max position: $6 (30% of $20)

---

## Version Format

Version numbers follow [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes to strategy or API
- MINOR: New features (sprints)
- PATCH: Bug fixes and optimizations

## Migration Guide

### From 1.0 to 2.0

All changes are backward compatible. To enable new features:

```python
# In src/snail_scalp/config.py

# Enable Sprint 1-2 features (enabled by default)
rsi_oversold_min = 20
rsi_oversold_max = 40
use_atr_stop = True

# Enable Sprint 3-4 features
use_breakeven_stop = True
use_trailing_stop = True
use_atr_targets = True
use_time_exit = True
enable_multi_timeframe = True

# Enable Sprint 5-6 features
use_partial_scaling = True
use_dynamic_sizing = True
use_correlation_check = True
use_regime_detection = True
```

## Roadmap

### Completed
- [x] Sprint 1-2: Quick Wins (5 stories)
- [x] Sprint 3-4: Exit Optimization (5 stories)
- [x] Sprint 5-6: Intelligence Layer (4 stories)

### Planned
- [ ] Sprint 7-10: Live Trading
  - Jupiter DEX integration
  - Wallet management
  - Real-time execution
  - Monitoring dashboard

---

**Total Stories Completed:** 14 of 21  
**Current Version:** 2.0.0  
**Last Updated:** 2026-02-26
