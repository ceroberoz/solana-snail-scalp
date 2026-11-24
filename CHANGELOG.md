# Changelog

All notable changes to the Solana Snail Scalp Bot project.

## [Unreleased]

### Fixed
- **Honest CLI exit codes**: `python -m snail_scalp` now returns `main()`'s exit code. `--multi --live` exits `1` after the refusal, and a completed backtest exits `0` even when the strategy loses money.
- **Live exits no longer book unconfirmed sells**: `_close_position` and `_partial_close` now sell first and update position state only when Jupiter confirms execution. A failed swap leaves the position open, prints `[LIVE][CRITICAL]`, and retries on the next tick. Scale-out levels are only marked hit after a confirmed partial sell.

## [2.3.0] - 2026-11-23

### Added
- **Live Solana Memecoin Discovery (US-6.1)**:
  - Upgraded screener to query DexScreener's public API (`/token-profiles/latest/v1` and `/dex/search?q=solana`) with batch token lookup (`/dex/tokens/{addrs}`).
  - Automatically surfaces trending, boosted, and high-volume Solana memecoins in real time with real mint addresses, live prices, and 24h volume.
- **Rug & Liquidity Safety Gate (US-6.2)**:
  - Implemented configurable `--min-liquidity` threshold (default `$20,000` USD) that eliminates dead pools, drained liquidity rugs, and illiquid traps.
  - Added resilient offline fallback to local cache (`data/live_screened_tokens.json` or `top10_solana_coins.json`) via `--offline`.
- **Solana USDT Base Currency (US-6.3)**:
  - Switched default `TOKEN_IN` to Solana USDT (`Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB`) with 6-decimal scaling (`BASE_TOKEN_DECIMALS = 6`).
  - Added constants for `USDT_MINT`, `USDC_MINT`, and `SOL_MINT`.
  - Verified Jupiter v2 quote routing for `USDT -> MEME` and `MEME -> USDT`.
- **Top 3–5 USDT Scalping Candidate Highlights**:
  - `uv run python -m snail_scalp --screen` now actively displays the top 3–5 candidate memecoins formatted with mint address, price, liquidity, hype score, and Jupiter USDT swap route.
- **Unit Tests**:
  - Added `tests/test_live_screener_usdt.py` covering USDT config, liquidity filtering, offline fallback, and candidate ranking.

### Fixed
- **Test event loop lifecycle**: made `_run_check` in `tests/test_regime_entries.py` robust against closed event loops across test files.

## [2.2.0] - 2026-11-23

### Added
- **Regime-aware entry modes**: the trader now picks an entry engine per detected regime instead of using mean reversion everywhere.
  - `TRENDING_UP` → momentum entries (price above middle BB, RSI 45-70, rising momentum, volume >1.1x, 15m uptrend, no blow-off top).
  - `RANGING` → existing mean-reversion entries (lower BB, RSI 20-40).
  - `TRENDING_DOWN` → short when `enable_short_entries=True`, otherwise skip.
  - `CHOPPY` → skip.
  - New config: `regime_aware_entries`, `bull_entry_mode`, `range_entry_mode`, `momentum_rsi_min/max`, `momentum_volume_threshold`, `regime_target_multiplier`, `regime_scale_levels`.
- **Regime-aware exits**: bull momentum trades use wider scale-out targets (2% / 3.5% / 6%) while ranging trades keep 1.5% / 2.5% / 4%; `get_exit_levels` accepts `target_multiplier`.
- **ATR-based short stops**: shorts now use `entry + ATR × 1.5` capped by `short_stop_percent`, mirroring long stops (`short_use_atr_stop`, `short_stop_atr_multiplier`).
- **Tests**: `tests/test_regime_entries.py` covers regime routing, momentum/mean-reversion signals, exit target widening, and config defaults.

### Fixed
- **Live long closes**: removed an undefined helper call and sized the SOL→USDC sell from the position's USD notional at the current price (0.5% buffer).
- **Live partial scale-outs**: partial closes now execute their proportional on-chain swap instead of only updating bookkeeping.
- **Fail-closed entries**: live entries abort when Jupiter does not confirm execution (`pending_signature` / `execute_failed`).
- **Live shorts refused**: spot mode now rejects short entries instead of silently opening a long swap.

### Added
- **[Agent Operations](docs/AGENT_OPERATIONS.md)**: copy-paste 24/7 operator prompt, systemd unit, monitoring cadence, escalation rules and kill switch.

### Changed
- **Slimmer README**: now a product overview (what it does, why run it, benefits). Setup, CLI, strategy, risk limits and project layout live under `docs/`.
- **Faster indicators**: `calculate_bb`, `calculate_rsi`, `calculate_atr`, `calculate_adx`, and `calculate_confidence_score` are cached and invalidated on new price data.
- **Accurate ATR/ADX**: ATR and ADX now use Wilder smoothing and true high/low ranges instead of approximations, making regime detection materially more reliable.

## [2.1.0] - 2026-11-23

### Added
- **Profiles**: `--profile {default,balanced,aggressive}` plus `--aggressive` shorthand. Each profile tunes entries, exits, sizing, risk limits and regime handling.
- **`--fast`**: skip per-candle delays in simulation for rapid iteration.
- **`--dashboard`**: monitoring view combining portfolio state, trade attribution by regime/confidence, and last backtest.
- **Trade attribution logging**: every closed trade is appended to `data/trade_attribution.csv` with entry regime and confidence; `scripts/analyze_trades.py` summarizes by regime/confidence.
- **Short-side / bear-market handling**: in `TRENDING_DOWN` regimes the bot can short (upper BB, overbought RSI 60-80) when `enable_short_entries=True` (enabled in aggressive profile). Includes stop/TP/trailing/time exit and correct PnL sign.
- **Jupiter live trading**: `src/snail_scalp/jupiter.py` implements Jupiter Swap API v2 (`/order`, `/execute`), wired into the trader's live path. Signing via optional `solders`/`base58`; unsigned tx saved to `data/pending_swap.json` when no signer. Config URLs updated to current endpoints.
- **Confidence gating**: `use_confidence_gate` / `min_confidence_score` config to skip low-confidence entries.
- **Trending-down entry filter**: `skip_trending_down_entries` skips long entries in `TRENDING_DOWN` regimes (configurable per profile).
- **Deterministic backtests**: `BacktestEngine` now accepts a `seed` (default 42) and uses an isolated portfolio state file for reproducible results.
- **ATR uses true high/low**: `TechnicalIndicators.add_price`/`add_ohlcv` accept high/low; `calculate_atr` uses them when available, falling back to close-only.

### Changed
- Confidence score recalibrated: regime-weighted (TRENDING_UP +12, RANGING 0, TRENDING_DOWN -8, CHOPPY -15); RSI/volume/BB bonuses re-banded to avoid over-rewarding extreme oversold/high-volume setups.
- Trading window checks consistently use UTC.
- `Trade` dataclass now carries `side` (long/short) and `symbol` for attribution.
- Config keys aligned between `StrategyConfig`, `Trader`, `CLI`, screening bot, backtest engine, and real-data fetcher.

### Fixed
- `Trader.check_entry` overwrote the detected regime with `UNKNOWN` (trending-down filter branch).
- CLI/config mismatches (`dca_allocation`, `stop_loss_percent`) that broke `--simulate`, `--backtest`, `--real-data`.
- `regime_size_multiplier` was `None` at runtime.
- Backtest/portfolio state leakage across runs.

## [2.0.0] - 2026-02-26
 - 2026-02-26

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
